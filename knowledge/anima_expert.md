# Base 1.0 提示词规范

## 标签顺序

```
[质量/安全] [人数] [角色] [作品] [外观] [画师] [风格] [标签] [环境] [自然语言]
```

## 字段规则

- `quality_meta_year_safe`: 含 `score_7`。安全等级 `safe/sensitive/nsfw/explicit` 必须明确，负面加相反约束。
- `count`: `1girl` / `2girls` / `1boy` / `1other`
- `character`: 角色名可带作品 `hatsune miku` 或 `yunli (honkai star rail)`。多人逗号分隔。
- `series`: 作品/系列名
- `appearance`: 逗号分隔 Danbooru 标签（发色、瞳色、服装）。仅单角色使用，多角色时必须留空。
- `artist`: `@` 开头，如 `@wlop`。无明确需求时留空。
- `style`: 风格标签
- `tags`: 逗号分隔的标准 Danbooru 标签（姿势、构图、表情、服装）
- `environment`: 环境/光照标签
- `nltags`: 自然语言描述，2-4 句。多角色时是避免混淆的核心手段。
- `neg`: `worst quality, low quality, score_1, score_2, score_3, artist name, blurry, jpeg artifacts, chromatic aberration, bad anatomy, bad hands, bad feet, extra fingers, missing fingers, text, watermark, logo` + 安全对立约束（正面 safe → 负面加 nsfw/explicit）

## tags 与 nltags 分工

- `tags` 只写真实存在的标准 Danbooru 标签。
- 没有特别符合的 tag 时，不要编造不标准的 tag（如 `holding_hands_and_smiling`），改在 `nltags` 中用自然语言描述。不标准 tag 会干扰模型理解、降低出图质量。
- 两者分工：`tags` 放标准标签，`nltags` 补充无法标签化的细节与氛围。

## 提示词技巧

- nltags 留空或 2-4 句，足够细节但不冗长
- 构图优先：主体占画面足够大，否则细节糊
- 手脚易崩：正面可加 `fingernails` / `fingers`；负面细列 bad hands / missing fingers / extra fingers / malformed limbs / bad feet
- 负面量大管饱，细分常见崩坏
- 兽耳娘负面加 `anthro`
- NSFW 正面强调 `uncensored, detailed anatomy`；负面追加审查类词：`censored, mosaic, mosaic censoring, bar censor, black bar, pixelated, censored genitalia`
- 权重需高：`(chibi:2)` 而非 `(chibi:1.1)`
- 标签差异优先 Gelbooru 版本
- 角色名/系列名遵循标准英文大小写：`Hatsune Miku (Vocaloid)`、`Fern (Sousou no Frieren)`
- 标签与自然语言可混合，质量/画师标签可放自然语言开头

## 多角色

- `character`: 所有角色名逗号分隔
- `appearance`: 必须留空
- `tags`: 只写共性姿势/构图标签，禁止出现任何角色外貌信息（发色、瞳色、发型、服装、饰品）
- `nltags`: 逐角色分别描述外观归属，每个角色至少写明发色、发型、瞳色、服装
- 避免位置分割词（"On the left..."会切断画面），用共处式描述
