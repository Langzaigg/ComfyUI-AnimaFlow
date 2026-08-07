# API 参考

ComfyUI-AnimaTool 提供三种 API 接入方式：

1. **MCP Server** - Cursor/Claude 原生图片显示
2. **ComfyUI HTTP API** - 随 ComfyUI 启动
3. **独立 FastAPI Server** - 可独立部署

## MCP Tools

### generate_anima_image

生成二次元/插画图片。

#### 参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `prompt_hint` | string | 否 | - | 人类可读的需求摘要 |
| `aspect_ratio` | string | 否 | - | 长宽比（如 `16:9`、`9:16`） |
| `width` | integer | 否 | - | 宽度（像素，16 的倍数，会覆盖 aspect_ratio） |
| `height` | integer | 否 | - | 高度（像素，16 的倍数，会覆盖 aspect_ratio） |
| `quality_meta_year_safe` | string | **是** | - | 质量/年份/安全标签（必须含 safe/sensitive/nsfw/explicit） |
| `count` | string | **是** | - | 人数（`1girl`、`2girls`、`1boy`） |
| `character` | string | 否 | `""` | 角色名 |
| `series` | string | 否 | `""` | 作品名 |
| `appearance` | string | 否 | `""` | 外观描述（发色、眼睛等） |
| `artist` | string | **否** | `""` | 画师（必须带 `@`，如 `@fkey`）。仅在用户明确要求时填写 |
| `style` | string | 否 | `""` | 画风 |
| `tags` | string | **是** | - | Danbooru 标签（逗号分隔） |
| `nltags` | string | 否 | `""` | 自然语言补充 |
| `environment` | string | 否 | `""` | 环境/光影 |
| `neg` | string | **是** | - | 负面提示词 |
| `steps` | integer | 否 | 35 | 步数 |
| `cfg` | number | 否 | 4.5 | CFG |
| `sampler_name` | string | 否 | `er_sde` | 采样器 |
| `seed` | integer | 否 | 随机 | 种子 |
| `repeat` | integer | 否 | 1 | 提交几次独立生成任务（queue 模式，每次独立随机 seed）。范围 1-16 |
| `batch_size` | integer | 否 | 1 | 单次任务内生成几张（latent batch，更吃显存）。范围 1-4 |
| `loras` | array | 否 | `[]` | 追加 LoRA（仅 UNET）。每项 `{"name": "...", "weight": 1.0}`，name 必须与 `/models/loras` 返回值一致 |

> 总生成张数 = `repeat` × `batch_size`。推荐使用 `repeat`（默认方式，显存友好）。

#### 返回

MCP Server 返回：
- `ImageContent`: 图片（base64 编码，原生显示）
- `TextContent`: 历史记录提示（如 `已保存为历史记录 #12。可用 reroll_anima_image(source="last") 重新生成。`）

---

### list_anima_models

查询 ComfyUI 当前可用的模型文件列表。

#### 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `model_type` | string | **是** | `loras` / `diffusion_models` / `vae` / `text_encoders` |

> 当 `model_type=loras` 时，强制只返回存在同名 `.json` sidecar 元数据文件的 LoRA。

#### 返回

`TextContent`：JSON 格式的模型列表。

---

### list_anima_history

查看最近的图片生成历史记录。

#### 参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `limit` | integer | 否 | 5 | 返回最近几条（1-50） |

#### 返回

`TextContent`：每行一条记录摘要，格式：

```
#12 [2026-02-06 17:30] @fkey | 1girl, white hair, blue eyes | seed:42 | 872x1160
#11 [2026-02-06 17:28] @ciloranko | 2girls, school uniform | seed:78923 | 1024x1024
```

---

### reroll_anima_image

基于历史记录重新生成图片。引用一条历史记录作为基础参数，可选覆盖部分参数。

#### 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `source` | string | **是** | `"last"`（最近一条）或历史 ID（如 `"12"` 或 `"#12"`） |
| *其他* | - | 否 | 所有 `generate_anima_image` 的参数均可作为覆盖项 |

> - `seed` 默认自动随机（出不同画面）。手动指定 seed 可复现相同画面。
> - `repeat` 同样可用，如 `reroll_anima_image(source="last", repeat=3)` 一次出 3 张。

#### 典型用法

| 场景 | 调用 |
|------|------|
| 再 roll 一次 | `reroll_anima_image(source="last")` |
| 再来 3 张 | `reroll_anima_image(source="last", repeat=3)` |
| 换个画师再来 | `reroll_anima_image(source="last", artist="@ciloranko")` |
| 回溯第 3 条记录 | `reroll_anima_image(source="3")` |
| 保持 seed 不变加 LoRA | `reroll_anima_image(source="last", seed=原seed, loras=[...])` |

