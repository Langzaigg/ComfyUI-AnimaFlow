# Kira (Kirazuri Anima v4) 提示词规范

适用于 kira 与 kira-turbo 两个工作流。本模型使用 booru 标签、自然语言描述及两者混合训练，**tags 字段固定使用英文自然语言**。

## 标签顺序

```
[质量/美学/安全] [角色] [作品] [画师] [人数] [外观] [通用标签(自然语言)]
```

与 base Anima 的差异：人数标签（`1girl`/`1boy`/`1other`）位置靠后，移到 artist 之后（由后端自动组装，字段照常填写即可）。
`[质量/美学/安全]` `[角色]` `[作品]` `[画师]` 这几组在训练时不参与乱序，顺序对生成有影响，保持上述顺序。
外观（`appearance`）经实测放在通用标签之前、人数之后效果最好（已对比过紧跟角色的写法）。

## 字段规则

- `quality_meta_year_safe`: `masterpiece, best quality, very aesthetic, <safe/sensitive/nsfw/explicit>`。安全等级必须明确，负面加相反约束。
- `character`: 角色名可带作品 `yukikaze (azur lane)`。多人逗号分隔。
- `series`: 作品/系列名
- `artist`: `@` 开头，如 `@wlop`。无明确需求时留空。
- `count`: `1girl` / `2girls` / `1boy` / `1other`
- `appearance`: 逗号分隔 Danbooru 标签（发色、瞳色、服装）。仅单角色使用，多角色时必须留空。
- `tags`: **英文自然语言完整句子**，描述场景、动作、表情、构图、氛围与光影，至少 2-3 句并写足细节。不要用逗号分隔的标签堆叠——短提示词/纯标签在本模型上会出现明显的概念串扰与不稳定（本模型是标签与自然语言混合训练的，自然语言细节能显著缓解）。
- `neg`: `worst quality, low quality, artist name, blurry, jpeg artifacts, chromatic aberration, bad anatomy, bad hands, bad feet, extra fingers, missing fingers, text, watermark, logo` + 安全对立约束（正面 safe/sensitive → 负面加 nsfw, explicit；反之亦然）

## 美学与风格标签

- 美学（本模型特有，引导模型自带审美倾向）：`very aesthetic`, `aesthetic`
- Meta：`absurdres`, `official art`
- 风格：`painterly`, `chiaroscuro`, `ligne claire`, `flat color`, `no lineart`, `blending`
- 传统媒介：`traditional media`, `oil painting \(medium\)`, `watercolor \(medium\)`（括号需转义）

以上风格类词条可放在 quality_meta_year_safe 或自然语言描述中。

## 多角色

- `appearance` 必须留空
- `tags` 的自然语言中禁止堆砌角色外貌标签，逐角色分别描述外观："The girl with crimson hair..."
- 共处式描述，不用位置分割词（"On the left... On the right..."）

## 采样参数

- kira：30-50 步（默认 40），CFG 4-5（默认 4.5）。
- kira-turbo：固定 8 步、CFG 1，默认 1024×1024 分辨率。

## 宽高比

`16:9` `3:2` `1:1` `2:3` `9:16`，默认 `1:1`。
