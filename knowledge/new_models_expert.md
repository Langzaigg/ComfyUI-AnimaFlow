# 提示词字段

| 字段 | 写法 |
|------|------|
| `quality_meta_year_safe` | `masterpiece, best quality, <safe/sensitive/nsfw/explicit>` |
| `count` | `1girl` / `2girls` / `1boy` / `1other` |
| `character` | 角色名可带作品 `yunli (honkai star rail)`。多人逗号分隔。 |
| `series` | 作品/系列名 |
| `artist` | `@` 开头，如 `@wlop`。无需求时空着。 |
| `appearance` | 逗号分隔 Danbooru 标签（发色、瞳色、服装）。仅单角色使用，多角色必须留空。 |
| `tags` | 以标准 Danbooru 标签（逗号分隔）为主，写动作、表情、构图。没有特别符合的标准 tag 时用英文自然语言句子补充，不要编造不标准 tag（会干扰模型理解）。多角色时禁止写角色外貌，外貌用自然语言逐角色分别描述。 |
| `neg` | `worst quality, low quality, artist name, blurry, jpeg artifacts, chromatic aberration, bad anatomy, bad hands, bad feet, extra fingers, missing fingers, text, watermark, logo`。safe/sensitive 加 `nsfw, explicit`；nsfw/explicit 加 `safe, sensitive, censored, mosaic`。 |
| `aspect_ratio` | `16:9` `3:2` `1:1` `2:3` `9:16`，默认 `1:1` |

## 自然语言技巧

- 角色名/系列名遵循标准英文大小写
- 自然语言部分至少 1-2 句，过短可能意外
- 标签与自然语言可混用，质量/画师标签可放自然语言开头
- 先命名角色再描述外观。多角色必须逐角色描述外观，否则混淆

## tags 示例

```
standing, looking at viewer, smile, full body, sunflower field, white dress, sunlight. A girl stands in a vast sunflower field. Warm dreamy atmosphere with soft golden light.
```

## 多角色

- `appearance` 必须留空
- `tags` 只写共性姿势/构图标签，禁止任何角色外貌标签（发色、瞳色、发型、服装、饰品）
- 外貌在 tags 的自然语言部分逐角色分别描述："The girl with crimson hair and wolf ears..."
- 共处式描述，不用位置分割词（"On the left... On the right..."）

## 模型限制

不支持生成文字/LOGO/UI/对话框/气泡。`tags` 中禁止 text, sign, letter, ui, interface, hud, menu, button, dialog, speech bubble, thought bubble, logo。
