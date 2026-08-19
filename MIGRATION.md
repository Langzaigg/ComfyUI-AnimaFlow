# 迁移参考：AnimaFlow 2026-08 变更

本文档汇总两轮变更：2026-08-18 版本（Anima 2.9B、弃用标记与发现 API，见第 0 节）与此前一轮变更（主 API 统一化、提示词策略调整、Kira 工作流新增、项目重命名，见第 1-6 节），供从旧版 AnimaTool 迁移时参考。

---

## 0. 2026-08-18 版本：Anima 2.9B、弃用标记与工作流发现 API

### 0.1 变更摘要

| 项 | 内容 |
|----|------|
| 新增工作流 | `anima29`（Anima 2.9B v1.0：base 层扩展微调，cfg 3.5-5，steps 28-50 默认 30，euler + sgm_uniform）；`anima29_turbo`（加载 `Anima-2.9B_Turbo-BF16.safetensors` LoRA，cfg=1，steps 8-12 默认 8）；`anima29_rdbt`（rdbt v2.0 双 LoRA：base→distilled addon 串联，cfg=1，steps 默认 16——实测追平/反超 anima29 30 步，anima29 系性价比最优） |
| 新增工作流（2026-08-19） | `aura` / `aura-speed`（AuraAnima 2.9B qpolaP101 Int8 W8a8 量化模型：质量/速度与 BF16 anima29 同档，显存约减半）。`aura` 为精度重视档（er_sde+beta，steps 默认 12），`aura-speed` 为速度重视档（euler+simple，steps 默认 10）；cfg 4.0-5.0 可调、默认 5.0，负面提示词正常生效。提示词规则与 anima29 系一致（year 2026 + 安全等级、无质量/分数词、无下划线），唯一新增：**风格质量标签三选一**——`photo real`（写实照片风，默认，用户无指定时用此）/ `anime color`（动画平涂风，配 artist 画师标签效果最佳）/ `real skin`（写实肤质风）。注意：写实路线（photo real / real skin）下**不要带画师 tag**（画师画风会接管画面丢失写实感）；版权角色还原场景建议 anime color（写实标签会真人化、丢失动画角色特征） |
| 弃用工作流 | `turbo`(0.2) / `kira` / `kira_turbo` / `nova` / `miao` / `miao_turbo` 标记 `deprecated: true`——仍可调通，但不要在新流程中使用 |
| int8 量化版移除 | `anima29_int8` / `anima29_int8_turbo` 预设已删除（XPU 实测更慢且加载不稳定）；确需量化版时在 `anima29` 工作流下用 payload `unet_name` 手动覆盖 |
| cfg=1 负面规范 | 所有 turbo 工作流（cfg=1）：**不要写负面提示词**，不想要的元素用正向写法规避（不要提及，用正向描述替代）；仅 nsfw/explicit 分级时在 `tags` 末尾保留无码提示词 `no mosaic, uncensored` |
| 实验性参数 | `neg_scale` / `nag_scale` / `anima_nag_scale`（cfg=1 强制负面生效的三种互斥引导）：实测对场景级概念全部无效、仅个别简单属性部分生效，默认关闭，仅保留供后续模型复测 |
| 部署相关 | 启动脚本精简为 `run_intel_gpu.bat`（去掉了 --highvram 与自动重启逻辑），新增 `--reserve-vram 1` 为系统预留 1GB 显存；`ComfyUI-Anima-NAG` 插件仅实验性参数需要，可不装 |

### 0.2 工作流发现 API

`GET /anima/workflows`（ComfyUI 插件路由）与 `GET /workflows`（独立 FastAPI 服务）返回**当前全部工作流及其元信息**：

```json
{
  "default": "base",
  "workflows": {
    "anima29_turbo": {
      "description": "Anima 2.9B Turbo：Anima 2.9B + Turbo-BF16 LoRA 快速生成（cfg=1, steps 8-12 默认 8）",
      "deprecated": false,
      "endpoints": {
        "generate": "POST /anima/generate（body 带 \"workflow\": \"anima29_turbo\"）",
        "schema": "GET /anima/schema?workflow=anima29_turbo",
        "knowledge": "GET /anima/knowledge?workflow=anima29_turbo"
      }
    },
    "turbo": {
      "description": "Turbo 0.2（Legacy）：base UNET + turbo LoRA 快速生成（cfg=1, steps=10）",
      "deprecated": true,
      "endpoints": { "generate": "...", "schema": "...", "knowledge": "..." }
    }
  }
}
```

### 0.3 下游服务免适配接入约定

