from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Tuple


def _get_env_bool(key: str, default: bool) -> bool:
    """从环境变量获取布尔值"""
    val = os.environ.get(key, "").lower()
    if val in ("1", "true", "yes", "on"):
        return True
    if val in ("0", "false", "no", "off"):
        return False
    return default


def _get_env_float(key: str, default: float) -> float:
    """从环境变量获取浮点数"""
    val = os.environ.get(key)
    if val:
        try:
            return float(val)
        except ValueError:
            pass
    return default


def _get_env_int(key: str, default: int) -> int:
    """从环境变量获取整数"""
    val = os.environ.get(key)
    if val:
        try:
            return int(val)
        except ValueError:
            pass
    return default


# 默认模型文件名（preview 版本）
DEFAULT_UNET_NAME = "anima-preview.safetensors"
DEFAULT_CLIP_NAME = "qwen_3_06b_base.safetensors"
DEFAULT_VAE_NAME = "qwen_image_vae.safetensors"

# base v1.0 模型文件名
BASE10_UNET_NAME = "anima-base-v1.0.safetensors"

# 新模型 v1.0 文件名
TURBO10_UNET_NAME = "anima-turbo-v1.1.safetensors"
AESTHETIC10_UNET_NAME = "anima-aesthetic-v1.1.safetensors"

# UltraReal (Danrisi/UltraReal_FineTune_Anima_base1_v3) 模型文件名
# Anima base1.0 的真实系微调：@ 前缀相机/灯光标签 + 自然语言 + @年份 score_N 后缀
ULTRAREAL_UNET_NAME = "Anima_UltraReal_finetune_v3.safetensors"
# UltraReal 默认采样组合（实测得出，详见 knowledge/ultrareal_expert.md）
ULTRAREAL_SAMPLER = ("er_sde", "simple")
ULTRAREAL_STEPS = 28
ULTRAREAL_CFG = 4.0

# Silvermoon (silvermoonmixAnima_v2329B，2.9B 架构) 模型文件名
# 官方推荐：Euler a + normal，CFG 4-5，steps 20-28；Turbo 版 CFG 1，steps 8-12。
# 官方建议从无负面开始（示例图均无负面生成），故默认负面为空。
# 画师 tag 必须带 @ 前缀（如 @makihitsuji），否则效果很弱。
SILVERMOON_UNET_NAME = "silvermoonmixAnima_v2329B.safetensors"
SILVERMOON_SAMPLER = ("euler_ancestral", "normal")
SILVERMOON_STEPS = 24
SILVERMOON_CFG = 4.5
# Turbo 变体（silvermoonmixAnima_v2329BTurbo）：官方推荐 CFG 1，steps 8-12，无负面
SILVERMOON_TURBO_UNET_NAME = "silvermoonmixAnima_v2329BTurbo.safetensors"
SILVERMOON_TURBO_STEPS = 10

# Anima 2.9B v1.0（preview）：Anima base 的层扩展微调（28→40 层，~2.9B 参数），
# 追加 1.7M 二次元/插画样本训练，知识截止 2026-07。训练数据无 score 标签（不用 score_N）。
# 官方推荐：Euler + sgm-uniform（或 res-multistep + linear-quadratic），steps 28-50（最高质量 50），
# CFG 3.5-5，分辨率 812x1216 / 1152x1536 / 1536x1536；提示词越详细越好。
ANIMA29_UNET_NAME = "anima29B_v10.safetensors"
ANIMA29_SAMPLER = ("euler", "sgm_uniform")
ANIMA29_STEPS = 30
ANIMA29_CFG = 4.0

# Anima 2.9B Turbo LoRA v1.1（Turbo-ANIMA-v4 重映射到 2.9B 40 块架构，见
# examples/remap_turbo_v4_lora_29b.py；原始 LoRA 出自
# https://civitai.com/models/2619830/turbo-for-anima-less-steps）：配合 CFG 1 + 8-12 步使用
ANIMA29_TURBO_LORA_NAME = "anima29b-turbolora1.1.safetensors"
ANIMA29_TURBO_STEPS = 8

# Fuse v1.1：silvermoonmixAnima_v2329BTurbo 与 anima-turbo-v1.1 按 0.3/0.7 加权融合
# （见 examples/merge_sm29t_fuse_turbo.py；silvermoon 出自
# https://civitai.com/models/2639339/silvermoonmix-anima-evolved）。
# 横评（examples/results/anima29_newmodels_20260918_101609/report.md）：0.3 为甜区，
# 采样沿用 silvermoon turbo 官方参数（Euler a + normal，CFG 固定 1，10 步，无负面）。
FUSE_UNET_NAME = "anima29b-sm29t-fuse1.1.safetensors"
FUSE_SAMPLER = ("euler_ancestral", "normal")
FUSE_STEPS = 10

