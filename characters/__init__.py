"""
人设（角色）库：随 ComfyUI 启动的 /anima/characters 接口，供 Web 前端、机器人等下游共用。

- store.py：JSON 文件存储（data/characters.json，可用 ANIMATOOL_CHARACTERS_FILE 覆盖）
- routes.py：aiohttp 路由注册
"""
from .store import (
    CHARACTER_JSON_SCHEMA,
    SCHEMA_VERSION,
    CharacterError,
    CharacterStore,
    default_characters_file,
    match_characters,
    normalize_tags,
)

__all__ = [
    "CHARACTER_JSON_SCHEMA",
    "SCHEMA_VERSION",
    "CharacterError",
    "CharacterStore",
    "default_characters_file",
    "match_characters",
    "normalize_tags",
]
