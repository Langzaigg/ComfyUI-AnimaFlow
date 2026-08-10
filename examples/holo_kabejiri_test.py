# s9: 赫萝壁尻场景（@kawakami_rokkaku），7 模型横评（含 kira_turbo），3:2 横向构图
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
TAGS = ("A wolf girl is stuck in a hole in the wooden wall of an old shed, her bare lower half protruding "
        "completely from the hole with her legs fully visible all the way down to her feet, butt raised toward "
        "the viewer, her pussy fully exposed between her legs, wolf tail lifted above her rear, a small amount "
        "of white cum trickling down her inner thighs, torn fabric around the edges of the hole. Her flushed "
        "upper body and wryly smiling face are shown in a wooden picture frame mounted on the wall above the "
        "hole like a portrait. Dim warm lantern light inside the shed, rustic wooden textures, naughty prank atmosphere.")

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
    prefix = f"{name}_s9_"
    p = {
        "aspect_ratio": "3:2", "seed": 20260820, "count": "1girl",
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