#### 返回

与 `generate_anima_image` 一致（图片 + 历史记录提示）。

---

## ComfyUI HTTP API

随 ComfyUI 启动自动注册以下路由。

### 主 API（推荐）：workflow 参数

`/anima/schema`、`/anima/knowledge`、`/anima/generate` 是统一主 API，通过 `workflow` 参数返回/使用各个不同工作流的信息，缺省为 `base`：

| workflow | 说明 |
|----------|------|
| `base`（缺省） | Base 1.0：完整字段工作流 |
| `turbo` | Turbo 0.2（Legacy）：base UNET + turbo LoRA 快速生成 |
| `turbo_v1` | Turbo 1.0：独立完整 UNET 快速生成 |
| `aesthetic_v1` | Aesthetic 1.0：高质量微调完整 UNET |
| `kira` | Kira (Kirazuri Anima v4)：Anima 微调 UNET（cfg 4-5，steps 30-50，er_sde） |
| `kira_turbo` | Kira Turbo：Kira + 8-step LoRA（cfg=1，steps=8，默认 1536²） |

- `GET /anima/schema?workflow=turbo_v1` — 返回对应工作流的 Tool Schema
- `GET /anima/knowledge?workflow=turbo_v1` — 返回对应工作流的专家知识
- `POST /anima/generate?workflow=turbo` 或在请求体顶层加 `"workflow": "turbo"` — 用对应工作流生成
- `GET /anima/workflows` — 列出所有可用工作流及缺省值

旧的独立端点（`/anima/schema_turbo`、`/anima/knowledge_turbo`、`/anima/generate_turbo` 等）保持兼容、继续可用，等价于主 API 固定 workflow 的写法。

### GET /anima/health

健康检查。

**响应**：

```json
{
  "status": "ok",
  "comfyui_url": "http://127.0.0.1:8188",
  "tool_root": "/path/to/ComfyUI-AnimaTool"
}
```

### GET /anima/schema

获取 Tool Schema（JSON Schema 格式）。`?workflow=` 选择工作流，缺省 `base`。

**响应**：

```json
{
  "name": "generate_anima_image",
  "description": "...",
  "parameters": { ... }
}
```

### GET /anima/knowledge

获取专家知识库。`?workflow=` 选择工作流，缺省 `base`。

**响应**：

```json
{
  "anima_expert": "...",
  "artist_list": "...",
  "prompt_examples": "..."
}
```

### POST /anima/generate

执行图片生成。支持 `repeat` 参数一次提交多个独立任务。`?workflow=` 或请求体顶层 `"workflow"` 选择工作流，缺省 `base`。

**请求体**：

```json
{
  "aspect_ratio": "3:4",
  "quality_meta_year_safe": "masterpiece, best quality, newest, year 2025, sensitive",
  "count": "1girl",
  "artist": "@mignon",
  "tags": "upper body, smile, white dress",
  "neg": "worst quality, low quality, blurry, bad hands, nsfw",
  "repeat": 1
}
```

**响应**：

```json
{
  "success": true,
  "prompt_id": "uuid-xxx",
  "positive": "masterpiece, best quality, ...",
  "negative": "worst quality, ...",
  "seed": 1234567890,
  "width": 872,
  "height": 1160,
  "history_id": 12,
  "images": [
    {
      "filename": "AnimaTool__00001_.png",
      "subfolder": "",
      "type": "output",
      "view_url": "http://127.0.0.1:8188/view?filename=...",
      "saved_path": "/path/to/outputs/AnimaTool__00001_.png",
      "base64": "...",
      "mime_type": "image/png",
      "data_url": "data:image/png;base64,...",
      "markdown": "![AnimaTool__00001_.png](data:image/png;base64,...)"
    }
  ]
}
```

> `repeat > 1` 时，响应为 `{"success": true, "results": [...]}`，每项结构同上。

### GET /anima/history

查看最近生成历史。

**参数**：`?limit=5`（默认 5，范围 1-50）

**响应**：

```json
{
  "count": 2,
  "records": [
    {
      "id": 12,
      "timestamp": "2026-02-06T17:30:00",
      "params": { "artist": "@fkey", "tags": "...", "..." : "..." },
      "positive_text": "masterpiece, ...",
      "seed": 1234567890,
      "width": 872,
      "height": 1160
    }
  ]
}
```

### POST /anima/reroll

基于历史记录重新生成。

**请求体**：

```json
{
  "source": "last",
  "overrides": {
    "artist": "@ciloranko",
    "repeat": 3
  }
}
```