下游服务**不要硬编码工作流清单、参数字段或提示词规则**，按以下约定接入即可对工作流的增/删/改免疫：

1. **会话开始（或缓存到期）时拉一次 `/workflows`**，以返回的 `workflows` 键集为可选工作流全集，`default` 为缺省工作流；每个条目的一句话 `description` 可直接展示给用户或注入 LLM 上下文做选型依据。
2. **过滤 `deprecated: true`**：默认不向终端用户提供弃用工作流（或仅作 legacy 标识展示），新流程一律不绑定它们。
3. **参数校验/表单生成走 `GET /schema?workflow=X`**：字段集、默认值、取值范围以各工作流自己的 schema 为准——它们确实因模型而异（如 `kira_turbo` 不暴露 steps/cfg，`anima29_turbo` 多出实验性引导参数）。schema 各字段的 `description` 本身就是面向调用方/LLM 的最新填写规范（含 cfg=1 负面策略），应直接使用而不是另写模板。
4. **提示词规则走 `GET /knowledge?workflow=X`**：把返回的专家知识（字段写法、质量前缀、模型限制、示例）整体注入生成侧上下文，不要把各模型的提示词规则写死在下游代码里。
5. **生成统一调 `POST /generate`**，body 顶层带 `"workflow": "X"`（ComfyUI 路由为 `/anima/generate`）。不要再调用各工作流的旧独立端点（`/anima/generate_turbo` 等）——它们仅为兼容保留，**新增工作流不会有对应的独立端点**。
6. **错误自愈**：不传 `workflow` 时服务端使用 `default`；传了未知值会返回 400 并在错误信息里列出当前可选值，下游捕获后可重新拉取 `/workflows` 自愈。

按以上约定，服务端新增工作流（如未来的 anima30）、删除弃用工作流、调整默认参数或提示词规范时，下游服务零改动。

---

## 1. 主 API 统一：workflow 参数

### 变更内容

`/anima/schema`、`/anima/knowledge`、`/anima/generate` 三个主接口现在通过 `workflow` 参数返回/使用各个不同工作流的信息，**缺省为 `base`**。新增 `GET /anima/workflows` 列出全部可用工作流。

| workflow | 说明 |
|----------|------|
| `base`（缺省） | Base 1.0：完整字段工作流 |
| `turbo` | Turbo 0.2（Legacy）：base UNET + turbo LoRA |
| `turbo_v1` | Turbo 1.0：独立完整 UNET 快速生成 |
| `aesthetic_v1` | Aesthetic 1.0：高质量微调完整 UNET |
| `kira` | Kira (Kirazuri Anima v4)：cfg 4-5，steps 30-50，er_sde |
| `kira_turbo` | Kira + 8-step LoRA：cfg=1，steps=8，res_2s+bong_tangent（主用，需 RES4LYF 节点；不可用自动回落 res_multistep+simple），默认 1024×1024 |

### 用法

```bash
# schema / knowledge：query 参数
curl "http://127.0.0.1:8188/anima/schema?workflow=kira_turbo"
curl "http://127.0.0.1:8188/anima/knowledge?workflow=kira"

# generate：query 参数或请求体顶层 "workflow" 字段
curl -X POST "http://127.0.0.1:8188/anima/generate?workflow=turbo_v1" -d '{...}'
curl -X POST "http://127.0.0.1:8188/anima/generate" -d '{"workflow": "kira", "count": "1girl", ...}'
```

非法 workflow 返回 400 并列出可选值。

### 兼容性

- 不传 `workflow` 时行为与旧版完全一致（base）。
- 旧独立端点全部保留、行为不变：`/anima/schema_turbo`、`/anima/knowledge_turbo`、`/anima/generate_turbo`、`/anima/generate_turbo_v1`、`/anima/generate_aesthetic_v1`、`/anima/schema_turbo_v1`、`/anima/schema_aesthetic_v1`、`/anima/knowledge_new_models`。它们内部改走统一注册表。
- 独立 FastAPI 服务（`servers/http_server.py`）同步支持：`/schema`、`/knowledge`、`/generate` 的 `workflow` 参数（query 或 body 字段）及 `/workflows`。

---

## 2. 提示词策略变更（所有模型）

### 新策略

1. `tags` 使用**标准 Danbooru 标签**（逗号分隔）。
2. 没有特别符合的标准 tag 时，用**自然语言**描述，**不要编造不标准 tag**（如 `holding_hands_and_smiling`）——不标准 tag 会干扰模型理解、降低出图质量。
   - base：自然语言放 `nltags`
   - turbo / turbo_v1 / aesthetic_v1 / kira / kira_turbo：自然语言句子接在 `tags` 标签之后
