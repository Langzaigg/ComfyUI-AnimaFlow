from __future__ import annotations

import base64
import hashlib
import json
import logging
import math
import os
import shutil
import time
import uuid
from datetime import datetime
from copy import deepcopy
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode, urljoin

from .config import AnimaToolConfig, BASE10_UNET_NAME, TURBO10_UNET_NAME, AESTHETIC10_UNET_NAME, ULTRAREAL_UNET_NAME, ULTRAREAL_SAMPLER, ULTRAREAL_STEPS, ULTRAREAL_CFG, SILVERMOON_UNET_NAME, SILVERMOON_SAMPLER, SILVERMOON_STEPS, SILVERMOON_CFG, SILVERMOON_TURBO_UNET_NAME, SILVERMOON_TURBO_STEPS, ANIMA29_UNET_NAME, ANIMA29_SAMPLER, ANIMA29_STEPS, ANIMA29_CFG, ANIMA29_TURBO_LORA_NAME, ANIMA29_TURBO_STEPS, RDBT_BASE_LORA_NAME, RDBT_DISTILLED_ADDON_LORA_NAME, RDBT_STEPS, AURA_UNET_NAME, AURA_SAMPLER, AURA_STEPS, AURA_SPEED_SAMPLER, AURA_SPEED_STEPS, AURA_CFG, FUSE_UNET_NAME, FUSE_SAMPLER, FUSE_STEPS, FUSE10_UNET_NAME, FUSE_DEFAULT_NEGATIVE, CYBERREAL_UNET_NAME, CYBERREAL_SAMPLER, CYBERREAL_STEPS, CYBERREAL_CFG, MOSS_CKPT_NAME, MOSS_SAMPLER, MOSS_STEPS, MOSS_CFG
from .history import HistoryManager

try:  # ComfyUI 内以插件包导入
    from ..device_guard import get_guard, is_device_lost
except ImportError:  # 独立进程（FastAPI / MCP）以顶层包导入
    from device_guard import get_guard, is_device_lost

logger = logging.getLogger("anima_tool")


def _round_up(x: int, base: int) -> int:
    if base <= 1:
        return x
    return int(math.ceil(x / base) * base)


def _parse_aspect_ratio(ratio: str) -> float:
    """
    解析 "16:9" -> 16/9。
    """
    s = (ratio or "").strip()
    if ":" not in s:
        raise ValueError(f"aspect_ratio 必须形如 '16:9'，收到：{ratio!r}")
    a_str, b_str = s.split(":", 1)
    a = float(a_str.strip())
    b = float(b_str.strip())
    if a <= 0 or b <= 0:
        raise ValueError(f"aspect_ratio 两边必须 > 0，收到：{ratio!r}")
    return a / b


def estimate_size_from_ratio(
    *,
    aspect_ratio: str,
    target_megapixels: float = 1.048576,
    round_to: int = 16,
) -> Tuple[int, int]:
    """
    只给定长宽比时，估算 width/height，使像素数接近 target_megapixels。
    宽高会向上取整到 round_to 的倍数。
    
    注意：Anima 基于 Cosmos 架构，VAE 缩放 8 倍后还需被 spatial_patch_size=2 整除，
    所以 round_to 必须至少是 16（8×2），否则会报错 "should be divisible by spatial_patch_size"。
    """
    r = _parse_aspect_ratio(aspect_ratio)
    target_px = max(1.0, float(target_megapixels)) * 1_000_000.0
    w = int(math.sqrt(target_px * r))
    h = int(math.sqrt(target_px / r))
    w = _round_up(max(64, w), round_to)
    h = _round_up(max(64, h), round_to)
    return w, h


def align_dimension(value: int, round_to: int = 16) -> int:
    """
    将尺寸对齐到 round_to 的倍数（向上取整）。
    用于处理用户直接传入的 width/height。
    """
    return _round_up(max(64, int(value)), round_to)


def _join_csv(*parts: str) -> str:
    cleaned: List[str] = []
    for p in parts:
        if p is None:
            continue
        s = str(p).strip()
        if not s:
            continue
        cleaned.append(s)
    return ", ".join(cleaned)


def build_turbo_positive_text(prompt_json: Dict[str, Any]) -> str:
    """
    Turbo 模式拼接正面提示词。
    顺序：[安全标签] [人数] [角色] [作品] [外观] [画师] [通用标签(自然语言)]
    """
    return _join_csv(
        prompt_json.get("quality_meta_year_safe", ""),
        prompt_json.get("count", ""),
        prompt_json.get("character", ""),
        prompt_json.get("series", ""),
        prompt_json.get("appearance", ""),
        prompt_json.get("artist", ""),
        prompt_json.get("tags", ""),
    )


def build_ultrareal_positive_text(prompt_json: Dict[str, Any]) -> str:
    """
    UltraReal (UltraReal_FineTune_Anima_base1_v3) 拼接正面提示词。
    官方 Prompt Formula（空格分隔，不用逗号）：
    [Prefix Tags] + [Natural Language Description] + [Suffix Tags & Score]

    字段映射：
    - tags: 前缀标签（@相机/@灯光/@风格，如 @smartphone_photo @candid_photo @available_light）
    - nltags: 自然语言场景描述（英文完整句子，避免标签堆叠）
    - quality_meta_year_safe: 后缀（安全等级 + @年份 + score_N，如 @sfw @2025 score_8）
    """
    parts: List[str] = []
    for key in ("tags", "nltags", "quality_meta_year_safe"):
        s = str(prompt_json.get(key) or "").strip()
        if s:
            parts.append(s)
    return " ".join(parts)


def build_ultrareal_negative_text(prompt_json: Dict[str, Any]) -> str:
    """
    UltraReal 默认负面提示词。
    以低分标签（score_1-4，官方建议 score 可用于负面）+ 通用质量反咒为基础，
    根据正面后缀中的安全标签追加对立约束（@sfw → 负面加 @nsfw，反之亦然）。
    """
    q = (prompt_json.get("quality_meta_year_safe") or "").lower()
    nsfw = "@nsfw" in q or "nsfw" in q
    base = "score_1, score_2, score_3, score_4, worst quality, low quality, blurry, jpeg artifacts, bad anatomy, bad hands, bad feet, extra fingers, missing fingers, text, watermark, logo"
    if nsfw:
        return f"{base}, @sfw, censored, mosaic"
    return f"{base}, @nsfw"


def build_new_models_negative_text(prompt_json: Dict[str, Any]) -> str:
    """
    新模型（turbo-v1.0 / aesthetic-v1.0）默认负面提示词。
    保留 base 设计，但**不包含质量标签**。根据 quality_meta_year_safe 中的安全等级追加对立约束。
    """
    q = (prompt_json.get("quality_meta_year_safe") or "").lower()
    explicit = "nsfw" in q or "explicit" in q
    base = "worst quality, low quality, artist name, blurry, jpeg artifacts, chromatic aberration, bad anatomy, bad hands, bad feet, extra fingers, missing fingers, text, watermark, logo"
    if explicit:
        return f"{base}, safe, sensitive, censored, mosaic, no mosaic, uncensored"
    return f"{base}, nsfw, explicit"


def build_silvermoon_negative_text(prompt_json: Dict[str, Any]) -> str:
    """Silvermoon (silvermoonmixAnima_v2329B) 官方建议从无负面开始，默认负面为空。"""
    return ""


def build_anima_positive_text(prompt_json: Dict[str, Any]) -> str:
    """
    按 Anima 官方推荐顺序拼接正面提示词。

    README 推荐顺序：
    [quality/meta/year/safety] [count] [character] [series] [artist] [general tags]

    输出格式：
    [质量/安全] [人数] [角色] [作品] [外观] [画师] [风格] [标签] [环境] [自然语言]
    """
    return _join_csv(
        prompt_json.get("quality_meta_year_safe", ""),
        prompt_json.get("count", ""),
        prompt_json.get("character", ""),
        prompt_json.get("series", ""),
        prompt_json.get("appearance", ""),
        prompt_json.get("artist", ""),
        prompt_json.get("style", ""),
        prompt_json.get("tags", ""),
        prompt_json.get("environment", ""),
        prompt_json.get("nltags", ""),
    )


