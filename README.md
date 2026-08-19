# AnimaFlow

> 前身 ComfyUI-AnimaTool。把 ComfyUI 上的 Anima 系列模型包装成 AI Agent 可直接调用的统一 Tool Use API。

<p align="center">
  <img src="assets/hero.webp" alt="AnimaFlow Demo" width="100%">
</p>

<p align="center">
  Cursor / Claude / Gemini / OpenAI → MCP / HTTP API → ComfyUI → Anima 模型
</p>

## 特性

- **多工作流统一 API**：base / turbo / 2.9B / Aura 等多模型，通过 `workflow` 参数切换
- **工作流发现 API**：`GET /anima/workflows` 返回全部工作流的 schema、知识与弃用状态，下游服务启动时动态拉取即可，工作流增删改无需额外适配
- **三种接入方式**：MCP Server（图片原生显示在聊天窗口）、ComfyUI 内置 HTTP API、独立 FastAPI / CLI
- **结构化提示词**：按各模型规范自动拼接（tag 系 / 自然语言系各自匹配）
- **14 种长宽比预设**（21:9 ~ 9:21）、`repeat` / `batch_size` 批量生成、历史记录与 reroll

![Screenshot](assets/screenshot.webp)

## 安装

**方式一（推荐）**：ComfyUI Manager 搜索 "Anima Tool" 安装，重启 ComfyUI。

**方式二：手动安装**

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/Moeblack/ComfyUI-AnimaTool.git
pip install -r ComfyUI-AnimaTool/requirements.txt
```

所需模型文件（按工作流选用，文件名可用环境变量覆盖）：

| 文件 | 路径 | 说明 |
|------|------|------|
| `anima-preview.safetensors` | `models/diffusion_models/` | Anima base UNET |
| `anima29B_v10.safetensors` | `models/diffusion_models/` | Anima 2.9B UNET |
| `qwen_3_06b_base.safetensors` | `models/text_encoders/` | Qwen3 CLIP |
| `qwen_image_vae.safetensors` | `models/vae/` | VAE |

模型下载：[circlestone-labs/Anima on Hugging Face](https://huggingface.co/circlestone-labs/Anima)。各工作流对应的具体模型文件见其 schema / knowledge 文档。

## 使用

### 方式 1：MCP Server（推荐，图片原生显示）

在 Cursor 项目根目录创建 `.cursor/mcp.json`：

```json
{
  "mcpServers": {
    "anima-tool": {
      "command": "C:\\ComfyUI\\.venv\\Scripts\\python.exe",
      "args": ["C:\\ComfyUI\\custom_nodes\\ComfyUI-AnimaTool\\servers\\mcp_server.py"]
    }
  }
}
```

重启 Cursor 后直接对 AI 说「画一个穿白裙的少女在花园里，竖屏 9:16，safe」即可。详见 [MCP_SETUP.md](MCP_SETUP.md)。

> 云端/远程 ComfyUI 或不想装到 custom_nodes：可用独立 PyPI 包 `uvx --from comfyui-animatool animatool-mcp`，仅通过 ComfyUI 标准 API 工作。

### 方式 2：ComfyUI 内置 HTTP API

启动 ComfyUI 后自动注册：

| 路由 | 方法 | 说明 |
|------|------|------|
| `/anima/workflows` | GET | **列出所有工作流**（含描述与弃用状态），供下游动态适配 |
| `/anima/schema` | GET | Tool Schema（`?workflow=` 选择，缺省 base） |
| `/anima/knowledge` | GET | 专家知识（`?workflow=` 选择，缺省 base） |
| `/anima/generate` | POST | 生成（body 顶层 `workflow` 字段选择；支持 `repeat` 批量） |
| `/anima/history` | GET | 最近生成历史 |
| `/anima/reroll` | POST | 基于历史记录重新生成 |

```bash
curl -X POST "http://127.0.0.1:8188/anima/generate" \
  -H "Content-Type: application/json" \
  -d '{"workflow":"anima29_turbo","aspect_ratio":"3:4","count":"1girl","tags":"white dress, smile, garden"}'
```

### 方式 3：独立 FastAPI / CLI

```bash
pip install fastapi uvicorn
python -m servers.http_server   # http://127.0.0.1:8000/docs
python -m servers.cli --help
```

## 工作流一览

`GET /anima/workflows` 始终返回最新列表（下游应以此为准）：

| 工作流 | 说明 |
|--------|------|
| `anima29_turbo` | Anima 2.9B + Turbo LoRA（cfg=1，默认 8 步）——速度优先推荐 |
| `anima29_rdbt` | Anima 2.9B + rdbt v2.0 双 LoRA（cfg=1，默认 16 步）——质量/速度均衡最优 |
| `anima29` | Anima 2.9B 完整 UNET（cfg 3.5-5，默认 30 步）——质量优先 |
| `aura` / `aura_speed` | AuraAnima 2.9B Int8 量化，精度重视（er_sde+beta, 12 步）/ 速度重视（euler+simple, 10 步），显存约为 BF16 一半 |
| `base` | Anima base 1.0 完整字段工作流（默认） |
| `turbo_v1` / `aesthetic_v1` | Turbo 1.0 独立 UNET / Aesthetic 1.0 高质量微调 |
| `ultrareal` / `silvermoon` | 写实照片风微调 / Silvermoon 混合模型 |
| `turbo` / `kira*` / `nova` / `miao*` | 已弃用（deprecated），仅保留兼容 |

各工作流的提示词规范、参数范围见对应的 schema 与 knowledge 文档（`schemas/`、`knowledge/`，或经 `/anima/schema?workflow=xxx` 获取）。

## 配置

全部配置可用环境变量覆盖，常用项：

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `COMFYUI_URL` | `http://127.0.0.1:8188` | ComfyUI 地址（远程/Docker 时修改） |
| `COMFYUI_MODELS_DIR` | - | models 根目录，启用模型预检查与 LoRA sidecar 列表 |
| `ANIMATOOL_OUTPUT_DIR` | `./outputs` | 图片输出目录 |
| `ANIMATOOL_TIMEOUT` | `600` | 生成超时（秒） |
| `ANIMATOOL_TARGET_MP` | `1.0` | 目标像素数（MP） |

完整配置与远程部署说明见 wiki。

## 文档

- [📖 Wiki](https://github.com/Moeblack/ComfyUI-AnimaTool/wiki)：安装教程、提示词指南、API 参考、模型对比
- [MCP_SETUP.md](MCP_SETUP.md)：MCP 客户端配置（含酒馆 SillyTavern）
- [MIGRATION.md](MIGRATION.md)：版本迁移说明与下游 API 适配指南
- [CURSOR_SKILL.md](CURSOR_SKILL.md)：给 Cursor/Windsurf 的 Agent Skill
- [CHANGELOG.md](CHANGELOG.md)：更新记录

## 相关项目

- [SillyTavern MCP Client](https://github.com/Moeblack/sillytavern-mcp-client)：酒馆 MCP 客户端（stdio + Streamable HTTP）
- [SillyTavern Tool Use Fix](https://github.com/Moeblack/sillytavern-tooluse-fix)：工具调用体验修复
- [AnimaLoraToolkit](https://github.com/Moeblack/AnimaLoraToolkit)：Anima LoRA/LoKr 训练工具，产物可直接配合本工具 `loras` 参数使用

## License

AGPL-3.0 License - see [LICENSE](LICENSE) for details.
