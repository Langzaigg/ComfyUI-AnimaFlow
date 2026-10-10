# 反推模型对比测试（本地推理，不依赖 ComfyUI 后端）
# 图片：复用 anima29 横评结果图（4 张 SFW + 4 张 NSFW），ground truth 取自对应 prompts.json
# 用法：python examples/reverse_tag/run_test.py
# 模型下载：python -m tagger.download
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from tagger.service import MODELS, model_dir

IMAGE_SETS = [
    ("anima29_compare_20260817_161658", ["s1_picnic", "s2_cpk_trio", "s4_rurudo_lion", "s5_senko"]),
    ("anima29_compare_nsfw_20260817_161835", ["s6_holo_onsen", "s7_holo_front", "s8_holo_cum", "s9_holo_kabejiri"]),
]


def load_ground_truth():
    gt = {}
    for run, scenes in IMAGE_SETS:
        data = json.load(open(ROOT / "examples" / "results" / run / "prompts.json", encoding="utf-8"))
        for job in data["jobs"]:
            if not job["job"].startswith("anima29__"):
                continue
            scene = job["scene"]
            if scene in scenes:
                img = ROOT / "examples" / "results" / run / "images" / f"{job['job']}.png"
                if img.exists():
                    gt[scene] = {
                        "image": img,
                        "character": job["payload"].get("character", ""),
                        "tags": job["payload"].get("tags", ""),
                    }
    return gt


def fmt_tags(d, limit=None):
    items = list(d.items())[:limit] if limit else d.items()
    return ", ".join(f"{k} ({v:.2f})" for k, v in items)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default=",".join(MODELS))
    args = ap.parse_args()

    gt = load_ground_truth()
    missing = [s for s, v in gt.items() if not v["image"].exists()]
    assert not missing, f"missing images: {missing}"

    ts = time.strftime("%Y%m%d_%H%M%S")
    out_dir = ROOT / "examples" / "results" / f"reverse_tag_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    all_results = {}
    for name in args.models.split(","):
        name = name.strip()
        if name not in MODELS:
            print(f"[skip] {name}: 未注册（可选：{list(MODELS)}）")
            continue
        d = model_dir(name)
        if not d.exists():
            print(f"[skip] {name}: {d} 不存在（请先 python -m tagger.download {name}）")
            continue
        print(f"[load] {name} ...")
        t0 = time.perf_counter()
        tagger = MODELS[name]["cls"](d)
        print(f"[load] {name} 完成，{time.perf_counter() - t0:.1f}s")
        for scene, info in gt.items():
            r = tagger.tag(info["image"])
            all_results.setdefault(scene, {})[name] = r
            print(f"[tag] {name} / {scene}: {r['seconds']:.2f}s, "
                  f"rating={list(r['rating'])[:1]} char={list(r['character'])[:3]} "
                  f"general={len(r['general'])} tags")

    (out_dir / "results.json").write_text(
        json.dumps(all_results, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = ["# 反推模型对比测试\n"]
    for scene, info in gt.items():
        lines.append(f"## {scene}")
        lines.append(f"- 图片：`{info['image'].relative_to(ROOT)}`")
        lines.append(f"- 原始角色字段：{info['character'] or '(无)'}")
        lines.append(f"- 原始 tags 节选：{info['tags'][:200]}...")
        for name, r in all_results.get(scene, {}).items():
            lines.append(f"\n### {name}（{r['seconds']:.2f}s）")
            lines.append(f"- rating: {fmt_tags(r['rating'])}")
            lines.append(f"- character: {fmt_tags(r['character'], 5) or '(无)'}")
            lines.append(f"- character top5（含低于阈值）: {fmt_tags(r['character_top5'])}")
            for cat, tags in r.get("other", {}).items():
                lines.append(f"- {cat}: {fmt_tags(tags, 10)}")
            lines.append(f"- general top30: {fmt_tags(r['general'], 30)}")
        lines.append("")
    (out_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"\n结果已保存: {out_dir}")


if __name__ == "__main__":
    main()
