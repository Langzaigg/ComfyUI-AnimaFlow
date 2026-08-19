# 安装指南

## 前置要求

- ComfyUI 已安装并可正常运行
- Python 3.10+
- 足够的显存（推荐 8GB+）

## 安装方法

### 方法 1：ComfyUI Manager（推荐）

1. 打开 ComfyUI Manager
2. 搜索 "AnimaFlow"
3. 点击 Install
4. 重启 ComfyUI

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
[ComfyUI-AnimaTool] Routes registered: /anima/health, /anima/schema, /anima/knowledge, /anima/generate
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

## kira_turbo 工作流额外依赖（可选）

`kira_turbo` 工作流的主用采样组合为 `res_2s` + `bong_tangent`（官方推荐，指令遵循度实测最高），来自 **RES4LYF** 自定义节点。未安装 RES4LYF、或设备执行该组合报错（如 fp64 不支持）时无需处理——接口会自动回落到 ComfyUI 内置的 `res_multistep` + `simple` 完成生成（返回结果带 `sampler_fallback: true` 标记），但指令遵循度略逊于主组合。其余工作流（含 `kira`）无此依赖。

## 故障排除

### 模型加载失败？

1. 确认文件路径正确
2. 确认文件完整（检查文件大小）
3. 确认 ComfyUI 版本支持 Anima 模型

### 路由未注册？

1. 确认 `ComfyUI-AnimaTool` 目录在 `custom_nodes/` 下
2. 检查 Python 导入错误（查看 ComfyUI 启动日志）
3. 确认依赖已安装