> `source`：`"last"` 或历史 ID（如 `"12"`）。`overrides` 中的参数会覆盖原始记录。
> seed 不指定则自动随机。

**响应**：与 `/anima/generate` 一致。

---

### Turbo 0.2（Legacy）端点

Turbo 0.2 使用 base UNET + turbo LoRA 实现快速生成。简化字段。

#### GET /anima/schema_turbo

返回 Turbo 0.2 Tool Schema（简化字段，`aspect_ratio` 限 5 种，不含 `style`/`tags`/`environment`/`neg`）。

#### GET /anima/knowledge_turbo

返回 Turbo 0.2 专家知识：

```json
{
  "turbo_expert": "...",
  "artist_list": "...",
  "turbo_examples": "..."
}
```

#### POST /anima/generate_turbo

执行 Turbo 0.2 快速生成（cfg=1, steps=10, 内置 turbo LoRA）。

**请求体**：

```json
{
  "quality_meta_year_safe": "masterpiece, best quality, highres, newest, year 2025, safe",
  "count": "1girl",
  "character": "hatsune miku",
  "series": "vocaloid",
  "appearance": "long teal hair, blue eyes, school uniform",
  "artist": "@rurudo",
  "tags": "standing, looking at viewer, smile, upper body, classroom, sunlight. A girl is standing in a classroom. Soft daylight.",
  "aspect_ratio": "1:1"
}
```

> `tags` 以标准 Danbooru 标签（逗号分隔）为主；没有特别符合的标准 tag 时用英文自然语言句子补充，不要编造不标准 tag。多角色时 `appearance` 留空、`tags` 禁止包含角色外貌信息，外貌在自然语言部分逐角色分别描述。`cfg`/`steps`/`neg` 由后端固定，无需传入。

**响应**：与 `/anima/generate` 一致。

---

### Turbo v1.0 端点

Turbo v1.0 是独立完整 UNET 模型，不依赖 LoRA。简化字段，拥有 `neg` 字段。

#### GET /anima/schema_turbo_v1

返回 Turbo v1.0 Schema（简化字段，包含 `neg`，`cfg` 范围 0.7-1，`steps` 范围 8-12）。

#### POST /anima/generate_turbo_v1

执行 Turbo v1.0 生成。

**请求体**：

```json
{
  "quality_meta_year_safe": "masterpiece, best quality, safe",
  "count": "1girl",
  "character": "holo (spice and wolf)",
  "series": "spice and wolf",
  "appearance": "long brown hair, red eyes, wolf ears, brown cloak",
  "artist": "@rurudo",
  "tags": "standing, looking at viewer, smile, holding, apple, upper body. A beautiful girl with long flowing brown hair and bright red eyes, wearing a brown hooded cloak. She has fluffy wolf ears and a bushy tail, holding a red apple, smiling at the viewer.",
  "neg": "bad anatomy, bad hands, bad feet, extra fingers, missing fingers, text, watermark, logo, nsfw, explicit",
  "aspect_ratio": "1:1",
  "steps": 10,
  "cfg": 1.0
}
```

> `tags` 以标准 Danbooru 标签为主，无标准 tag 的内容用英文自然语言补充。`steps` 默认 10，`cfg` 默认 1。`neg` 可选，留空时后端按安全等级自动填充。

**响应**：与 `/anima/generate` 一致。

---

### Aesthetic v1.0 端点

Aesthetic v1.0 是完整 UNET 模型，在高质量图像上微调。简化字段与 Turbo v1.0 相同，但 `cfg`/`steps` 范围与 base 一致。

#### GET /anima/schema_aesthetic_v1

返回 Aesthetic v1.0 Schema（字段与 Turbo v1.0 相同，`cfg` 范围 3-8，`steps` 范围 20-60）。

#### POST /anima/generate_aesthetic_v1

执行 Aesthetic v1.0 生成。请求/响应格式与 `/anima/generate_turbo_v1` 一致，但 `steps` 默认 35，`cfg` 默认 4。

---

### 新模型共享端点

#### GET /anima/knowledge_new_models

返回 Turbo v1.0 / Aesthetic v1.0 共享的专家知识：

```json
{
  "new_models_expert": "...",
  "artist_list": "...",
  "new_models_examples": "..."
}
```

---

### Kira 工作流

Kira (Kirazuri Anima v4) 是 Anima 的微调模型，通过主 API 的 `workflow` 参数使用（无独立兼容端点）：

