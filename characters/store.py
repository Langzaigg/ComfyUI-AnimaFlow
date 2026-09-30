"""
人设（角色）存储：单个 JSON 文件 + 进程内锁 + 原子写。

文件结构（schema_version = 1）：
{
  "schema_version": 1,
  "revision": 12,                 # 每次写入 +1，下游据此做缓存校验（HTTP ETag）
  "updated_at": 1790700000.0,     # 最近一次写入时间（epoch 秒）
  "characters": [ {人设记录}, ... ]  # 新建的插在最前
}

人设记录字段见 CHARACTER_JSON_SCHEMA（GET /anima/characters/schema 原样返回）。
设计要点：
- 画图只用外观字段：tag_name / series / count / tags / outfits / artist / notes；
  personality 仅供对话类下游（如 QQ 机器人）参考，画图不使用。
- 基础 tags 只写本体特征（发型/瞳色/兽耳等），服装放 outfits（造型），
  组合时 = 基础 tags + 选中造型 tags；没有 outfits 时 tags 自带服装亦可。
- 文件被外部改写（离线迁移/手工编辑）时按 mtime 自动重新加载，无需重启 ComfyUI。
"""
from __future__ import annotations

import copy
import json
import os
import re
import shutil
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCHEMA_VERSION = 1

# 字符串字段 -> 最大长度
_STR_FIELDS = {
    "name": 64,
    "tag_name": 200,
    "series": 200,
    "count": 32,
    "tags": 4000,
    "description": 4000,
    "artist": 200,
    "notes": 2000,
    "personality": 2000,
    "source": 32,
}
# 逗号分隔的标签字段：保存时统一规范成 "a, b, c"（去空项、去重、去零宽字符）
_TAG_FIELDS = {"tags"}
# 字符串数组字段 -> (最多条数, 单条最大长度)
_LIST_FIELDS = {
    "aliases": (16, 64),
    "labels": (16, 32),
}
_MAX_OUTFITS = 12
_MAX_EXTRA_BYTES = 16 * 1024
_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
# 与路由的静态段冲突的 id（/anima/characters/schema 等）
_RESERVED_IDS = {"schema", "match", "import"}
_ZERO_WIDTH_RE = re.compile("[​-‏⁠﻿]")
_ASCII_ALNUM = re.compile(r"[A-Za-z0-9]")