# v2 统一工作流的模型预设：默认 UNET、采样参数（默认值与取值范围均为各模型官方推荐）、
# 默认采样组合、文件名前缀。steps_range / cfg_range 为 None 表示不限制。
_V2_MODEL_PRESETS = {
    "turbo1.0": {
        "unet": TURBO10_UNET_NAME, "steps": 10, "cfg": 1.0,
        "steps_range": (8, 12), "cfg_range": (1.0, 1.6), "cfg_neg": 1.2,
        "sampler": "euler", "scheduler": None, "prefix": "AnimaTool_turbo_v1_",
    },
    # fuse：anima29b-sm29t-fuse1.2（v1.1 融合 UNET + NextGen 2.9bV1 LoRA@0.3）；
    # 沿用 silvermoon turbo 官方参数（Euler a + normal，10 步）。
    # cfg 固定 1.0（负面惰性），官方建议无负面，故无 default_negative。
    "fuse": {
        "unet": FUSE_UNET_NAME, "steps": FUSE_STEPS, "cfg": 1.0,
        "steps_range": (8, 12), "cfg_range": (1.0, 1.0),
        "sampler": FUSE_SAMPLER[0], "scheduler": FUSE_SAMPLER[1], "prefix": "AnimaTool_fuse_",
    },
    # fuse1.0（已过期）：turbo 1.1 × Anima 2.9B preview1 融合 UNET anima29b-p1-turbo1.1
    # （turbo 权重 0.8，40 块），turbo 提示词体系 + anima29 采样组合；
    # default_negative 常驻 → 默认按 cfg_neg 1.2 采样，文字类负面生效以压制假签名/水印。
    "fuse1.0": {
        "unet": FUSE10_UNET_NAME, "steps": 8, "cfg": 1.0,
        "steps_range": (8, 12), "cfg_range": (1.0, 1.6), "cfg_neg": 1.2,
        "sampler": "euler", "scheduler": "sgm_uniform", "prefix": "AnimaTool_fuse10_",
        "default_negative": FUSE_DEFAULT_NEGATIVE,
    },
    "aesthetic1.0": {
        "unet": AESTHETIC10_UNET_NAME, "steps": 35, "cfg": 4.0,
        "steps_range": None, "cfg_range": None,
        "sampler": "euler", "scheduler": None, "prefix": "AnimaTool_aesthetic_",
    },
    "silvermoon": {
        "unet": SILVERMOON_UNET_NAME, "steps": SILVERMOON_STEPS, "cfg": SILVERMOON_CFG,
        "steps_range": (20, 28), "cfg_range": (4.0, 5.0),
        "sampler": SILVERMOON_SAMPLER[0], "scheduler": SILVERMOON_SAMPLER[1], "prefix": "AnimaTool_silvermoon_",
    },
    # v2329B Turbo 变体：官方 CFG 1 + 8-12 步 + 无负面（turbo 系规则：写 neg 默认 cfg_neg 1.2 生效）
    "silvermoon_turbo": {
        "unet": SILVERMOON_TURBO_UNET_NAME, "steps": SILVERMOON_TURBO_STEPS, "cfg": 1.0,
        "steps_range": (8, 12), "cfg_range": (1.0, 1.6), "cfg_neg": 1.2,
        "sampler": SILVERMOON_SAMPLER[0], "scheduler": SILVERMOON_SAMPLER[1], "prefix": "AnimaTool_silvermoon_turbo_",
    },
    # Anima 2.9B：base 的层扩展微调（训练数据无 score 标签；质量前缀避免一切质量/score 词，只留 year 2026 + 安全标签）。
    # turbo 变体通过预设 "lora" 启用 anima29b-turbolora1.1（Turbo-ANIMA-v4 重映射版；steps 8-12；
    # turbo 系规则：cfg 1-1.6，有 neg 默认 1.2）。
    "anima29": {
        "unet": ANIMA29_UNET_NAME, "steps": ANIMA29_STEPS, "cfg": ANIMA29_CFG,
        "steps_range": (28, 50), "cfg_range": (3.5, 5.0),
        "sampler": ANIMA29_SAMPLER[0], "scheduler": ANIMA29_SAMPLER[1], "prefix": "AnimaTool_anima29_",
    },
    "anima29_turbo": {
        "unet": ANIMA29_UNET_NAME, "steps": ANIMA29_TURBO_STEPS, "cfg": 1.0,
        "steps_range": (8, 12), "cfg_range": (1.0, 1.6), "cfg_neg": 1.2,
        "sampler": ANIMA29_SAMPLER[0], "scheduler": ANIMA29_SAMPLER[1], "prefix": "AnimaTool_anima29_turbo_",
        "lora": ANIMA29_TURBO_LORA_NAME, "lora_strength": 0.8,
    },
    # rdbt v2.0：base LoRA + distilled addon LoRA 双串联（lora_addon 在第一个 LoRA 之后链入）。
    # 探针结论：16 步 cfg1 双 LoRA 为 anima29 系性价比最优；仅 base（无 addon）在任何步数下均不可用。
    # cfg 规则同 turbo 系：1.0-1.6，有 neg 默认 1.2 使负面生效，无 neg 默认 1.0。
    "anima29_rdbt": {
        "unet": ANIMA29_UNET_NAME, "steps": RDBT_STEPS, "cfg": 1.0,
        "steps_range": (8, 32), "cfg_range": (1.0, 1.6), "cfg_neg": 1.2,
        "sampler": ANIMA29_SAMPLER[0], "scheduler": ANIMA29_SAMPLER[1], "prefix": "AnimaTool_anima29_rdbt_",
        "lora": RDBT_BASE_LORA_NAME, "lora_strength": 1.0,
        "lora_addon": RDBT_DISTILLED_ADDON_LORA_NAME, "lora_addon_strength": 1.0,
    },
    # AuraAnima 2.9B qpolaP101 Int8 W8a8：anima29 量化变体（质量/速度均与 BF16 同档，显存约减半）。
    # aura=精度重视 er_sde+beta 12 步；aura-speed=速度重视 euler+simple 10 步。cfg 4.0-5.0 可调，默认 5.0。
    # 风格质量标签由调用方在 quality_meta_year_safe 给出（默认 photo real，可选 anime color / real skin）。
    "aura": {
        "unet": AURA_UNET_NAME, "steps": AURA_STEPS, "cfg": AURA_CFG,
        "steps_range": (8, 30), "cfg_range": (4.0, 5.0),
        "sampler": AURA_SAMPLER[0], "scheduler": AURA_SAMPLER[1], "prefix": "AnimaTool_aura_",
    },
    "aura-speed": {
        "unet": AURA_UNET_NAME, "steps": AURA_SPEED_STEPS, "cfg": AURA_CFG,
        "steps_range": (8, 30), "cfg_range": (4.0, 5.0),
        "sampler": AURA_SPEED_SAMPLER[0], "scheduler": AURA_SPEED_SAMPLER[1], "prefix": "AnimaTool_aura_speed_",
    },
    # CyberRealistic Anima v7.0 Turbo：写实向微调（基于 Anima Turbo V1.1）。
    # 官方推荐 cfg 1-1.5 / steps 8-12；turbo 系规则：默认 cfg 1.0 负面惰性，
    # 写 neg 默认 cfg_neg 1.2 生效。提示词用官方真实感写法（score_8, score_9 + real life,
    # realistic，见 knowledge/cyberreal_expert.md）；写实风慎用画师 tag。
    "cyberreal": {
        "unet": CYBERREAL_UNET_NAME, "steps": CYBERREAL_STEPS, "cfg": CYBERREAL_CFG,
        "steps_range": (8, 12), "cfg_range": (1.0, 1.5), "cfg_neg": 1.2,
        "sampler": CYBERREAL_SAMPLER[0], "scheduler": CYBERREAL_SAMPLER[1], "prefix": "AnimaTool_cyberreal_",
    },
}


# MOSS-Image 预设：单文件 checkpoint（DiT + TE + VAE），无 LoRA 槽位，也不进 _V2_MODEL_PRESETS。
# 项目默认 4 步 / CFG 1 / res_multistep + simple（官方推荐 8 步 euler + simple） / 无负面；cfg 上限 1.6 只给显式写 neg 的实验场景。
_MOSS_PRESET = {
    "ckpt": MOSS_CKPT_NAME, "steps": MOSS_STEPS, "cfg": MOSS_CFG,
    "steps_range": (4, 12), "cfg_range": (1.0, 1.6), "cfg_neg": 1.2,
    "sampler": MOSS_SAMPLER[0], "scheduler": MOSS_SAMPLER[1], "prefix": "MOSS_",
}

# MOSS Layout 的合法标签，与官方 compile_prompt.py 一致
_MOSS_LABELS = ("object", "character", "text")

# 提示词固定用混合写法：tag 块（顺序同 Anima）在前，自然语言在后。
# tag 块字段名复用 Anima 的 schema；Quality → Score → Meta → Year → Safe 都塞在
# quality_meta_year_safe 一个字段里，Knowledge 里写明这个顺序。
_MOSS_TAG_ORDER = (
    "quality_meta_year_safe", "count", "character", "series",
    "appearance", "artist", "style", "tags", "environment",
)


