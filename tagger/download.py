"""反推模型下载：python -m tagger.download [模型名...]（缺省下载全部）

需要访问 huggingface.co；国内可走代理（设置 HTTPS_PROXY 环境变量）或镜像
（设置 HF_ENDPOINT=https://hf-mirror.com）。
"""
from __future__ import annotations

import sys

from huggingface_hub import hf_hub_download

from .service import MODELS, model_dir

_FILES = {
    "canary": ["model.safetensors", "config.json", "selected_tags.csv"],
}


def main() -> int:
    names = sys.argv[1:] or list(_FILES)
    ok = True
    for name in names:
        if name not in MODELS:
            print(f"[skip] 未知模型：{name}（可选：{list(MODELS)}）")
            ok = False
            continue
        dest = model_dir(name)
        dest.mkdir(parents=True, exist_ok=True)
        for f in _FILES[name]:
            try:
                hf_hub_download(MODELS[name]["repo"], f, local_dir=dest)
                print(f"[ok] {MODELS[name]['repo']}/{f}", flush=True)
            except Exception as e:
                print(f"[fail] {MODELS[name]['repo']}/{f}: {str(e)[:150]}", flush=True)
                ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