CHARACTER_JSON_SCHEMA: Dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "AnimaTool Character",
    "description": "人设（角色）记录。画图只用外观字段；personality 仅供对话类下游参考。"
                   "组合提示词时 = count + tag_name + series + tags + 选中造型的 tags，画师单独放 artist。",
    "type": "object",
    "required": ["name"],
    "properties": {
        "id": {"type": "string", "pattern": _ID_RE.pattern,
               "description": "稳定 ID（新建时可省略，自动生成 c_xxxxxxxx）"},
        "name": {"type": "string", "maxLength": 64,
                 "description": "显示名（全库唯一，大小写不敏感）。文本匹配时按名称与别名命中"},
        "aliases": {"type": "array", "items": {"type": "string", "maxLength": 64}, "maxItems": 16,
                    "description": "别名/昵称/曾用名，参与文本匹配（如 狼仔 的 Momiji）"},
        "tag_name": {"type": "string", "maxLength": 200,
                     "description": "Danbooru 角色标签（如 yanami anna）；原创角色写体现特征的英文（如 rabbit girl）"},
        "series": {"type": "string", "maxLength": 200,
                   "description": "Danbooru 作品标签（如 blue archive）；原创写 original，未知留空"},
        "count": {"type": "string", "maxLength": 32,
                  "description": "人数/主体标签，缺省按 1girl 处理（男性 1boy，吉祥物/动物 no humans）"},
        "tags": {"type": "string", "maxLength": 4000,
                 "description": "基础外观 Danbooru 标签，逗号分隔（本体特征：发型/瞳色/兽耳/体型；有 outfits 时不写服装）"},
        "description": {"type": "string", "maxLength": 4000,
                        "description": "中文外观描述（自然语言，给 LLM 参考）"},
        "outfits": {
            "type": "array", "maxItems": _MAX_OUTFITS,
            "description": "造型（服装/季节装/形态变体），组合时 = 基础 tags + 造型 tags",
            "items": {
                "type": "object",
                "required": ["name"],
                "properties": {
                    "name": {"type": "string", "maxLength": 64, "description": "造型名（如 秋装、清凉版）"},
                    "tags": {"type": "string", "maxLength": 4000, "description": "该造型的 Danbooru 标签"},
                    "description": {"type": "string", "maxLength": 2000, "description": "该造型的中文描述"},
                    "default": {"type": "boolean", "description": "是否默认造型（最多一个）"},
                },
            },
        },
        "artist": {"type": "string", "maxLength": 200,
                   "description": "偏好画师标签（带 @ 前缀，如 @makihitsuji）"},
        "notes": {"type": "string", "maxLength": 2000,
                  "description": "绘制注意事项/禁忌（如 发型不要辫子、红晕只画在脸颊）"},
        "personality": {"type": "string", "maxLength": 2000,
                        "description": "性格/称呼/行为设定（对话类下游参考，画图不使用）"},
        "labels": {"type": "array", "items": {"type": "string", "maxLength": 32}, "maxItems": 16,
                   "description": "分组标签（如 群友、原创、角色）"},
        "nsfw": {"type": "boolean", "description": "人设本身含 NSFW 内容（SFW 场景可据此过滤）"},
        "source": {"type": "string", "maxLength": 32,
                   "description": "来源：web / bot / import / api 等"},
        "extra": {"type": "object", "description": "下游自定义扩展字段（原样保存，≤16KB）"},
        "created_at": {"type": "number", "description": "创建时间（epoch 秒，只读）"},
        "updated_at": {"type": "number", "description": "更新时间（epoch 秒，只读）"},
    },
}


class CharacterError(Exception):
    """带 HTTP 状态码的业务错误（路由层直接转成 {"error": msg}）"""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


def default_characters_file() -> Path:
    """数据文件位置：环境变量 ANIMATOOL_CHARACTERS_FILE，缺省为插件目录 data/characters.json"""
    env = os.environ.get("ANIMATOOL_CHARACTERS_FILE", "").strip()
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent / "data" / "characters.json"


# -------------------------
# 规范化 / 校验
# -------------------------

def _clean_str(value: Any, field: str, max_len: int) -> str:
    if value is None:
        return ""
    if not isinstance(value, (str, int, float)):
        raise CharacterError(f"字段 {field} 必须是字符串")
    s = _ZERO_WIDTH_RE.sub("", str(value)).strip()
    if len(s) > max_len:
        raise CharacterError(f"字段 {field} 超长（最多 {max_len} 字）")
    return s


def _as_number(value: Any, default: float = 0.0) -> float:
    """读文件时的容错数值转换（外部改写/迁移来的脏 meta 不让整库报错）"""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_tags(value: str) -> str:
    """'a,b ,  c，a' → 'a, b, c'：按中英文逗号拆分、去空项、大小写不敏感去重、保持顺序"""
    seen = set()
    out = []
    for part in re.split(r"[,，\n]", value or ""):
        t = " ".join(part.split())
        if not t:
            continue
        k = t.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(t)
    return ", ".join(out)


def _clean_list(value: Any, field: str, max_items: int, max_len: int) -> List[str]:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        value = re.split(r"[,，\n]", value)
    if not isinstance(value, list):
        raise CharacterError(f"字段 {field} 必须是字符串数组")
    seen = set()
    out = []
    for item in value:
        s = _clean_str(item, field, max_len)
        if s and s.lower() not in seen:
            seen.add(s.lower())
            out.append(s)
    if len(out) > max_items:
        raise CharacterError(f"字段 {field} 最多 {max_items} 项")
    return out


