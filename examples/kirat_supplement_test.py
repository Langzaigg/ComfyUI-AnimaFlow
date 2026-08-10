# kira_turbo 补测：s5 仙狐(@makihitsuji) / s6 赫萝温泉(@kawakami_rokkaku) / s7 赫萝正面 NSFW
# 与同场景其他模型同 seed 同提示词，质量前缀同 kira（masterpiece, best quality, very aesthetic, <rating>）
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from executor import AnimaExecutor, AnimaToolConfig

ex = AnimaExecutor(config=AnimaToolConfig())

S5 = {
    "aspect_ratio": "2:3", "seed": 20260816, "count": "1girl",
    "quality_meta_year_safe": "masterpiece, best quality, very aesthetic, safe",
    "character": "senko (sewayaki kitsune no senko-san)",
    "series": "sewayaki kitsune no senko-san",
    "artist": "@makihitsuji",
    "appearance": ("short golden blonde hair, amber eyes, fox ears, large fluffy golden fox tail, "
                   "red camellia flower hair accessory, white kimono-style top with red striped trim, "
                   "red skirt, white apron"),
    "tags": ("A fox girl cooks in a cozy home kitchen, stirring a pot of curry on the stove and turning "
             "to smile brightly at the viewer. Soft daylight through the window, warm homely cheerful atmosphere."),
}

S6 = {
    "aspect_ratio": "2:3", "seed": 20260817, "count": "1girl",
    "quality_meta_year_safe": "masterpiece, best quality, very aesthetic, explicit",
    "character": "holo", "series": "spice and wolf",
    "artist": "@kawakami_rokkaku",
    "appearance": "long light brown hair, red eyes, wolf ears, wolf tail",
    "tags": ("A nude wolf girl sits at the edge of an outdoor hot spring at night, arms raised behind her head "
             "tying up her wet hair, glancing at the viewer with a sly knowing smile. Full moon in a deep blue "
             "night sky, rising steam, warm light glistening on wet skin, relaxed intimate atmosphere."),
}

S7 = {
    "aspect_ratio": "2:3", "seed": 20260818, "count": "1girl",
    "quality_meta_year_safe": "masterpiece, best quality, very aesthetic, explicit",
    "character": "holo", "series": "spice and wolf",
    "artist": "@kawakami_rokkaku",
    "appearance": "long light brown hair, red eyes, wolf ears, wolf tail",
    "tags": ("A completely nude wolf girl sits on a bed of furs inside a rustic wooden wagon, facing the viewer "
             "directly and leaning back on her hands, legs spread apart with her pussy fully exposed, "
             "looking at the viewer with a teasing confident smile, long hair draped over her shoulders and chest. "
             "Warm candlelight at night, intimate cozy atmosphere."),
}

for scene, payload in (("s5", S5), ("s6", S6), ("s7", S7)):
    payload["filename_prefix"] = f"kirat_{scene}_"
    t0 = time.time()
    try:
        result = ex.generate_kira(payload, turbo=True)
        paths = [img.get("saved_path") for img in result.get("images", [])]
        fb = result.get("sampler_fallback")
        print(f"[kirat_{scene}_] {time.time()-t0:.1f}s fallback={fb} -> {paths}")
    except Exception as e:
        print(f"[kirat_{scene}_] FAILED after {time.time()-t0:.1f}s: {e}")
