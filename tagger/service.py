"""反推服务层：模型注册、懒加载、线程安全、Anima 字段映射。

模型文件放在 model_repos/huggingface/<repo 名（/ 换成 __）>/ 下，
用 `python -m tagger.download` 下载。

推理设备：默认自动检测（Intel XPU / CUDA 可用则用 GPU，否则 CPU），
推理固定使用 CPU，不占用显存（避免与 MOSS 等大模型抢显存导致驱动复位）。
"""
from __future__ import annotations

import base64
import io
import re
import threading
from pathlib import Path
from typing import Any, Dict, Optional

from PIL import Image

from .core import TimmTagger

_MODEL_ROOT = Path(__file__).resolve().parent.parent / "model_repos" / "huggingface"

# 反推模型：固定使用 WD EVA02 2026 canary（Danbooru 标准标签 16,473 个，
# 含 2024-07 后新角色；timm 原生权重，XPU 可用时自动加速）
MODELS: Dict[str, Dict[str, Any]] = {
    "canary": {
        "cls": TimmTagger,
        "repo": "ashen-sensored/wd-eva02-tagger-2026-canary",
        "description": "WD EVA02 2026 canary：Danbooru 标准标签 16,473 个（含 2024-07 后新角色），标签密度适中、噪声少",
        "default": True,
    },
}

DEFAULT_MODEL = next(k for k, v in MODELS.items() if v.get("default"))

_taggers: Dict[str, Any] = {}
_lock = threading.Lock()


class TaggerError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


def model_dir(name: str) -> Path:
    if name not in MODELS:
        raise TaggerError(f"未知模型：{name!r}，可选值：{list(MODELS)}（缺省 {DEFAULT_MODEL}）")
    return _MODEL_ROOT / MODELS[name]["repo"].replace("/", "__")


def list_models() -> Dict[str, Any]:
    """列出注册的模型及本地可用状态。"""
    return {
        "default": DEFAULT_MODEL,
        "device": _resolve_device(),
        "models": {
            name: {
                "description": info["description"],
                "repo": info["repo"],
                "downloaded": model_dir(name).exists(),
            }
            for name, info in MODELS.items()
        },
    }


def _resolve_device() -> str:
    """timm 模型推理固定走 CPU。

    反推是偶发调用、单张几百毫秒级，没必要占用显存；Arc 上 MOSS 这类大模型会把
    16GB 显存吃到见底，反推再抢显存容易把驱动推到 DEVICE_LOST，所以这里不碰 GPU。
    """
    return "cpu"


def get_tagger(name: Optional[str] = None):
    """按名获取已加载的反推器（懒加载 + 全局缓存）。"""
    name = (name or DEFAULT_MODEL).strip()
    info = MODELS.get(name)
    if info is None:
        raise TaggerError(f"未知模型：{name!r}，可选值：{list(MODELS)}（缺省 {DEFAULT_MODEL}）")
    with _lock:
        if name not in _taggers:
            d = model_dir(name)
            if not d.exists():
                raise TaggerError(
                    f"模型 {name} 未下载（{d}）。"
                    f"请先运行：python -m tagger.download {name}",
                    status=409,
                )
            _taggers[name] = info["cls"](d, device=_resolve_device())
    return _taggers[name]


def decode_image(body: Dict[str, Any]) -> Image.Image:
    """从请求体解析图片：image_base64（可带 data: 前缀）或 image_path（本机路径）。"""
    b64 = body.get("image_base64")
    if b64:
        if "," in b64 and b64.lstrip().startswith("data:"):
            b64 = b64.split(",", 1)[1]
        try:
            return Image.open(io.BytesIO(base64.b64decode(b64)))
        except Exception as e:
            raise TaggerError(f"image_base64 解码失败：{e}")
    path = body.get("image_path")
    if path:
        p = Path(str(path))
        if not p.is_file():
            raise TaggerError(f"图片不存在：{p}", status=404)
        return Image.open(p)
    raise TaggerError("必须提供 image_base64 或 image_path")


_RATING_MAP = {"general": "safe", "sensitive": "sensitive", "questionable": "nsfw", "explicit": "explicit"}
_COUNT_RE = re.compile(r"^\d+(girls?|boys?|others?)$")


def to_anima_fields(result: Dict[str, Any], max_tags: int = 40) -> Dict[str, Any]:
    """把反推结果映射为 Anima 提示词字段（供 /generate 的 payload 参考使用）。"""
    def clean(tag: str) -> str:
        return tag.replace("_", " ").strip()

    rating = ""
    if result["rating"]:
        rating = _RATING_MAP.get(next(iter(result["rating"])), "")

    characters = [clean(t) for t in result["character"]]
    series = []
    for t in characters:
        m = re.search(r"\(([^)]+)\)$", t)
        if m:
            series.append(m.group(1))

    count = ""
    tags = []
    for t in result["general"]:
        if not count and _COUNT_RE.match(t):
            count = t
        elif len(tags) < max_tags:
            tags.append(t)

    return {
        "quality_meta_year_safe": rating,
        "count": count,
        "character": ", ".join(characters),
        "series": ", ".join(dict.fromkeys(series)),
        "tags": ", ".join(tags),
    }


def tag_image(image: Image.Image, model: Optional[str] = None,
              general_threshold: Optional[float] = None,
              character_threshold: Optional[float] = None,
              rating_threshold: Optional[float] = None,
              max_tags: int = 40) -> Dict[str, Any]:
    """对 PIL 图片执行反推，返回原始标签 + Anima 字段映射。"""
    name = (model or DEFAULT_MODEL).strip()
    tagger = get_tagger(name)
    kwargs = {}
    if general_threshold is not None:
        kwargs["general_threshold"] = float(general_threshold)
    if character_threshold is not None:
        kwargs["character_threshold"] = float(character_threshold)
    if rating_threshold is not None:
        kwargs["rating_threshold"] = float(rating_threshold)
    result = tagger.tag(image, **kwargs)
    return {
        "success": True,
        "model": name,
        "device": getattr(tagger, "device", "cpu"),
        "seconds": round(result.pop("seconds"), 3),
        **result,
        "anima": to_anima_fields(result, max_tags=max_tags),
    }
