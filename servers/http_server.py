"""
独立 FastAPI 服务（不启动 ComfyUI 时单独用）。

启动方式（在 ComfyUI-AnimaTool 目录下）：
    uvicorn servers.http_server:app --host 127.0.0.1 --port 8000
"""
from __future__ import annotations

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


class GenerateRequest(BaseModel):
    # 允许任意字段（由 tool schema 约束；服务端只做最小校验）
    payload: Dict[str, Any] = Field(default_factory=dict)
    # 工作流选择：base / turbo / turbo_v1 / aesthetic_v1 / kira / kira_turbo / ultrareal / nova / miao / miao_turbo，缺省 base
    workflow: Optional[str] = Field(default=None)


class RerollRequest(BaseModel):
    source: str = Field(..., description="历史记录引用：'last' 或历史 ID")
    overrides: Dict[str, Any] = Field(default_factory=dict, description="覆盖参数")


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


_SCHEMA_DIR = _PARENT / "schemas"
_KNOWLEDGE_DIR = _PARENT / "knowledge"

# turbo_v1 / aesthetic_v1 共享同一套专家知识（质量前缀、默认负面、字段策略完全一致）
_SIMPLE_KNOWLEDGE = {
    "simple_expert": "simple_expert.md",
    "artist_list": "artist_list.md",
    "simple_examples": "simple_examples.md",
}

# kira / kira_turbo 共享同一套专家知识
_KIRA_KNOWLEDGE = {
    "kira_expert": "kira_expert.md",
    "artist_list": "artist_list.md",
    "kira_examples": "kira_examples.md",
}

# 工作流注册表：与 ComfyUI 路由（包 __init__.py）保持一致。
# 主 API（/schema、/knowledge、/generate）通过 workflow 参数分发，缺省 base。
WORKFLOWS = {
    "base": {
        "description": "Base 1.0：完整字段工作流（默认）",
        "schema": "tool_schema_universal.json",
        "knowledge": {
            "anima_expert": "anima_expert.md",
            "artist_list": "artist_list.md",
            "prompt_examples": "prompt_examples.md",
        },
    },
    "turbo": {
        "description": "Turbo 0.2（Legacy）：base UNET + turbo LoRA 快速生成（cfg=1, steps=10）",
        "schema": "tool_schema_turbo.json",
        "knowledge": {
            "turbo_expert": "turbo_expert.md",
            "artist_list": "artist_list.md",
            "turbo_examples": "turbo_examples.md",
        },
    },
    "turbo_v1": {
        "description": "Turbo 1.0：独立完整 UNET 快速生成（cfg 0.7-1, steps 8-12）",
        "schema": "tool_schema_simple.json",
        "knowledge": _SIMPLE_KNOWLEDGE,
    },
    "aesthetic_v1": {
        "description": "Aesthetic 1.0：高质量微调完整 UNET（cfg 3-8, steps 20-60）",
        "schema": "tool_schema_simple.json",
        "knowledge": _SIMPLE_KNOWLEDGE,
    },
    "kira": {
        "description": "Kira (Kirazuri Anima v4)：Anima 微调完整 UNET（cfg 4-5, steps 30-50, er_sde）",
        "schema": "tool_schema_simple.json",
        "knowledge": _KIRA_KNOWLEDGE,
    },
    "kira_turbo": {
        "description": "Kira Turbo：Kira + 8-step LoRA 快速生成（cfg=1, steps=8, 默认 1024x1024）",
        "schema": "tool_schema_kira_turbo.json",
        "knowledge": _KIRA_KNOWLEDGE,
    },
    "ultrareal": {
        "description": "UltraReal (UltraReal_FineTune_Anima_base1_v3)：Anima base1.0 真实系微调，写实照片风（@前缀标签+自然语言+@年份/score 后缀三段式）",
        "schema": "tool_schema_ultrareal.json",
        "knowledge": {
            "ultrareal_expert": "ultrareal_expert.md",
            "ultrareal_examples": "ultrareal_examples.md",
        },
    },
    "nova": {
        "description": "Nova (novaAnimeAM v4.0)：完整 UNET（cfg 4-6, steps 20-30, Euler a + normal），score_N 质量前缀",
        "schema": "tool_schema_simple.json",
        "knowledge": {
            "nova_expert": "nova_expert.md",
            "artist_list": "artist_list.md",
        },
    },
    "miao": {
        "description": "Miao (MiaomiaoHarem Anima 1.5)：完整 UNET（cfg 4-5, steps 30），score_N 质量前缀",
        "schema": "tool_schema_simple.json",
        "knowledge": {
            "miao_expert": "miao_expert.md",
            "artist_list": "artist_list.md",
        },
    },
    "miao_turbo": {
        "description": "Miao Turbo (MiaomiaoHarem Anima 8-step)：快速 UNET（cfg=1, steps 8-30 推荐 12）",
        "schema": "tool_schema_simple.json",
        "knowledge": {
            "miao_turbo_expert": "miao_turbo_expert.md",
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
        if workflow == "turbo":
            return executor.generate_turbo(payload)
        if workflow == "turbo_v1":
            return executor.generate_v2(payload, "turbo1.0")
        if workflow == "aesthetic_v1":
            return executor.generate_v2(payload, "aesthetic1.0")
        if workflow == "kira":
            return executor.generate_kira(payload)
        if workflow == "kira_turbo":
            return executor.generate_kira(payload, turbo=True)
        if workflow == "ultrareal":
            return executor.generate_ultrareal(payload)
        if workflow == "nova":
            return executor.generate_v2(payload, "nova")
        if workflow == "miao":
            return executor.generate_v2(payload, "miao")
        if workflow == "miao_turbo":
            return executor.generate_v2(payload, "miao_turbo")
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
                name: {"description": info["description"]}
                for name, info in WORKFLOWS.items()
            },
        }

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
