"""反推模型推理核心（纯 torch/timm，不依赖 ComfyUI）。

模型目录为 timm 格式（WD14/EVA02 系列）：config.json + model.safetensors + selected_tags.csv。
"""
from __future__ import annotations

import csv
import json
import time
from pathlib import Path
from typing import Dict, Union

import numpy as np
from PIL import Image

ImageInput = Union[str, Path, Image.Image]


def _load_image(image: ImageInput) -> Image.Image:
    if isinstance(image, Image.Image):
        return image.convert("RGB")
    return Image.open(image).convert("RGB")


class TimmTagger:
    """WD14/EVA02 系列标签器（timm safetensors 原生权重，无需转 ONNX）。"""

    def __init__(self, model_dir, device="cpu"):
        import torch
        import timm
        from safetensors.torch import load_file

        model_dir = Path(model_dir)
        cfg = json.load(open(model_dir / "config.json", encoding="utf-8"))
        pre_cfg = cfg.get("pretrained_cfg", {})
        self.input_size = pre_cfg.get("input_size", [3, 448, 448])[1]
        self.mean = np.array(pre_cfg.get("mean", [0.5, 0.5, 0.5]), dtype=np.float32)
        self.std = np.array(pre_cfg.get("std", [0.5, 0.5, 0.5]), dtype=np.float32)

        self._torch = torch
        self.model = timm.create_model(cfg["architecture"], pretrained=False,
                                       num_classes=cfg["num_classes"])
        self.model.load_state_dict(load_file(model_dir / "model.safetensors"))
        self.model.eval().to(device)
        self.device = device

        self.tags = []  # (name, category)：category 0=general 4=character 9=rating
        with open(model_dir / "selected_tags.csv", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                self.tags.append((row["name"], row["category"]))

    def _preprocess(self, image: Image.Image):
        size = self.input_size
        ratio = size / max(image.size)
        new_size = (max(1, round(image.width * ratio)), max(1, round(image.height * ratio)))
        image = image.resize(new_size, Image.BICUBIC)
        canvas = Image.new("RGB", (size, size), (255, 255, 255))
        canvas.paste(image, ((size - new_size[0]) // 2, (size - new_size[1]) // 2))
        arr = np.asarray(canvas, dtype=np.float32) / 255.0
        arr = (arr - self.mean) / self.std
        return self._torch.from_numpy(arr.transpose(2, 0, 1)).unsqueeze(0)

    def tag(self, image: ImageInput, general_threshold=0.35, character_threshold=0.75,
            rating_threshold=0.35) -> Dict:
        torch = self._torch
        x = self._preprocess(_load_image(image)).to(self.device)
        t0 = time.perf_counter()
        with torch.no_grad():
            probs = torch.sigmoid(self.model(x))[0].cpu().numpy()
        elapsed = time.perf_counter() - t0

        result = {"rating": {}, "character": {}, "general": {}, "other": {}, "seconds": elapsed}
        char_probs = []
        for (name, cat), p in zip(self.tags, probs):
            p = float(p)
            if cat == "9" and p >= rating_threshold:
                result["rating"][name] = p
            elif cat == "4":
                char_probs.append((name, p))
                if p >= character_threshold:
                    result["character"][name] = p
            elif cat == "0" and p >= general_threshold:
                result["general"][name] = p
        char_probs.sort(key=lambda kv: -kv[1])
        result["character_top5"] = dict(char_probs[:5])
        for k in ("rating", "character", "general"):
            result[k] = dict(sorted(result[k].items(), key=lambda kv: -kv[1]))
        return result
