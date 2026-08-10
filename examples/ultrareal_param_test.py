"""
UltraReal (UltraReal_FineTune_Anima_base1_v3) 超参数对比测试。

场景 A：碧蓝档案 白子(Shiroko) 手机自拍（固定 seed，遍历采样器/步数/CFG）
场景 B：碧蓝档案 芹香(Serika) 胶片风（用最优组合验证指令遵循）

用法：
    python examples/ultrareal_param_test.py round1   # 采样器对比
    python examples/ultrareal_param_test.py round2   # 步数/CFG 对比
    python examples/ultrareal_param_test.py sceneb   # 场景 B 验证
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

_PARENT = Path(__file__).resolve().parent.parent
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

from executor import AnimaExecutor, AnimaToolConfig

SEED = 20250807

# 场景 A：白子手机自拍（指令遵循检查点：狼耳/围巾/领带/自拍姿势/教室黑板/平静表情）
SCENE_A = {
    "tags": "@smartphone_photo @amateur_photo @candid_photo @available_light",
    "nltags": (
        "A medium close-up selfie of Shiroko from Blue Archive. "
        "She has short silver-grey hair, grey wolf ears, and wears a black scarf over a "
        "blue-and-white school uniform with a blue necktie. "
        "She holds the phone at arm's length with one hand and looks at the camera with a calm, expressionless face. "
        "The background is a sunlit classroom with wooden desks and a green chalkboard, slightly blurred."
    ),
    "quality_meta_year_safe": "@sfw @2025 score_8",
    "width": 1024,
    "height": 1024,
    "seed": SEED,
}

# 场景 B：芹香胶片风（指令遵循检查点：双马尾/红瞳/围裙/拉面店/站姿）
SCENE_B = {
    "tags": "@film_photo @amateur_photo @posed_photo @available_light",
    "nltags": (
        "A full-body photo of Serika from Blue Archive standing in front of a small ramen shop. "
        "She has long dark blue hair tied in twin-tails and red eyes, wearing a beige work apron over a "
        "blue-and-white school uniform. She is holding a serving tray with both hands and smiling awkwardly at the camera. "
        "Warm afternoon sunlight, a noren curtain and a wooden signboard visible behind her."
    ),
    "quality_meta_year_safe": "@sfw @2015 score_8",
    "width": 1024,
    "height": 1024,
    "seed": SEED,
}

# 场景 C：白子+芹香 双人复杂场景（指令遵循检查点：两人外观不串扰/狼耳vs双马尾/自拍互动/教室逆光）
SCENE_C = {
    "tags": "@smartphone_photo @amateur_photo @candid_photo @available_light",
    "nltags": (
        "A candid photo of Shiroko and Serika from Blue Archive in a classroom after school. "
        "Shiroko, on the left, has short silver-grey hair, grey wolf ears, a black scarf over a "
        "blue-and-white school uniform with a blue necktie, a calm expression, holding up a smartphone to take a selfie of the two. "
        "Serika, on the right, has long dark blue twin-tails, red eyes, a beige cardigan over the same uniform, "
        "pouting with her arms crossed. "
        "Late afternoon sunlight comes through the windows, with wooden desks and a green chalkboard behind them."
    ),
    "quality_meta_year_safe": "@sfw @2025 score_8",
    "width": 1024,
    "height": 1024,
    "seed": SEED,
}

# Round 1：采样器对比（steps=28, cfg=4 固定）
ROUND1 = [
    ("er_sde+simple", {"sampler_name": "er_sde", "scheduler": "simple"}),
    ("euler+simple", {"sampler_name": "euler", "scheduler": "simple"}),
    ("dpmpp_2m+karras", {"sampler_name": "dpmpp_2m", "scheduler": "karras"}),
    ("dpmpp_2m_sde+karras", {"sampler_name": "dpmpp_2m_sde", "scheduler": "karras"}),
    ("res_multistep+simple", {"sampler_name": "res_multistep", "scheduler": "simple"}),
    ("sa_solver_pece+simple", {"sampler_name": "sa_solver_pece", "scheduler": "simple"}),
]

# Round 2：步数 / CFG 对比（采样器取 round1 结论，默认 er_sde+simple）
ROUND2 = [
    ("steps20", {"steps": 20}),
    ("steps28", {"steps": 28}),
    ("steps40", {"steps": 40}),
    ("cfg3", {"cfg": 3.0}),
    ("cfg5", {"cfg": 5.0}),
    ("cfg6", {"cfg": 6.0}),
]


# Round 3：双人复杂场景，round1 选出的两个快速方案（steps=28, cfg=4）
ROUND3 = [
    ("er_sde+simple", {"sampler_name": "er_sde", "scheduler": "simple"}),
    ("euler+simple", {"sampler_name": "euler", "scheduler": "simple"}),
]

# Round 4：双人场景下步数 / CFG 对比（采样器取 round3 结论，默认 er_sde+simple）
ROUND4 = [
    ("steps20", {"steps": 20}),
    ("steps28", {"steps": 28}),
    ("steps40", {"steps": 40}),
    ("cfg3", {"cfg": 3.0}),
    ("cfg5", {"cfg": 5.0}),
    ("cfg6", {"cfg": 6.0}),
]


def run(ex: AnimaExecutor, scene: dict, name: str, overrides: dict) -> dict:
    payload = dict(scene)
    payload.update(overrides)
    payload["filename_prefix"] = f"UR_{name}_"
    t0 = time.time()
    result = ex.generate_ultrareal(payload)
    elapsed = time.time() - t0
    files = [im["filename"] for im in result.get("images", [])]
    print(f"[{name}] {elapsed:.1f}s -> {files}", flush=True)
    return {"name": name, "elapsed_s": round(elapsed, 1), "files": files,
            "overrides": overrides, "seed": result.get("seed")}


def main() -> None:
    which = sys.argv[1] if len(sys.argv) > 1 else "round1"
    ex = AnimaExecutor(config=AnimaToolConfig())

    ok, msg = ex.check_comfyui_health()
    if not ok:
        raise SystemExit(msg)
    print(msg, flush=True)

    results = []
    if which == "round1":
        # 预热（模型加载，不计入对比）
        run(ex, SCENE_A, "warmup", {"steps": 8, "sampler_name": "euler", "scheduler": "simple", "seed": 1})
        for name, ov in ROUND1:
            results.append(run(ex, SCENE_A, f"A_{name}", ov))
    elif which == "round2":
        for name, ov in ROUND2:
            results.append(run(ex, SCENE_A, f"A2_{name}", ov))
    elif which == "round3":
        for name, ov in ROUND3:
            results.append(run(ex, SCENE_C, f"C_{name}", ov))
    elif which == "round4":
        for name, ov in ROUND4:
            results.append(run(ex, SCENE_C, f"C2_{name}", ov))
    elif which == "sceneb":
        results.append(run(ex, SCENE_B, "B_best", {}))
        # 换个 seed 再验证一次稳定性
        results.append(run(ex, SCENE_B, "B_best_s2", {"seed": 114514}))
    else:
        raise SystemExit(f"未知轮次：{which}")

    out = _PARENT / "examples" / f"ultrareal_test_{which}.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n结果已写入 {out}")


if __name__ == "__main__":
    main()