def _moss_tag_value(payload: Dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if isinstance(value, (list, tuple)):
        value = ", ".join(str(v).strip() for v in value if str(v).strip())
    return str(value or "").strip().strip(",")


def build_moss_positive_text(payload: Dict[str, Any]) -> str:
    """
    混合拼提示词：tag 块 + 换行 + 自然语言。

    tag 顺序（与 Anima 一致）：quality_meta_year_safe → count → character → series →
    appearance → artist → style → tags → environment；自然语言取 nltags（兼容旧字段 prompt）。
    两者都为空时返回空串，由调用方报错。
    """
    tags_block = ", ".join(
        value for value in (_moss_tag_value(payload, key) for key in _MOSS_TAG_ORDER) if value
    )
    prose = str(payload.get("nltags") or payload.get("prompt") or "").strip()
    if tags_block and prose:
        return tags_block + "\n" + prose
    return tags_block or prose


def _moss_centered_box(box: Any, width: int, height: int, location: str) -> List[int]:
    """
    草稿的顶左像素框 [x1, y1, x2, y2] → 模型要求的中心原点 yxyx 框。

    换算与官方 compile_prompt.py 完全一致：先向外取整成像素边界，再减去画布中心。
    """
    if not isinstance(box, (list, tuple)) or len(box) != 4:
        raise ValueError(f"{location} 必须是 [x1, y1, x2, y2] 四个数")
    try:
        x1, y1, x2, y2 = (float(v) for v in box)
    except (TypeError, ValueError):
        raise ValueError(f"{location} 必须是 [x1, y1, x2, y2] 四个数") from None
    if not all(math.isfinite(v) for v in (x1, y1, x2, y2)):
        raise ValueError(f"{location} 含非法数值")
    if not (x1 < x2 and y1 < y2):
        raise ValueError(f"{location} 的宽高必须为正")
    if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
        raise ValueError(f"{location} 超出 {width}x{height} 画布")
    return [
        math.floor(round(y1, 9)) - height // 2,
        math.floor(round(x1, 9)) - width // 2,
        math.ceil(round(y2, 9)) - height // 2,
        math.ceil(round(x2, 9)) - width // 2,
    ]


def normalize_moss_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    兼容官方 prompt skill 的草稿格式：`summary` + `items` 直接当入参。

    官方 compile_prompt.py 的草稿是 {width, height, bbox_coord_space, bbox_format,
    summary{caption,meta,canvas}, items[...]}，与 /moss/generate 的 prompt + elements
    只差一层字段名，这里统一成后者的形状再编译。
    """
    if payload.get("prompt") or not isinstance(payload.get("summary"), dict):
        return payload
    summary = payload["summary"]
    merged = dict(payload)
    merged["prompt"] = summary.get("caption", "")
    if summary.get("canvas"):
        merged["canvas"] = summary["canvas"]
    if summary.get("meta"):
        merged["meta"] = summary["meta"]
    if payload.get("items") and not payload.get("elements"):
        merged["elements"] = payload["items"]
    return merged


def compile_moss_layout(prompt_json: Dict[str, Any], width: int, height: int) -> str:
    """
    把 Layout 草稿编译成 MOSS-Image 的单行 Layout JSON 提示词。

    入参字段（见 schemas/tool_schema_moss.json）：
    - prompt：整体画面描述 → summary.caption
    - meta：媒介/体裁标签数组 → summary.meta
    - canvas：single / multi_panel / collage → summary.canvas
    - elements：items 数组，每项 {label, caption, bbox, text?, tags?, palette?}，
      bbox 用画布左上角为原点的像素 xyxy

    没有 elements 时退化为纯文本 caption 提示词（模型同样接受自然语言）。
    """
    caption = build_moss_positive_text(prompt_json)
    if not caption:
        raise ValueError("Layout 模式缺少画面描述：nltags（或 tag 字段）不能为空")

    elements = prompt_json.get("elements") or []
    if not isinstance(elements, list):
        raise ValueError("elements 必须是数组")
    if not elements:
        return caption

    summary: Dict[str, Any] = {}
    meta = prompt_json.get("meta")
    if meta:
        if not isinstance(meta, list) or not all(isinstance(m, str) and m.strip() for m in meta):
            raise ValueError("meta 必须是非空字符串数组")
        summary["meta"] = list(meta)

    canvas = str(prompt_json.get("canvas") or "").strip()
    if canvas:
        if canvas not in ("single", "multi_panel", "collage"):
            raise ValueError("canvas 只能是 single / multi_panel / collage")
        summary["canvas"] = canvas
    summary["caption"] = caption

    items: List[Dict[str, Any]] = []
    for index, element in enumerate(elements):
        location = f"elements[{index}]"
        if not isinstance(element, dict):
            raise ValueError(f"{location} 必须是对象")
        label = str(element.get("label") or "").strip()
        if label not in _MOSS_LABELS:
            raise ValueError(f"{location}.label 只能是 object / character / text")
        item_caption = str(element.get("caption") or "").strip()
        if not item_caption:
            raise ValueError(f"{location}.caption 不能为空")
        if "bbox" not in element:
            raise ValueError(f"{location}.bbox 不能为空")

        item: Dict[str, Any] = {"label": label, "caption": item_caption}
        if label == "text":
            literal = element.get("text")
            if not isinstance(literal, str) or not literal.strip():
                raise ValueError(f"{location} 是 text 元素，必须给 text（要渲染的字面文字）")
            item["text"] = literal
        elif element.get("text"):
            # 只有 text 元素渲染字面文字；其他标签带 text 是误用，直接报错而不是静默丢弃
            raise ValueError(f"{location}.text 仅 text 元素可用（当前 label={label}）")
        for key in ("tags", "palette"):
            values = element.get(key)
            if values:
                if not isinstance(values, list) or not all(isinstance(v, str) and v.strip() for v in values):
                    raise ValueError(f"{location}.{key} 必须是非空字符串数组")
                item[key] = list(values)
        item["bbox"] = _moss_centered_box(element["bbox"], width, height, f"{location}.bbox")
        items.append(item)

    layout = {
        "summary": summary,
        "items": items,
        "bbox_coord_space": "abs_centralized",
        "bbox_format": "yxyx",
    }
    return json.dumps(layout, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


@dataclass(frozen=True)
class GeneratedImage:
    filename: str
    subfolder: str
    folder_type: str
    view_url: str
    saved_path: Optional[str] = None
    content: Optional[bytes] = None  # 原始图片数据


class AnimaExecutor:
    _SUPPORTED_MODEL_TYPES = ("loras", "diffusion_models", "vae", "text_encoders")
    """
    将结构化 JSON 注入 ComfyUI prompt 并执行，获取输出图片。
    """

    def __init__(self, config: Optional[AnimaToolConfig] = None):
        self.config = config or AnimaToolConfig()
        self._client_id = str(uuid.uuid4())

        # 远端 ComfyUI 返回的模型名称分隔符（Windows 常为 "\\"，Linux 常为 "/"）
        self._remote_model_path_sep_cache: Dict[str, str] = {}

        template_path = Path(__file__).resolve().parent / "workflow_template.json"
        with template_path.open("r", encoding="utf-8") as f:
            self._workflow_template: Dict[str, Any] = json.load(f)

        fine_template_path = Path(__file__).resolve().parent / "workflow_template_fine.json"
        with fine_template_path.open("r", encoding="utf-8") as f:
            self._workflow_template_fine: Dict[str, Any] = json.load(f)

        refine_template_path = Path(__file__).resolve().parent / "workflow_template_refine.json"
        with refine_template_path.open("r", encoding="utf-8") as f:
            self._workflow_template_refine: Dict[str, Any] = json.load(f)

        # base v1.0 工作流模板（保留用于 fine/refine 等模式）
        base10_template_path = Path(__file__).resolve().parent / "workflow_template_base1.0.json"
        with base10_template_path.open("r", encoding="utf-8") as f:
            self._workflow_template_base10: Dict[str, Any] = json.load(f)

        # 统一工作流模板（LoRA 节点始终存在，turbo/base 共用）
        unified_template_path = Path(__file__).resolve().parent / "workflow_template_unified.json"
        with unified_template_path.open("r", encoding="utf-8") as f:
            self._workflow_template_unified: Dict[str, Any] = json.load(f)

        # MOSS-Image 单文件 checkpoint 模板（独立接口 /moss/*，节点 id 与统一模板对齐）
        moss_template_path = Path(__file__).resolve().parent / "workflow_template_moss.json"
        with moss_template_path.open("r", encoding="utf-8") as f:
            self._workflow_template_moss: Dict[str, Any] = json.load(f)

        # 生成历史管理器
        self.history = HistoryManager()

    # -------------------------
    # Model listing / metadata
    # -------------------------
    def _read_lora_metadata(self, lora_name: str) -> Optional[Dict[str, Any]]:
        """读取 LoRA 的 sidecar 元数据文件（同名 .json）。"""
        import os
        if not self.config.comfyui_models_dir:
            return None

        models_dir = Path(self.config.comfyui_models_dir)
        # 兼容处理：lora_name 可能带路径，针对 Windows 统一斜杠并去除首尾空格
        clean_name = lora_name.strip().replace("/", os.sep).replace("\\", os.sep)
        # 核心修复：如果 clean_name 以斜杠开头，Path / 拼接会变成绝对路径导致失败
        while clean_name.startswith(os.sep):
            clean_name = clean_name[1:]
        
        # 尝试几种可能的路径拼接方式
        search_paths = [
            # 1. 标准路径: models/loras/subfolder/file.safetensors.json
            models_dir / "loras" / f"{clean_name}.json",
            # 2. 移除扩展名后的路径: models/loras/subfolder/file.json
            models_dir / "loras" / f"{os.path.splitext(clean_name)[0]}.json",
            # 3. 如果 clean_name 本身已经包含 loras 目录（容错）
            models_dir / f"{clean_name}.json" if "loras" in clean_name.lower() else None
        ]

        for meta_path in search_paths:
            if meta_path and meta_path.exists():
                try:
                    return json.loads(meta_path.read_text(encoding="utf-8"))
                except Exception:
                    continue
        return None

    def list_models(self, model_type: str) -> List[Dict[str, Any]]:
        """列出 ComfyUI 模型文件。

        - model_type=loras：强制只返回存在 sidecar 元数据（.json）的 LoRA。
        - 其他类型：返回 ComfyUI API 的原始列表。
        - 返回的 name 统一使用正斜杠（/）作为分隔符，避免 Windows 反斜杠转义问题。
        """
        model_type = (model_type or "").strip()
        if model_type not in self._SUPPORTED_MODEL_TYPES:
            raise ValueError(f"不支持的 model_type={model_type!r}，仅支持：{self._SUPPORTED_MODEL_TYPES}")

        url = urljoin(self.config.comfyui_url.rstrip("/") + "/", f"models/{model_type}")
        files = self._http_get_json(url)

        if not isinstance(files, list):
            raise RuntimeError(f"ComfyUI /models/{model_type} 返回异常：{files!r}")

        results: List[Dict[str, Any]] = []
        for raw_name in files:
            if not isinstance(raw_name, str) or not raw_name.strip():
                continue
            
            # 统一使用正斜杠格式返回，避免 Windows 反斜杠在 JSON 中的转义问题
            normalized_name = raw_name.replace("\\", "/")
            item: Dict[str, Any] = {"name": normalized_name}

            if model_type == "loras":
                # 读取 sidecar 时仍使用原始路径（因为文件系统可能需要系统分隔符）
                meta = self._read_lora_metadata(raw_name)
                if not meta:
                    # 强制要求：不提供 json sidecar 的 LoRA 不允许被 list 出来
                    continue
                item["metadata"] = meta

            results.append(item)

        return results

    def _detect_remote_model_path_sep(self, model_type: str) -> str:
        """探测远端 ComfyUI 返回的模型名路径分隔符。

        ComfyUI 在 Windows 下通常使用 "\\" 返回子目录模型名，在 Linux/macOS 下通常使用 "/"。
        这里通过调用 /models/{model_type} 做一次探测并缓存。
        """
        model_type = (model_type or "").strip()
        if model_type in self._remote_model_path_sep_cache:
            return self._remote_model_path_sep_cache[model_type]

        url = urljoin(self.config.comfyui_url.rstrip("/") + "/", f"models/{model_type}")
        files = self._http_get_json(url)

        sep = "/"
        if isinstance(files, list):
            for it in files:
                if not isinstance(it, str):
                    continue
                if "\\" in it:
                    sep = "\\"
                    break
                if "/" in it:
                    sep = "/"
                    break

        self._remote_model_path_sep_cache[model_type] = sep
        return sep

    def _normalize_remote_model_name(self, name: str, model_type: str) -> str:
        """将用户输入的 name 规范化为远端 ComfyUI 可接受的模型名格式。"""
        import os

        s = (name or "").strip()
        if not s:
            return s

        # 先统一把两种分隔符都视为路径分隔
        remote_sep = self._detect_remote_model_path_sep(model_type)
        s = s.replace("/", remote_sep).replace("\\", remote_sep)

        # 去掉可能的前导分隔符（否则在某些 Path 拼接/校验场景会变成绝对路径语义）
        while s.startswith(remote_sep):
            s = s[len(remote_sep):]
        # 也顺手把当前系统分隔符的前导去掉
        while s.startswith(os.sep):
            s = s[len(os.sep):]

        return s

    # -------------------------
    # Workflow helpers
    # -------------------------
    def _inject_loras(self, wf: Dict[str, Any], loras: Any) -> None:
        """在 UNET 与 KSampler(model) 之间注入多 LoRA（仅 UNET）。

        loras: [{"name": "xxx.safetensors", "weight": 0.8}, ...]
        """
        if not loras:
            return
        if not isinstance(loras, list):
            raise ValueError("loras 必须是数组：[{name, weight}, ...]")

        # 兼容模板变化：以 KSampler 的 model 输入为起点
        if "19" not in wf or "inputs" not in wf["19"] or "model" not in wf["19"]["inputs"]:
            raise RuntimeError("workflow_template.json 缺少 KSampler(19).inputs.model，无法注入 LoRA")

        prev_model = wf["19"]["inputs"]["model"]

        # 生成不会冲突的数字 node id
        numeric_ids = [int(k) for k in wf.keys() if str(k).isdigit()]
        next_id = (max(numeric_ids) + 1) if numeric_ids else 1

        for i, lora in enumerate(loras):
            if not isinstance(lora, dict):
                continue
            name = str(lora.get("name") or "").strip()
            if not name:
                continue
            # ComfyUI 会对 lora_name 做枚举校验，必须与 /models/loras 返回的字符串完全一致
            name = self._normalize_remote_model_name(name, "loras")
            weight = float(lora.get("weight", 1.0))

            node_id = str(next_id + i)
            wf[node_id] = {
                "class_type": "LoraLoaderModelOnly",
                "inputs": {
                    "model": prev_model,
                    "lora_name": name,
                    "strength_model": weight,
                },
            }
            prev_model = [node_id, 0]

        wf["19"]["inputs"]["model"] = prev_model

    # -------------------------
    # HTTP helpers (requests 优先, 无则 urllib)
    # -------------------------
    def _http_post_json(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            import requests  # type: ignore
        except Exception:
            requests = None  # type: ignore

        data = json.dumps(payload).encode("utf-8")
        if requests is not None:
            r = requests.post(url, json=payload, timeout=self.config.timeout_s)
            r.raise_for_status()
            return r.json()

        import urllib.request

        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self.config.timeout_s) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw)

    def _http_get_json(self, url: str) -> Any:
        try:
            import requests  # type: ignore
        except Exception:
            requests = None  # type: ignore

        if requests is not None:
            r = requests.get(url, timeout=self.config.timeout_s)
            r.raise_for_status()
            return r.json()

        import urllib.request

        with urllib.request.urlopen(url, timeout=self.config.timeout_s) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw)

    def _http_get_bytes(self, url: str) -> bytes:
        try:
            import requests  # type: ignore
        except Exception:
            requests = None  # type: ignore

        if requests is not None:
            r = requests.get(url, timeout=self.config.timeout_s)
            r.raise_for_status()
            return r.content

        import urllib.request

        with urllib.request.urlopen(url, timeout=self.config.timeout_s) as resp:
            return resp.read()

    # -------------------------
    # Core workflow injection
    # -------------------------
    def _inject_unified(self, prompt_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        base 工作流注入：统一模板，内置 LoRA 节点强度固定 0（模型保持缓存），
        支持用户自定义 LoRA。
        """
        wf = deepcopy(self._workflow_template_unified)

        clip_name = prompt_json.get("clip_name") or self.config.clip_name
        unet_name = prompt_json.get("unet_name") or BASE10_UNET_NAME
        vae_name = prompt_json.get("vae_name") or self.config.vae_name

        wf["45"]["inputs"]["clip_name"] = str(clip_name)
        wf["44"]["inputs"]["unet_name"] = str(unet_name)
        wf["15"]["inputs"]["vae_name"] = str(vae_name)

        # 内置 LoRA 关闭（strength=0，仅保持模型缓存）；支持用户自定义 LoRA
        wf["60"]["inputs"]["strength_model"] = 0.0
        self._inject_loras(wf, prompt_json.get("loras"))

        # 文本
        positive = (prompt_json.get("positive") or "").strip()
        if not positive:
            positive = build_anima_positive_text(prompt_json)
        negative = (prompt_json.get("neg") or prompt_json.get("negative") or "").strip()

        wf["11"]["inputs"]["text"] = positive
        wf["12"]["inputs"]["text"] = negative

        # 分辨率
        width = prompt_json.get("width")
        height = prompt_json.get("height")
        aspect_ratio = (prompt_json.get("aspect_ratio") or "").strip()
        round_to = int(prompt_json.get("round_to") or self.config.round_to)

        if (width is None or height is None) and aspect_ratio:
            w, h = estimate_size_from_ratio(
                aspect_ratio=aspect_ratio,
                target_megapixels=float(prompt_json.get("target_megapixels") or self.config.target_megapixels),
                round_to=round_to,
            )
            width, height = w, h
        elif width is not None and height is not None:
            width = align_dimension(width, round_to)
            height = align_dimension(height, round_to)

        if width is None or height is None:
            width, height = 1024, 1024

        wf["28"]["inputs"]["width"] = int(width)
        wf["28"]["inputs"]["height"] = int(height)
        wf["28"]["inputs"]["batch_size"] = int(prompt_json.get("batch_size") or 1)

        # 种子
        seed = prompt_json.get("seed")
        if seed is None:
            seed = int.from_bytes(uuid.uuid4().bytes[:4], "big", signed=False)
        wf["19"]["inputs"]["seed"] = int(seed)

        # base 可调参数
        wf["19"]["inputs"]["steps"] = int(prompt_json.get("steps") or 35)
        wf["19"]["inputs"]["cfg"] = float(prompt_json.get("cfg") or 4)

        # 通用可覆盖参数
        if prompt_json.get("sampler_name"):
            wf["19"]["inputs"]["sampler_name"] = str(prompt_json["sampler_name"])
        if prompt_json.get("scheduler"):
            wf["19"]["inputs"]["scheduler"] = str(prompt_json["scheduler"])
        if prompt_json.get("denoise") is not None:
            wf["19"]["inputs"]["denoise"] = float(prompt_json["denoise"])

        # 文件名前缀
        default_prefix = "AnimaTool_"
        wf["52"]["inputs"]["filename_prefix"] = str(prompt_json.get("filename_prefix") or default_prefix)

        return wf

    def _inject_v2(self, prompt_json: Dict[str, Any], model: str) -> Dict[str, Any]:
        """
        新模型 v1.0 统一工作流注入：turbo-v1.0、aesthetic-v1.0、silvermoon、anima29 等共用同一模板。
        完整 UNET 的模型 LoRA 关闭；预设带 "lora" 的变体（如 anima29_turbo）启用对应 LoRA。

        model: 见 _V2_MODEL_PRESETS 的键（turbo1.0 / aesthetic1.0 / silvermoon / anima29 等）
        """
        preset = _V2_MODEL_PRESETS.get(model)
        if preset is None:
            raise ValueError(f"不支持的 v2 model={model!r}，可选：{sorted(_V2_MODEL_PRESETS)}")

        wf = deepcopy(self._workflow_template_unified)

        # 模型选择
        unet_name = prompt_json.get("unet_name") or preset["unet"]

        clip_name = prompt_json.get("clip_name") or self.config.clip_name
        vae_name = prompt_json.get("vae_name") or self.config.vae_name

        wf["45"]["inputs"]["clip_name"] = str(clip_name)
        wf["44"]["inputs"]["unet_name"] = str(unet_name)
        wf["15"]["inputs"]["vae_name"] = str(vae_name)

        # LoRA：预设带 "lora" 时启用（如 anima29_turbo 的 anima29b-turbolora1.1），
        # 其余完整 UNET 模型关闭 LoRA。可用 prompt_json 的 lora_name / lora_strength 覆盖。
        preset_lora = preset.get("lora")
        if preset_lora or prompt_json.get("lora_name"):
            wf["60"]["inputs"]["lora_name"] = str(prompt_json.get("lora_name") or preset_lora)
            wf["60"]["inputs"]["strength_model"] = float(
                prompt_json.get("lora_strength") or preset.get("lora_strength", 1.0)
            )
        else:
            wf["60"]["inputs"]["strength_model"] = 0.0

        # 预设可再带 "lora_addon"（如 anima29_rdbt 的 rdbt distilled addon）：
        # 在第一个 LoRA(60) 与 KSampler(19) 之间串联第二个 LoraLoaderModelOnly（与 _inject_loras 同构）。
        # addon 依赖第一个 LoRA 处于启用状态（strength>0），否则跳过。
        preset_lora_addon = preset.get("lora_addon")
        if preset_lora_addon and float(wf["60"]["inputs"].get("strength_model") or 0) > 0:
            numeric_ids = [int(k) for k in wf.keys() if str(k).isdigit()]
            addon_id = str(max(numeric_ids) + 1)
            wf[addon_id] = {
                "class_type": "LoraLoaderModelOnly",
                "inputs": {
                    "model": wf["19"]["inputs"]["model"],
                    "lora_name": str(preset_lora_addon),
                    "strength_model": float(preset.get("lora_addon_strength", 1.0)),
                },
            }
            wf["19"]["inputs"]["model"] = [addon_id, 0]

        # 文本（与 turbo 一致的字段拼接顺序，使用自然语言 tags）
        positive = (prompt_json.get("positive") or "").strip()
        if not positive:
            positive = build_turbo_positive_text(prompt_json)
        user_negative = (prompt_json.get("neg") or prompt_json.get("negative") or "").strip()
        negative = user_negative
        if not negative:
            default_negative = preset.get("default_negative")
            if default_negative:
                negative = default_negative
            elif model.startswith("silvermoon") or model == "fuse":
                negative = build_silvermoon_negative_text(prompt_json)
            else:
                negative = build_new_models_negative_text(prompt_json)

        wf["11"]["inputs"]["text"] = positive
        wf["12"]["inputs"]["text"] = negative

        # 分辨率
        width = prompt_json.get("width")
        height = prompt_json.get("height")
        aspect_ratio = (prompt_json.get("aspect_ratio") or "").strip()
        round_to = int(prompt_json.get("round_to") or self.config.round_to)

        if (width is None or height is None) and aspect_ratio:
            w, h = estimate_size_from_ratio(
                aspect_ratio=aspect_ratio,
                target_megapixels=float(prompt_json.get("target_megapixels") or self.config.target_megapixels),
                round_to=round_to,
            )
            width, height = w, h
        elif width is not None and height is not None:
            width = align_dimension(width, round_to)
            height = align_dimension(height, round_to)

        if width is None or height is None:
            width, height = 1024, 1024

        wf["28"]["inputs"]["width"] = int(width)
        wf["28"]["inputs"]["height"] = int(height)
        wf["28"]["inputs"]["batch_size"] = int(prompt_json.get("batch_size") or 1)

        # 种子
        seed = prompt_json.get("seed")
        if seed is None:
            seed = int.from_bytes(uuid.uuid4().bytes[:4], "big", signed=False)
        wf["19"]["inputs"]["seed"] = int(seed)

        # 采样参数（默认值与取值范围见 _V2_MODEL_PRESETS，均为各模型官方推荐）
        steps = int(prompt_json.get("steps") or preset["steps"])
        if preset["steps_range"]:
            lo, hi = preset["steps_range"]
            steps = max(lo, min(hi, steps))
        wf["19"]["inputs"]["steps"] = steps
        cfg_value = prompt_json.get("cfg")
        if cfg_value is None:
            # 负面进采样的情况（调用方显式给 neg，或预设带 default_negative）默认用 cfg_neg；
            # 无负面时保持预设 cfg（turbo 系为 1.0，负面惰性）。
            cfg_value = preset.get("cfg_neg", preset["cfg"]) if (user_negative or preset.get("default_negative")) else preset["cfg"]
        cfg = float(cfg_value)
        if preset["cfg_range"]:
            lo, hi = preset["cfg_range"]
            cfg = max(lo, min(hi, cfg))
        wf["19"]["inputs"]["cfg"] = cfg

        # 采样器：默认各模型官方推荐组合（老工作流 base/turbo0.2 用 er_sde）
        wf["19"]["inputs"]["sampler_name"] = str(prompt_json.get("sampler_name") or preset["sampler"])
        scheduler = prompt_json.get("scheduler") or preset["scheduler"]
        if scheduler:
            wf["19"]["inputs"]["scheduler"] = str(scheduler)
        if prompt_json.get("denoise") is not None:
            wf["19"]["inputs"]["denoise"] = float(prompt_json["denoise"])

        # 文件名前缀
        wf["52"]["inputs"]["filename_prefix"] = str(prompt_json.get("filename_prefix") or preset["prefix"])

        return wf

    def _inject_moss(self, prompt_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        MOSS-Image（单文件 checkpoint，独立接口 /moss/*）工作流注入。

        提示词是 Layout JSON 而不是 tag 系写法：prompt + elements 由 compile_moss_layout
        编译成模型要求的 summary + items + abs_centralized/yxyx 单行 JSON；
        只给 prompt 时退化为纯文本 caption。
        """
        preset = _MOSS_PRESET
        prompt_json = normalize_moss_payload(prompt_json)
        wf = deepcopy(self._workflow_template_moss)

        wf["1"]["inputs"]["ckpt_name"] = str(prompt_json.get("ckpt_name") or preset["ckpt"])

        # 分辨率：MOSS 要求宽高为 16 的倍数，官方建议约 1MP
        width = prompt_json.get("width")
        height = prompt_json.get("height")
        aspect_ratio = (prompt_json.get("aspect_ratio") or "").strip()
        if (width is None or height is None) and aspect_ratio:
            width, height = estimate_size_from_ratio(
                aspect_ratio=aspect_ratio,
                target_megapixels=float(prompt_json.get("target_megapixels") or self.config.target_megapixels),
                round_to=16,
            )
        elif width is not None and height is not None:
            width = align_dimension(int(width), 16)
            height = align_dimension(int(height), 16)
        if width is None or height is None:
            width, height = 1024, 1024
        width, height = int(width), int(height)

        # 提示词：混合写法（tag 块 + 自然语言），有 elements 时把拼好的文字作为 Layout 的 summary.caption
        positive = str(prompt_json.get("positive") or "").strip()
        if not positive:
            if prompt_json.get("elements"):
                positive = compile_moss_layout(prompt_json, width, height)
            else:
                positive = build_moss_positive_text(prompt_json)
        if not positive:
            raise ValueError("提示词为空：nltags 与 tags 等字段至少给一个")
        negative = str(prompt_json.get("neg") or prompt_json.get("negative") or "").strip()

        # 参考图：送到文本编码器的视觉分支（MOSS 的 Qwen3.5 TE 是多模态的），
        # 不走 VAE latent。Qwen 对话模板要求显式图像占位符，每张一行 Picture N。
        refs = prompt_json.get("reference_images") or []
        if isinstance(refs, str):
            refs = [refs]
        single = str(prompt_json.get("reference_image") or "").strip()
        if single:
            refs = [single] + [r for r in refs if str(r).strip() != single]
        refs = [str(r).strip() for r in refs if str(r).strip()][:4]
        if refs:
            prefix = "\n".join(
                f"Picture {index}: <|vision_start|><|image_pad|><|vision_end|>"
                for index in range(1, len(refs) + 1)
            )
            wf["6"] = {
                "class_type": "TextEncodeMingImageEdit",
                "inputs": {"clip": ["1", 1], "prompt": prefix + "\n\n" + positive},
            }
            for index, name in enumerate(refs, 1):
                source, scaled = str(20 + index), str(30 + index)
                wf[source] = {"class_type": "LoadImage", "inputs": {"image": self._resolve_reference_image(name)}}
                # 每张缩到约 384²（0.147456 MP），保留各自比例
                wf[scaled] = {"class_type": "ImageScaleToTotalPixels", "inputs": {
                    "image": [source, 0], "upscale_method": "area",
                    "megapixels": 0.147456, "resolution_steps": 1,
                }}
                wf["6"]["inputs"][f"images.image_{index}"] = [scaled, 0]
            wf["19"]["inputs"]["positive"] = ["6", 0]

        wf["11"]["inputs"]["text"] = positive
        wf["12"]["inputs"]["text"] = negative
        wf["28"]["inputs"]["width"] = width
        wf["28"]["inputs"]["height"] = height
        wf["28"]["inputs"]["batch_size"] = int(prompt_json.get("batch_size") or 1)

        seed = prompt_json.get("seed")
        if seed is None:
            seed = int.from_bytes(uuid.uuid4().bytes[:4], "big", signed=False)
        wf["19"]["inputs"]["seed"] = int(seed)

        # 采样参数：项目默认 4 步 / CFG 1 / res_multistep + simple（官方推荐 8 步 euler + simple）
        steps = int(prompt_json.get("steps") or preset["steps"])
        lo, hi = preset["steps_range"]
        wf["19"]["inputs"]["steps"] = max(lo, min(hi, steps))

        cfg_value = prompt_json.get("cfg")
        if cfg_value is None:
            # cfg 1 时负面不进采样；显式写 neg 才抬到 cfg_neg 让负面生效
            cfg_value = preset["cfg_neg"] if negative else preset["cfg"]
        cfg_lo, cfg_hi = preset["cfg_range"]
        wf["19"]["inputs"]["cfg"] = max(cfg_lo, min(cfg_hi, float(cfg_value)))

        wf["19"]["inputs"]["sampler_name"] = str(prompt_json.get("sampler_name") or preset["sampler"])
        scheduler = prompt_json.get("scheduler") or preset["scheduler"]
        if scheduler:
            wf["19"]["inputs"]["scheduler"] = str(scheduler)
        denoise = prompt_json.get("denoise")
        if denoise is not None:
            wf["19"]["inputs"]["denoise"] = max(0.2, min(1.0, float(denoise)))

        wf["52"]["inputs"]["filename_prefix"] = str(prompt_json.get("filename_prefix") or preset["prefix"])

        return wf

    def _resolve_reference_image(self, name: str) -> str:
        """
        解析参考图为 ComfyUI input 目录里的文件名。

        LoadImage 只接受 input 目录内的文件（有目录穿越校验），所以本机绝对路径会先
        按内容哈希复制进 input 目录；远端 ComfyUI 请自行上传后直接传文件名。
        """
        value = str(name).strip()
        if not value:
            raise ValueError("reference_image 不能为空")
        if not os.path.isabs(value):
            return value

        path = Path(value)
        if not path.is_file():
            raise ValueError(f"参考图不存在：{value}")
        digest = hashlib.md5(path.read_bytes()).hexdigest()[:8]
        target = self._comfyui_input_dir() / f"{path.stem}_{digest}{path.suffix}"
        if not target.exists():
            shutil.copyfile(path, target)
        return target.name

    def _comfyui_input_dir(self) -> Path:
        """ComfyUI 的 input 目录（LoadImage 的唯一可读目录）。"""
        try:
            import folder_paths

            return Path(folder_paths.get_input_directory())
        except Exception:
            if self.config.comfyui_models_dir:
                return Path(self.config.comfyui_models_dir).parent / "input"
        raise ValueError("定位不到 ComfyUI input 目录，请先把参考图上传到 input 目录再传文件名")

    def _inject_ultrareal(self, prompt_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        UltraReal (UltraReal_FineTune_Anima_base1_v3) 工作流注入。
        Anima base1.0 的真实系微调完整 UNET，复用统一模板，LoRA 关闭。
        提示词为官方三段式：[Prefix @标签] + [自然语言] + [@年份 score 后缀]。
        """
        wf = deepcopy(self._workflow_template_unified)

        clip_name = prompt_json.get("clip_name") or self.config.clip_name
        unet_name = prompt_json.get("unet_name") or ULTRAREAL_UNET_NAME
        vae_name = prompt_json.get("vae_name") or self.config.vae_name

        wf["45"]["inputs"]["clip_name"] = str(clip_name)
        wf["44"]["inputs"]["unet_name"] = str(unet_name)
        wf["15"]["inputs"]["vae_name"] = str(vae_name)

        # 完整 UNET，不需要额外 LoRA
        wf["60"]["inputs"]["strength_model"] = 0.0

        # 文本：三段式拼接（tags + nltags + quality_meta_year_safe）
        positive = (prompt_json.get("positive") or "").strip()
        if not positive:
            positive = build_ultrareal_positive_text(prompt_json)
        negative = (prompt_json.get("neg") or prompt_json.get("negative") or "").strip()
        if not negative:
            negative = build_ultrareal_negative_text(prompt_json)

        wf["11"]["inputs"]["text"] = positive
        wf["12"]["inputs"]["text"] = negative

        # 分辨率
        width = prompt_json.get("width")
        height = prompt_json.get("height")
        aspect_ratio = (prompt_json.get("aspect_ratio") or "").strip()
        round_to = int(prompt_json.get("round_to") or self.config.round_to)

        if (width is None or height is None) and aspect_ratio:
            w, h = estimate_size_from_ratio(
                aspect_ratio=aspect_ratio,
                target_megapixels=float(prompt_json.get("target_megapixels") or self.config.target_megapixels),
                round_to=round_to,
            )
            width, height = w, h
        elif width is not None and height is not None:
            width = align_dimension(width, round_to)
            height = align_dimension(height, round_to)

        if width is None or height is None:
            width, height = 1024, 1024

        wf["28"]["inputs"]["width"] = int(width)
        wf["28"]["inputs"]["height"] = int(height)
        wf["28"]["inputs"]["batch_size"] = int(prompt_json.get("batch_size") or 1)

        # 种子
        seed = prompt_json.get("seed")
        if seed is None:
            seed = int.from_bytes(uuid.uuid4().bytes[:4], "big", signed=False)
        wf["19"]["inputs"]["seed"] = int(seed)

        # 采样参数（默认值来自实测，见 knowledge/ultrareal_expert.md）
        wf["19"]["inputs"]["steps"] = int(prompt_json.get("steps") or ULTRAREAL_STEPS)
        wf["19"]["inputs"]["cfg"] = float(prompt_json.get("cfg") or ULTRAREAL_CFG)
        sampler, scheduler = ULTRAREAL_SAMPLER
        wf["19"]["inputs"]["sampler_name"] = str(prompt_json.get("sampler_name") or sampler)
        wf["19"]["inputs"]["scheduler"] = str(prompt_json.get("scheduler") or scheduler)
        if prompt_json.get("denoise") is not None:
            wf["19"]["inputs"]["denoise"] = float(prompt_json["denoise"])

        # 文件名前缀
        wf["52"]["inputs"]["filename_prefix"] = str(prompt_json.get("filename_prefix") or "AnimaTool_ultrareal_")

        return wf

    def _inject_base10(self, prompt_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        Base v1.0 模式：使用 anima-base-v1.0 模型的工作流注入。
        """
        wf = deepcopy(self._workflow_template_base10)

        # 模型文件：使用 base v1.0 的 unet，clip 和 vae 保持不变
        clip_name = prompt_json.get("clip_name") or self.config.clip_name
        unet_name = prompt_json.get("unet_name") or BASE10_UNET_NAME
        vae_name = prompt_json.get("vae_name") or self.config.vae_name
        
        wf["45"]["inputs"]["clip_name"] = str(clip_name)
        wf["44"]["inputs"]["unet_name"] = str(unet_name)
        wf["15"]["inputs"]["vae_name"] = str(vae_name)

        # 可选：LoRA 注入（仅 UNET）
        self._inject_loras(wf, prompt_json.get("loras"))

        # 文本：优先使用直接指定的 positive，否则从结构化字段构建
        positive = (prompt_json.get("positive") or "").strip()
        if not positive:
            positive = build_anima_positive_text(prompt_json)
        wf["11"]["inputs"]["text"] = positive

        negative = (prompt_json.get("neg") or prompt_json.get("negative") or "").strip()
        wf["12"]["inputs"]["text"] = negative

        # 分辨率
        width = prompt_json.get("width")
        height = prompt_json.get("height")
        aspect_ratio = (prompt_json.get("aspect_ratio") or "").strip()
        round_to = int(prompt_json.get("round_to") or self.config.round_to)

        if (width is None or height is None) and aspect_ratio:
            w, h = estimate_size_from_ratio(
                aspect_ratio=aspect_ratio,
                target_megapixels=float(prompt_json.get("target_megapixels") or self.config.target_megapixels),
                round_to=round_to,
            )
            width, height = w, h
        elif width is not None and height is not None:
            width = align_dimension(width, round_to)
            height = align_dimension(height, round_to)

        if width is None or height is None:
            width, height = 1024, 1024

        wf["28"]["inputs"]["width"] = int(width)
        wf["28"]["inputs"]["height"] = int(height)
        wf["28"]["inputs"]["batch_size"] = int(prompt_json.get("batch_size") or 1)

        # 采样参数
        seed = prompt_json.get("seed")
        if seed is None:
            seed = int.from_bytes(uuid.uuid4().bytes[:4], "big", signed=False)
        wf["19"]["inputs"]["seed"] = int(seed)

        wf["19"]["inputs"]["steps"] = int(prompt_json.get("steps") or wf["19"]["inputs"]["steps"])
        wf["19"]["inputs"]["cfg"] = float(prompt_json.get("cfg") or wf["19"]["inputs"]["cfg"])
        wf["19"]["inputs"]["sampler_name"] = str(prompt_json.get("sampler_name") or wf["19"]["inputs"]["sampler_name"])
        wf["19"]["inputs"]["scheduler"] = str(prompt_json.get("scheduler") or wf["19"]["inputs"]["scheduler"])
        wf["19"]["inputs"]["denoise"] = float(prompt_json.get("denoise") or wf["19"]["inputs"]["denoise"])

        # 文件名前缀
        wf["52"]["inputs"]["filename_prefix"] = str(prompt_json.get("filename_prefix") or wf["52"]["inputs"]["filename_prefix"])

        return wf

    def _inject_fine(self, prompt_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fine 模式：两阶段工作流注入（Anima 出图 → 放大 → animeArtflow_v12 细化）。
        """
        wf = deepcopy(self._workflow_template_fine)

        # 模型文件：阶段 1（Anima）
        clip_name = prompt_json.get("clip_name") or self.config.clip_name
        unet_name = prompt_json.get("unet_name") or self.config.unet_name
        vae_name = prompt_json.get("vae_name") or self.config.vae_name

        wf["45"]["inputs"]["clip_name"] = str(clip_name)
        wf["44"]["inputs"]["unet_name"] = str(unet_name)
        wf["15"]["inputs"]["vae_name"] = str(vae_name)

        # 阶段 2 checkpoint（固定为 animeArtflow_v12）
        # 可通过 prompt_json["fine_ckpt_name"] 覆盖
        fine_ckpt = prompt_json.get("fine_ckpt_name") or "animeArtflow_v12.safetensors"
        wf["62"]["inputs"]["ckpt_name"] = str(fine_ckpt)

        # 文本：阶段 1 使用 StringFunction(81) 组装 positive
        positive = (prompt_json.get("positive") or "").strip()
        if not positive:
            positive = build_anima_positive_text(prompt_json)
        negative = (prompt_json.get("neg") or prompt_json.get("negative") or "").strip()

        # 阶段 1 提示词：将完整 positive 注入 text_b，清空 text_a/text_c 避免重复
        wf["81"]["inputs"]["text_a"] = ""
        wf["81"]["inputs"]["text_b"] = positive
        wf["81"]["inputs"]["text_c"] = ""
        wf["12"]["inputs"]["text"] = negative

        # 阶段 2 提示词：同理
        wf["73"]["inputs"]["text_a"] = ""
        wf["73"]["inputs"]["text_b"] = positive
        wf["73"]["inputs"]["text_c"] = ""
        wf["64"]["inputs"]["text"] = negative

        # 分辨率（阶段 1 生成尺寸，阶段 2 自动 1.5x 放大）
        width = prompt_json.get("width")
        height = prompt_json.get("height")
        aspect_ratio = (prompt_json.get("aspect_ratio") or "").strip()
        round_to = int(prompt_json.get("round_to") or self.config.round_to)

        if (width is None or height is None) and aspect_ratio:
            w, h = estimate_size_from_ratio(
                aspect_ratio=aspect_ratio,
                target_megapixels=float(prompt_json.get("target_megapixels") or self.config.target_megapixels),
                round_to=round_to,
            )
            width, height = w, h
        elif width is not None and height is not None:
            width = align_dimension(width, round_to)
            height = align_dimension(height, round_to)

        if width is None or height is None:
            width, height = 1024, 1024

        wf["28"]["inputs"]["width"] = int(width)
        wf["28"]["inputs"]["height"] = int(height)
        wf["28"]["inputs"]["batch_size"] = int(prompt_json.get("batch_size") or 1)

        # 种子（rgthree Seed 节点）
        seed = prompt_json.get("seed")
        if seed is None:
            seed = int.from_bytes(uuid.uuid4().bytes[:4], "big", signed=False)
        wf["53"]["inputs"]["seed"] = int(seed)

        # 阶段 1 采样参数
        wf["19"]["inputs"]["steps"] = int(prompt_json.get("steps") or wf["19"]["inputs"]["steps"])
        wf["19"]["inputs"]["cfg"] = float(prompt_json.get("cfg") or wf["19"]["inputs"]["cfg"])
        wf["19"]["inputs"]["sampler_name"] = str(prompt_json.get("sampler_name") or wf["19"]["inputs"]["sampler_name"])
        wf["19"]["inputs"]["scheduler"] = str(prompt_json.get("scheduler") or wf["19"]["inputs"]["scheduler"])

        # 阶段 2 采样参数（可通过 fine_steps/fine_cfg 等覆盖）
        wf["60"]["inputs"]["steps"] = int(prompt_json.get("fine_steps") or wf["60"]["inputs"]["steps"])
        wf["60"]["inputs"]["cfg"] = float(prompt_json.get("fine_cfg") or wf["60"]["inputs"]["cfg"])
        wf["60"]["inputs"]["sampler_name"] = str(prompt_json.get("fine_sampler_name") or wf["60"]["inputs"]["sampler_name"])
        wf["60"]["inputs"]["scheduler"] = str(prompt_json.get("fine_scheduler") or wf["60"]["inputs"]["scheduler"])
        wf["60"]["inputs"]["denoise"] = float(prompt_json.get("fine_denoise") or wf["60"]["inputs"]["denoise"])

        # 放大倍数（可通过 fine_scale_by 覆盖）
        wf["55"]["inputs"]["scale_by"] = float(prompt_json.get("fine_scale_by") or wf["55"]["inputs"]["scale_by"])

        # 文件名前缀
        wf["99"]["inputs"]["filename_prefix"] = str(prompt_json.get("filename_prefix") or wf["99"]["inputs"]["filename_prefix"])

        return wf

    def _inject_refine(self, prompt_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        Refine 模式：使用阶段 1 的图片作为输入，进行放大细化。
        """
        wf = deepcopy(self._workflow_template_refine)

        # 输入图片文件名（从 ComfyUI output 目录）
        refine_from = prompt_json.get("refine_from")
        if not refine_from:
            raise ValueError("refine_from 参数必须指定阶段 1 的图片文件名")
        wf["67"]["inputs"]["image"] = str(refine_from)

        # Checkpoint
        fine_ckpt = prompt_json.get("fine_ckpt_name") or "animeArtflow_v12.safetensors"
        wf["62"]["inputs"]["ckpt_name"] = str(fine_ckpt)

        # 提示词
        positive = (prompt_json.get("positive") or "").strip()
        if not positive:
            positive = build_anima_positive_text(prompt_json)
        negative = (prompt_json.get("neg") or prompt_json.get("negative") or "").strip()

        wf["73"]["inputs"]["text_a"] = ""
        wf["73"]["inputs"]["text_b"] = positive
        wf["73"]["inputs"]["text_c"] = ""
        wf["64"]["inputs"]["text"] = negative

        # 种子
        seed = prompt_json.get("seed")
        if seed is None:
            seed = int.from_bytes(uuid.uuid4().bytes[:4], "big", signed=False)
        wf["60"]["inputs"]["seed"] = int(seed)

        # 采样参数
        wf["60"]["inputs"]["steps"] = int(prompt_json.get("fine_steps") or wf["60"]["inputs"]["steps"])
        wf["60"]["inputs"]["cfg"] = float(prompt_json.get("fine_cfg") or wf["60"]["inputs"]["cfg"])
        wf["60"]["inputs"]["sampler_name"] = str(prompt_json.get("fine_sampler_name") or wf["60"]["inputs"]["sampler_name"])
        wf["60"]["inputs"]["scheduler"] = str(prompt_json.get("fine_scheduler") or wf["60"]["inputs"]["scheduler"])
        wf["60"]["inputs"]["denoise"] = float(prompt_json.get("fine_denoise") or wf["60"]["inputs"]["denoise"])

        # 放大倍数
        wf["55"]["inputs"]["scale_by"] = float(prompt_json.get("fine_scale_by") or wf["55"]["inputs"]["scale_by"])

        # 文件名前缀
        wf["99"]["inputs"]["filename_prefix"] = str(prompt_json.get("filename_prefix") or wf["99"]["inputs"]["filename_prefix"])

        return wf

    # -------------------------
    # Health check
    # -------------------------
    def check_comfyui_health(self) -> Tuple[bool, str]:
        """
        检查 ComfyUI 是否可访问。
        返回 (is_healthy, message)
        """
        try:
            url = urljoin(self.config.comfyui_url.rstrip("/") + "/", "system_stats")
            self._http_get_json(url)
            return True, f"ComfyUI 运行正常 ({self.config.comfyui_url})"
        except Exception as e:
            error_msg = str(e)
            # 提供友好的错误提示
            if "Connection refused" in error_msg or "连接" in error_msg:
                return False, (
                    f"无法连接到 ComfyUI ({self.config.comfyui_url})\n"
                    f"请确认：\n"
                    f"  1. ComfyUI 已启动\n"
                    f"  2. 地址和端口正确（可通过 COMFYUI_URL 环境变量修改）\n"
                    f"  3. 防火墙未阻止连接"
                )
            elif "timeout" in error_msg.lower() or "超时" in error_msg:
                return False, (
                    f"连接 ComfyUI 超时 ({self.config.comfyui_url})\n"
                    f"可能原因：网络延迟、ComfyUI 负载过高"
                )
            else:
                return False, f"ComfyUI 连接错误: {error_msg}"

    # -------------------------
    # ComfyUI execution
    # -------------------------
    def queue_prompt(self, prompt: Dict[str, Any]) -> str:
        url = urljoin(self.config.comfyui_url.rstrip("/") + "/", "prompt")
        payload = {"prompt": prompt, "client_id": self._client_id}
        
        try:
            resp = self._http_post_json(url, payload)
        except Exception as e:
            # 先检查 ComfyUI 是否可访问
            is_healthy, health_msg = self.check_comfyui_health()
            if not is_healthy:
                raise RuntimeError(health_msg) from e
            raise
        
        prompt_id = str(resp.get("prompt_id") or "")
        if not prompt_id:
            # 检查是否有错误信息
            error = resp.get("error") or resp.get("node_errors")
            if error:
                raise RuntimeError(f"ComfyUI 执行错误：{error}")
            raise RuntimeError(f"ComfyUI /prompt 返回异常：{resp}")
        return prompt_id

    def wait_history(self, prompt_id: str) -> Dict[str, Any]:
        url = urljoin(self.config.comfyui_url.rstrip("/") + "/", f"history/{prompt_id}")
        deadline = time.time() + float(self.config.timeout_s)
        last = None
        while time.time() < deadline:
            data = self._http_get_json(url)
            last = data
            if isinstance(data, dict) and prompt_id in data:
                return data[prompt_id]
            time.sleep(float(self.config.poll_interval_s))
        raise TimeoutError(f"等待 ComfyUI 生成超时：prompt_id={prompt_id}, last={last}")

    def _extract_images(self, prompt_id: str, history_item: Dict[str, Any]) -> List[GeneratedImage]:
        outputs = history_item.get("outputs") or {}
        images: List[GeneratedImage] = []
        for node_id, node_out in outputs.items():
            if not isinstance(node_out, dict):
                continue
            for im in node_out.get("images") or []:
                filename = str(im.get("filename") or "")
                subfolder = str(im.get("subfolder") or "")
                folder_type = str(im.get("type") or "output")
                if not filename:
                    continue
                qs = urlencode({"filename": filename, "subfolder": subfolder, "type": folder_type})
                view_url = urljoin(self.config.comfyui_url.rstrip("/") + "/", f"view?{qs}")
                images.append(
                    GeneratedImage(
                        filename=filename,
                        subfolder=subfolder,
                        folder_type=folder_type,
                        view_url=view_url,
                        saved_path=None,
                    )
                )
        return images

    def _download_images(self, images: List[GeneratedImage]) -> List[GeneratedImage]:
        """下载图片并保存到本地，按年月分目录存储"""
        out_dir = Path(self.config.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        # 按年月建立子目录
        now = datetime.now()
        ym_dir = out_dir / f"{now.year}-{now.month:02d}"
        ym_dir.mkdir(parents=True, exist_ok=True)

        downloaded: List[GeneratedImage] = []
        for im in images:
            content = self._http_get_bytes(im.view_url)

            saved_path = None
            if self.config.download_images:
                dst = ym_dir / im.filename
                if dst.exists():
                    # 编号重合兜底：ComfyUI output 被清理/重置后，新文件编号可能撞上
                    # 本月已归档的同名图片。此时加时间戳后缀落盘，避免覆盖历史图片，
                    # 并同步修正返回的 filename / saved_path（预览走 saved_path，不受影响）。
                    p = Path(im.filename)
                    stamp = now.strftime("%Y%m%d_%H%M%S")
                    new_name = f"{p.stem}_{stamp}{p.suffix}"
                    counter = 1
                    while (ym_dir / new_name).exists():
                        new_name = f"{p.stem}_{stamp}_{counter}{p.suffix}"
                        counter += 1
                    im = replace(im, filename=new_name)
                    dst = ym_dir / new_name
                dst.write_bytes(content)
                saved_path = str(dst)

            downloaded.append(
                GeneratedImage(
                    filename=im.filename,
                    subfolder=im.subfolder,
                    folder_type=im.folder_type,
                    view_url=im.view_url,
                    saved_path=saved_path,
                    content=content,
                )
            )
        return downloaded

    # -------------------------
    # 月初清理 ComfyUI output（编号重置 + 归档防覆盖）
    # -------------------------
    _CLEAN_MARKER = ".last_clean_month"
    _IMG_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif")

    def _resolve_comfyui_output_dir(self) -> Optional[Path]:
        """解析 ComfyUI 原生 output 目录：配置项 > folder_paths 自动探测 > None"""
        if self.config.comfyui_output_dir:
            return self.config.comfyui_output_dir
        try:
            import folder_paths  # type: ignore

            d = folder_paths.get_output_directory()
            if d:
                return Path(d)
        except Exception:
            pass
        return None

    def _get_queue_counts(self) -> Tuple[int, int]:
        """查询 ComfyUI 当前队列 (running, pending)，查不到返回 (0, 0)"""
        try:
            resp = self._http_get_json(f"{self.config.comfyui_url}/queue")
            return len(resp.get("queue_running", []) or []), len(resp.get("queue_pending", []) or [])
        except Exception:
            return 0, 0

    def _maybe_clean_comfyui_output(self) -> None:
        """月份切换后（当月第一个图片任务）清理 ComfyUI 原生 output 目录。

        - 用 marker 文件（outputs/.last_clean_month）记录上次清理月份，跨月才清理一次。
        - 仅删除 output 根目录下的图片文件，保留占位文件与子目录。
        - 队列非空时推迟清理（等待下个任务），避免干扰正在执行/排队的任务。
        - 安全护栏：目标目录与插件 outputs 归档目录存在相等/包含关系时拒绝清理。
        - 清理后 web 预览不受影响：Anima 的预览依赖插件 outputs 月份归档副本。
        """
        if not self.config.clean_output_monthly:
            return
        now = datetime.now()
        current_ym = f"{now.year}-{now.month:02d}"
        marker = Path(self.config.output_dir) / self._CLEAN_MARKER
        try:
            if marker.exists() and marker.read_text(encoding="utf-8").strip() == current_ym:
                return  # 本月已清理过
        except OSError:
            pass

        out_dir = self._resolve_comfyui_output_dir()
        if not out_dir:
            logger.warning(
                "月初清理 ComfyUI output 跳过：无法定位 output 目录"
                "（可设置 ANIMATOOL_COMFYUI_OUTPUT_DIR）"
            )
            return

        # ---- 安全护栏：绝不允许清理插件自身的归档目录 ----
        # 目标目录与插件 outputs 归档目录存在相等/包含关系时一律拒绝，
        # 防止 ANIMATOOL_COMFYUI_OUTPUT_DIR 配错或 ComfyUI output 被重定向到
        # 插件 outputs（或其父/子目录）时误删历史归档。
        archive = Path(self.config.output_dir).resolve()

        def _is_within(p: Path, parent: Path) -> bool:
            try:
                p.relative_to(parent)
                return True
            except ValueError:
                return False

        out_abs = out_dir.resolve()
        if out_abs == archive or _is_within(out_abs, archive) or _is_within(archive, out_abs):
            logger.warning(
                f"月初清理已阻止：目标目录 {out_dir} 与插件归档目录 {archive} 存在相等/包含关系，跳过清理"
            )
            return

        running, pending = self._get_queue_counts()
        if running or pending:
            logger.info(
                f"月初清理 ComfyUI output 推迟：队列非空 (running={running}, pending={pending})"
            )
            return

        removed = 0
        if out_dir.is_dir():
            for entry in os.scandir(out_dir):
                if entry.is_file() and entry.name.lower().endswith(self._IMG_EXTS):
                    try:
                        os.remove(entry.path)
                        removed += 1
                    except OSError as e:
                        logger.error(f"清理 ComfyUI output 失败: {entry.path}: {e}")
        try:
            Path(self.config.output_dir).mkdir(parents=True, exist_ok=True)
            marker.write_text(current_ym, encoding="utf-8")
        except OSError as e:
            logger.error(f"写入清理标记失败: {marker}: {e}")
        logger.info(
            f"[AnimaTool] 月初清理 ComfyUI output 完成：删除 {removed} 张图片（{current_ym}），编号已重置"
        )

    def _get_mime_type(self, filename: str) -> str:
        """根据文件名推断 MIME 类型"""
        ext = Path(filename).suffix.lower()
        return {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
            ".gif": "image/gif",
        }.get(ext, "image/png")

    def check_models(self) -> Tuple[bool, str]:
        """
        检查模型文件是否存在（如果配置了 COMFYUI_MODELS_DIR）。
        返回 (is_ok, message)
        """
        if not self.config.check_models or not self.config.comfyui_models_dir:
            return True, "模型检查已跳过（未配置 COMFYUI_MODELS_DIR）"
        
        all_exist, missing = self.config.check_models_exist()
        if all_exist:
            return True, "所有模型文件已就绪"
        
        missing_str = "\n".join(f"  - {m}" for m in missing)
        return False, (
            f"缺少以下模型文件：\n{missing_str}\n\n"
            f"请从 HuggingFace 下载：https://huggingface.co/circlestone-labs/Anima\n"
            f"并放置到 ComfyUI/models/ 对应子目录"
        )

    def generate(self, prompt_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        输入结构化 JSON，执行生成。

        参数：
        - prompt_json: 提示词和参数
        - use_base10: 可在 prompt_json 中传入 "use_base10": true 使用 base v1.0 模型

        返回：
        - prompt_id
        - positive / negative（最终发送给 ComfyUI 的文本）
        - width / height
        - images: [{filename, url, file_path, base64, mime_type, markdown}]
        """
        # 始终使用统一工作流（LoRA 节点始终存在，base 模式 strength=0）
        mode = "base1.0"
        prompt = self._inject_unified(prompt_json)

        # 月份切换后（当月第一个任务）清理 ComfyUI output，编号从 00001 重新计数
        self._maybe_clean_comfyui_output()
        prompt_id = self.queue_prompt(prompt)
        history_item = self.wait_history(prompt_id)
        images = self._extract_images(prompt_id, history_item)
        images = self._download_images(images)

        # 构建图片信息（包含多种格式）
        images_data = []
        for im in images:
            mime_type = self._get_mime_type(im.filename)
            b64 = base64.b64encode(im.content).decode("ascii") if im.content else None
            
            img_info = {
                "filename": im.filename,
                "subfolder": im.subfolder,
                "type": im.folder_type,
                # URL 格式
                "url": im.view_url,
                "view_url": im.view_url,  # 兼容旧字段
                # 本地路径
                "file_path": im.saved_path,
                "saved_path": im.saved_path,  # 兼容旧字段
                # Base64 格式（用于 MCP / Gemini / 嵌入）
                "base64": b64,
                "mime_type": mime_type,
                # Data URL（可直接用于 <img src> 或 markdown）
                "data_url": f"data:{mime_type};base64,{b64}" if b64 else None,
                # Markdown 格式（AI 可直接输出）
                "markdown": f"![{im.filename}]({im.view_url})",
            }
            images_data.append(img_info)

        # 回显最终参数（便于调试）
        actual_seed = int(prompt["19"]["inputs"]["seed"])
        actual_positive = prompt["11"]["inputs"]["text"]
        actual_negative = prompt["12"]["inputs"]["text"]
        actual_width = int(prompt["28"]["inputs"]["width"])
        actual_height = int(prompt["28"]["inputs"]["height"])

        result = {
            "success": True,
            "mode": mode,
            "prompt_id": prompt_id,
            "positive": actual_positive,
            "negative": actual_negative,
            "seed": actual_seed,
            "width": actual_width,
            "height": actual_height,
            "images": images_data,
        }

        # 记录到历史
        record = self.history.add(
            params=prompt_json,
            positive_text=actual_positive,
            negative_text=actual_negative,
            prompt_id=prompt_id,
            seed=actual_seed,
            width=actual_width,
            height=actual_height,
        )
        result["history_id"] = record.id

        return result

    def generate_v2(self, prompt_json: Dict[str, Any], model: str) -> Dict[str, Any]:
        """
        新模型 v1.0 统一生成入口。

        参数：
        - model: 见 _V2_MODEL_PRESETS 的键（turbo1.0 / aesthetic1.0 / silvermoon / anima29 等）
        - 其余字段与 turbo 模式一致，使用自然语言 tags
        """
        prompt = self._inject_v2(prompt_json, model)

        # 月份切换后（当月第一个任务）清理 ComfyUI output，编号从 00001 重新计数
        self._maybe_clean_comfyui_output()
        prompt_id = self.queue_prompt(prompt)
        history_item = self.wait_history(prompt_id)
        images = self._extract_images(prompt_id, history_item)
        images = self._download_images(images)

        images_data = []
        for im in images:
            mime_type = self._get_mime_type(im.filename)
            b64 = base64.b64encode(im.content).decode("ascii") if im.content else None

            img_info = {
                "filename": im.filename,
                "subfolder": im.subfolder,
                "type": im.folder_type,
                "url": im.view_url,
                "view_url": im.view_url,
                "file_path": im.saved_path,
                "saved_path": im.saved_path,
                "base64": b64,
                "mime_type": mime_type,
                "data_url": f"data:{mime_type};base64,{b64}" if b64 else None,
                "markdown": f"![{im.filename}]({im.view_url})",
            }
            images_data.append(img_info)

        # 兼容探针期 PerpNeg 工作流：KSampler(19) 被替换删除时，种子在 RandomNoise(72).noise_seed
        if "19" in prompt:
            actual_seed = int(prompt["19"]["inputs"]["seed"])
        else:
            actual_seed = int(prompt["72"]["inputs"]["noise_seed"])
        actual_positive = prompt["11"]["inputs"]["text"]
        actual_negative = prompt["12"]["inputs"]["text"]
        actual_width = int(prompt["28"]["inputs"]["width"])
        actual_height = int(prompt["28"]["inputs"]["height"])

        result = {
            "success": True,
            "mode": model,
            "prompt_id": prompt_id,
            "positive": actual_positive,
            "negative": actual_negative,
            "seed": actual_seed,
            "width": actual_width,
            "height": actual_height,
            "images": images_data,
        }

        record = self.history.add(
            params=prompt_json,
            positive_text=actual_positive,
            negative_text=actual_negative,
            prompt_id=prompt_id,
            seed=actual_seed,
            width=actual_width,
            height=actual_height,
        )
        result["history_id"] = record.id

        return result

    def _raise_on_moss_failure(self, history_item: Dict[str, Any], prompt_id: str) -> None:
        """ComfyUI 执行失败时抛错；遇到设备上下文丢失则上报设备守护触发重启。"""
        status = history_item.get("status") or {}
        if status.get("status_str") != "error":
            return
        detail = json.dumps(status.get("messages") or [], ensure_ascii=False)
        if is_device_lost(detail):
            get_guard().notify_device_lost(detail)
            raise RuntimeError(
                "MOSS 执行失败：XPU 设备上下文丢失（UR_RESULT_ERROR_DEVICE_LOST，"
                f"prompt_id={prompt_id}）。16GB 卡上 TE(9.7GB)/DiT(5.4GB) 反复换页时容易触发，"
                "已通知设备守护按 ANIMATOOL_DEVICE_RESTART_MODE 重启。"
            )
        raise RuntimeError(f"MOSS 执行失败（prompt_id={prompt_id}）：{detail[:500]}")

    def generate_moss(self, prompt_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        MOSS-Image 生成入口（独立接口 /moss/generate，Layout JSON 提示词而非 tag 串）。

        参数：
        - prompt：整体画面描述（必填，编译进 summary.caption）
        - elements：Layout 元素数组 [{label, caption, bbox, text?, tags?, palette?}]，
          bbox 为画布左上角原点的像素 xyxy，服务端换算成模型要求的中心原点 yxyx
        - canvas / meta：summary.canvas（single/multi_panel/collage）/ summary.meta
        - 其余：width / height / aspect_ratio / steps / cfg / seed / batch_size / filename_prefix
        """
        prompt = self._inject_moss(prompt_json)
        payload = normalize_moss_payload(prompt_json)

        # 月份切换后（当月第一个任务）清理 ComfyUI output，编号从 00001 重新计数
        self._maybe_clean_comfyui_output()
        prompt_id = self.queue_prompt(prompt)
        history_item = self.wait_history(prompt_id)
        self._raise_on_moss_failure(history_item, prompt_id)
        images = self._extract_images(prompt_id, history_item)
        images = self._download_images(images)

        images_data = []
        for im in images:
            mime_type = self._get_mime_type(im.filename)
            b64 = base64.b64encode(im.content).decode("ascii") if im.content else None

            img_info = {
                "filename": im.filename,
                "subfolder": im.subfolder,
                "type": im.folder_type,
                "url": im.view_url,
                "view_url": im.view_url,
                "file_path": im.saved_path,
                "saved_path": im.saved_path,
                "base64": b64,
                "mime_type": mime_type,
                "data_url": f"data:{mime_type};base64,{b64}" if b64 else None,
                "markdown": f"![{im.filename}]({im.view_url})",
            }
            images_data.append(img_info)

        # 参考图模式下正向条件来自 TextEncodeMingImageEdit(6)，其 prompt 字段带 Picture 占位符
        positive_node = prompt["19"]["inputs"]["positive"][0]
        actual_positive = (
            prompt[positive_node]["inputs"].get("prompt")
            or prompt[positive_node]["inputs"].get("text", "")
        )
        result = {
            "success": True,
            "mode": "moss",
            "prompt_format": "layout" if payload.get("elements") else "caption",
            "prompt_id": prompt_id,
            "positive": actual_positive,
            "negative": prompt["12"]["inputs"]["text"],
            "seed": int(prompt["19"]["inputs"]["seed"]),
            "width": int(prompt["28"]["inputs"]["width"]),
            "height": int(prompt["28"]["inputs"]["height"]),
            "reference_images": [
                node["inputs"]["image"] for node in prompt.values()
                if node.get("class_type") == "LoadImage"
            ],
            "images": images_data,
        }

        record = self.history.add(
            params=payload,
            positive_text=actual_positive,
            negative_text=result["negative"],
            prompt_id=prompt_id,
            seed=result["seed"],
            width=result["width"],
            height=result["height"],
        )
        result["history_id"] = record.id

        return result

    def generate_ultrareal(self, prompt_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        UltraReal (UltraReal_FineTune_Anima_base1_v3) 生成入口。
        Anima base1.0 真实系微调：写实照片风（手机/数码/胶片/VHS/DSLR）。

        参数（官方三段式 Prompt Formula，按此顺序拼接）：
        - tags: 前缀标签 —— @相机/@灯光/@风格，如 '@smartphone_photo @candid_photo @available_light'
        - nltags: 自然语言场景描述 —— 英文完整句子（人物、服装、姿势、背景），避免标签堆叠
        - quality_meta_year_safe: 后缀 —— 安全等级 + @年份 + score_N，如 '@sfw @2025 score_8'
        - 其余：steps / cfg / sampler_name / scheduler / aspect_ratio / width / height / seed
        """
        prompt = self._inject_ultrareal(prompt_json)

        # 月份切换后（当月第一个任务）清理 ComfyUI output，编号从 00001 重新计数
        self._maybe_clean_comfyui_output()
        prompt_id = self.queue_prompt(prompt)
        history_item = self.wait_history(prompt_id)
        images = self._extract_images(prompt_id, history_item)
        images = self._download_images(images)

        images_data = []
        for im in images:
            mime_type = self._get_mime_type(im.filename)
            b64 = base64.b64encode(im.content).decode("ascii") if im.content else None

            img_info = {
                "filename": im.filename,
                "subfolder": im.subfolder,
                "type": im.folder_type,
                "url": im.view_url,
                "view_url": im.view_url,
                "file_path": im.saved_path,
                "saved_path": im.saved_path,
                "base64": b64,
                "mime_type": mime_type,
                "data_url": f"data:{mime_type};base64,{b64}" if b64 else None,
                "markdown": f"![{im.filename}]({im.view_url})",
            }
            images_data.append(img_info)

        actual_seed = int(prompt["19"]["inputs"]["seed"])
        actual_positive = prompt["11"]["inputs"]["text"]
        actual_negative = prompt["12"]["inputs"]["text"]
        actual_width = int(prompt["28"]["inputs"]["width"])
        actual_height = int(prompt["28"]["inputs"]["height"])

        result = {
            "success": True,
            "mode": "ultrareal",
            "prompt_id": prompt_id,
            "positive": actual_positive,
            "negative": actual_negative,
            "seed": actual_seed,
            "width": actual_width,
            "height": actual_height,
            "images": images_data,
        }

        record = self.history.add(
            params=prompt_json,
            positive_text=actual_positive,
            negative_text=actual_negative,
            prompt_id=prompt_id,
            seed=actual_seed,
            width=actual_width,
            height=actual_height,
        )
        result["history_id"] = record.id

        return result
