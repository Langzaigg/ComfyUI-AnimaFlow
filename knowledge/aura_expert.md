# AuraAnima 2.9B Int8（aura，精度重视）提示词规范

AuraAnima 2.9B qpolaP101 Int8 W8a8 量化模型（3.46 GB）：Anima 2.9B 的量化变体，实测质量/速度与 BF16 同档（完整场景测试 48 张无量化 artifacts，~2.7 s/步），显存占用约减半。本工作流为**精度重视**档：er_sde + beta，默认 12 步，实测 12 个场景 11 个质量第一。

## 字段规则

| 字段 | 写法 |
|------|------|
| `quality_meta_year_safe` | `<风格标签>, year 2026, <safe/sensitive/nsfw/explicit>`。风格标签三选一：`photo real`（写实照片风，**默认**，用户无指定时用此）/ `anime color`（动画平涂风，配画师 tag 效果最佳）/ `real skin`（写实肤质风）。**除此风格位外避免一切质量与分数标签**：masterpiece / great quality / best quality / very aesthetic / score_N 等一律不要。 |
| `count` | `1girl` / `2girls` / `1boy` / `1other` |
| `character` / `series` | 角色名可带作品 `yunli (honkai star rail)`，角色名必须紧跟作品/版权标签。多人逗号分隔。**避免下划线**。版权角色还原建议配 `anime color` 风格：`photo real` / `real skin` 会真人化，丢失动画角色的脸型/瞳色特征（变成"coser 照片"）。 |
| `artist` | `@` 开头，如 `@wlop`。**仅在 `anime color` 风格下使用**：画师 tag 生效显著且优先级高于写实标签；`photo real` / `real skin` 写实路线下**必须留空**（否则画师画风接管画面，丢失写实感）。画师标签避免下划线。 |
| `appearance` | 逗号分隔的标准 Danbooru 标签，只填有明确指代的标准 tag，不要编造。仅单角色使用，多角色必须留空。 |
| `tags` | **英文自然语言完整句子**，写动作、表情、构图、场景、氛围与光影。**提示词越详细越好**：至少 2-3 句写足细节，短提示常生成平淡的简单背景。多角色时禁止写角色外貌，外貌逐角色分别描述。 |
| `neg` | cfg>1 负面正常生效。留空即可，后端自动使用默认负面并按安全等级追加对立约束（正面 safe/sensitive → 负面加 `nsfw, explicit`，反之亦然）。 |
| `aspect_ratio` | `16:9` `3:2` `1:1` `2:3` `9:16`，默认 `1:1` |

默认负面：`worst quality, low quality, artist name, blurry, jpeg artifacts, chromatic aberration, bad anatomy, bad hands, bad feet, extra fingers, missing fingers, text, watermark, logo`

**NSFW 提示词**：正面 `tags` 中强调 `uncensored, detailed anatomy`；`neg` 追加审查类词（cfg>1 负面正常生效；默认负面在 explicit 时已含 censored/mosaic，补全其余）：`censored, mosaic, mosaic censoring, bar censor, black bar, pixelated, censored genitalia`。

## 多角色

- `appearance` 必须留空
- `tags` 的自然语言只写共性姿势/构图，角色与其外貌/服装就近归属，逐角色分别描述："The girl with crimson hair and wolf ears..."
- 共处式描述，不用位置分割词（"On the left... On the right..."）

## 采样参数

er_sde + beta，steps 8-30（默认 12），cfg 4.0-5.0（默认 5.0）。

- 精度重视档的提升集中在：氛围要素（光斑/蒸汽/发光特效）、细节密度（发丝/服装纹样）、指令修复（手部解剖、表情神韵）。氛围词密集或重指令场景尤其受益。
- 12 步 er_sde 耗时约为 10 步 euler 的 1.7 倍；实测画质提升肉眼可见，为默认推荐。

## 分辨率

默认 `aspect_ratio`（~1MP，如 2:3 → 848x1264）即可。官方推荐档位 812x1216 / 1152x1536 亦可（1536x1536 不太稳）。

## 模型限制

不支持生成文字/LOGO/UI/对话框/气泡。`tags` 中禁止 text, sign, letter, ui, interface, hud, menu, button, dialog, speech bubble, thought bubble, logo。写实路线（photo real / real skin）下偶发衣物乱码字母印花，出现时可换 seed 重roll。
