# nova x 超时空辉夜姬（Cosmic Princess Kaguya!, 2026.1 Netflix）角色还原测试
# 1) 纯角色名+作品名：检验模型是否内置该角色
# 2) 角色名+appearance 外貌辅助
# 3) 三人组：多角色规则（appearance 留空，自然语言逐角色描述）
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from executor import AnimaExecutor, AnimaToolConfig

ex = AnimaExecutor(config=AnimaToolConfig())

Q = "masterpiece, best quality, score_9, score_8, score_7, year 2025, newest, highres, absurdres, very aesthetic, safe"

tests = [
    ("cpk1_kaguya_name_", {
        "aspect_ratio": "2:3",
        "seed": 20260811,
        "quality_meta_year_safe": Q,
        "count": "1girl",
        "character": "kaguya (chou kaguya-hime!)",
        "series": "chou kaguya-hime!",
        "tags": "A girl stands in a neon-lit city street at night, grinning energetically at the viewer with one hand raised in a peace sign. Colorful holographic lights glow around her.",
    }),
    ("cpk2_kaguya_full_", {
        "aspect_ratio": "2:3",
        "seed": 20260811,
        "quality_meta_year_safe": Q,
        "count": "1girl",
        "character": "kaguya (chou kaguya-hime!)",
        "series": "chou kaguya-hime!",
        "appearance": "very long straight blonde hair, blunt bangs, red eyes, oversized dark grey t-shirt, pink shorts, light blue sneakers, bracelet on left wrist",
        "tags": "A girl stands in a neon-lit city street at night, grinning energetically at the viewer with one hand raised in a peace sign. Colorful holographic lights glow around her.",
    }),
    ("cpk3_trio_", {
        "aspect_ratio": "3:2",
        "seed": 20260811,
        "quality_meta_year_safe": Q,
        "count": "3girls",
        "character": "kaguya (chou kaguya-hime!), iroha sakayori, yachiyo runami",
        "series": "chou kaguya-hime!",
        "appearance": "",
        "tags": "Three girls sit together on a couch in a cozy small apartment, chatting and laughing over snacks. Kaguya has very long straight blonde hair with blunt bangs and red eyes, wearing an oversized dark grey t-shirt and pink shorts, laughing heartily. Iroha has medium-length dark blue hair and green eyes, wearing a plain white shirt, smiling wryly. Yachiyo has very long purple hair and wears an elegant dark purple dress with a light purple skirt in a Japanese style, smiling gently. Warm indoor lighting, lively friendly atmosphere.",
    }),
]

for prefix, payload in tests:
    payload["filename_prefix"] = prefix
    t0 = time.time()
    try:
        result = ex.generate_v2(payload, "nova")
        paths = [img.get("saved_path") for img in result.get("images", [])]
        print(f"[{prefix}] {time.time()-t0:.1f}s -> {paths}")
    except Exception as e:
        print(f"[{prefix}] FAILED after {time.time()-t0:.1f}s: {e}")
