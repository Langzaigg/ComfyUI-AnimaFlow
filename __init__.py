"""
ComfyUI-AnimaTool：随 ComfyUI 启动的 Anima Tool Use API

主 API（推荐）：
  GET  /anima/workflows        - 列出所有可用工作流
  GET  /anima/schema           - 返回 Tool Schema（?workflow= 选择工作流，缺省 base）
  GET  /anima/knowledge        - 返回专家知识（?workflow= 选择工作流，缺省 base）
  POST /anima/generate         - 执行生成（body/query 中 workflow 选择工作流，缺省 base）

兼容性接口（保持不变，等价于 workflow 参数的固定写法）：
  POST /anima/generate_turbo   - Turbo 0.2 快速生成（cfg=1, steps=10, 内置 turbo LoRA）
  GET  /anima/schema_turbo     - 返回 Turbo 0.2 Tool Schema
  GET  /anima/knowledge_turbo  - 返回 Turbo 0.2 专家知识
  POST /anima/generate_turbo_v1 - Anima Turbo v1.0 生成
  POST /anima/generate_aesthetic_v1 - Anima Aesthetic v1.0 生成
  GET  /anima/schema_turbo_v1  - 返回 Turbo v1.0 Schema
  GET  /anima/schema_aesthetic_v1 - 返回 Aesthetic v1.0 Schema
  GET  /anima/knowledge_new_models - 返回新模型共享专家知识
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from aiohttp import web

from .executor import AnimaExecutor, AnimaToolConfig


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

# turbo_v1 的专家知识（cfg=1：负面不生效，示例不含 neg）
_TURBO_V1_KNOWLEDGE = {
    "turbo_v1_expert": "turbo_v1_expert.md",
    "artist_list": "artist_list.md",
    "turbo_v1_examples": "turbo_v1_examples.md",
}

# kira 的专家知识
_KIRA_KNOWLEDGE = {
    "kira_expert": "kira_expert.md",
    "artist_list": "artist_list.md",
    "kira_examples": "kira_examples.md",
}

# kira_turbo 的专家知识（cfg=1：负面不生效；示例与 kira 共用）
_KIRA_TURBO_KNOWLEDGE = {
    "kira_turbo_expert": "kira_turbo_expert.md",
    "artist_list": "artist_list.md",
    "kira_examples": "kira_examples.md",
}

# 工作流注册表：主 API 通过 workflow 参数分发，缺省为 base。
# 每个工作流声明自己的 schema 文件、知识文件与生成方式。
# 各工作流的 schema/knowledge 按"唯一工作流"视角编写：规则有出入时拆成独立文件，
# 不在共享文件的描述里为某个工作流写条件特例。
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
        "deprecated": True,
        "schema": "tool_schema_turbo.json",
        "knowledge": {
            "turbo_expert": "turbo_expert.md",
            "artist_list": "artist_list.md",
            "turbo_examples": "turbo_examples.md",
        },
    },
    "turbo_v1": {
        "description": "Turbo 1.0：独立完整 UNET 快速生成（cfg 0.7-1, steps 8-12）",
        "schema": "tool_schema_simple_turbo.json",
        "knowledge": _TURBO_V1_KNOWLEDGE,
    },
    "aesthetic_v1": {
        "description": "Aesthetic 1.0：高质量微调完整 UNET（cfg 3-8, steps 20-60）",
        "schema": "tool_schema_simple.json",
        "knowledge": _SIMPLE_KNOWLEDGE,
    },
    "kira": {
        "description": "Kira (Kirazuri Anima v4)：Anima 微调完整 UNET（cfg 4-5, steps 30-50, er_sde）",
        "deprecated": True,
        "schema": "tool_schema_simple.json",
        "knowledge": _KIRA_KNOWLEDGE,
    },
    "kira_turbo": {
        "description": "Kira Turbo：Kira + 8-step LoRA 快速生成（cfg=1, steps=8, 默认 1024x1024）",
        "deprecated": True,
        "schema": "tool_schema_kira_turbo.json",
        "knowledge": _KIRA_TURBO_KNOWLEDGE,
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
        "deprecated": True,
        "schema": "tool_schema_simple.json",
        "knowledge": {
            "nova_expert": "nova_expert.md",
            "artist_list": "artist_list.md",
        },
    },
    "miao": {
        "description": "Miao (MiaomiaoHarem Anima 1.5)：完整 UNET（cfg 4-5, steps 30），score_N 质量前缀",
        "deprecated": True,
        "schema": "tool_schema_simple.json",
        "knowledge": {
            "miao_expert": "miao_expert.md",
            "artist_list": "artist_list.md",
        },
    },
    "miao_turbo": {
        "description": "Miao Turbo (MiaomiaoHarem Anima 8-step)：快速 UNET（cfg=1, steps 8-30 推荐 12）",
        "deprecated": True,
        "schema": "tool_schema_simple_turbo.json",
        "knowledge": {
            "miao_turbo_expert": "miao_turbo_expert.md",
            "artist_list": "artist_list.md",
        },
    },
    "silvermoon": {
        "description": "Silvermoon (silvermoonmixAnima_v23)：完整 UNET（cfg 4-5, steps 20-30 默认 20, Euler a + normal）",
        "schema": "tool_schema_silvermoon.json",
        "knowledge": {
            "silvermoon_expert": "silvermoon_expert.md",
            "silvermoon_examples": "silvermoon_examples.md",
            "artist_list": "artist_list.md",
        },
    },
    "anima29": {
        "description": "Anima 2.9B v1.0：base 层扩展微调完整 UNET（cfg 3.5-5, steps 28-50 默认 30, Euler + sgm_uniform）",
        "schema": "tool_schema_anima29.json",
        "knowledge": {
            "anima29_expert": "anima29_expert.md",
            "artist_list": "artist_list.md",
        },
    },
    "anima29_turbo": {
        "description": "Anima 2.9B Turbo：Anima 2.9B + Turbo-BF16 LoRA 快速生成（cfg=1, steps 8-12 默认 8）",
        "schema": "tool_schema_anima29_turbo.json",
        "knowledge": {
            "anima29_turbo_expert": "anima29_turbo_expert.md",
            "artist_list": "artist_list.md",
        },
    },
    "anima29_rdbt": {
        "description": "Anima 2.9B + rdbt v2.0 双 LoRA（base→distilled addon，cfg=1, steps 默认 16）：实测 16 步追平/反超 anima29 30 步，anima29 系性价比最优",
        "schema": "tool_schema_anima29_rdbt.json",
        "knowledge": {
            "anima29_rdbt_expert": "anima29_rdbt_expert.md",
            "artist_list": "artist_list.md",
        },
    },
    "aura": {
        "description": "AuraAnima 2.9B Int8 量化·精度重视（er_sde+beta, steps 默认 12, cfg 4-5 默认 5）：质量/速度与 BF16 anima29 同档且显存约减半；风格标签默认 photo real，可选 anime color / real skin",
        "schema": "tool_schema_aura.json",
        "knowledge": {
            "aura_expert": "aura_expert.md",
            "artist_list": "artist_list.md",
        },
    },
    "aura-speed": {
        "description": "AuraAnima 2.9B Int8 量化·速度重视（euler+simple, steps 默认 10, cfg 4-5 默认 5）：批量/迭代/简单场景/复杂构图用；风格标签默认 photo real，可选 anime color / real skin",
        "schema": "tool_schema_aura_speed.json",
        "knowledge": {
            "aura_speed_expert": "aura_speed_expert.md",
            "artist_list": "artist_list.md",
        },
    },
}

DEFAULT_WORKFLOW = "base"


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
    if workflow == "silvermoon":
        return executor.generate_v2(payload, "silvermoon")
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
    # 兼容性接口：等价于 workflow 参数的固定写法，保持不变
    # -------------------------
    @routes.get("/anima/schema_turbo")
    async def anima_schema_turbo(request):
        return _schema_response("turbo")

    @routes.get("/anima/knowledge_turbo")
    async def anima_knowledge_turbo(request):
        return _knowledge_response("turbo")

    @routes.post("/anima/generate_turbo")
    async def anima_generate_turbo(request):
        try:
            body = await request.json()
        except Exception as e:
            return web.json_response({"error": f"JSON parse error: {e}"}, status=400)

        if "payload" in body and isinstance(body["payload"], dict):
            payload = body["payload"]
        else:
            payload = body

        try:
            result = await asyncio.to_thread(executor.generate_turbo, payload)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

        return web.json_response(result)

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

    print("[ComfyUI-AnimaTool] Routes registered: /anima/health, /anima/workflows, /anima/schema, /anima/knowledge, /anima/generate (主 API，支持 workflow 参数，缺省 base), /anima/schema_turbo, /anima/knowledge_turbo, /anima/generate_turbo, /anima/generate_turbo_v1, /anima/generate_aesthetic_v1, /anima/schema_turbo_v1, /anima/schema_aesthetic_v1, /anima/knowledge_new_models (兼容接口)")


# ComfyUI 加载 custom_nodes 时会 import 这个模块
# 我们在模块加载时注册路由
_setup_routes()

# ComfyUI 要求导出 NODE_CLASS_MAPPINGS（即使为空也要有）
NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}