# Fuse v1.0（已过期，仅保留兼容）：anima-turbo-v1.1 与 anima29B_v10 融合（turbo 权重 0.8）；
# cfg 1.2 使文字类负面生效（压制假签名/水印）
FUSE10_UNET_NAME = "anima29b-p1-turbo1.1.safetensors"
FUSE_DEFAULT_NEGATIVE = "text, letters, sign, logo, watermark, signature, username, artist name"

# rdbt v2.0 LoRA（anima2.9b p1）：base + distilled addon 双串联，CFG 1、默认 16 步。
# 探针实测（examples/results/anima29_rdbt_probe_20260818_210509/report.md）：
# 双 LoRA 16 步质量追平/反超 anima29 30 步，耗时仅 1/3-1/4；仅 base 在 16/20/25 步下均不可用
# （16 步不收敛、25 步大部分收敛但仍追不平双 LoRA 且更慢），distilled addon 是必需组件。
RDBT_BASE_LORA_NAME = "rdbt_v2.0_base_anima2.9b_p1_lora.safetensors"
RDBT_DISTILLED_ADDON_LORA_NAME = "rdbt_v2.0_distilled_addon_anima2.9b_p1_lora.safetensors"
RDBT_STEPS = 16

# AuraAnima 2.9B qpolaP101 Int8 W8a8 量化模型文件名
# anima29 的量化变体：质量与 BF16 同档（48 张完整场景测试无量化 artifacts），
# 速度与 BF16 同档（~2.7 s/步），体积/显存约减半。
# aura=精度重视（er_sde+beta 12 步，完整测试 11/12 场景质量第一），
# aura-speed=速度重视（euler+simple 10 步，批量/简单场景/复杂构图噱头用）。
# 风格质量标签三选一：anime color（动画，配画师 tag）/ photo real（写实，默认，勿配画师 tag）/ real skin（写实肤质，同勿配画师 tag）。
AURA_UNET_NAME = "auranima29B_qpolaP101Int8W8a8.safetensors"
AURA_SAMPLER = ("er_sde", "beta")
AURA_STEPS = 12
AURA_SPEED_SAMPLER = ("euler", "simple")
AURA_SPEED_STEPS = 10
AURA_CFG = 5.0

# CyberRealistic Anima v7.0 Turbo BF16（写实向微调，基于 Anima Turbo V1.1）模型文件名
# 官方推荐：CFG 1-1.5，steps 8-12；基于 turbo 1.1，采样沿用 turbo 系组合 euler。
# turbo 系规则：默认 cfg 1.0（负面惰性），写 neg 时默认 cfg_neg 1.2 使负面生效。
CYBERREAL_UNET_NAME = "cyberrealisticAnima_v70Turbo_bf16.safetensors"
CYBERREAL_SAMPLER = ("euler", None)
CYBERREAL_STEPS = 10
CYBERREAL_CFG = 1.0


