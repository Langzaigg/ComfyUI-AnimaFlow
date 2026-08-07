# Turbo 0.2 提示词规范

## 核心规则

1. `tags` 以标准 Danbooru 标签为主（逗号分隔），写动作/姿势、表情、构图/视角。
2. 没有特别符合的标准 tag 时，用英文自然语言句子接在标签后面描述，不要编造不标准的 tag（不标准 tag 会干扰模型理解）。
3. `appearance` 使用逗号分隔 Danbooru 标签，仅单角色使用；多角色时必须留空。
4. 多角色时 `tags` 中禁止任何角色外貌信息，外貌用自然语言逐角色分别描述。
5. `quality_meta_year_safe` 必须明确安全等级 `safe/sensitive/nsfw/explicit`。
6. `artist` 必须以 `@` 开头，无明确需求时空着。
7. 默认非写实。

## 参数

- `cfg`: LoRA 强度 0.7-1，默认 1（越小越多样，越大越稳定）
- `steps`: 8-12，默认 10

## tags 写法

标签在前、自然语言在后。标签覆盖动作/姿势、表情、构图/视角；没有标准 tag 的内容（氛围、光影、复杂互动）用自然语言句子补充，至少 1-2 句。

**示例:**
> sitting, on desk, looking at viewer, smile, upper body, classroom, window, sunlight. Soft warm sunlight streams through the window, creating a cozy atmosphere.

## 自然语言技巧

- 角色名/系列名遵循标准英文大小写
- 描述越详细越好，过短可能出意外
- 质量/画师标签可放在自然语言开头
- 先命名角色再描述外观。多角色时尤其重要，否则模型混淆

## 多角色

- `appearance` 必须留空
- `tags` 只写共性姿势/构图标签，禁止任何角色外貌标签（发色、瞳色、发型、服装、饰品）
- 外貌在 tags 的自然语言部分逐角色分别描述："The girl with crimson hair..."
- 用共处式描述，不用位置分割词（"On the left... On the right..."）
- `character` 多人名逗号分隔

## 负面提示词

`worst quality, low quality, artist name, blurry, jpeg artifacts, chromatic aberration, bad anatomy, bad hands, bad feet, extra fingers, missing fingers, text, watermark, logo` + 安全对立约束。nsfw/explicit 时 tags 末尾加 `no mosaic, uncensored`。

## 模型限制

不支持生成文字/LOGO/UI/界面/对话框/气泡。`tags` 中禁止出现 text, sign, letter, ui, interface, hud, menu, button, dialog, speech bubble, thought bubble, logo 等词。

## 宽高比

`16:9` `3:2` `1:1` `2:3` `9:16`，默认 `1:1`。
