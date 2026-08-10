# s8: 赫萝事后 cum 流出画面（@kawakami_rokkaku），7 模型横评（含 kira_turbo）
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from executor import AnimaExecutor, AnimaToolConfig

ex = AnimaExecutor(config=AnimaToolConfig())

Q = {
    "miao": "best quality, score_7, score_9, very aesthetic, ultra detailed, fair skin, high contrast, explicit",
    "miao_turbo": "masterpiece, best quality, score_7, very aesthetic, ultra detailed, pale skin, fair skin, high contrast, explicit",
    "aes": "masterpiece, best quality, explicit",
    "kira": "masterpiece, best quality, very aesthetic, explicit",
    "nova": "masterpiece, best quality, score_9, score_8, score_7, year 2025, newest, highres, absurdres, very aesthetic, explicit",
    "turbo_v1": "masterpiece, best quality, explicit",
}

APPEARANCE = "long light brown hair, red eyes, wolf ears, wolf tail"
TAGS = ("A completely nude wolf girl sits on a bed of furs inside a rustic wooden wagon after sex, "
        "leaning back with her face flushed, using one hand to pull one side of her pussy open for the viewer "
        "while her other hand props her up, a small amount of white cum slowly trickling out from inside, "
        "looking at the viewer with a satisfied languid smile, sweat and stray hair strands on her skin. "
        "Warm candlelight at night, intimate afterglow atmosphere.")

MODELS = [
    ("miao", "miao", "v2", "miao"),
    ("miaot", "miao_turbo", "v2", "miao_turbo"),
    ("aes", "aes", "v2", "aesthetic1.0"),
    ("kira", "kira", "kira", False),
    ("kirat", "kira", "kira", True),
    ("nova", "nova", "v2", "nova"),
    ("turbov1", "turbo_v1", "v2", "turbo1.0"),
]

for name, qkey, kind, arg in MODELS:
    prefix = f"{name}_s8_"
    p = {
        "aspect_ratio": "2:3", "seed": 20260819, "count": "1girl",
        "quality_meta_year_safe": Q[qkey],
        "character": "holo", "series": "spice and wolf",
        "artist": "@kawakami_rokkaku",
        "appearance": APPEARANCE, "tags": TAGS,
        "filename_prefix": prefix,
    }
    t0 = time.time()
    try:
        if kind == "kira":
            result = ex.generate_kira(p, turbo=arg)
        else:
            result = ex.generate_v2(p, arg)
        paths = [img.get("saved_path") for img in result.get("images", [])]
        print(f"[{prefix}] {time.time()-t0:.1f}s -> {paths}")
    except Exception as e:
        print(f"[{prefix}] FAILED after {time.time()-t0:.1f}s: {e}")
