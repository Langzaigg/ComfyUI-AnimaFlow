# s7: 赫萝正面视角 NSFW（@kawakami_rokkaku），pussy 绘制质量横评
# 阵容同 s5/s6：miao / miao_turbo / aes / kira / nova / turbo_v1
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
TAGS = ("A completely nude wolf girl sits on a bed of furs inside a rustic wooden wagon, facing the viewer "
        "directly and leaning back on her hands, legs spread apart with her pussy fully exposed, "
        "looking at the viewer with a teasing confident smile, long hair draped over her shoulders and chest. "
        "Warm candlelight at night, intimate cozy atmosphere.")

MODELS = [
    ("miao", "miao", ("v2", "miao")),
    ("miaot", "miao_turbo", ("v2", "miao_turbo")),
    ("aes", "aes", ("v2", "aesthetic1.0")),
    ("kira", "kira", ("kira", None)),
    ("nova", "nova", ("v2", "nova")),
    ("turbov1", "turbo_v1", ("v2", "turbo1.0")),
]

for name, qkey, (kind, model) in MODELS:
    prefix = f"{name}_s7_"
    p = {
        "aspect_ratio": "2:3", "seed": 20260818, "count": "1girl",
        "quality_meta_year_safe": Q[qkey],
        "character": "holo", "series": "spice and wolf",
        "artist": "@kawakami_rokkaku",
        "appearance": APPEARANCE, "tags": TAGS,
        "filename_prefix": prefix,
    }
    t0 = time.time()
    try:
        if kind == "kira":
            result = ex.generate_kira(p)
        else:
            result = ex.generate_v2(p, model)
        paths = [img.get("saved_path") for img in result.get("images", [])]
        print(f"[{prefix}] {time.time()-t0:.1f}s -> {paths}")
    except Exception as e:
        print(f"[{prefix}] FAILED after {time.time()-t0:.1f}s: {e}")
