"""
ComfyUI-AnimaTool：随 ComfyUI 启动的 Anima Tool Use API

主 API（推荐）：
  GET  /anima/workflows        - 列出所有可用工作流
  GET  /anima/schema           - 返回 Tool Schema（?workflow= 选择工作流，缺省 base）
  GET  /anima/knowledge        - 返回专家知识（?workflow= 选择工作流，缺省 base）
  POST /anima/generate         - 执行生成（body/query 中 workflow 选择工作流，缺省 base）

兼容性接口（保持不变，等价于 workflow 参数的固定写法）：
  POST /anima/generate_turbo_v1 - Anima Turbo v1.0 生成
  POST /anima/generate_aesthetic_v1 - Anima Aesthetic v1.0 生成
  GET  /anima/schema_turbo_v1  - 返回 Turbo v1.0 Schema
  GET  /anima/schema_aesthetic_v1 - 返回 Aesthetic v1.0 Schema
  GET  /anima/knowledge_new_models - 返回新模型共享专家知识

人设库（characters/，数据存 data/characters.json）：
  GET    /anima/characters          - 人设列表（?q= / ?label= / ?nsfw=0，ETag 缓存校验）
  POST   /anima/characters          - 新建人设
  GET    /anima/characters/schema   - 人设记录 JSON Schema
  POST   /anima/characters/match    - 文本按名称/别名匹配人设
  POST   /anima/characters/import   - 批量导入（merge / replace）
  GET|PUT|PATCH|DELETE /anima/characters/{id} - 单个人设读取/部分更新/删除

图像反推（tagger/，CPU 推理，不经过 ComfyUI 后端）：
  GET  /anima/tagger/models    - 反推模型列表及下载状态
  POST /anima/reverse_tag      - 图片反推 Danbooru 标签 + Anima 字段映射
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from aiohttp import web

from .executor import AnimaExecutor, AnimaToolConfig
from .characters import CharacterStore
from .characters.routes import register_character_routes
from .tagger.routes import register_tagger_routes


# ComfyUI 的 PromptServer（延迟导入，避免 import 顺序问题）
def _get_prompt_server():
    try:
        from server import PromptServer
        return PromptServer.instance
    except Exception:
        return None


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


_TOOL_ROOT = Path(__file__).resolve().parent
_SCHEMA_DIR = _TOOL_ROOT / "schemas"
_KNOWLEDGE_DIR = _TOOL_ROOT / "knowledge"

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

# 工作流注册表：主 API 通过 workflow 参数分发，缺省为 base。
# 每个工作流声明自己的 schema 文件、知识文件与生成方式。
# 各工作流的 schema/knowledge 按"唯一工作流"视角编写：规则有出入时拆成独立文件，
# 不在共享文件的描述里为某个工作流写条件特例。
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

# MOSS-Image 独立接口（/moss/*）：刻意不进上面的 WORKFLOWS 注册表。
# 它的提示词是 Layout JSON（summary + items + 框位），不是 tag 系字段与拼接规则，
# 所以 schema / knowledge / 生成入口都自成一套，不走 /anima/* 的 workflow 统一分发。
_MOSS_SCHEMA_FILE = "tool_schema_moss.json"
_MOSS_KNOWLEDGE = {
    "moss_expert": "moss_expert.md",
    "moss_examples": "moss_examples.md",
}


def _schema_response(workflow: str) -> web.Response:
    schema_path = _SCHEMA_DIR / WORKFLOWS[workflow]["schema"]
    if not schema_path.exists():
        return web.json_response({"error": f"schema not found: {workflow}"}, status=404)
    obj = json.loads(schema_path.read_text(encoding="utf-8"))
    return web.json_response(obj)


def _knowledge_response(workflow: str) -> web.Response:
    return web.json_response({
        key: _read_text(_KNOWLEDGE_DIR / filename)
        for key, filename in WORKFLOWS[workflow]["knowledge"].items()
    })


def _generate_dispatch(executor: AnimaExecutor, workflow: str, payload: dict):
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


def _setup_routes():
    server = _get_prompt_server()
    if server is None:
        print("[ComfyUI-AnimaTool] PromptServer not available, skip route registration.")
        return

    routes = server.routes

    # 配置 & 执行器
    config = AnimaToolConfig()
    executor = AnimaExecutor(config=config)

    def _resolve_workflow(request, body: dict | None = None):
        """解析 workflow 参数：query 优先，其次 body 顶层，缺省 base。非法值返回 None。"""
        workflow = request.query.get("workflow")
        if not workflow and isinstance(body, dict):
            workflow = body.get("workflow")
        workflow = (workflow or DEFAULT_WORKFLOW).strip()
        return workflow if workflow in WORKFLOWS else None

    def _unknown_workflow_response(request, body: dict | None = None) -> web.Response:
        return web.json_response(
            {"error": f"未知 workflow，可选值：{list(WORKFLOWS)}（缺省 {DEFAULT_WORKFLOW}）"},
            status=400,
        )

    # -------------------------
    # GET /anima/health
    # -------------------------
    @routes.get("/anima/health")
    async def anima_health(request):
        return web.json_response({
            "status": "ok",
            "comfyui_url": config.comfyui_url,
            "tool_root": str(_TOOL_ROOT),
        })

    # -------------------------
    # GET /anima/workflows：列出所有可用工作流（含弃用状态与各工作流相关接口）
    # -------------------------
    @routes.get("/anima/workflows")
    async def anima_workflows(request):
        return web.json_response({
            "default": DEFAULT_WORKFLOW,
            "workflows": {
                name: {
                    "description": info["description"],
                    "deprecated": bool(info.get("deprecated")),
                    "endpoints": {
                        "generate": f"POST /anima/generate（body 带 \"workflow\": \"{name}\"）",
                        "schema": f"GET /anima/schema?workflow={name}",
                        "knowledge": f"GET /anima/knowledge?workflow={name}",
                    },
                }
                for name, info in WORKFLOWS.items()
            },
        })

    # -------------------------
    # GET /anima/schema（主 API，?workflow= 选择，缺省 base）
    # -------------------------
    @routes.get("/anima/schema")
    async def anima_schema(request):
        workflow = _resolve_workflow(request)
        if workflow is None:
            return _unknown_workflow_response(request)
        return _schema_response(workflow)

    # -------------------------
    # GET /anima/knowledge（主 API，?workflow= 选择，缺省 base）
    # -------------------------
    @routes.get("/anima/knowledge")
    async def anima_knowledge(request):
        workflow = _resolve_workflow(request)
        if workflow is None:
            return _unknown_workflow_response(request)
        return _knowledge_response(workflow)

    # -------------------------
    # POST /anima/generate（主 API，workflow 选择，缺省 base）
    # -------------------------
    @routes.post("/anima/generate")
    async def anima_generate(request):
        try:
            body = await request.json()
        except Exception as e:
            return web.json_response({"error": f"JSON parse error: {e}"}, status=400)

        # 兼容两种格式：直接传 JSON，或 {"payload": {...}}
        if "payload" in body and isinstance(body["payload"], dict):
            payload = body["payload"]
        else:
            payload = body

        workflow = _resolve_workflow(request, body)
        if workflow is None:
            return _unknown_workflow_response(request, body)
        # workflow 是路由参数，不属于生成 payload
        payload.pop("workflow", None)

        try:
            # 在线程池中执行同步阻塞操作，避免阻塞 aiohttp 事件循环
            result = await asyncio.to_thread(_generate_dispatch, executor, workflow, payload)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

        return web.json_response(result)

    # -------------------------
    # MOSS-Image 独立接口：/moss/*（Layout JSON 提示词，与 /anima/* 的 workflow 统一分发无关）
    # -------------------------
    @routes.get("/moss/info")
    async def moss_info(request):
        return web.json_response({
            "workflow": "moss",
            "description": "MOSS-Image 图像生成（Layout JSON 提示词 + 中英文字面文字渲染，原生分格控制）",
            "model": {
                "checkpoint": "moss_image_sft_turbo_int8_convrot_aio.safetensors",
                "path": "models/checkpoints/",
            },
            "prompt_format": "layout_json",
            "sampling": {
                "steps": 8,
                "cfg": 1.0,
                "sampler_name": "euler",
                "scheduler": "simple",
                "denoise": 1.0,
                "shift": 5,
            },
            "reference": {
                "fields": ["reference_image", "reference_images"],
                "mode": "text_encoder_vision",
                "note": "参考图送 TE 视觉分支（TextEncodeMingImageEdit + Picture N 占位符），每张缩到约 384²，不带 VAE latent，最多 4 张",
            },
            "endpoints": {
                "generate": "POST /moss/generate",
                "schema": "GET /moss/schema",
                "knowledge": "GET /moss/knowledge",
            },
        })

    @routes.get("/moss/schema")
    async def moss_schema(request):
        schema_path = _SCHEMA_DIR / _MOSS_SCHEMA_FILE
        if not schema_path.exists():
            return web.json_response({"error": f"schema not found: {_MOSS_SCHEMA_FILE}"}, status=404)
        return web.json_response(json.loads(schema_path.read_text(encoding="utf-8")))

    @routes.get("/moss/knowledge")
    async def moss_knowledge(request):
        return web.json_response({
            key: _read_text(_KNOWLEDGE_DIR / filename)
            for key, filename in _MOSS_KNOWLEDGE.items()
        })

    @routes.post("/moss/generate")
    async def moss_generate(request):
        try:
            body = await request.json()
        except Exception as e:
            return web.json_response({"error": f"JSON parse error: {e}"}, status=400)

        # 与 /anima/generate 一样兼容 {"payload": {...}} 包装
        payload = body["payload"] if isinstance(body.get("payload"), dict) else body
        try:
            result = await asyncio.to_thread(executor.generate_moss, payload)
        except ValueError as e:
            # Layout 草稿不合法（label/bbox/画布越界）属于调用方问题
            return web.json_response({"error": str(e)}, status=400)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

        return web.json_response(result)

    # -------------------------
    # 兼容性接口：等价于 workflow 参数的固定写法，保持不变
    # -------------------------
    @routes.post("/anima/generate_turbo_v1")
    async def anima_generate_turbo_v1(request):
        try:
            body = await request.json()
        except Exception as e:
            return web.json_response({"error": f"JSON parse error: {e}"}, status=400)

        if "payload" in body and isinstance(body["payload"], dict):
            payload = body["payload"]
        else:
            payload = body

        try:
            result = await asyncio.to_thread(executor.generate_v2, payload, "turbo1.0")
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

        return web.json_response(result)

    @routes.post("/anima/generate_aesthetic_v1")
    async def anima_generate_aesthetic_v1(request):
        try:
            body = await request.json()
        except Exception as e:
            return web.json_response({"error": f"JSON parse error: {e}"}, status=400)

        if "payload" in body and isinstance(body["payload"], dict):
            payload = body["payload"]
        else:
            payload = body

        try:
            result = await asyncio.to_thread(executor.generate_v2, payload, "aesthetic1.0")
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

        return web.json_response(result)

    @routes.get("/anima/schema_turbo_v1")
    async def anima_schema_turbo_v1(request):
        return _schema_response("turbo_v1")

    @routes.get("/anima/schema_aesthetic_v1")
    async def anima_schema_aesthetic_v1(request):
        return _schema_response("aesthetic_v1")

    @routes.get("/anima/knowledge_new_models")
    async def anima_knowledge_new_models(request):
        return _knowledge_response("turbo_v1")

    # -------------------------
    # 人设库：/anima/characters*（Web 前端、机器人等下游共用）
    # -------------------------
    character_store = CharacterStore()
    register_character_routes(routes, character_store)

    # -------------------------
    # 图像反推：/anima/reverse_tag（CPU 推理，不经过 ComfyUI 后端）
    # -------------------------
    register_tagger_routes(routes)

    print("[ComfyUI-AnimaTool] Routes registered: /anima/health, /anima/workflows, /anima/schema, /anima/knowledge, /anima/generate (主 API，支持 workflow 参数，缺省 base), /anima/generate_turbo_v1, /anima/generate_aesthetic_v1, /anima/schema_turbo_v1, /anima/schema_aesthetic_v1, /anima/knowledge_new_models (兼容接口), /anima/characters* (人设库，数据 " + str(character_store.path) + "), /anima/tagger/models, /anima/reverse_tag (图像反推), /moss/info, /moss/schema, /moss/knowledge, /moss/generate (MOSS-Image 独立接口)")


# ComfyUI 加载 custom_nodes 时会 import 这个模块
# 我们在模块加载时注册路由
_setup_routes()

# ComfyUI 要求导出 NODE_CLASS_MAPPINGS（即使为空也要有）
NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}