3. **多角色时**：`tags` 中禁止任何角色外貌信息（发色、瞳色、发型、服装、饰品），`appearance` 必须留空；每个角色的外观在自然语言部分**逐角色分别描述**（base 用 `nltags`，其余用 `tags` 的自然语言句子）。

> 例外：**kira / kira_turbo 的 `tags` 固定使用全自然语言完整句子**（至少 2-3 句、写足细节），不做标签堆叠——该模型短提示词/纯标签容易概念串扰，自然语言描述对角色特征还原更好（详见第 3 节）。

### 迁移要点

- 旧用法"多角色时把所有角色外观标签一起写进 `appearance`"已废弃，改为 `appearance` 留空 + 自然语言逐角色描述。
- turbo 系此前"`tags` 直接用英文自然语言整句"的写法改为"Danbooru 标签为主 + 自然语言补充"。

### 涉及文件

- knowledge：`anima_expert.md`、`turbo_expert.md`、`new_models_expert.md`、`prompt_examples.md`、`turbo_examples.md`、`new_models_examples.md`
- schemas：4 个 schema 的 `tags` / `appearance`（及 universal 的 `nltags`、顶层 `description`）字段描述已同步为新策略

---

## 3. 新增 kira / kira_turbo 工作流

### 模型文件（需已就位）

| 用途 | 文件 | 目录 |
|------|------|------|
| Kira UNET | `anima-kirazuri-v4.safetensors` | `models/diffusion_models` |
| Kira Turbo LoRA | `kirazuri-anima-turbo-v4-8step.safetensors` | `models/loras` |

### 与 base Anima 的提示词差异

- 标签顺序：`[质量/美学/安全] [角色] [作品] [画师] [人数] [通用标签]`（人数标签靠后，后端自动组装，字段照常填写）
- `appearance` 位置经 A/B 实测：放在通用标签之前（人数之后）比紧跟角色之后还原角色特征更好，后端按此顺序组装
- `tags` **固定使用英文自然语言完整句子**（至少 2-3 句、写足细节）：该模型为标签与自然语言混合训练，短提示词/纯标签容易概念串扰，且自然语言写法对角色特征（如雪风的发色/狐耳/服装）还原明显更好
- 美学标签：`very aesthetic` / `aesthetic` 为本模型特有，引导模型自带审美倾向
- 风格标签：`painterly`、`chiaroscuro`、`ligne claire`、`flat color`、`no lineart`、`blending`、`traditional media`、`oil painting \(medium\)`、`watercolor \(medium\)`

### 采样参数（实测后固定，不对外暴露 sampler/scheduler）

| workflow | cfg | steps | sampler/scheduler | 默认分辨率 |
|----------|-----|-------|-------------------|-----------|
| `kira` | 4-5，默认 4.5 | 30-50，默认 40 | `er_sde`（固定） | ~1MP（同 base） |
| `kira_turbo` | 固定 1 | 固定 8 | 主用 `res_2s` + `bong_tangent`；不可用时自动回落 `res_multistep` + `simple` | 1024×1024 |

> `kira_turbo` 的 steps=8 / cfg=1 为代码写死，payload 中传入的 steps/cfg 一律忽略（schema 也不暴露这两个字段）。
> 自动回落：`res_2s` + `bong_tangent` 依赖 RES4LYF 自定义节点；节点未安装（400 校验失败）或执行期报错（如设备不支持 fp64）时，`generate_kira` 自动改用 `res_multistep` + `simple` 重试一次，回落后该 executor 实例后续 turbo 任务直接走回落组合，返回结果以 `sampler_fallback: true` 标记。

### 采样实测结论

共四轮实测：第一轮为雪风战斗场景（同 seed，含 base 工作流参考图）；第三轮（安装 RES4LYF 后）为岛风单人战斗场景（s1）+ 碧蓝档案白子/芹香/星野三人咖啡馆复杂场景（s2）；第四轮为 8 约束指令遵循度测试 + 换 seed 连跑稳态计时，全部 1024²。

**kira**（1024²）：

| 组合 | s1 耗时 | s2 耗时 | 质量 |
|------|--------|--------|------|
| `er_sde` 40 步 | ~70s | ~101s | 两场景均干净稳定，三人特征还原好，无文字 → **选用** |
| `sa_solver_pece` 16 步 | ~59s | ~87s | s1 与 er_sde 相当且快 ~15%；但 s2 复杂场景生成"ブルーアーカイブ"文字 LOGO、伪版权小字及手部色块异常 → 淘汰 |

