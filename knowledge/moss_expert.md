# MOSS-Image（moss_image_anime_turbo）提示词规范

OpenMOSS 的 5B 单流 DiT（FLUX.2 latent 空间 + Qwen3.5-9B 文本编码器 + FLUX.2 VAE）。
本项目用的是 `moss_image_anime_turbo.safetensors`：社区合并的 8 步蒸馏主采样权重（miaoka turbo1 + NSFW LoRA 0.7 融合，
INT8 ConvRot、fused-qkv 布局）配原生 Qwen3.5 TE 与 FLUX.2 VAE。两个卖点是**原生 Layout 框位控制**与**画面内字面文字渲染**。

提示词固定用**混合写法**：结构化 tag 字段在前，`nltags` 自然语言句子在后。
字段名与 Anima 系完全一致，同一份人设/标签数据可以直接复用。

## 拼接顺序

```
quality_meta_year_safe → count → character → series → appearance → artist → style → tags → environment
（, 分隔）→ 换行 → nltags（自然语言句子）
```

`quality_meta_year_safe` 一个字段承载四段，字段内按 **Quality → Score → Meta → Year → 安全等级** 排列：

```
masterpiece, best quality, score_8, highres, year 2026, safe
└──── Quality ───┘  └Score┘  └Meta┘  └─Year─┘  └Safe┘
```

服务端按上面的顺序拼，调用方不用自己排；只有手写 `positive` 时才需要自己保证顺序。

## 字段规则

| 字段 | 写法 |
|------|------|
| `quality_meta_year_safe` | 见上，四段合一。质量词点到为止（`masterpiece, best quality` 足够）；MOSS 没有明确的 score 训练体系，`score_N` 可留空；安全等级必须明确（safe/sensitive/nsfw/explicit）。 |
| `count` | `1girl` / `2girls` / `1boy` / `no humans`。 |
| `character` / `series` | 角色名可带作品 `hatsune miku`，作品单独放 `series`。**避免下划线**。 |
| `appearance` | 逗号分隔的标准 Danbooru 标签：发色发型、瞳色、服装、饰品。仅单角色使用；多角色留空，外貌写进 `nltags` 逐角色描述。 |
| `artist` | `@` 开头，如 `@wlop`。写实向题材慎用。 |
| `style` | 画风/媒介/渲染：`anime color`、`watercolor`、`flat illustration`、`monochrome`、`gouache`。 |
| `tags` | 通用标签：动作、服装细节、构图、道具，如 `white dress, standing, holding cup, outdoors`。 |
| `environment` | 场景/天气/时间/背景：`sunflower field, sunlight, outdoors, depth of field`。 |
| `nltags` | **英文完整句子**，写动作、镜头、光线、材质、氛围与剧情。排在 tag 块之后换行分隔，是氛围与叙事的主要载体。也接受旧字段名 `prompt`。 |
| `neg` | 一般留空（默认 CFG 1，负面不进采样）。填写后默认以 CFG 1.2 采样。 |
| `aspect_ratio` | `16:9` `3:2` `1:1` `2:3` `9:16`，默认 `1:1`；宽高须为 16 的倍数，约 1MP 最稳。 |

## 写好的要点

- **tag 块定元素，nltags 定氛围**：人数、发色、服装、构图词放 tag；镜头、光线、材质、情绪放句子。
- 质量词不是越多越好。MOSS 训练里没有「堆质量词提升画质」的机制，堆多了只会挤占正文。
- 多角色时 `appearance` 留空，`nltags` 里逐角色就近描述外貌（"The girl with crimson hair and wolf ears…"），
  不要用「左边是谁、右边是谁」这种位置分割。
- 想要干净背景：写 `simple background`（正向），而不是把 "no background" 塞进负面。

## Layout 模式（框位控制）

给了 `elements` 就走 Layout：`nltags` 变成整图描述（进 `summary.caption`，tag 块拼在它前面），每个元素单独给框位。
适合漫画分格、海报、贴纸文案、UI 稿。

