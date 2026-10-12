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

### reverse_tag_image

图像反推：分析本地图片，返回 Danbooru 标签（分级/角色/一般）及映射好的 Anima 生成字段，可直接作为 `generate_anima_image` 的参考。本地推理（XPU 可用时自动加速，否则 CPU 单张约 3.5s），不需要 ComfyUI 后端运行。

模型固定为 [wd-eva02-tagger-2026-canary](https://huggingface.co/ashen-sensored/wd-eva02-tagger-2026-canary)（Danbooru 标准标签 16,473 个，含 2024-07 后新角色），首次使用前下载：

```bash
python -m tagger.download
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `image_path` | string | 二选一 | 本机图片文件路径 |
| `image_base64` | string | 二选一 | base64 编码图片（可带 `data:` 前缀） |
| `general_threshold` | number | 否 | 一般标签阈值（默认 0.35） |
| `character_threshold` | number | 否 | 角色标签阈值（默认 0.75） |
| `max_tags` | integer | 否 | Anima 字段映射中最多保留的一般标签数（默认 40） |

#### 返回

JSON 文本：`rating` / `character` / `general`（含置信度）、`character_top5`（含低于阈值的候选）、`seconds`，以及 `anima` 字段映射：

```json
"anima": {
  "quality_meta_year_safe": "safe",
  "count": "1girl",
  "character": "senko (sewayaki kitsune no senko-san)",
  "series": "sewayaki kitsune no senko-san",
  "tags": "tail, animal_ears, fox_tail, blue_eyes, ..."
}
```

> 分级映射：`general→safe`、`sensitive→sensitive`、`questionable→nsfw`、`explicit→explicit`。
> 角色/作品标签已按 Anima 规范去除下划线；`series` 取自角色标签的括号部分。

---

## ComfyUI HTTP API

随 ComfyUI 启动自动注册以下路由。

### 主 API（推荐）：workflow 参数

`/anima/schema`、`/anima/knowledge`、`/anima/generate` 是统一主 API，通过 `workflow` 参数返回/使用各个不同工作流的信息，缺省为 `base`：

| workflow | 说明 |
|----------|------|
| `base`（缺省） | Base 1.0：完整字段工作流 |
| `turbo_v1` | Turbo 1.0（实为 1.1）：独立完整 UNET 快速生成 |
| `fuse` | Fuse v1.2：Silvermoon29 Turbo × turbo 1.1 融合 UNET + NextGen 2.9bV1 LoRA@0.3 快速生成（cfg 固定 1，无负面，Euler a，steps 8-12 默认 10） |
| `fuse1.0`（已过期） | Fuse v1.0：turbo 1.1 × Anima 2.9B P1 融合 UNET（内置文字类负面，默认 cfg 1.2） |
| `aesthetic_v1` | Aesthetic 1.0：高质量微调完整 UNET |
| `ultrareal` | UltraReal (UltraReal_FineTune_Anima_base1_v3)：真实系微调，写实照片风（@前缀标签+自然语言+@年份/score 后缀三段式） |
| `silvermoon` | Silvermoon (silvermoonmixAnima_v2329B)：混合模型（cfg 4-5，steps 20-28 默认 24，Euler a + normal，无负面），score_N 质量前缀 |
| `silvermoon_turbo` | Silvermoon v2329B Turbo：快速变体（cfg 1-1.6 默认 1，steps 8-12 默认 10，Euler a + normal，无负面） |
| `anima29` | Anima 2.9B v1.0：base 层扩展微调（cfg 3.5-5，steps 28-50 默认 30，euler + sgm_uniform） |
| `anima29_turbo` | Anima 2.9B + anima29b-turbolora1.1 LoRA（Turbo-ANIMA-v4 重映射版，强度 0.8，cfg 1-1.6，steps 8-12 默认 8） |
| `anima29_rdbt` | Anima 2.9B + rdbt v2.0 双 LoRA（cfg 1-1.6，steps 8-32 默认 16） |
| `aura` | AuraAnima 2.9B Int8 量化·精度重视（er_sde+beta，steps 默认 12，cfg 4-5） |
| `aura-speed` | AuraAnima 2.9B Int8 量化·速度重视（euler+simple，steps 默认 10，cfg 4-5） |
| `cyberreal` | CyberRealistic Anima v7.0 Turbo：写实插画微调（基于 Anima Turbo V1.1，cfg 1-1.5 默认 1，steps 8-12 默认 10，euler），score_N + 风格槽提示词 |

- `GET /anima/schema?workflow=turbo_v1` — 返回对应工作流的 Tool Schema
- `GET /anima/knowledge?workflow=turbo_v1` — 返回对应工作流的专家知识
- `POST /anima/generate?workflow=fuse` 或在请求体顶层加 `"workflow": "fuse"` — 用对应工作流生成
- `GET /anima/workflows` — 列出所有可用工作流及缺省值

旧的独立端点（`/anima/generate_turbo_v1`、`/anima/generate_aesthetic_v1`、`/anima/schema_turbo_v1`、`/anima/schema_aesthetic_v1`、`/anima/knowledge_new_models`）保持兼容、继续可用，等价于主 API 固定 workflow 的写法。

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

### 人设库 `/anima/characters`

给 Web 画图前端、聊天机器人等下游共用的一份角色人设。数据存插件目录 `data/characters.json`（可用环境变量 `ANIMATOOL_CHARACTERS_FILE` 改位置），写入原子替换并保留一份 `.bak`，文件被外部改写后按 mtime 自动重载，无需重启 ComfyUI。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/anima/characters` | 列表，支持 `?q=` 关键词、`?label=` 分组、`?nsfw=0` 排除 NSFW |
| POST | `/anima/characters` | 新建（201；重名 409） |
| GET | `/anima/characters/schema` | 人设记录的 JSON Schema（完整字段约束） |
| POST | `/anima/characters/match` | 文本按名称/别名匹配人设 |
| POST | `/anima/characters/import` | 批量导入（`merge` / `replace`） |
| GET | `/anima/characters/{id}` | 单个人设 |
| PUT / PATCH | `/anima/characters/{id}` | 部分更新（只改传了的字段） |
| DELETE | `/anima/characters/{id}` | 删除 |

一条人设（完整约束见 `GET /anima/characters/schema`）：

```json
{
  "id": "c_1a2b3c4d", "name": "兔酱", "aliases": ["兔兔"],
  "tag_name": "rabbit girl", "series": "original", "count": "1girl",
  "tags": "rabbit girl, light brown hair, long hair, amber eyes, rabbit ears",
  "description": "浅茶色及腰长发，琥珀色眼睛，长兔耳……",
  "outfits": [{"name": "秋装", "tags": "white shirt, brown pinafore dress", "description": "", "default": true}],
  "artist": "@makihitsuji",
  "labels": ["本家"], "nsfw": false, "source": "web", "extra": {},
  "created_at": 1790700000.0, "updated_at": 1790700000.0
}
```

- 只存画图用的外观信息：组合提示词 = `count + tag_name + series + tags + 选中造型的 tags`，画师单独放 `artist`；自然语言只有 `description` 一个字段（外观描述，绘制注意/禁忌也写在这里），性格/称呼等对话设定不在人设库维护。
- 早期草案的 `notes`（绘制注意）在读取时并入 `description`，`personality` 不再维护（读取时丢弃）；客户端再传这两个字段会被忽略。
- 名称全库唯一（大小写不敏感，重名 409）；`tags` 保存时规范为 `a, b, c`（去空项、去重、去零宽字符）。
- id 可省略（自动生成 `c_xxxxxxxx`），不能与 `schema` / `match` / `import` 重名。
- `match` 要求 ASCII 名有词边界（`cy` 不命中 `cyan`）；某人设的全部命中都落在另一个人设更长的命中词里时丢弃（「Chaos前世」只命中别名为 `Chaos前世` 的那条）。

**列表**（响应带 `revision` 与 `ETag: "chars-<revision>"`，可用 `If-None-Match` 拿 304）：

```json
{
  "schema_version": 1, "revision": 12, "updated_at": 1790700000.0,
  "total": 27, "characters": [ { 人设记录 } ]
}
```

**匹配**：`POST /anima/characters/match`，请求 `{"text": "今天兔酱很开心", "limit": 10}`，响应 `{"matches": [{"id": "...", "name": "兔酱", "matched": "兔酱", "character": {...}}]}`（按首次出现位置排序）。

**导入**：`POST /anima/characters/import`，请求 `{"characters": [...], "mode": "merge"}`。
`merge` 先按 `id` 再按名称（大小写不敏感）匹配已有人设并部分更新，都没有则新建；`replace` 清空后整体写入，需额外传 `"confirm_replace": true`。响应 `{"ok": true, "created": [...], "updated": [...], "errors": [{"index", "name", "error"}], "revision", "total"}`。

---

### 图像反推 `/anima/reverse_tag`

本地反推图片为 Danbooru 标签（模型固定 [wd-eva02-tagger-2026-canary](https://huggingface.co/ashen-sensored/wd-eva02-tagger-2026-canary)，timm 原生权重；XPU 可用时自动加速，否则 CPU 单张约 3.5s），不经过 ComfyUI 后端。首次使用前下载模型：`python -m tagger.download`。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/anima/tagger/models` | 模型信息与下载状态 |
| POST | `/anima/reverse_tag` | 反推图片 → 标签 + Anima 字段映射 |

**请求**（`image_base64` 与 `image_path` 二选一）：

```json
{
  "image_path": "D:/path/to/image.png",
  "general_threshold": 0.35,
  "character_threshold": 0.75,
  "max_tags": 40
}
```

**响应**：`success` / `device` / `seconds` / `rating` / `character` / `general` / `character_top5`，以及映射好的 `anima` 字段（`quality_meta_year_safe` / `count` / `character` / `series` / `tags`，可直接作为 `/anima/generate` payload 的参考）。分级映射：`general→safe`、`sensitive→sensitive`、`questionable→nsfw`、`explicit→explicit`。

```json
{
  "success": true, "model": "canary", "device": "xpu", "seconds": 0.22,
  "rating": {"general": 0.98},
  "character": {"senko_(sewayaki_kitsune_no_senko-san)": 0.99},
  "anima": {
    "quality_meta_year_safe": "safe", "count": "1girl",
    "character": "senko (sewayaki kitsune no senko-san)",
    "series": "sewayaki kitsune no senko-san",
    "tags": "tail, animal_ears, fox_tail, blue_eyes, ..."
  }
}
```

---

### Turbo v1.0 端点

Turbo v1.0 是独立完整 UNET 模型，不依赖 LoRA。简化字段，拥有 `neg` 字段。

#### GET /anima/schema_turbo_v1

返回 Turbo v1.0 Schema（简化字段，包含 `neg`，`cfg` 范围 1.0-1.6，`steps` 范围 8-12）。

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

> `tags` 以标准 Danbooru 标签为主，无标准 tag 的内容用英文自然语言补充。`steps` 默认 10，`cfg` 默认 1（写 `neg` 时默认 1.2 使负面生效）。`neg` 可选，留空时后端按安全等级自动填充。

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
  "simple_expert": "...",
  "artist_list": "...",
  "simple_examples": "..."
}
```

---

### UltraReal 工作流

UltraReal (UltraReal_FineTune_Anima_base1_v3) 是 Anima base1.0 的真实系微调，生成写实照片风图片，通过主 API 的 `workflow=ultrareal` 使用：

| 项 | 值 |
|----|----|
| 模型 | `Anima_UltraReal_finetune_v3.safetensors`（`models/diffusion_models`） |
| 采样 | `er_sde` + `simple`，steps 默认 28，cfg 默认 4.0 |

```bash
curl -X POST "http://127.0.0.1:8188/anima/generate?workflow=ultrareal" \
  -H "Content-Type: application/json" \
  -d '{"tags":"@smartphone_photo @amateur_photo @candid_photo @available_light","nltags":"A close-up selfie of Shiroko from Blue Archive. She has short silver-grey hair, grey wolf ears and a black scarf.","quality_meta_year_safe":"@sfw @2025 score_8"}'
```

字段与其他工作流不同（必填 `tags` / `nltags` / `quality_meta_year_safe`）：

- `tags`：@ 开头的相机/灯光/风格标签（如 `@film_photo` `@direct_flash` `@mirror_reflection`）
- `nltags`：英文自然语言完整句子描述场景，角色外观必须写在这里
- `quality_meta_year_safe`：安全等级（`@sfw`/`@nsfw`）+ 模拟年份（`@1995`~`@2025`）+ 质量分（`score_5`~`score_9`）
- 负面提示词留空即可，默认内置低分标签（score_1-4）+ 安全对立约束

---

### 模型对比

| 模型 | 端点 | cfg | steps | neg | 字段 |
|------|------|-----|-------|-----|------|
| Base 1.0 | `/anima/generate` | 3-8, 默认 4 | 20-60, 默认 35 | 有 | 全部 14 字段 |
| Turbo 1.0 | `/anima/generate_turbo_v1` | 1-1.6，默认 1（写 neg 时 1.2） | 8-12, 默认 10 | 有 | 简化（无 style/tags/environment） |
| Fuse | `/anima/generate?workflow=fuse` | 固定 1（负面惰性，无负面） | 8-12, 默认 10 | 无 | 简化（无 style/tags/environment） |
| Fuse 1.0（已过期） | `/anima/generate?workflow=fuse1.0` | 1-1.6，默认 1.2（内置文字类负面常驻） | 8-12, 默认 8 | 有（内置默认） | 简化（无 style/tags/environment） |
| Aesthetic 1.0 | `/anima/generate_aesthetic_v1` | 3-8, 默认 4 | 20-60, 默认 35 | 有 | 简化（无 style/tags/environment） |
| UltraReal | `/anima/generate?workflow=ultrareal` | 默认 4 | 默认 28 | 有（内置默认） | 三段式（tags 前缀 + nltags 自然语言 + 后缀） |
| Silvermoon | `/anima/generate?workflow=silvermoon` | 4-5, 默认 4.5 | 20-28, 默认 24 | 无 | 简化（无 style/tags/environment），score_N 质量前缀 |
| Silvermoon Turbo | `/anima/generate?workflow=silvermoon_turbo` | 1-1.6，默认 1（写 neg 时 1.2） | 8-12, 默认 10 | 无（默认惰性） | 简化（无 style/tags/environment），score_N 质量前缀 |
| Anima 2.9B | `/anima/generate?workflow=anima29` | 3.5-5, 默认 4 | 28-50, 默认 30 | 有 | 简化（无 style/tags/environment），无质量词前缀 |
| Anima 2.9B Turbo | `/anima/generate?workflow=anima29_turbo` | 1-1.6，默认 1（写 neg 时 1.2） | 8-12, 默认 8 | 有 | 简化，无质量词前缀 |
| Anima 2.9B rdbt | `/anima/generate?workflow=anima29_rdbt` | 1-1.6，默认 1（写 neg 时 1.2） | 8-32, 默认 16 | 有 | 简化，无质量词前缀 |
| Aura | `/anima/generate?workflow=aura` | 4-5, 默认 5 | 8-30, 默认 12 | 有 | 简化，风格质量标签三选一 |
| Aura-speed | `/anima/generate?workflow=aura-speed` | 4-5, 默认 5 | 8-30, 默认 10 | 有 | 简化，风格质量标签三选一 |
| CyberReal | `/anima/generate?workflow=cyberreal` | 1-1.5，默认 1（写 neg 时 1.2） | 8-12, 默认 10 | 有（默认惰性） | 简化，score_N + 风格槽 |

> 简化字段工作流（turbo_v1 / fuse / aesthetic_v1 / silvermoon / anima29 系 / aura 系）的 `tags` 为英文自然语言完整句子；base 的自然语言在 `nltags`，ultrareal 为三段式。`appearance` 等标签字段只填有明确指代的标准 Danbooru tag，不要编造。多角色时 `appearance` 留空、`tags` 禁止包含角色外貌信息，每个角色的外观在自然语言部分逐角色分别描述。

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
| `/tagger/models` | GET | 反推模型信息与下载状态 |
| `/reverse_tag` | POST | 图像反推（字段同 ComfyUI 路由 `/anima/reverse_tag`） |
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
