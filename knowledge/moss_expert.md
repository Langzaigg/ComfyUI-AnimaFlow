# MOSS-Image（SFT Turbo INT8 ConvRot AIO）提示词与 Layout 规范

OpenMOSS 的 5B 单流 DiT（FLUX.2 latent 空间 + Qwen3.5-9B 文本编码器 + FLUX.2 VAE），
本项目用 `toxicdog/MOSS-Image-SFT-Turbo-INT8-ConvRot-AIO` 的 8 步蒸馏单文件版本。
两个卖点：**原生 Layout 框位控制**（角色/物件/文字各自摆放）与**画面内字面文字渲染**（中英文都能出字）。

和 Anima 系完全不同：**不写 tag 串，也不写质量词**。提示词是「整体描述 + 元素框位」的结构化 Layout。

## 字段规则

| 字段 | 写法 |
|------|------|
| `prompt` | 整体画面描述 → `summary.caption`。主体、动作、场景、媒介、镜头、光线、配色、氛围，以及版面形态（单幅 / 2x2 四格 / 拼贴）。**只写可见内容**，不要写坐标换算或 JSON 字段说明。英文描述为主。 |
| `canvas` | `single` 单幅 / `multi_panel` 多格（漫画、连环画）/ `collage` 拼贴。多格漫画必须填 `multi_panel`。 |
| `meta` | 媒介/体裁标签，如 `["four-panel comic", "manga", "black and white"]`。可选，但对画风锚定有用。 |
| `elements[].label` | `character` 角色 / `object` 物件或场景块 / `text` 需要渲染的字。 |
| `elements[].caption` | 该元素的视觉描述：外观、动作、姿态、材质、光影；`text` 元素还要写字体与底材（如「黑色描边的白色圆角气泡，手写体中文」）。 |
| `elements[].text` | **仅 `text` 元素可用**：要渲染的字面文字，原样保留语言、标点与换行（`\n`）。其他 label 填了会报错。 |
| `elements[].bbox` | 画布左上角原点的像素框 `[x1, y1, x2, y2]`，范围 `0..width` / `0..height`。服务端换算成模型要求的 `abs_centralized` + `yxyx`。 |
| `neg` | 一般留空（默认 CFG 1，负面不进采样）。填写后默认以 CFG 1.2 采样，但会损失 turbo 的稳定性。 |
| `aspect_ratio` / `width` / `height` | 约 1MP 最稳；宽高必须是 **16 的倍数**。同时给出时以 `width`/`height` 为准。 |

## Layout 框位规则

- 坐标系是**画布左上角原点、像素单位**，`[x1, y1, x2, y2]` 且 `x1 < x2`、`y1 < y2`。不要用 0-1 归一化坐标。
- 服务端按官方算法换算：先向外取整成像素边界，再减画布中心，输出 `yxyx` 顺序的中心原点坐标
  （例：1536×1024 上 `[176, 224, 800, 864]` → `[-288, -592, 352, 32]`）。
- **框只是摆放约束，不会画出边框或贴纸**。要分格黑框、白边、留白，写在 `prompt` 里
  （如 "2x2 grid with thick black panel borders and narrow white gutters"）。
- 一个元素 = 一个可独立摆放的可见单元。同一主体不要拆成多个框；允许自然遮挡与重叠。
- 框位必须落在当前 `width`/`height` 画布内，超出会被拒绝（不会静默裁剪）。

## 参考图作画（`reference_image` / `reference_images`）

MOSS 的文本编码器是多模态的 Qwen3.5，参考图走的是 **TE 的视觉分支**，不是 VAE latent：

- 服务端用 `TextEncodeMingImageEdit` 把图片喂给编码器，并在提示词前面自动补上 Qwen 对话模板要求的占位符：
  `Picture 1: <|vision_start|><|image_pad|><|vision_end|>`，多张依次为 Picture 2、3、4（最多 4 张）。
- 每张图会缩到约 384²（`ImageScaleToTotalPixels`，area，0.147456 MP，保留各自比例），负向条件保持纯文本。
- 不给 VAE：图片只作为视觉语义条件，不会像编辑模型那样把参考图拼进 latent 序列。所以这是「带参考的生图」，
  **不是逐像素复刻、也不是身份锁定**——脸、服装、logo 会接近，但不要指望完全一致。

用法要点：

- 一个主体配一张图，`reference_images` 的顺序就是 Picture 1、2、3、4 的顺序；提示词里用 `Picture 1 character`
  / `the device in Picture 2` 这样指代，模型才对得上号。
- **每张图对应的主体仍要在 `prompt` 与各格 `caption` 里写清外观**：角色写发色/瞳色/服装/配饰；道具写材质、
  颜色、形状（例：白色塑料外壳、圆孔喇叭网、翻盖磁带仓、圆形小按键、小 logo）。图和文字一起才稳。
- 多主体同框时给出明确的空间关系（"she holds the white repeater in both hands"），否则两个主体容易各自漂移。
- 四格漫画里想稳定出现两个主体，**每格都显式写到两者**，而不是只在第一格提一次。
- 参考图只影响语义，不改变画幅：`width`/`height` 照常决定输出尺寸，框位照常按画布像素算。
- 图片需在 ComfyUI 的 input 目录里（本机绝对路径会被自动复制进去）。

## 分格漫画写法


1. `canvas: "multi_panel"`，`prompt` 里交代版面：2×2 或 1×4、格线粗细、留白、阅读顺序。
2. 每个分格给一个 `object`/`character` 框，`caption` 用 "Top-left panel: ..." / "Bottom-right panel: ..." 指明归属。
3. 每句台词/拟声词单独一个 `text` 框，`text` 里放原文字面文字，`caption` 描述气泡样式。
4. 分格坐标建议按画布均分并对齐：1536×1024 的 2×2 可用四角 (56,56,748,492) / (788,56,1480,492) /
   (56,532,748,968) / (788,532,1480,968)，气泡放在对应格内上部或下部。
5. 一次出一整页四格比四次单格省时（约 45-50 s/页），代价是单格细节密度低于单幅大图。

## 文字渲染

- 要出的字**必须放在 `text` 字段**，只写在 caption 里模型不一定照排。
- 中文短句最稳：每行 4-8 字、字号约占框高 60-70%，框比字面略宽留给气泡边距。
- 字号过小（像素高 < 约 24px）会糊字或漏笔画；字多就加高框或拆成多个 `text` 元素。
- 英文同理；数字、缩写（如 `24H`、`BUILD PASSED`）可直接放在 text 里。

## 采样参数

steps 8（4-12 可调），CFG 1.0（1.0-1.6），`euler` + `simple`，denoise 1.0。
shift 固定 5 由模型侧自动应用，不需要额外的采样偏移节点。turbo 蒸馏版本**不要**开到 20-50 步。

## 分辨率

约 1MP 最稳（1024×1024、1536×1024、1024×1536）；官方支持 0.25-4MP，高分辨率会更慢且更容易在
多元素 layout 下漏框。宽高一律取 16 的倍数。

## 模型限制

- 提示词上限 4K token；但 `elements` 越多越容易漏框，四格漫画 6-10 个元素是甜区。
- 不支持在图里生成复杂排版正文（多段落小字）；海报级细排文字建议单幅大图 + 少量 text 元素。
- 不要写质量/分数标签（masterpiece、best quality、score_N 等）——训练体系里没有这套，只会引入噪声。
- 与 Anima 系模型的人设库 tag 不通用：这里的 `caption` 是自然语言句子，不是逗号标签串。