- 坐标系是**画布左上角原点、像素单位**，`[x1, y1, x2, y2]` 且 `x1 < x2`、`y1 < y2`。不要用 0-1 归一化坐标。
- 服务端按官方算法换算：先向外取整成像素边界，再减画布中心，输出 `yxyx` 顺序的中心原点坐标
  （例：1536×1024 上 `[176, 224, 800, 864]` → `[-288, -592, 352, 32]`）。
- **框只是摆放约束，不会画出边框或贴纸**。要分格黑框、白边、留白，写在 `nltags` 里。
- 一个元素 = 一个可独立摆放的可见单元；同一主体不要拆框；允许自然遮挡。框必须落在画布内，超出会被拒绝。

## 分格漫画写法

1. `canvas: "multi_panel"`，`nltags` 交代版面：2×2 或 1×4、格线粗细、留白、阅读顺序。
2. 每格给一个 `object`/`character` 框，`caption` 用 "Top-left panel: ..." 指明归属。
3. 每句台词单独一个 `text` 框，`text` 放原文字面文字，`caption` 描述气泡样式。
4. 1536×1024 的 2×2 可用四角 (56,56,748,492) / (788,56,1480,492) / (56,532,748,968) / (788,532,1480,968)。
5. 一次出整页比四次单格省时（约 45-55 s/页），代价是单格细节密度低于单幅大图。

## 参考图作画（`reference_image` / `reference_images`）

MOSS 的文本编码器是多模态 Qwen3.5，参考图走 **TE 的视觉分支**，不是 VAE latent：

- 服务端用 `TextEncodeMingImageEdit` 把图喂给编码器，并在提示词前自动补占位符
  `Picture 1: <|vision_start|><|image_pad|><|vision_end|>`，多张依次 Picture 2/3/4（最多 4 张）。
- 每张缩到约 384²（0.147456 MP，保留各自比例），负向条件保持纯文本。
- 不给 VAE：图片只作视觉语义条件，**不是逐像素复刻、也不是身份锁定**——脸、服装、logo 会接近，但别指望完全一致。

用法要点：

- 一个主体配一张图，顺序就是 Picture 编号；提示词里用 `Picture 1 character` / `the device in Picture 2` 指代。
- 每个主体的外观仍要写进 `appearance` / `nltags` 与各格 `caption`（道具写材质颜色形状）。图和文字一起才稳。
- 多主体同框要给明确空间关系（"she holds the white repeater in both hands"），否则各自漂移。
- 参考图只影响语义，不改变画幅：`width`/`height` 照常决定尺寸，框位照常按画布像素算。

## 采样参数

项目默认 steps 4（4-12），CFG 1.0（1.0-1.6），`res_multistep` + `simple`，denoise 1.0。shift 固定 5 由模型侧自动应用。
新版模型 19 场景同 seed 实测中，4/6 步质量接近；res_multistep 4 步与 euler 4 步耗时同档、部分细节略清楚，中位耗时约 28.2s（euler 4/6 步为 27.5/34.3s）。备选组合为 `euler` + `simple`；官方推荐 8 步。
turbo 蒸馏权重**不要**开到 20-50 步。

## 分辨率

约 1MP 最稳（1024×1024、1536×1024、1024×1536）；支持 0.25-4MP，高分辨率更慢且多元素 layout 容易漏框。
宽高一律取 16 的倍数。

## 模型限制

- 提示词上限 4K token；`elements` 越多越容易漏框，四格漫画 6-10 个元素是甜区。
- 不支持画面内多段落小字排版；细排文字建议单幅大图 + 少量 text 元素。
- 质量/分数标签不是它的训练重点，堆砌无收益；`score_N` 尤其可疑。
- 与 Anima 系人设库字段通用（`count` / `character` / `series` / `appearance` / `artist` / `tags`），
  但 MOSS 还会读 `nltags` 的叙事，别只给 tag 串。
- 该权重已融合 NSFW LoRA（0.7），默认倾向比官方 SFT 更偏；需要保守输出时在 `appearance` / `nltags` 里明确服装、姿态与场景。
