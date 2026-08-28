# 安装指南

## 前置要求

- ComfyUI 已安装并可正常运行
- Python 3.10+
- 足够的显存（推荐 8GB+）

## 安装方法

### 方法 1：ComfyUI Manager

> ComfyUI Manager 暂时无法安装本插件，请使用方法 2 手动安装。

### 方法 2：手动安装

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/Langzaigg/ComfyUI-AnimaFlow.git
pip install -r ComfyUI-AnimaFlow/requirements.txt
```

## 模型文件

确保以下模型文件已放置到 ComfyUI 对应目录：

### 必需文件

| 文件 | 路径 | 说明 | 大小 |
|------|------|------|------|
| `anima-preview.safetensors` | `models/diffusion_models/` | Anima UNET | ~3.5GB |
| `qwen_3_06b_base.safetensors` | `models/text_encoders/` | Qwen3 CLIP | ~1.2GB |
| `qwen_image_vae.safetensors` | `models/vae/` | VAE | ~330MB |

### 按工作流选用的附加模型

| 文件 | 路径 | 用于工作流 |
|------|------|-----------|
| `anima-base-v1.0.safetensors` | `models/diffusion_models/` | base |
| `anima29B_v10.safetensors` | `models/diffusion_models/` | anima29 系 / aura 系底座 |
| `anima-turbo-v1.0.safetensors`（实为 turbo 1.1） | `models/diffusion_models/` | turbo_v1 |
| `anima-aesthetic-v1.0.safetensors` | `models/diffusion_models/` | aesthetic_v1 |
| `anima29b-p1-turbo1.1.safetensors` | `models/diffusion_models/` | fuse（融合 UNET，非官方拼接衍生） |
| `Turbo-ANIMA-v2.9.safetensors` | `models/loras/` | anima29_turbo（强度 0.8） |
| `anima29b-turbo-v2.9-remap.safetensors` | `models/loras/` | anima29_turbo 的重映射 LoRA 替代（免补丁） |
| `rdbt_v2.0_base_anima2.9b_p1_lora.safetensors` + `rdbt_v2.0_distilled_addon_anima2.9b_p1_lora.safetensors` | `models/loras/` | anima29_rdbt（双 LoRA 串联） |
| `auranima29B_qpolaP101Int8W8a8.safetensors` | `models/diffusion_models/` | aura / aura-speed（Int8 量化） |
| `Anima_UltraReal_finetune_v3.safetensors` | `models/diffusion_models/` | ultrareal |
| `silvermoonmixAnima_v23.safetensors` | `models/diffusion_models/` | silvermoon |

> **anima29_turbo 的 LoRA 注意**：Anima 2.9B 是 base 的 28→40 块深度扩展，28 块布局的原版 `Turbo-ANIMA-v2.9.safetensors` 需安装 `ComfyUI-Anima-2.9B-loraPatch` 自定义节点做运行时索引修正；或改用离线重映射版 `anima29b-turbo-v2.9-remap.safetensors`（免补丁，payload 传 `lora_name` 覆盖，与原版+补丁同 seed 逐像素等价）。

### 下载方式

**方式 1：Hugging Face**

访问 [circlestone-labs/Anima](https://huggingface.co/circlestone-labs/Anima) 下载。

**方式 2：命令行**

```bash
# 需要安装 huggingface_hub
pip install huggingface_hub

# 下载模型
huggingface-cli download circlestone-labs/Anima anima-preview.safetensors --local-dir ./
```

## 验证安装

1. 启动 ComfyUI
2. 查看控制台，应该看到：

```
[ComfyUI-AnimaTool] Routes registered: /anima/health, /anima/workflows, /anima/schema, /anima/knowledge, /anima/generate (主 API，支持 workflow 参数，缺省 base), /anima/generate_turbo_v1, /anima/generate_aesthetic_v1, /anima/schema_turbo_v1, /anima/schema_aesthetic_v1, /anima/knowledge_new_models (兼容接口)
```

3. 访问 `http://127.0.0.1:8188/anima/health`，应该返回：

```json
{"status": "ok", "comfyui_url": "http://127.0.0.1:8188", ...}
```

## MCP Server 额外依赖

如果要使用 MCP Server（Cursor 原生图片显示），需要额外安装：

```bash
pip install mcp
```

详细配置见 [MCP Server 配置](MCP-Setup)。

## 故障排除

### 模型加载失败？

1. 确认文件路径正确
2. 确认文件完整（检查文件大小）
3. 确认 ComfyUI 版本支持 Anima 模型

### 路由未注册？

1. 确认 `ComfyUI-AnimaTool` 目录在 `custom_nodes/` 下
2. 检查 Python 导入错误（查看 ComfyUI 启动日志）
3. 确认依赖已安装
