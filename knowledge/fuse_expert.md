# Fuse（turbo × Anima 2.9B 融合模型）提示词规范

turbo 提示词体系：质量词有效，字段写法与 turbo_v1 一致；采样为 euler + sgm_uniform 8-12 步（默认 8）。

## 字段规则

| 字段 | 写法 |
|------|------|
| `quality_meta_year_safe` | `masterpiece, best quality, <safe/sensitive/nsfw/explicit>` |
| `count` | `1girl` / `2girls` / `1boy` / `1other` |
| `character` / `series` | 角色名可带作品 `yunli (honkai star rail)`，角色名必须紧跟作品/版权标签，否则模型可能张冠李戴。多人逗号分隔。**避免下划线**：写 `hatsune miku` 而非 `hatsune_miku`。 |
| `artist` | `@` 开头，如 `@wlop`。无需求时空着。画师标签同样**避免下划线**。 |
| `appearance` | 逗号分隔的标准 Danbooru 标签（发色、瞳色、服装），只填有明确指代的标准 tag，不要编造；没有合适 tag 的外貌细节写到 tags 的自然语言中。仅单角色使用，多角色必须留空。 |
| `tags` | **英文自然语言完整句子**，写动作、表情、构图、场景、氛围与光影，至少 1-2 句并写足细节。多角色时禁止写角色外貌，外貌用自然语言逐角色分别描述。 |
| `neg` | **一般不要填写**：工作流内置文字类负面（text, letters, sign, logo, watermark, signature, username, artist name），默认以 cfg 1.2 使其生效，假签名/水印已被默认抑制；填写会替换内置负面。 |
| `aspect_ratio` | `16:9` `3:2` `1:1` `2:3` `9:16`，默认 `1:1` |

## 多角色

- `appearance` 必须留空
- `tags` 的自然语言只写共性姿势/构图，角色与其外貌/服装就近归属，逐角色分别描述："The girl with crimson hair and wolf ears..."
- 共处式描述，不用位置分割词（"On the left... On the right..."）

## 采样参数

steps 8-12（默认 8），cfg 1.0-1.6（有负面时默认 1.2），euler + sgm_uniform。

## 负面提示词

内置文字类负面已默认生效（cfg 1.2），针对的是"附加物"型文字伪影：角落假签名、@用户名水印、logo 式标记。它压不住"内容型"文字（霓虹招牌、包装图案这类画面内容本身）——不想要的场景元素仍用正向写法规避：不要提及（模型常把否定词也当成概念引入），用正向描述替代（如要干净背景就写 `simple background`）。自填 `neg` 会替换内置负面，需要同时保留时把文字类词一并写上。

## 模型限制

不支持生成文字/LOGO/UI/对话框/气泡。`tags` 中禁止 text, sign, letter, ui, interface, hud, menu, button, dialog, speech bubble, thought bubble, logo。
