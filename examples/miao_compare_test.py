# miao / miao_turbo 三场景对比（各用各的质量前缀）
# s1: @makihitsuji 三兽耳娘野餐（seed 20260810, 3:2）
# s2: 超时空辉夜姬三人组（seed 20260811, 3:2）
# s3: 明日方舟终末地 洛茜 单人（seed 20260812, 2:3，附 nova 对照）
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from executor import AnimaExecutor, AnimaToolConfig

ex = AnimaExecutor(config=AnimaToolConfig())

Q_MIAO = "best quality, score_7, score_9, very aesthetic, ultra detailed, fair skin, high contrast, safe"
Q_MIAO_T = "masterpiece, best quality, score_7, very aesthetic, ultra detailed, pale skin, fair skin, high contrast, safe"
Q_NOVA = "masterpiece, best quality, score_9, score_8, score_7, year 2025, newest, highres, absurdres, very aesthetic, safe"

TAGS_S1 = "Three kemonomimi girls relax together in a sunny flower meadow, sitting on a picnic blanket and sharing snacks, all smiling. The girl with long golden blonde hair, green eyes and fox ears wears a red plaid country dress with a white apron. The girl with short silver hair, blue eyes and wolf ears wears a black hoodie and denim shorts. The girl with pink twin-tails, amber eyes and cat ears wears a frilly white lolita dress with ribbon bows. Warm afternoon sunlight, cheerful carefree atmosphere."

TAGS_S2 = "Three girls sit together on a couch in a cozy small apartment, chatting and laughing over snacks. Kaguya has very long straight blonde hair with blunt bangs and red eyes, wearing an oversized dark grey t-shirt and pink shorts, laughing heartily. Iroha has medium-length dark blue hair and green eyes, wearing a plain white shirt, smiling wryly. Yachiyo has very long purple hair and wears an elegant dark purple dress with a light purple skirt in a Japanese style, smiling gently. Warm indoor lighting, lively friendly atmosphere."

S3_APPEARANCE = "warm golden blonde hair, low twin braids, amber eyes, wolf ears, wolf tail, red hood, red and white dress, red cape, black and red boots"
TAGS_S3 = "A young wolf girl stands in a sunlit forest clearing, holding a red apple and grinning confidently at the viewer. Dappled light filters through the trees, a fairy-tale storybook atmosphere with a bold adventurous edge."

tests = [
    ("miao_s1_", "miao", {
        "aspect_ratio": "3:2", "seed": 20260810,
        "quality_meta_year_safe": Q_MIAO, "count": "3girls",
        "artist": "@makihitsuji", "tags": TAGS_S1,
    }),
    ("miaot_s1_", "miao_turbo", {
        "aspect_ratio": "3:2", "seed": 20260810,
        "quality_meta_year_safe": Q_MIAO_T, "count": "3girls",
        "artist": "@makihitsuji", "tags": TAGS_S1,
    }),
    ("miao_s2_cpk_", "miao", {
        "aspect_ratio": "3:2", "seed": 20260811,
        "quality_meta_year_safe": Q_MIAO, "count": "3girls",
        "character": "kaguya (chou kaguya-hime!), iroha sakayori, yachiyo runami",
        "series": "chou kaguya-hime!", "appearance": "", "tags": TAGS_S2,
    }),
    ("miaot_s2_cpk_", "miao_turbo", {
        "aspect_ratio": "3:2", "seed": 20260811,
        "quality_meta_year_safe": Q_MIAO_T, "count": "3girls",
        "character": "kaguya (chou kaguya-hime!), iroha sakayori, yachiyo runami",
        "series": "chou kaguya-hime!", "appearance": "", "tags": TAGS_S2,
    }),
    ("miao_s3_rossi_", "miao", {
        "aspect_ratio": "2:3", "seed": 20260812,
        "quality_meta_year_safe": Q_MIAO, "count": "1girl",
        "character": "rossi (arknights: endfield)", "series": "arknights: endfield",
        "appearance": S3_APPEARANCE, "tags": TAGS_S3,
    }),
    ("miaot_s3_rossi_", "miao_turbo", {
        "aspect_ratio": "2:3", "seed": 20260812,
        "quality_meta_year_safe": Q_MIAO_T, "count": "1girl",
        "character": "rossi (arknights: endfield)", "series": "arknights: endfield",
        "appearance": S3_APPEARANCE, "tags": TAGS_S3,
    }),
    ("nova_s3_rossi_", "nova", {
        "aspect_ratio": "2:3", "seed": 20260812,
        "quality_meta_year_safe": Q_NOVA, "count": "1girl",
        "character": "rossi (arknights: endfield)", "series": "arknights: endfield",
        "appearance": S3_APPEARANCE, "tags": TAGS_S3,
    }),
]

for prefix, model, payload in tests:
    payload["filename_prefix"] = prefix
    t0 = time.time()
    try:
        result = ex.generate_v2(payload, model)
        paths = [img.get("saved_path") for img in result.get("images", [])]
        print(f"[{prefix}] {time.time()-t0:.1f}s -> {paths}")
    except Exception as e:
        print(f"[{prefix}] FAILED after {time.time()-t0:.1f}s: {e}")
