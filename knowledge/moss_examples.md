# MOSS-Image 调用示例

下面都是 `/moss/generate` 的请求体（`schemas/tool_schema_moss.json` 的字段），
框位一律是**画布左上角原点的像素 `[x1, y1, x2, y2]`**，服务端负责换算成模型坐标。

## 例 1：2×2 四格漫画（Layout 模式）

`width/height` 定 1536×1024，四格按 56 边距均分：(56,56,748,492) / (788,56,1480,492) /
(56,532,748,968) / (788,532,1480,968)，气泡放在各自格内上部。

```json
{
  "prompt": "A four-panel black-and-white manga page in a 2x2 grid with thick black panel borders and narrow white gutters, clean ink lines and screentone shading. Panels read left to right, top to bottom; the same two characters throughout: a middle-aged interviewer in a grey suit and an orange tabby cat in a tiny navy suit.",
  "canvas": "multi_panel",
  "meta": ["four-panel comic", "manga", "black and white"],
  "width": 1536,
  "height": 1024,
  "elements": [
    {"label": "object", "caption": "Top-left panel: a job interview; the interviewer behind a desk holds a resume while the cat in a small navy suit sits upright on the chair opposite.", "bbox": [56, 56, 748, 492]},
    {"label": "text", "caption": "Hand-lettered Chinese dialogue in a white speech bubble with a black outline, top of the first panel.", "text": "你的经验？", "bbox": [120, 80, 520, 190]},
    {"label": "object", "caption": "Top-right panel: the cat proudly holds up a sheet of paper with a crude drawing of a caught mouse, chest puffed out.", "bbox": [788, 56, 1480, 492]},
    {"label": "text", "caption": "Bouncy white speech bubble with a black outline, second panel.", "text": "三年捕鼠经验。", "bbox": [880, 84, 1400, 200]},
    {"label": "object", "caption": "Bottom-left panel: the interviewer presses a palm to his forehead with an exasperated half-smile, laptop and paper cup on the desk.", "bbox": [56, 532, 748, 968]},
    {"label": "text", "caption": "White speech bubble with a thin black outline, third panel.", "text": "我们要的是程序员…", "bbox": [104, 596, 640, 726]},
    {"label": "object", "caption": "Bottom-right panel: the cat wears round glasses and types on a laptop, tongue slightly out, the interviewer leaning in with an amused eyebrow.", "bbox": [788, 532, 1480, 968]},
    {"label": "text", "caption": "Compact white speech bubble with short motion lines, fourth panel.", "text": "那我现学。", "bbox": [860, 700, 1240, 824]}
  ]
}
```

要点：`prompt` 只交代版面与两个角色，每格的画面细节放在对应 `object` 的 `caption` 里；
气泡的框不要压住人物脸部，字号按框高 60% 左右估算。

## 例 2：单幅带字海报（Layout 模式）

```json
{
  "prompt": "A minimalist travel poster with a cream background, a flat blue mountain illustration and restrained dark-blue typography, offset-print texture, calm and airy composition.",
  "canvas": "single",
  "meta": ["poster", "flat illustration"],
  "width": 1024,
  "height": 1536,
  "elements": [
    {"label": "object", "caption": "A flat blue mountain range illustration across the lower half, layered silhouettes with a pale sun disc behind them.", "bbox": [96, 820, 928, 1400]},
    {"label": "text", "caption": "Large dark-blue uppercase title, geometric sans-serif, centered with generous letter spacing.", "text": "EXPLORE", "bbox": [160, 220, 864, 400]},
    {"label": "text", "caption": "Smaller dark-blue Chinese subtitle on one line, clean and legible.", "text": "去山里走走", "bbox": [240, 440, 784, 540]}
  ]
}
```

## 例 3：纯文本 caption（不写 elements）

不写框位时就是普通文生图，模型自己排版，适合快速试风格：

```json
{
  "prompt": "A handwritten Chinese note stuck on a stainless-steel refrigerator with a small magnet, blue ballpoint pen, slightly crooked lines, soft kitchen light, shallow depth of field.",
  "aspect_ratio": "3:2",
  "steps": 8
}
```

## 例 4：参考图 + 四格漫画（img2img）

两张参考图分别绑一个主体（Picture 1 = 角色，Picture 2 = 道具），提示词用整页 Layout：

```json
{
  "prompt": "A four-panel full-color anime comic page in a 2x2 grid with thin dark borders and narrow white gutters. The same character in every panel: a girl with long wavy brown hair, amber eyes, tall brown rabbit ears with pink inner fur, a black ribbon bow, white off-shoulder blouse and brown pinafore dress. Warm autumn palette of ginkgo yellow and café amber. Panels read left to right, top to bottom.",
  "canvas": "multi_panel",
  "width": 1536,
  "height": 1024,
  "reference_images": ["girl.png", "repeater.png"],
  "elements": [
    {"label": "object", "caption": "Top-left panel: she walks a ginkgo avenue looking down at her phone with a startled, guilty expression.", "bbox": [56, 56, 748, 492]},
    {"label": "text", "caption": "White rounded speech bubble with a dark outline.", "text": "迟到了！", "bbox": [110, 80, 470, 190]},
    {"label": "object", "caption": "Top-right panel: she pushes open the café's glass door, wind chime above, cheeks flushed, breathing hard.", "bbox": [788, 56, 1480, 492]},
    {"label": "text", "caption": "White speech bubble with a thin dark outline.", "text": "抱歉抱歉…", "bbox": [850, 84, 1290, 200]},
    {"label": "object", "caption": "Bottom-left panel: across a wooden table a hand slides a steaming latte toward her; she cups it with both hands, ears perked, relieved smile.", "bbox": [56, 532, 748, 968]},
    {"label": "text", "caption": "Rounded white bubble with a soft brown outline.", "text": "还热着。", "bbox": [104, 600, 470, 716]},
    {"label": "object", "caption": "Bottom-right panel: two girls by the tall window laughing, ginkgo leaves drifting outside, coffee cups on the table.", "bbox": [788, 532, 1480, 968]},
    {"label": "text", "caption": "White rounded bubble with small motion lines.", "text": "下次早点出门。", "bbox": [830, 720, 1440, 848]}
  ]
}
```

要点：参考图不是身份锁定——人物与道具的特征仍要写进 `prompt` 与每格 `caption`；
两张图的顺序决定 Picture 1 / Picture 2 的编号，提示词里按编号指代，主体才不会串。

## 常见调整

| 想要的效果 | 调整方式 |
|---|---|
| 某格内容跑偏 | 收紧该格 `object` 的 `caption`，只写这一格里看得见的东西，不要写别格内容 |
| 气泡文字缺笔画/糊 | 加高该 `text` 的框（字号相对框高变大），或把长句拆成两个 `text` 元素 |
| 分格没画出来 | `canvas` 必须是 `multi_panel`，并在 `prompt` 里写明格数与格线样式（"2x2 grid with thick black borders"） |
| 风格不统一 | 把画风、媒介、配色写进 `prompt`，每格 `caption` 只写内容不写风格 |
| 想更细的单格画面 | 改用单幅 Layout 或 caption，一次一图，别硬塞四格 |
