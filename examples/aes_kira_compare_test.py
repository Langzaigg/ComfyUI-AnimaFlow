# aes / kira 对比：复用本会话两个样例场景（各自提示词风格）
# 样例1: @makihitsuji 三兽耳娘野餐（seed 20260810, 3:2，对照 nova_vs_ / turbov1_vs_）
# 样例2: 超时空辉夜姬三人组（seed 20260811, 3:2，对照 cpk3_trio_）
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from executor import AnimaExecutor, AnimaToolConfig

ex = AnimaExecutor(config=AnimaToolConfig())

TAGS_S1 = "Three kemonomimi girls relax together in a sunny flower meadow, sitting on a picnic blanket and sharing snacks, all smiling. The girl with long golden blonde hair, green eyes and fox ears wears a red plaid country dress with a white apron. The girl with short silver hair, blue eyes and wolf ears wears a black hoodie and denim shorts. The girl with pink twin-tails, amber eyes and cat ears wears a frilly white lolita dress with ribbon bows. Warm afternoon sunlight, cheerful carefree atmosphere."

TAGS_S2 = "Three girls sit together on a couch in a cozy small apartment, chatting and laughing over snacks. Kaguya has very long straight blonde hair with blunt bangs and red eyes, wearing an oversized dark grey t-shirt and pink shorts, laughing heartily. Iroha has medium-length dark blue hair and green eyes, wearing a plain white shirt, smiling wryly. Yachiyo has very long purple hair and wears an elegant dark purple dress with a light purple skirt in a Japanese style, smiling gently. Warm indoor lighting, lively friendly atmosphere."

tests = [
    ("aes_s1_", "aes", {
        "aspect_ratio": "3:2", "seed": 20260810,
        "quality_meta_year_safe": "masterpiece, best quality, safe",
        "count": "3girls", "artist": "@makihitsuji", "tags": TAGS_S1,
    }),
    ("kira_s1_", "kira", {
        "aspect_ratio": "3:2", "seed": 20260810,
        "quality_meta_year_safe": "masterpiece, best quality, very aesthetic, safe",
        "count": "3girls", "artist": "@makihitsuji", "tags": TAGS_S1,
    }),
    ("aes_s2_cpk_", "aes", {
        "aspect_ratio": "3:2", "seed": 20260811,
        "quality_meta_year_safe": "masterpiece, best quality, safe",
        "count": "3girls",
        "character": "kaguya (chou kaguya-hime!), iroha sakayori, yachiyo runami",
        "series": "chou kaguya-hime!", "appearance": "", "tags": TAGS_S2,
    }),
    ("kira_s2_cpk_", "kira", {
        "aspect_ratio": "3:2", "seed": 20260811,
        "quality_meta_year_safe": "masterpiece, best quality, very aesthetic, safe",
        "count": "3girls",
        "character": "kaguya (chou kaguya-hime!), iroha sakayori, yachiyo runami",
        "series": "chou kaguya-hime!", "appearance": "", "tags": TAGS_S2,
    }),
]

for prefix, wf, payload in tests:
    payload["filename_prefix"] = prefix
    t0 = time.time()
    try:
        if wf == "aes":
            result = ex.generate_v2(payload, "aesthetic1.0")
        else:
            result = ex.generate_kira(payload)
        paths = [img.get("saved_path") for img in result.get("images", [])]
        print(f"[{prefix}] {time.time()-t0:.1f}s -> {paths}")
    except Exception as e:
        print(f"[{prefix}] FAILED after {time.time()-t0:.1f}s: {e}")
