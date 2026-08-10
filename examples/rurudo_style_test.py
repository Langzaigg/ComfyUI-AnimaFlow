# rurudo 自设（金毛狮子娘）画风遵循度对比：miao / miao_turbo / aes / kira / nova
# 同 seed 同提示词，仅质量前缀按各模型推荐写法，重点看 @rurudo 画风还原度
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from executor import AnimaExecutor, AnimaToolConfig

ex = AnimaExecutor(config=AnimaToolConfig())

Q_MIAO = "best quality, score_7, score_9, very aesthetic, ultra detailed, fair skin, high contrast, safe"
Q_MIAO_T = "masterpiece, best quality, score_7, very aesthetic, ultra detailed, pale skin, fair skin, high contrast, safe"
Q_AES = "masterpiece, best quality, safe"
Q_KIRA = "masterpiece, best quality, very aesthetic, safe"
Q_NOVA = "masterpiece, best quality, score_9, score_8, score_7, year 2025, newest, highres, absurdres, very aesthetic, safe"

APPEARANCE = "long golden blonde hair, amber eyes, lion ears, lion tail with a tufted tip, small fang"
TAGS = "A small lion girl sits on a wooden chair in a sunlit artist's studio, hugging a sketchbook against her chest and smiling shyly at the viewer, wearing a simple white dress. Warm soft light, cozy gentle atmosphere."

SEED = 20260815

def make_payload(q):
    return {
        "aspect_ratio": "2:3", "seed": SEED, "count": "1girl",
        "quality_meta_year_safe": q, "artist": "@rurudo",
        "appearance": APPEARANCE, "tags": TAGS,
    }

tests = [
    ("miao_s4_rurudo_", ("v2", "miao"), make_payload(Q_MIAO)),
    ("miaot_s4_rurudo_", ("v2", "miao_turbo"), make_payload(Q_MIAO_T)),
    ("aes_s4_rurudo_", ("v2", "aesthetic1.0"), make_payload(Q_AES)),
    ("kira_s4_rurudo_", ("kira", None), make_payload(Q_KIRA)),
    ("nova_s4_rurudo_", ("v2", "nova"), make_payload(Q_NOVA)),
]

for prefix, (kind, model), payload in tests:
    payload["filename_prefix"] = prefix
    t0 = time.time()
    try:
        if kind == "kira":
            result = ex.generate_kira(payload)
        else:
            result = ex.generate_v2(payload, model)
        paths = [img.get("saved_path") for img in result.get("images", [])]
        print(f"[{prefix}] {time.time()-t0:.1f}s -> {paths}")
    except Exception as e:
        print(f"[{prefix}] FAILED after {time.time()-t0:.1f}s: {e}")