def _clean_outfits(value: Any) -> List[Dict[str, Any]]:
    if value is None or value == "":
        return []
    if not isinstance(value, list):
        raise CharacterError("字段 outfits 必须是数组")
    if len(value) > _MAX_OUTFITS:
        raise CharacterError(f"字段 outfits 最多 {_MAX_OUTFITS} 项")
    out = []
    has_default = False
    for i, item in enumerate(value):
        if not isinstance(item, dict):
            raise CharacterError(f"outfits[{i}] 必须是对象")
        name = _clean_str(item.get("name"), f"outfits[{i}].name", 64)
        tags = normalize_tags(_clean_str(item.get("tags"), f"outfits[{i}].tags", 4000))
        desc = _clean_str(item.get("description"), f"outfits[{i}].description", 2000)
        if not name and not tags and not desc:
            continue  # 整条空白的造型直接丢弃（前端编辑器留下的空行）
        if not name:
            name = f"造型{len(out) + 1}"
        is_default = bool(item.get("default")) and not has_default
        has_default = has_default or is_default
        out.append({"name": name, "tags": tags, "description": desc, "default": is_default})
    return out


def _clean_extra(value: Any) -> Dict[str, Any]:
    if value is None or value == "":
        return {}
    if not isinstance(value, dict):
        raise CharacterError("字段 extra 必须是对象")
    try:
        raw = json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        raise CharacterError("字段 extra 必须可 JSON 序列化")
    if len(raw.encode("utf-8")) > _MAX_EXTRA_BYTES:
        raise CharacterError("字段 extra 超过 16KB")
    return json.loads(raw)


def _clean_field(field: str, value: Any) -> Any:
    """按字段类型规范化单个字段值；未知字段返回 KeyError"""
    if field in _STR_FIELDS:
        s = _clean_str(value, field, _STR_FIELDS[field])
        return normalize_tags(s) if field in _TAG_FIELDS else s
    if field in _LIST_FIELDS:
        max_items, max_len = _LIST_FIELDS[field]
        return _clean_list(value, field, max_items, max_len)
    if field == "outfits":
        return _clean_outfits(value)
    if field == "nsfw":
        return bool(value)
    if field == "extra":
        return _clean_extra(value)
    raise KeyError(field)


_EDITABLE_FIELDS = list(_STR_FIELDS) + list(_LIST_FIELDS) + ["outfits", "nsfw", "extra"]


def _blank_record() -> Dict[str, Any]:
    rec: Dict[str, Any] = {"id": ""}
    for f in _STR_FIELDS:
        rec[f] = ""
    for f in _LIST_FIELDS:
        rec[f] = []
    rec["outfits"] = []
    rec["nsfw"] = False
    rec["extra"] = {}
    rec["created_at"] = 0.0
    rec["updated_at"] = 0.0
    return rec


def _ordered(rec: Dict[str, Any]) -> Dict[str, Any]:
    """固定输出字段顺序（文件可读性 + diff 友好）"""
    order = ["id", "name", "aliases", "tag_name", "series", "count", "tags", "description",
             "outfits", "artist", "notes", "personality", "labels", "nsfw", "source", "extra",
             "created_at", "updated_at"]
    return {k: rec[k] for k in order if k in rec}


def _term_spans(text_l: str, term: str) -> List[Tuple[int, int]]:
    """term 在文本中的全部出现区间。两端是 ASCII 字母数字时要求词边界，
    避免 cy 命中 cyan、XX 命中 XXL；中文名不受影响。"""
    spans = []
    start = 0
    n = len(term)
    while True:
        pos = text_l.find(term, start)
        if pos < 0:
            break
        end = pos + n
        ok = True
        if _ASCII_ALNUM.match(term[0]) and pos > 0 and _ASCII_ALNUM.match(text_l[pos - 1]):
            ok = False
        if ok and _ASCII_ALNUM.match(term[-1]) and end < len(text_l) and _ASCII_ALNUM.match(text_l[end]):
            ok = False
        if ok:
            spans.append((pos, end))
        start = pos + 1
    return spans


