# Anima 2.9B + rdbt v2.0 双 LoRA（anima29_rdbt）提示词规范

Anima base 的层扩展微调（28→40 层，~2.9B 参数，追加 1.7M 二次元/插画样本，知识截止 2026-07），
串联加载两个 rdbt v2.0 LoRA（均为 strength 1.0，顺序不可换）：
`rdbt_v2.0_base_anima2.9b_p1_lora.safetensors` → `rdbt_v2.0_distilled_addon_anima2.9b_p1_lora.safetensors`。
distilled addon 是必需组件：仅 base 在 16/20/25 步下均不可用（不收敛或追不平双 LoRA），实测见
`examples/results/anima29_rdbt_probe_20260818_210509/report.md`。

## 字段规则

| 字段 | 写法 |
|------|------|
| `quality_meta_year_safe` | `year 2026, <safe/sensitive/nsfw/explicit>`。**避免一切质量标签与 score**：masterpiece / great quality / best quality / very aesthetic / score_N 等一律不要（训练数据无 score 标签，质量词对本模型只会引入噪声）；保留年份/时期标签。 |
| `count` | `1girl` / `2girls` / `1boy` / `1other` |
| `character` / `series` | 角色名可带作品 `yunli (honkai star rail)`，角色名必须紧跟作品/版权标签，否则模型可能张冠李戴。多人逗号分隔。**避免下划线**：写 `hatsune miku` 而非 `hatsune_miku`（角色/作品标签对下划线最敏感）。 |
| `artist` | `@` 开头，如 `@wlop`。基础画风仅比 base 略好，**仍建议显式给 @画师标签**来锚定画风。画师标签同样**避免下划线**。 |
| `appearance` | 逗号分隔的标准 Danbooru 标签（发色、瞳色、服装），只填有明确指代的标准 tag，不要编造；没有合适 tag 的外貌细节写到 tags 的自然语言中。仅单角色使用，多角色必须留空。带下划线的标准 tag 可接受（其他标签也尽量避免 `_`，但影响不大）。 |
| `tags` | **英文自然语言完整句子**，写动作、表情、构图、场景、氛围与光影。**提示词越详细越好**：至少 2-3 句写足细节，短提示常生成平淡的简单背景。多角色时禁止写角色外貌，外貌逐角色分别描述。nsfw/explicit 分级时在末尾保留无码提示词 `no mosaic, uncensored`。 |
| `neg` | **不要填写**：cfg=1 时负面不进采样、不生效，见下方"负面提示词"一节。 |
| `aspect_ratio` | `16:9` `3:2` `1:1` `2:3` `9:16`，默认 `1:1` |

## 多角色

- `appearance` 必须留空
- `tags` 的自然语言只写共性姿势/构图，角色与其外貌/服装就近归属，逐角色分别描述："The girl with crimson hair and wolf ears..."
- 共处式描述，不用位置分割词（"On the left... On the right..."）

## 采样参数

steps 8-32（默认 16，实测 16 步已收敛且为质量/速度甜点位），cfg 固定 1，euler + sgm_uniform。
12 场景同 seed 实测：16 步双 LoRA 质量追平或反超同模型 30 步无 LoRA 出图（含复杂构图与 NSFW 场景）。

## 分辨率

官方推荐 812x1216 / 1152x1536 / 1536x1536（1536 不太稳）。约 70% 训练算力在 1024px，
默认 `aspect_ratio`（~1MP，如 2:3 → 848x1264）即可，与推荐档位接近。

## 负面提示词

**不要写负面**：cfg=1 时 KSampler 完全跳过负面分支，且实测三种事后引导方案也基本无效——对 text/sign 等场景级概念全部压制失败，PerpNeg 仅对 blush 类简单属性偶尔有效，并有改构图/引入反义元素的副作用（见 `examples/results/anima29_negprobe2_20260818_113417/report.md`）。正确做法是**正向写法规避**：不想要的元素不要提及（模型常把否定词也当成概念引入），用正向描述替代（如要无文字背景就简化场景、写 `simple background`）。**唯一例外：nsfw/explicit 分级时在 `tags` 末尾保留无码提示词 `no mosaic, uncensored`。**

**实验性参数（默认关闭，不推荐日常使用）**：`neg_scale`（PerpNegGuider，>1 启用）/ `nag_scale`（内核 NAGuidance）/ `anima_nag_scale`（ComfyUI-Anima-NAG 插件）三者互斥，仅保留用于后续模型复测。

## 风格特性

双 LoRA 出图为精致 glossy 的商业插画质感、饱和度偏高、完成度高；需要严格贴清淡系画师风格时
显式给 @画师标签锚定。霓虹夜景/招牌场景有概率出乱码伪文字（模型通病），偶发小伪签名。

## 模型限制

不支持生成文字/LOGO/UI/对话框/气泡。`tags` 中禁止 text, sign, letter, ui, interface, hud, menu, button, dialog, speech bubble, thought bubble, logo。
