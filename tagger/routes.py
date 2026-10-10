"""图像反推接口（aiohttp 路由，随 ComfyUI PromptServer 注册）：

  GET  /anima/tagger/models    反推模型信息及下载状态
  POST /anima/reverse_tag      反推图片 → Danbooru 标签 + Anima 字段映射
                               body: {image_base64 | image_path,
                                      general_threshold?, character_threshold?,
                                      rating_threshold?, max_tags?}

模型固定为 wd-eva02-tagger-2026-canary，本地推理（XPU 可用时自动加速，
否则 CPU 单张约 3.5s），全程不经过 ComfyUI 后端。
"""
from __future__ import annotations

import asyncio
import json

from aiohttp import web

from .service import TaggerError, decode_image, list_models, tag_image


def _dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)


def _json(obj, status: int = 200) -> web.Response:
    return web.json_response(obj, status=status, dumps=_dumps)


def register_tagger_routes(routes) -> None:
    """把反推接口注册到 aiohttp RouteTableDef（ComfyUI 的 PromptServer.instance.routes）"""

    @routes.get("/anima/tagger/models")
    async def tagger_models(request):
        return _json(list_models())

    @routes.post("/anima/reverse_tag")
    async def reverse_tag(request):
        try:
            try:
                body = await request.json()
            except Exception as e:
                raise TaggerError(f"JSON parse error: {e}")
            if not isinstance(body, dict):
                raise TaggerError("请求体必须是 JSON 对象")
            image = decode_image(body)
            # 推理阻塞 CPU，放到线程池避免卡住 ComfyUI 事件循环
            result = await asyncio.to_thread(
                tag_image, image,
                general_threshold=body.get("general_threshold"),
                character_threshold=body.get("character_threshold"),
                rating_threshold=body.get("rating_threshold"),
                max_tags=int(body.get("max_tags") or 40),
            )
            return _json(result)
        except TaggerError as e:
            return _json({"success": False, "error": e.message}, status=e.status)
        except Exception as e:
            return _json({"success": False, "error": str(e)}, status=500)
