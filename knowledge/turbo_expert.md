# Turbo 0.2 提示词规范

## 核心规则

1. `tags` 固定使用英文自然语言完整句子，写动作/姿势、表情、构图/视角、场景与氛围，至少 1-2 句。
2. `appearance` 使用逗号分隔的标准 Danbooru 标签，只填有明确指代的标准 tag，不要编造；仅单角色使用，多角色时必须留空。
3. 多角色时 `tags` 中禁止任何角色外貌信息，外貌用自然语言逐角色分别描述。
4. `quality_meta_year_safe` 必须明确安全等级 `safe/sensitive/nsfw/explicit`。
5. `artist` 必须以 `@` 开头，无明确需求时空着。
6. 默认非写实。

## 参数

- `cfg`: LoRA 强度 0.7-1，默认 1（越小越多样，越大越稳定）
- `steps`: 8-12，默认 10

## tags 写法

英文自然语言完整句子，覆盖动作/姿势、表情、构图/视角、场景、氛围与光影，至少 1-2 句并写足细节。末尾固定加 `no text, no logo, no ui` 后缀（nsfw/explicit 分级再加 `no mosaic, uncensored`）。

**示例:**
> A girl sits on a classroom desk, smiling at the viewer, shown from the waist up. Soft warm sunlight streams through the window, creating a cozy atmosphere. no text, no logo, no ui

## 自然语言技巧

- 角色名/系列名遵循标准英文大小写
- 描述越详细越好，过短可能出意外
- 质量/画师标签可放在自然语言开头
- 先命名角色再描述外观。多角色时尤其重要，否则模型混淆

## 多角色

- `appearance` 必须留空
- `tags` 的自然语言只写共性姿势/构图，禁止任何角色外貌信息（发色、瞳色、发型、服装、饰品）
- 外貌在 tags 的自然语言中逐角色分别描述："The girl with crimson hair..."
- 用共处式描述，不用位置分割词（"On the left... On the right..."）
- `character` 多人名逗号分隔

## 负面提示词

`worst quality, low quality, artist name, blurry, jpeg artifacts, chromatic aberration, bad anatomy, bad hands, bad feet, extra fingers, missing fingers, text, watermark, logo` + 安全对立约束。nsfw/explicit 时 tags 末尾加 `no mosaic, uncensored`。

## 模型限制

不支持生成文字/LOGO/UI/界面/对话框/气泡。`tags` 中禁止出现 text, sign, letter, ui, interface, hud, menu, button, dialog, speech bubble, thought bubble, logo 等词。

## 宽高比

`16:9` `3:2` `1:1` `2:3` `9:16`，默认 `1:1`。
