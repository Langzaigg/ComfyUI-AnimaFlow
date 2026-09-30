"""
人设接口（aiohttp 路由，随 ComfyUI PromptServer 注册）：

  GET    /anima/characters             列表（?q= 关键词，?label= 分组，?nsfw=0 排除 NSFW 人设）；
                                       响应带 ETag（按 revision），支持 If-None-Match → 304
  POST   /anima/characters             新建（201；重名 409）
  GET    /anima/characters/schema      人设记录的 JSON Schema
  POST   /anima/characters/match       文本匹配 {text, limit?} → {matches: [{id, name, matched, character}]}
  POST   /anima/characters/import      批量导入 {characters: [...], mode: merge|replace, confirm_replace?}
  GET    /anima/characters/{id}        单个人设
  PUT    /anima/characters/{id}        部分更新（只改传了的字段；PATCH 同义）
  DELETE /anima/characters/{id}        删除

静态段（schema/match/import）必须先于 /{id} 注册；id 也禁止使用这些保留字。
"""
from __future__ import annotations

import json

from aiohttp import web

from .store import CHARACTER_JSON_SCHEMA, CharacterError, CharacterStore


def _dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)


def _json(obj, status: int = 200, headers=None) -> web.Response:
    return web.json_response(obj, status=status, headers=headers, dumps=_dumps)


def _error(e: CharacterError) -> web.Response:
    return _json({"error": e.message}, status=e.status)


async def _read_json(request) -> dict:
    try:
        body = await request.json()
    except Exception as e:
        raise CharacterError(f"JSON parse error: {e}")
    if not isinstance(body, dict):
        raise CharacterError("请求体必须是 JSON 对象")
    return body


def register_character_routes(routes, store: CharacterStore) -> None:
    """把人设接口注册到 aiohttp RouteTableDef（ComfyUI 的 PromptServer.instance.routes）"""

    @routes.get("/anima/characters")
    async def characters_list(request):
        try:
            etag = f'"chars-{store.revision}"'
            if request.headers.get("If-None-Match") == etag:
                return web.Response(status=304, headers={"ETag": etag})
            snap = store.snapshot(
                q=request.query.get("q", ""),
                label=request.query.get("label", ""),
                include_nsfw=request.query.get("nsfw", "1") != "0",
            )
            return _json(snap, headers={"ETag": f'"chars-{snap["revision"]}"'})
        except CharacterError as e:
            return _error(e)

    @routes.post("/anima/characters")
    async def characters_create(request):
        try:
            body = await _read_json(request)
            rec = store.create(body, source=str(body.get("source") or "api"))
            return _json({"ok": True, "character": rec}, status=201)
        except CharacterError as e:
            return _error(e)

    @routes.get("/anima/characters/schema")
    async def characters_schema(request):
        return _json(CHARACTER_JSON_SCHEMA)

    @routes.post("/anima/characters/match")
    async def characters_match(request):
        try:
            body = await _read_json(request)
            try:
                limit = int(body.get("limit") or 10)
            except (TypeError, ValueError):
                limit = 10
            matches = store.match(str(body.get("text") or ""), limit=limit)
            return _json({"matches": [
                {"id": m["character"]["id"], "name": m["character"]["name"],
                 "matched": m["matched"], "character": m["character"]}
                for m in matches
            ]})
        except CharacterError as e:
            return _error(e)

    @routes.post("/anima/characters/import")
    async def characters_import(request):
        try:
            body = await _read_json(request)
            mode = str(body.get("mode") or "merge")
            if mode == "replace" and not body.get("confirm_replace"):
                raise CharacterError("replace 会清空现有人设，需同时传 confirm_replace: true")
            result = store.import_many(body.get("characters"), mode=mode,
                                       source=str(body.get("source") or "import"))
            return _json({"ok": True, **result})
        except CharacterError as e:
            return _error(e)

    @routes.get("/anima/characters/{char_id}")
    async def characters_get(request):
        try:
            return _json(store.get(request.match_info["char_id"]))
        except CharacterError as e:
            return _error(e)

    async def _update(request):
        try:
            body = await _read_json(request)
            rec = store.update(request.match_info["char_id"], body)
            return _json({"ok": True, "character": rec})
        except CharacterError as e:
            return _error(e)

    routes.put("/anima/characters/{char_id}")(_update)
    routes.patch("/anima/characters/{char_id}")(_update)

    @routes.delete("/anima/characters/{char_id}")
    async def characters_delete(request):
        try:
            rec = store.delete(request.match_info["char_id"])
            return _json({"ok": True, "id": rec["id"]})
        except CharacterError as e:
            return _error(e)