def match_characters(characters: List[Dict[str, Any]], text: str, limit: int = 10) -> List[Dict[str, Any]]:
    """在文本中按名称/别名匹配人设，返回 [{"character", "matched"}]（按首次出现位置排序）。

    最长词优先：某人设的全部命中位置都落在另一个人设更长的命中词里时丢弃
    （如文本「Chaos前世」同时含 Chaos 与别名 Chaos前世，只保留后者）。
    """
    text_l = (text or "").lower()
    if not text_l.strip():
        return []
    hits = []  # (character, term, spans)
    for c in characters:
        best_term, best_spans = "", []
        for term in [c.get("name", "")] + list(c.get("aliases") or []):
            t = (term or "").strip().lower()
            if not t:
                continue
            spans = _term_spans(text_l, t)
            if spans and len(t) > len(best_term):
                best_term, best_spans = t, spans
        if best_spans:
            hits.append((c, best_term, best_spans))

    result = []
    for c, term, spans in hits:
        def covered(span):
            s, e = span
            return any(o is not c and len(ot) > len(term) and any(os_ <= s and e <= oe for os_, oe in ospans)
                       for o, ot, ospans in hits)
        if all(covered(sp) for sp in spans):
            continue
        result.append((spans[0][0], c, term))
    result.sort(key=lambda x: x[0])
    return [{"character": copy.deepcopy(c), "matched": term} for _, c, term in result[:max(1, limit)]]


# -------------------------
# 存储
# -------------------------

