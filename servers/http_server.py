"""
独立 FastAPI 服务（不启动 ComfyUI 时单独用）。

启动方式（在 ComfyUI-AnimaTool 目录下）：
    uvicorn servers.http_server:app --host 127.0.0.1 --port 8000

图像反推（CPU 推理，不依赖 ComfyUI）：
    GET  /tagger/models   反推模型列表及下载状态
    POST /reverse_tag     图片反推 Danbooru 标签 + Anima 字段映射
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# 确保能 import 上层 executor
_PARENT = Path(__file__).resolve().parent.parent
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

from copy import deepcopy

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from executor import AnimaExecutor, AnimaToolConfig
from device_guard import get_guard
from executor.config import MOSS_CKPT_NAME, MOSS_CFG, MOSS_SAMPLER, MOSS_STEPS
from tagger.service import TaggerError, decode_image, list_models as list_tagger_models, tag_image

# MOSS-Image 独立接口的 schema / knowledge 文件名（与 ComfyUI 路由 __init__.py 保持一致）
MOSS_SCHEMA_FILE = "tool_schema_moss.json"
MOSS_KNOWLEDGE = {
    "moss_expert": "moss_expert.md",
    "moss_examples": "moss_examples.md",
}


class GenerateRequest(BaseModel):
    # 允许任意字段（由 tool schema 约束；服务端只做最小校验）
    payload: Dict[str, Any] = Field(default_factory=dict)
    # 工作流选择：base / turbo_v1 / fuse / fuse1.0 / aesthetic_v1 / ultrareal / silvermoon / silvermoon_turbo / anima29 / anima29_turbo / anima29_rdbt / aura / aura-speed / cyberreal，缺省 base
    workflow: Optional[str] = Field(default=None)


class RerollRequest(BaseModel):
    source: str = Field(..., description="历史记录引用：'last' 或历史 ID")
    overrides: Dict[str, Any] = Field(default_factory=dict, description="覆盖参数")


class ReverseTagRequest(BaseModel):
    image_base64: Optional[str] = Field(default=None, description="base64 图片（可带 data: 前缀）")
    image_path: Optional[str] = Field(default=None, description="本机图片路径（与 image_base64 二选一）")
    general_threshold: Optional[float] = Field(default=None, description="一般标签阈值（默认 0.35）")
    character_threshold: Optional[float] = Field(default=None, description="角色标签阈值（默认 0.75）")
    rating_threshold: Optional[float] = Field(default=None, description="分级标签阈值（默认 0.35）")
    max_tags: int = Field(default=40, description="Anima 字段映射中最多保留的一般标签数")


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


_SCHEMA_DIR = _PARENT / "schemas"
_KNOWLEDGE_DIR = _PARENT / "knowledge"

# aesthetic_v1 的专家知识
_SIMPLE_KNOWLEDGE = {
    "simple_expert": "simple_expert.md",
    "artist_list": "artist_list.md",
    "simple_examples": "simple_examples.md",
}

# turbo_v1 的专家知识
_TURBO_V1_KNOWLEDGE = {
    "turbo_v1_expert": "turbo_v1_expert.md",
    "artist_list": "artist_list.md",
    "turbo_v1_examples": "turbo_v1_examples.md",
}

# 工作流注册表：与 ComfyUI 路由（包 __init__.py）保持一致。
# 主 API（/schema、/knowledge、/generate）通过 workflow 参数分发，缺省 base。
WORKFLOWS = {
    "base": {
        "description": "AnimaTool 图像生成（Anima 系二次元插画）",
        "schema": "tool_schema_universal.json",
        "knowledge": {
            "anima_expert": "anima_expert.md",
            "artist_list": "artist_list.md",
            "prompt_examples": "prompt_examples.md",
        },
    },
    "turbo_v1": {
        "description": "AnimaTool 图像生成（Anima 系二次元插画，turbo 快速档）",
        "schema": "tool_schema_simple_turbo.json",
        "knowledge": _TURBO_V1_KNOWLEDGE,
    },
    "fuse": {
        "description": "AnimaTool 图像生成（Anima 系二次元插画，turbo 快速档）",
        "schema": "tool_schema_fuse.json",
        "knowledge": {
            "fuse_expert": "fuse_expert.md",
            "artist_list": "artist_list.md",
        },
    },
    "fuse1.0": {
        "description": "AnimaTool 图像生成（Anima 系二次元插画，turbo 快速档，已过期）",
        "schema": "tool_schema_fuse10.json",
        "knowledge": {
            "fuse_expert": "fuse10_expert.md",
            "artist_list": "artist_list.md",
        },
        "deprecated": True,
    },
    "aesthetic_v1": {
        "description": "AnimaTool 图像生成（Anima 系二次元插画）",
        "schema": "tool_schema_simple.json",
        "knowledge": _SIMPLE_KNOWLEDGE,
    },
    "ultrareal": {
        "description": "AnimaTool 图像生成（Anima 系写实照片风）",
        "schema": "tool_schema_ultrareal.json",
        "knowledge": {
            "ultrareal_expert": "ultrareal_expert.md",
            "ultrareal_examples": "ultrareal_examples.md",
        },
    },
    "silvermoon": {
        "description": "AnimaTool 图像生成（Anima 系二次元插画）",
        "schema": "tool_schema_silvermoon.json",
        "knowledge": {
            "silvermoon_expert": "silvermoon_expert.md",
            "silvermoon_examples": "silvermoon_examples.md",
            "artist_list": "artist_list.md",
        },
    },
    "silvermoon_turbo": {
        "description": "AnimaTool 图像生成（Anima 系二次元插画，turbo 快速档）",
        "schema": "tool_schema_silvermoon_turbo.json",
        "knowledge": {
            "silvermoon_expert": "silvermoon_turbo_expert.md",
            "silvermoon_examples": "silvermoon_examples.md",
            "artist_list": "artist_list.md",
        },
    },
    # Anima 2.9B 家族：anima29 / anima29_turbo / anima29_rdbt 各有独立 schema 与 knowledge 文件
    "anima29": {
        "description": "AnimaTool 图像生成（Anima 系二次元插画）",
        "schema": "tool_schema_anima29.json",
        "knowledge": {
            "anima29_expert": "anima29_expert.md",
            "artist_list": "artist_list.md",
        },
    },
    "anima29_turbo": {
        "description": "AnimaTool 图像生成（Anima 系二次元插画，turbo 快速档）",
        "schema": "tool_schema_anima29_turbo.json",
        "knowledge": {
            "anima29_turbo_expert": "anima29_turbo_expert.md",
            "artist_list": "artist_list.md",
        },
    },
    "anima29_rdbt": {
        "description": "AnimaTool 图像生成（Anima 系二次元插画，turbo 快速档）",
        "schema": "tool_schema_anima29_rdbt.json",
        "knowledge": {
            "anima29_rdbt_expert": "anima29_rdbt_expert.md",
            "artist_list": "artist_list.md",
        },
    },
    "aura": {
        "description": "AnimaTool 图像生成（Anima 系二次元插画）",
        "schema": "tool_schema_aura.json",
        "knowledge": {
            "aura_expert": "aura_expert.md",
            "artist_list": "artist_list.md",
        },
    },
    "aura-speed": {
        "description": "AnimaTool 图像生成（Anima 系二次元插画）",
        "schema": "tool_schema_aura_speed.json",
        "knowledge": {
            "aura_speed_expert": "aura_speed_expert.md",
            "artist_list": "artist_list.md",
        },
    },
    "cyberreal": {
        "description": "AnimaTool 图像生成（Anima 系写实插画）",
        "schema": "tool_schema_cyberreal.json",
        "knowledge": {
            "cyberreal_expert": "cyberreal_expert.md",
            "artist_list": "artist_list.md",
        },
    },
}

DEFAULT_WORKFLOW = "base"


def create_app() -> FastAPI:
    app = FastAPI(title="Anima Tool API", version="0.1.0")

    config = AnimaToolConfig()
    executor = AnimaExecutor(config=config)

    def _resolve_workflow(workflow: Optional[str]) -> str:
        wf = (workflow or DEFAULT_WORKFLOW).strip()
        if wf not in WORKFLOWS:
            raise HTTPException(
                status_code=400,
                detail=f"未知 workflow：{wf!r}，可选值：{list(WORKFLOWS)}（缺省 {DEFAULT_WORKFLOW}）",
            )
        return wf

    def _generate_dispatch(workflow: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if workflow == "turbo_v1":
            return executor.generate_v2(payload, "turbo1.0")
        if workflow == "fuse":
            return executor.generate_v2(payload, "fuse")
        if workflow == "fuse1.0":
            return executor.generate_v2(payload, "fuse1.0")
        if workflow == "aesthetic_v1":
            return executor.generate_v2(payload, "aesthetic1.0")
        if workflow == "ultrareal":
            return executor.generate_ultrareal(payload)
        if workflow == "silvermoon":
            return executor.generate_v2(payload, "silvermoon")
        if workflow == "silvermoon_turbo":
            return executor.generate_v2(payload, "silvermoon_turbo")
        if workflow == "anima29":
            return executor.generate_v2(payload, "anima29")
        if workflow == "anima29_turbo":
            return executor.generate_v2(payload, "anima29_turbo")
        if workflow == "anima29_rdbt":
            return executor.generate_v2(payload, "anima29_rdbt")
        if workflow == "aura":
            return executor.generate_v2(payload, "aura")
        if workflow == "aura-speed":
            return executor.generate_v2(payload, "aura-speed")
        if workflow == "cyberreal":
            return executor.generate_v2(payload, "cyberreal")
        return executor.generate(payload)

    @app.get("/health")
    def health() -> Dict[str, Any]:
        # 不做真实连通性探测（避免阻塞），只返回配置
        return {"status": "ok", "comfyui_url": config.comfyui_url}

    @app.get("/workflows")
    def workflows() -> Dict[str, Any]:
        return {
            "default": DEFAULT_WORKFLOW,
            "workflows": {
                name: {
                    "description": info["description"],
                    "deprecated": bool(info.get("deprecated")),
                    "endpoints": {
                        "generate": f"POST /generate（body 带 \"workflow\": \"{name}\"）",
                        "schema": f"GET /schema?workflow={name}",
                        "knowledge": f"GET /knowledge?workflow={name}",
                    },
                }
                for name, info in WORKFLOWS.items()
            },
        }

    # -------------------------
    # MOSS-Image 独立接口：/moss/*（Layout JSON 提示词，不进上面的 WORKFLOWS 注册表）
    # -------------------------
    @app.get("/moss/info")
    def moss_info() -> Dict[str, Any]:
        return {
            "workflow": "moss",
            "description": "MOSS-Image 图像生成（Layout JSON 提示词 + 中英文字面文字渲染，原生分格控制）",
            "model": {
                "checkpoint": MOSS_CKPT_NAME,
                "path": "models/checkpoints/",
            },
            "prompt_format": "layout_json",
            "sampling": {
                "steps": MOSS_STEPS,
                "cfg": MOSS_CFG,
                "sampler_name": MOSS_SAMPLER[0],
                "scheduler": MOSS_SAMPLER[1],
                "denoise": 1.0,
                "shift": 5,
            },
            "endpoints": {
                "generate": "POST /moss/generate",
                "schema": "GET /moss/schema",
                "knowledge": "GET /moss/knowledge",
            },
        }

    @app.get("/moss/schema")
    def moss_schema() -> JSONResponse:
        schema_path = _SCHEMA_DIR / MOSS_SCHEMA_FILE
        if not schema_path.exists():
            raise HTTPException(status_code=404, detail=f"schema not found: {MOSS_SCHEMA_FILE}")
        return JSONResponse(content=json.loads(schema_path.read_text(encoding="utf-8")))

    @app.get("/moss/knowledge")
    def moss_knowledge() -> Dict[str, Any]:
        return {key: _read_text(_KNOWLEDGE_DIR / filename) for key, filename in MOSS_KNOWLEDGE.items()}

    # -------------------------
    # XPU 设备守护：/device/health、/device/restart（DEVICE_LOST 时自动重启进程）
    # -------------------------
    guard = get_guard()

    @app.get("/device/health")
    def device_health() -> Dict[str, Any]:
        return guard.health()

    @app.post("/device/restart")
    def device_restart(body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        reason = str((body or {}).get("reason") or "manual restart via /device/restart")[:200]
        guard.force_restart(reason)
        return {"scheduled": True, "mode": guard.mode, "reason": reason}

    @app.post("/moss/generate")
    async def moss_generate(body: Dict[str, Any]) -> Dict[str, Any]:
        payload = body["payload"] if isinstance(body.get("payload"), dict) else body
        try:
            return await asyncio.to_thread(executor.generate_moss, payload)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.get("/schema")
    def schema(workflow: Optional[str] = Query(default=None)) -> JSONResponse:
        wf = _resolve_workflow(workflow)
        schema_path = _SCHEMA_DIR / WORKFLOWS[wf]["schema"]
        if not schema_path.exists():
            raise HTTPException(status_code=404, detail=f"schema not found: {wf}")
        obj = json.loads(schema_path.read_text(encoding="utf-8"))
        return JSONResponse(content=obj)

    @app.get("/knowledge")
    def knowledge(workflow: Optional[str] = Query(default=None)) -> Dict[str, Any]:
        wf = _resolve_workflow(workflow)
        return {
            key: _read_text(_KNOWLEDGE_DIR / filename)
            for key, filename in WORKFLOWS[wf]["knowledge"].items()
        }

    def _generate_with_repeat(workflow: str, payload: Dict[str, Any]) -> list[Dict[str, Any]]:
        """执行生成（支持 repeat 多次独立 queue 提交），返回结果列表。"""
        repeat = max(1, int(payload.pop("repeat", 1) or 1))
        results = []
        for _ in range(repeat):
            run_params = deepcopy(payload)
            if "seed" not in payload or payload.get("seed") is None:
                run_params.pop("seed", None)
            results.append(_generate_dispatch(workflow, run_params))
        return results

    @app.post("/generate")
    def generate(
        req: GenerateRequest,
        workflow: Optional[str] = Query(default=None),
    ) -> Dict[str, Any]:
        # query 参数优先，其次 body 中的 workflow 字段，缺省 base
        wf = _resolve_workflow(workflow or req.workflow)
        payload = req.payload or {}
        payload.pop("workflow", None)  # workflow 是路由参数，不属于生成 payload
        try:
            results = _generate_with_repeat(wf, payload)
            # 单次兼容旧接口，多次返回数组
            if len(results) == 1:
                return results[0]
            return {"success": True, "results": results}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.get("/history")
    def history(limit: int = Query(default=5, ge=1, le=50)) -> Dict[str, Any]:
        records = executor.history.list_recent(limit)
        return {
            "count": len(records),
            "records": [r.to_dict() for r in records],
        }

    @app.get("/tagger/models")
    def tagger_models() -> Dict[str, Any]:
        return list_tagger_models()

    @app.post("/reverse_tag")
    async def reverse_tag(req: ReverseTagRequest) -> Dict[str, Any]:
        try:
            image = decode_image({k: v for k, v in {
                "image_base64": req.image_base64, "image_path": req.image_path,
            }.items() if v is not None})
            result = await asyncio.to_thread(
                tag_image, image,
                general_threshold=req.general_threshold,
                character_threshold=req.character_threshold,
                rating_threshold=req.rating_threshold,
                max_tags=req.max_tags,
            )
            return result
        except TaggerError as e:
            raise HTTPException(status_code=e.status, detail=e.message) from e
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.post("/reroll")
    def reroll(req: RerollRequest) -> Dict[str, Any]:
        record = executor.history.get(req.source)
        if record is None:
            raise HTTPException(status_code=404, detail=f"未找到历史记录：{req.source}")

        merged = deepcopy(record.params)
        overrides = {k: v for k, v in (req.overrides or {}).items() if v is not None}
        merged.update(overrides)

        # seed 默认行为：未显式指定则自动随机
        if "seed" not in req.overrides or req.overrides.get("seed") is None:
            merged.pop("seed", None)

        try:
            results = _generate_with_repeat(DEFAULT_WORKFLOW, merged)
            if len(results) == 1:
                return results[0]
            return {"success": True, "results": results}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    return app


app = create_app()
