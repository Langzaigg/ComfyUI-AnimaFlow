# Fuse（Silvermoon29 Turbo × Anima Turbo 1.1 融合模型）提示词规范

Fuse v1.2（`anima29b-sm29t-fuse1.2`）：fuse v1.1（silvermoonmixAnima_v2329BTurbo × anima-turbo-v1.1 按 0.3/0.7 加权融合，非官方衍生）融合 NextGen 2.9bV1 LoRA@0.3。v1.1 本体见下。
原始出处：SilvermoonMix Anima Evolved <https://civitai.com/models/2639339/silvermoonmix-anima-evolved>。
turbo 提示词体系：质量词有效，字段写法与 turbo_v1 一致；采样为 Euler a + normal 8-12 步（默认 10），cfg 固定 1.0。

## 字段规则

| 字段 | 写法 |
|------|------|
| `quality_meta_year_safe` | `masterpiece, best quality, <safe/sensitive/nsfw/explicit>` |
| `count` | `1girl` / `2girls` / `1boy` / `1other` |
| `character` / `series` | 角色名可带作品 `yunli (honkai star rail)`，角色名必须紧跟作品/版权标签，否则模型可能张冠李戴。多人逗号分隔。**避免下划线**：写 `hatsune miku` 而非 `hatsune_miku`。 |
| `artist` | `@` 开头，如 `@wlop`。无需求时空着。画师标签同样**避免下划线**。 |
| `appearance` | 逗号分隔的标准 Danbooru 标签（发色、瞳色、服装），只填有明确指代的标准 tag，不要编造；没有合适 tag 的外貌细节写到 tags 的自然语言中。仅单角色使用，多角色必须留空。 |
| `tags` | **英文自然语言完整句子**，写动作、表情、构图、场景、氛围与光影，至少 1-2 句并写足细节。多角色时禁止写角色外貌，外貌用自然语言逐角色分别描述。 |
| `neg` | **不要填写**：cfg 固定 1.0，负面不进入采样（惰性）；官方建议无负面。 |
| `aspect_ratio` | `16:9` `3:2` `1:1` `2:3` `9:16`，默认 `1:1` |

## 多角色

- `appearance` 必须留空
- `tags` 的自然语言只写共性姿势/构图，角色与其外貌/服装就近归属，逐角色分别描述："The girl with crimson hair and wolf ears..."
- 共处式描述，不用位置分割词（"On the left... On the right..."）

## 采样参数

steps 8-12（默认 10），cfg 固定 1.0，Euler a + normal，无负面。

## 负面提示词

不使用负面（cfg 固定 1.0，负面惰性）。不想要的场景元素用正向写法规避：不要提及（模型常把否定词也当成概念引入），用正向描述替代（如要干净背景就写 `simple background`）。

## NSFW 提示词

正面 `tags` 中强调 `uncensored, detailed anatomy`。cfg 固定 1.0 负面不进采样，审查类负面词不可用，出现打码/审查倾向只能靠正向写法（直接写清裸露细节与无遮挡）或换 seed 规避。

## 模型限制

不支持生成文字/LOGO/UI/对话框/气泡。`tags` 中禁止 text, sign, letter, ui, interface, hud, menu, button, dialog, speech bubble, thought bubble, logo。