class CharacterStore:
    """线程安全的人设存储（JSON 文件持久化，写入原子替换并保留一份 .bak）"""

    def __init__(self, path: Optional[Path] = None):
        self._path = Path(path) if path else default_characters_file()
        self._lock = threading.RLock()
        self._data: Dict[str, Any] = {"schema_version": SCHEMA_VERSION, "revision": 0,
                                      "updated_at": 0.0, "characters": []}
        self._mtime: Optional[float] = None
        self._loaded = False

    @property
    def path(self) -> Path:
        return self._path

    # -- 持久化 --

    def _file_mtime(self) -> Optional[float]:
        try:
            return self._path.stat().st_mtime
        except OSError:
            return None

    def _ensure_loaded(self) -> None:
        """首次访问加载；之后文件 mtime 变化（外部改写）时重新加载"""
        mtime = self._file_mtime()
        if self._loaded and mtime == self._mtime:
            return
        if mtime is None:
            self._data = {"schema_version": SCHEMA_VERSION, "revision": 0,
                          "updated_at": 0.0, "characters": []}
        else:
            try:
                raw = json.loads(self._path.read_text(encoding="utf-8-sig"))
            except (OSError, ValueError) as e:
                raise CharacterError(f"人设文件无法读取：{self._path}（{e}）", 500)
            chars = raw.get("characters") if isinstance(raw, dict) else raw
            if not isinstance(chars, list):
                raise CharacterError(f"人设文件格式错误：{self._path}", 500)
            meta = raw if isinstance(raw, dict) else {}
            self._data = {
                "schema_version": SCHEMA_VERSION,
                "revision": int(_as_number(meta.get("revision"))),
                "updated_at": _as_number(meta.get("updated_at")),
                "characters": [self._load_record(c) for c in chars if isinstance(c, dict)],
            }
        self._mtime = mtime
        self._loaded = True

    @staticmethod
    def _load_record(raw: Dict[str, Any]) -> Dict[str, Any]:
        """读文件时的宽松规范化：补齐缺省字段，非法值回落缺省，不因单条脏数据拒绝整库"""
        rec = _blank_record()
        rec["id"] = str(raw.get("id") or "")
        for f in _EDITABLE_FIELDS:
            if f in raw:
                try:
                    rec[f] = _clean_field(f, raw[f])
                except CharacterError:
                    pass
        if not rec["name"] and isinstance(raw.get("name"), (str, int, float)):
            # 名称超长等非法值被回落成空串，截断保留，避免这条记录再也无法更新
            rec["name"] = _ZERO_WIDTH_RE.sub("", str(raw["name"])).strip()[:_STR_FIELDS["name"]]
        rec["created_at"] = _as_number(raw.get("created_at"))
        rec["updated_at"] = _as_number(raw.get("updated_at"), rec["created_at"])
        return _ordered(rec)

    def _save(self) -> None:
        self._data["revision"] = int(self._data.get("revision", 0)) + 1
        self._data["updated_at"] = time.time()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        payload = {
            "schema_version": SCHEMA_VERSION,
            "revision": self._data["revision"],
            "updated_at": self._data["updated_at"],
            "characters": self._data["characters"],
        }
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        if self._path.exists():
            shutil.copy2(self._path, self._path.with_suffix(self._path.suffix + ".bak"))
        os.replace(tmp, self._path)
        self._mtime = self._file_mtime()

    # -- 内部工具 --

    def _find_index(self, char_id: str) -> int:
        for i, c in enumerate(self._data["characters"]):
            if c["id"] == char_id:
                return i
        return -1

    def _name_taken(self, name: str, exclude_id: str = "") -> Optional[Dict[str, Any]]:
        key = name.strip().lower()
        for c in self._data["characters"]:
            if c["id"] != exclude_id and c["name"].strip().lower() == key:
                return c
        return None

    def _new_id(self) -> str:
        while True:
            cid = "c_" + uuid.uuid4().hex[:8]
            if self._find_index(cid) < 0:
                return cid

    def _build(self, data: Dict[str, Any], base: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """把请求数据合并进 base（部分更新语义：只改传了的字段），返回新记录"""
        if not isinstance(data, dict):
            raise CharacterError("请求体必须是 JSON 对象")
        rec = copy.deepcopy(base) if base else _blank_record()
        for f in _EDITABLE_FIELDS:
            if f in data:
                rec[f] = _clean_field(f, data[f])
        if not rec["name"]:
            raise CharacterError("角色名不能为空")
        return rec

    # -- 公开接口 --

    @property
    def revision(self) -> int:
        with self._lock:
            self._ensure_loaded()
            return int(self._data.get("revision", 0))

    def snapshot(self, q: str = "", label: str = "", include_nsfw: bool = True) -> Dict[str, Any]:
        """整库快照（可按关键词/分组/NSFW 过滤），返回深拷贝"""
        with self._lock:
            self._ensure_loaded()
            chars = self._data["characters"]
            if label:
                chars = [c for c in chars if label in c["labels"]]
            if not include_nsfw:
                chars = [c for c in chars if not c["nsfw"]]
            if q:
                ql = q.strip().lower()
                def hit(c):
                    hay = " ".join([c["name"], c["tag_name"], c["series"], c["tags"], c["description"],
                                    c["artist"], " ".join(c["aliases"]), " ".join(c["labels"]),
                                    " ".join(o["name"] + " " + o["tags"] for o in c["outfits"])])
                    return ql in hay.lower()
                chars = [c for c in chars if hit(c)]
            return {
                "schema_version": SCHEMA_VERSION,
                "revision": int(self._data.get("revision", 0)),
                "updated_at": self._data.get("updated_at", 0.0),
                "total": len(chars),
                "characters": copy.deepcopy(chars),
            }

    def get(self, char_id: str) -> Dict[str, Any]:
        with self._lock:
            self._ensure_loaded()
            i = self._find_index(char_id)
            if i < 0:
                raise CharacterError("角色不存在", 404)
            return copy.deepcopy(self._data["characters"][i])

    def create(self, data: Dict[str, Any], source: str = "api") -> Dict[str, Any]:
        with self._lock:
            self._ensure_loaded()
            rec = self._build(data)
            if self._name_taken(rec["name"]):
                raise CharacterError(f"角色「{rec['name']}」已存在", 409)
            cid = str(data.get("id") or "").strip()
            if cid:
                if not _ID_RE.match(cid) or cid.lower() in _RESERVED_IDS:
                    raise CharacterError(f"非法 id：{cid}（仅限字母数字_-，且不能是保留字）")
                if self._find_index(cid) >= 0:
                    raise CharacterError(f"id {cid} 已存在", 409)
            rec["id"] = cid or self._new_id()
            rec["source"] = rec["source"] or source
            now = time.time()
            rec["created_at"] = now
            rec["updated_at"] = now
            rec = _ordered(rec)
            self._data["characters"].insert(0, rec)
            self._save()
            return copy.deepcopy(rec)

    def update(self, char_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            self._ensure_loaded()
            i = self._find_index(char_id)
            if i < 0:
                raise CharacterError("角色不存在", 404)
            rec = self._build(patch, self._data["characters"][i])
            if self._name_taken(rec["name"], exclude_id=char_id):
                raise CharacterError(f"角色「{rec['name']}」已存在", 409)
            rec["updated_at"] = time.time()
            rec = _ordered(rec)
            self._data["characters"][i] = rec
            self._save()
            return copy.deepcopy(rec)

    def delete(self, char_id: str) -> Dict[str, Any]:
        with self._lock:
            self._ensure_loaded()
            i = self._find_index(char_id)
            if i < 0:
                raise CharacterError("角色不存在", 404)
            rec = self._data["characters"].pop(i)
            self._save()
            return copy.deepcopy(rec)

    def import_many(self, items: List[Dict[str, Any]], mode: str = "merge",
                    source: str = "import") -> Dict[str, Any]:
        """批量导入。

        merge：按 id 更新，id 不存在再按名称（大小写不敏感）更新，都没有则新建；
               更新是部分更新（只覆盖条目里出现的字段）。
        replace：清空后整体写入（调用方需自行确认）。
        条目里的 created_at / updated_at 会保留（迁移旧数据用），校验失败的条目跳过并报告。
        """
        if mode not in ("merge", "replace"):
            raise CharacterError("mode 只能是 merge 或 replace")
        if not isinstance(items, list):
            raise CharacterError("characters 必须是数组")
        with self._lock:
            self._ensure_loaded()
            if mode == "replace":
                self._data["characters"] = []
            created, updated, errors = [], [], []
            for idx, item in enumerate(items):
                try:
                    if not isinstance(item, dict):
                        raise CharacterError("条目必须是对象")
                    cid = str(item.get("id") or "").strip()
                    i = self._find_index(cid) if cid else -1
                    if i < 0 and item.get("name"):
                        same = self._name_taken(str(item["name"]))
                        i = self._find_index(same["id"]) if same else -1
                    now = time.time()
                    if i >= 0:
                        rec = self._build(item, self._data["characters"][i])
                        if self._name_taken(rec["name"], exclude_id=rec["id"]):
                            raise CharacterError(f"角色「{rec['name']}」已存在", 409)
                        rec["updated_at"] = float(item.get("updated_at") or now)
                        self._data["characters"][i] = _ordered(rec)
                        updated.append(rec["id"])
                    else:
                        rec = self._build(item)
                        if self._name_taken(rec["name"]):
                            raise CharacterError(f"角色「{rec['name']}」已存在", 409)
                        if cid and (not _ID_RE.match(cid) or cid.lower() in _RESERVED_IDS):
                            raise CharacterError(f"非法 id：{cid}")
                        rec["id"] = cid or self._new_id()
                        rec["source"] = rec["source"] or source
                        rec["created_at"] = float(item.get("created_at") or now)
                        rec["updated_at"] = float(item.get("updated_at") or rec["created_at"])
                        self._data["characters"].append(_ordered(rec))
                        created.append(rec["id"])
                except CharacterError as e:
                    errors.append({"index": idx, "name": item.get("name") if isinstance(item, dict) else None,
                                   "error": e.message})
            if created or updated or mode == "replace":
                self._save()
            return {"created": created, "updated": updated, "errors": errors,
                    "revision": int(self._data["revision"]), "total": len(self._data["characters"])}

    def match(self, text: str, limit: int = 10) -> List[Dict[str, Any]]:
        with self._lock:
            self._ensure_loaded()
            return match_characters(self._data["characters"], text, limit)