@dataclass
class AnimaToolConfig:
    """
    Anima 工具配置。

    所有配置项都支持通过环境变量覆盖：
    - COMFYUI_URL: ComfyUI Web 服务地址（默认 http://127.0.0.1:8188）
    - ANIMATOOL_DOWNLOAD_IMAGES: 是否下载图片到本地（默认 true）
    - ANIMATOOL_OUTPUT_DIR: 图片输出目录
    - ANIMATOOL_TIMEOUT: 生成超时时间（秒，默认 600）
    - ANIMATOOL_POLL_INTERVAL: 轮询间隔（秒，默认 1）
    - ANIMATOOL_TARGET_MP: 目标像素数（MP，默认 1.0）
    - ANIMATOOL_ROUND_TO: 分辨率对齐倍数（默认 16）

    示例：
        # Windows PowerShell
        $env:COMFYUI_URL = "http://192.168.1.100:8188"

        # Linux/macOS
        export COMFYUI_URL=http://192.168.1.100:8188

        # Cursor MCP 配置中
        {
          "mcpServers": {
            "anima-tool": {
              "command": "python",
              "args": ["mcp_server.py"],
              "env": {
                "COMFYUI_URL": "http://192.168.1.100:8188"
              }
            }
          }
        }
    """

    # ComfyUI 服务地址
    # 支持：本地 (127.0.0.1)、局域网 (192.168.x.x)、Docker (host.docker.internal)
    comfyui_url: str = field(
        default_factory=lambda: os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188")
    )

    # 下载模式：把 /view 拿到的图片保存到本地
    download_images: bool = field(
        default_factory=lambda: _get_env_bool("ANIMATOOL_DOWNLOAD_IMAGES", True)
    )
    output_dir: Path = field(
        default_factory=lambda: Path(
            os.environ.get("ANIMATOOL_OUTPUT_DIR", "")
        ) if os.environ.get("ANIMATOOL_OUTPUT_DIR") else Path(__file__).resolve().parent.parent / "outputs"
    )

    # 轮询历史接口等待执行完成
    timeout_s: float = field(
        default_factory=lambda: _get_env_float("ANIMATOOL_TIMEOUT", 600.0)
    )
    poll_interval_s: float = field(
        default_factory=lambda: _get_env_float("ANIMATOOL_POLL_INTERVAL", 1.0)
    )

    # 月份切换后（当月第一个图片任务）自动清理 ComfyUI 原生 output 目录，
    # 使图片编号从 00001 重新计数；配合 outputs/YYYY-MM/ 按月归档，
    # 避免编号重置后与月份文件夹内同名旧图覆盖（预览依赖归档副本，不受清理影响）。
    # 可用 ANIMATOOL_CLEAN_OUTPUT_MONTHLY=0 关闭。
    clean_output_monthly: bool = field(
        default_factory=lambda: _get_env_bool("ANIMATOOL_CLEAN_OUTPUT_MONTHLY", True)
    )
    # ComfyUI 原生 output 目录；留空时优先从 ComfyUI 的 folder_paths 自动探测，
    # 探测失败（独立进程/远程场景）则跳过清理。可用 ANIMATOOL_COMFYUI_OUTPUT_DIR 手动指定。
    comfyui_output_dir: Optional[Path] = field(
        default_factory=lambda: (
            Path(os.environ["ANIMATOOL_COMFYUI_OUTPUT_DIR"])
            if os.environ.get("ANIMATOOL_COMFYUI_OUTPUT_DIR") else None
        )
    )

    # 分辨率生成：当只给 aspect_ratio 时，按目标像素数估算宽高
    target_megapixels: float = field(
        default_factory=lambda: _get_env_float("ANIMATOOL_TARGET_MP", 1.048576)
    )
    # 宽高向上取整到 round_to 的倍数
    # 注意：Anima 基于 Cosmos 架构，VAE 缩放 8 倍后还需被 spatial_patch_size=2 整除
    # 所以必须是 8×2=16 的倍数，否则会报错 "should be divisible by spatial_patch_size"
    round_to: int = field(
        default_factory=lambda: _get_env_int("ANIMATOOL_ROUND_TO", 16)
    )

    # -------------------------
    # 模型配置
    # -------------------------
    # ComfyUI models 根目录（用于模型预检查）
    # 如果不设置，则尝试自动探测，探测失败则跳过预检查（远程 ComfyUI 场景）
    comfyui_models_dir: Optional[Path] = field(
        default_factory=lambda: (
            Path(os.environ["COMFYUI_MODELS_DIR"]) if os.environ.get("COMFYUI_MODELS_DIR") else 
            (Path.cwd() / "models" if (Path.cwd() / "models").exists() else 
             (Path(__file__).resolve().parent.parent.parent.parent / "models" if (Path(__file__).resolve().parent.parent.parent.parent / "models").exists() else None))
        )
    )

    # 模型文件名（可通过环境变量或参数覆盖）
    unet_name: str = field(
        default_factory=lambda: os.environ.get("ANIMATOOL_UNET_NAME", DEFAULT_UNET_NAME)
    )
    clip_name: str = field(
        default_factory=lambda: os.environ.get("ANIMATOOL_CLIP_NAME", DEFAULT_CLIP_NAME)
    )
    vae_name: str = field(
        default_factory=lambda: os.environ.get("ANIMATOOL_VAE_NAME", DEFAULT_VAE_NAME)
    )

    # 是否启用模型预检查（默认启用，但需要设置 COMFYUI_MODELS_DIR）
    check_models: bool = field(
        default_factory=lambda: _get_env_bool("ANIMATOOL_CHECK_MODELS", True)
    )

    def get_model_paths(self) -> dict:
        """
        返回模型文件的预期路径（相对于 ComfyUI models 目录）。
        """
        return {
            "unet": ("diffusion_models", self.unet_name),
            "clip": ("text_encoders", self.clip_name),
            "vae": ("vae", self.vae_name),
        }

    def check_models_exist(self) -> Tuple[bool, List[str]]:
        """
        检查模型文件是否存在。
        
        Returns:
            (all_exist, missing_files): 是否全部存在，缺失的文件列表
        """
        if not self.comfyui_models_dir:
            # 未配置 models 目录，跳过检查
            return True, []
        
        models_dir = Path(self.comfyui_models_dir)
        if not models_dir.exists():
            return False, [f"ComfyUI models 目录不存在: {models_dir}"]
        
        missing = []
        for model_type, (subdir, filename) in self.get_model_paths().items():
            model_path = models_dir / subdir / filename
            if not model_path.exists():
                missing.append(f"{model_type}: {subdir}/{filename}")
        
        return len(missing) == 0, missing