**kira-turbo**（1024²，固定 8 步 cfg 1；耗时为换 seed 连跑 4 次的稳态值，同 seed 重复会命中 ComfyUI 缓存得到 ~1s 的假数据）：

| 组合 | 稳态耗时 | 质量 / 指令遵循度 |
|------|---------|-------------------|
| `res_2s` + `bong_tangent` | ~17-20s | **指令遵循度最高且最稳定**：4 场景 × 多 seed 详细对比 2 胜 3 平 0 负——复杂场景零手部/文字异常，计数约束（3 只纸鹤）唯一全对过；8 约束测试唯一全对姿势 → **选用** |
| `deis_2m` + `bong_tangent` | ~11-15s | 最接近的替补：遵循度与 res_2s 多数场景打平（n1 场景异色瞳展现更好），快 30-40%；但多人场景个别 seed 出现两处手部颜色异常（绿手/黑手）和轻微文字痕迹，计数约束同样会错。速度优先可改 `executor/config.py` 的 `KIRA_TURBO_SAMPLER` 为 `("deis_2m", "bong_tangent")` |
| `res_2m` + `bong_tangent` | ~12s | 多人场景检查点全命中，但整体偏色（高饱和青色阴影），质量逊于前两者 |
| `res_3m` + `bong_tangent` | ~16-17s | **过曝失真**：色彩溢出、暗部死黑，且出现手部绿色异常 → 淘汰 |
| `dpmpp_2m` + `sgm_uniform` | ~6s | 质量好但与 res_multistep 一样把"盘腿坐"画成抱膝坐，遵循度弱 |
| `res_multistep` + `simple` | ~8-10s | 与 dpmpp 同水平；复杂场景偶发手部色块异常（换 seed 可规避）。ComfyUI 内置，作为 res_2s 不可用时的**自动回落组合**（deis_2m/res_2m/res_3m 同属 RES4LYF，节点缺失时同样不可用，不能作回落） |

> 注：计数类约束（"正好 3 只纸鹤""正好 2 本书"）是 8 步 turbo 模型的共性弱项，两种采样器都会出错，res_2s 仅略准；`res_2s` 的 ~31s 首跑含冷加载，稳态约 17-20s。

> kira 系对文字没有硬性抑制，多人复杂场景偶发生成 LOGO/小字属模型倾向，与采样器稳定性相关（er_sde 两轮均未出现）。

### 新增文件

- `schemas/tool_schema_kira.json`、`schemas/tool_schema_kira_turbo.json`（turbo_v1 简化字段版；sampler/scheduler 实测后固定，不对外暴露）
- `knowledge/kira_expert.md`、`knowledge/kira_examples.md`（两个 kira 工作流共享）
- `executor`：`KIRA_UNET_NAME` / `KIRA_TURBO_LORA_NAME` 常量、`build_kira_positive_text`、`_inject_kira`、`generate_kira(payload, turbo=False)`

---

## 4. 其他变更

- 移除了 schema 描述中"接口支持并行调用"的相关描述（仅 `tool_schema_universal.json` 一处）。

---

## 5. 项目重命名：AnimaFlow

项目更名为 **AnimaFlow**，文件夹由 `ComfyUI-AnimaTool` 更名为 `ComfyUI-AnimaFlow`。

### 已变更

- 文件夹名、README 标题与路径引用、`pyproject.toml` 的 `name` / `DisplayName` / 描述

### 刻意保持不变（兼容性）

| 项 | 值 | 原因 |
|----|----|------|
| HTTP 路由 | `/anima/*` | 已有集成直接调用 |
| 环境变量 | `ANIMATOOL_*`、`COMFYUI_*` | 改名会破坏现有部署配置 |
| 输出文件名前缀 | `AnimaTool_*` 等 | 与历史归档一致 |
| MCP server 名 | `anima-tool` | 客户端（Cursor/Claude 等）配置无需修改 |
| GitHub 仓库 URL | `Moeblack/ComfyUI-AnimaTool` | 仓库本身尚未改名 |

---

## 6. 升级步骤

1. 文件夹重命名后，**重启 ComfyUI**（custom node 代码在启动时加载，新路由才会生效）。
2. 若 MCP 配置中写了旧的绝对路径（如 `...\ComfyUI-AnimaTool\servers\mcp_server.py`），改为新路径 `...\ComfyUI-AnimaFlow\servers\mcp_server.py`；MCP server 名 `anima-tool` 无需修改。
3. 调用方如需使用新工作流，改用主 API + `workflow` 参数；旧端点可继续沿用。
4. 按第 2 节调整提示词写法（尤其多角色场景与 turbo 系 tags 写法）。