| workflow | 说明 |
|----------|------|
| `kira` | 完整 UNET，cfg 4-5（默认 4.5），steps 30-50（默认 40），采样器固定 `er_sde` |
| `kira_turbo` | Kira + 8-step LoRA，固定 cfg=1 / steps=8（payload 传入无效），主用 `res_2s`+`bong_tangent`（需 RES4LYF 节点），不可用自动回落 `res_multistep`+`simple`，默认 1024×1024 |

```bash
# Schema / 知识
curl "http://127.0.0.1:8188/anima/schema?workflow=kira_turbo"
curl "http://127.0.0.1:8188/anima/knowledge?workflow=kira"

# 生成
curl -X POST "http://127.0.0.1:8188/anima/generate?workflow=kira_turbo" \
  -H "Content-Type: application/json" \
  -d '{"quality_meta_year_safe":"masterpiece, best quality, very aesthetic, sensitive","count":"1girl","character":"yukikaze (azur lane)","series":"azur lane","tags":"A girl charges across the ocean surface amid a naval battle, her rigging cannons firing. Explosions and black smoke rise in the background under a cloudy blue sky."}'
```

与 base Anima 的提示词差异：

- 标签顺序：`[质量/美学/安全] [角色] [作品] [画师] [人数] [通用标签]`（人数标签靠后，由后端自动组装）
- 美学标签：`very aesthetic` / `aesthetic` 为本模型特有，可引导模型自带审美倾向
- `tags` 使用**英文自然语言完整句子**（至少 2-3 句、写足细节），不要用标签堆叠——短提示词/纯标签在本模型上容易概念串扰
- 风格标签：`painterly`、`chiaroscuro`、`ligne claire`、`flat color`、`no lineart`、`blending`、`traditional media`、`oil painting \(medium\)`、`watercolor \(medium\)`

---

### 模型对比

| 模型 | 端点 | cfg | steps | neg | 字段 |
|------|------|-----|-------|-----|------|
| Base 1.0 | `/anima/generate` | 3-8, 默认 4 | 20-60, 默认 35 | 有 | 全部 14 字段 |
| Turbo 0.2 | `/anima/generate_turbo` | 固定 1 | 固定 10 | 无 | 简化（无 style/tags/environment/neg） |
| Turbo 1.0 | `/anima/generate_turbo_v1` | 0.7-1, 默认 1 | 8-12, 默认 10 | 有 | 简化（无 style/tags/environment） |
| Aesthetic 1.0 | `/anima/generate_aesthetic_v1` | 3-8, 默认 4 | 20-60, 默认 35 | 有 | 简化（无 style/tags/environment） |
| Kira | `/anima/generate?workflow=kira` | 4-5, 默认 4.5 | 30-50, 默认 40 | 有 | 简化（无 style/tags/environment） |
| Kira Turbo | `/anima/generate?workflow=kira_turbo` | 固定 1 | 固定 8 | 有 | 简化，默认 1024×1024 |

> 所有模型的 `tags` 均以标准 Danbooru 标签（逗号分隔）为主；没有特别符合的标准 tag 时用自然语言补充描述，不要编造不标准 tag。多角色时 `appearance` 留空、`tags` 禁止包含角色外貌信息，每个角色的外观在自然语言部分（base 为 `nltags`，其余为 `tags` 的自然语言句子）逐角色分别描述。Turbo 1.0 / Aesthetic 1.0 的 `quality_meta_year_safe` 格式为 `masterpiece, best quality, <rating>`。

---

### 启动

```bash
cd ComfyUI-AnimaTool
pip install fastapi uvicorn
python -m servers.http_server
```

默认运行在 `http://127.0.0.1:8000`。

### 路由

| 路由 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 欢迎信息 |
| `/health` | GET | 健康检查 |
| `/workflows` | GET | 列出所有可用工作流 |
| `/schema` | GET | Tool Schema（`?workflow=` 选择工作流，缺省 base） |
| `/knowledge` | GET | 专家知识（`?workflow=` 选择工作流，缺省 base） |
| `/generate` | POST | 执行生成（支持 repeat；`?workflow=` 或 body 中 `workflow` 字段选择工作流，缺省 base） |
| `/history` | GET | 查看生成历史 |
| `/reroll` | POST | 基于历史重新生成 |
| `/docs` | GET | Swagger UI |

### Swagger UI

访问 `http://127.0.0.1:8000/docs` 查看交互式 API 文档。

---

## CLI 工具

```bash
cd ComfyUI-AnimaTool
python -m servers.cli --help
```

### 示例

```bash
python -m servers.cli \
  --aspect-ratio "3:4" \
  --quality "masterpiece, best quality, newest, year 2025, sensitive" \
  --count "1girl" \
  --artist "@fkey" \
  --tags "upper body, smile, white dress" \
  --neg "worst quality, low quality, blurry"
```
