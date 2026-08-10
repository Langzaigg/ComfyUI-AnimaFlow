# 画风遵循度横评：s5 仙狐小姐(@makihitsuji, SFW) / s6 赫萝(@kawakami_rokkaku, NSFW)
# 阵容：miao / miao_turbo / aes / kira / nova / turbo_v1，同 seed 同提示词，仅质量前缀不同
# NSFW 组质量前缀尾部 rating 词由 safe 换成 explicit
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from executor import AnimaExecutor, AnimaToolConfig

ex = AnimaExecutor(config=AnimaToolConfig())

def q(sfw_rating):
    return {
        "miao": f"best quality, score_7, score_9, very aesthetic, ultra detailed, fair skin, high contrast, {sfw_rating}",
        "miao_turbo": f"masterpiece, best quality, score_7, very aesthetic, ultra detailed, pale skin, fair skin, high contrast, {sfw_rating}",
        "aes": f"masterpiece, best quality, {sfw_rating}",
        "kira": f"masterpiece, best quality, very aesthetic, {sfw_rating}",
        "nova": f"masterpiece, best quality, score_9, score_8, score_7, year 2025, newest, highres, absurdres, very aesthetic, {sfw_rating}",
        "turbo_v1": f"masterpiece, best quality, {sfw_rating}",
    }

# s5: 仙狐小姐（厨房煮咖喱，参照动画宣传图）
S5_APPEARANCE = ("short golden blonde hair, amber eyes, fox ears, large fluffy golden fox tail, "
                 "red camellia flower hair accessory, white kimono-style top with red striped trim, "
                 "red skirt, white apron")
S5_TAGS = ("A fox girl cooks in a cozy home kitchen, stirring a pot of curry on the stove and turning "
           "to smile brightly at the viewer. Soft daylight through the window, warm homely cheerful atmosphere.")

# s6: 赫萝（月下露天温泉，NSFW，参照川上六角同人图）
S6_APPEARANCE = "long light brown hair, red eyes, wolf ears, wolf tail"
S6_TAGS = ("A nude wolf girl sits at the edge of an outdoor hot spring at night, arms raised behind her head "
           "tying up her wet hair, glancing at the viewer with a sly knowing smile. Full moon in a deep blue "
           "night sky, rising steam, warm light glistening on wet skin, relaxed intimate atmosphere.")

SEEDS = {"s5": 20260816, "s6": 20260817}

def payload(model, scene):
    qs = q("safe" if scene == "s5" else "explicit")
    base = {"aspect_ratio": "2:3", "seed": SEEDS[scene], "count": "1girl",
            "quality_meta_year_safe": qs[model]}
    if scene == "s5":
        base.update({
            "character": "senko (sewayaki kitsune no senko-san)",
            "series": "sewayaki kitsune no senko-san",
            "artist": "@makihitsuji",
            "appearance": S5_APPEARANCE, "tags": S5_TAGS,
        })
    else:
        base.update({
            "character": "holo", "series": "spice and wolf",
            "artist": "@kawakami_rokkaku",
            "appearance": S6_APPEARANCE, "tags": S6_TAGS,
        })
    return base

MODELS = [
    ("miao", "miao", ("v2", "miao")),
    ("miaot", "miao_turbo", ("v2", "miao_turbo")),
    ("aes", "aes", ("v2", "aesthetic1.0")),
    ("kira", "kira", ("kira", None)),
    ("nova", "nova", ("v2", "nova")),
    ("turbov1", "turbo_v1", ("v2", "turbo1.0")),
]

for scene in ("s5", "s6"):
    for name, qkey, (kind, model) in MODELS:
        if scene == "s5" and name == "miao":
            continue  # miao_s5_ 已生成
        prefix = f"{name}_{scene}_"
        p = payload(qkey, scene)
        p["filename_prefix"] = prefix
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
