# nova vs turbo_v1 对比：@makihitsuji 画风，三兽耳娘多人场景（各自提示词风格）
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from executor import AnimaExecutor, AnimaToolConfig

ex = AnimaExecutor(config=AnimaToolConfig())

SEED = 20260810

nova_payload = {
    "aspect_ratio": "3:2",
    "seed": SEED,
    "quality_meta_year_safe": "masterpiece, best quality, score_9, score_8, score_7, year 2025, newest, highres, absurdres, very aesthetic, safe",
    "count": "3girls",
    "artist": "@makihitsuji",
    "tags": "Three kemonomimi girls relax together in a sunny flower meadow, sitting on a picnic blanket and sharing snacks, all smiling. The girl with long golden blonde hair, green eyes and fox ears wears a red plaid country dress with a white apron. The girl with short silver hair, blue eyes and wolf ears wears a black hoodie and denim shorts. The girl with pink twin-tails, amber eyes and cat ears wears a frilly white lolita dress with ribbon bows. Warm afternoon sunlight, cheerful carefree atmosphere.",
    "filename_prefix": "nova_vs_",
}

turbo_payload = {
    "aspect_ratio": "3:2",
    "seed": SEED,
    "steps": 12,
    "quality_meta_year_safe": "masterpiece, best quality, safe",
    "count": "3girls",
    "artist": "@makihitsuji",
    "tags": "Three kemonomimi girls relax together in a sunny flower meadow, sitting on a picnic blanket and sharing snacks, all smiling. The girl with long golden blonde hair, green eyes and fox ears wears a red plaid country dress with a white apron. The girl with short silver hair, blue eyes and wolf ears wears a black hoodie and denim shorts. The girl with pink twin-tails, amber eyes and cat ears wears a frilly white lolita dress with ribbon bows. Warm afternoon sunlight, cheerful carefree atmosphere.",
    "filename_prefix": "turbov1_vs_",
}

for name, model, payload in [("nova", "nova", nova_payload), ("turbo_v1", "turbo1.0", turbo_payload)]:
    t0 = time.time()
    try:
        result = ex.generate_v2(payload, model)
        dt = time.time() - t0
        paths = [img.get("saved_path") for img in result.get("images", [])]
        print(f"[{name}] {dt:.1f}s -> {paths}")
    except Exception as e:
        print(f"[{name}] FAILED after {time.time()-t0:.1f}s: {e}")
