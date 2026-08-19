# 提示词字段

| 字段 | 写法 |
|------|------|
| `quality_meta_year_safe` | `masterpiece, best quality, <safe/sensitive/nsfw/explicit>` |
| `count` | `1girl` / `2girls` / `1boy` / `1other` |
| `character` | 角色名可带作品 `yunli (honkai star rail)`。多人逗号分隔。 |
| `series` | 作品/系列名 |
| `artist` | `@` 开头，如 `@wlop`。无需求时空着。 |
| `appearance` | 逗号分隔的标准 Danbooru 标签（发色、瞳色、服装），只填有明确指代的标准 tag，不要编造；没有合适 tag 的外貌细节写到 tags 的自然语言中。仅单角色使用，多角色必须留空。 |
| `tags` | **英文自然语言完整句子**，写动作、表情、构图、场景、氛围与光影，至少 1-2 句并写足细节。多角色时禁止写角色外貌，外貌用自然语言逐角色分别描述。 |
| `neg` | **不要填写**：cfg=1 时负面不进采样、不生效。用正向写法规避（见下）；仅 nsfw/explicit 分级时在 `tags` 末尾保留无码提示词 `no mosaic, uncensored`。 |
| `aspect_ratio` | `16:9` `3:2` `1:1` `2:3` `9:16`，默认 `1:1` |

**cfg=1 时负面无效，一律用正向写法规避**：不想要的元素不要提及（模型常把否定词也当成概念引入），用正向描述替代（如要干净背景就写 `simple background`，或直接描述想要的场景本身）。唯一例外：nsfw/explicit 分级时在 `tags` 末尾保留无码提示词 `no mosaic, uncensored`。

**实验性参数（默认关闭，不推荐日常使用）**：`neg_scale`（PerpNegGuider，>1 启用）/ `nag_scale`（内核 NAGuidance）/ `anima_nag_scale`（ComfyUI-Anima-NAG 插件）三者互斥，可强制负面生效，但实测压制力有限（对场景级概念无效、仅个别简单属性部分生效，PerpNeg 会改构图且耗时 2-3 倍），仅保留用于后续模型复测。

## 自然语言技巧

- 角色名/系列名遵循标准英文大小写
- `tags` 自然语言部分至少 1-2 句，过短可能意外
- 质量/画师标签可放自然语言开头
- 先命名角色再描述外观。多角色必须逐角色描述外观，否则混淆

## 多角色

- `appearance` 必须留空
- `tags` 的自然语言只写共性姿势/构图，禁止任何角色外貌信息（发色、瞳色、发型、服装、饰品）
- 外貌在 tags 的自然语言中逐角色分别描述："The girl with crimson hair and wolf ears..."
- 共处式描述，不用位置分割词（"On the left... On the right..."）

## 模型限制

不支持生成文字/LOGO/UI/对话框/气泡。`tags` 中禁止 text, sign, letter, ui, interface, hud, menu, button, dialog, speech bubble, thought bubble, logo。
