# MOSS-Image 调用示例

下面都是 `/moss/generate` 的请求体（`schemas/tool_schema_moss.json` 的字段）。
提示词固定混合写法：tag 字段（字段名同 Anima）+ `nltags` 句子；服务端按
`quality_meta_year_safe → count → character → series → appearance → artist → style → tags → environment` 再换行接 `nltags`。
Layout 模式下框位是**画布左上角原点的像素 `[x1, y1, x2, y2]`**，服务端负责换算成模型坐标。

## 例 1：单幅（混合写法）

```json
{
  "quality_meta_year_safe": "masterpiece, best quality, highres, year 2026, safe",
  "count": "1girl",
  "appearance": "long silver hair, blue eyes, white dress",
  "style": "anime color",
  "tags": "standing, wind",
  "environment": "sunflower field, sunlight, outdoors, depth of field",
  "nltags": "Late afternoon sun rakes across the field; she stands with one hand shading her eyes, wind pushing the flowers sideways, pollen glinting in the backlight.",
  "aspect_ratio": "2:3"
}
```

## 例 2：2×2 四格漫画（Layout 模式）

`quality_meta_year_safe` 里带上媒介（Meta 段），`nltags` 交代版面，`elements` 定每格与台词位置：

```json
{
  "quality_meta_year_safe": "masterpiece, best quality, four-panel comic, manga, black and white, safe",
  "count": "1boy, 1cat",
  "style": "monochrome, screentone",
  "canvas": "multi_panel",
  "width": 1536,
  "height": 1024,
  "nltags": "A four-panel black-and-white manga page in a 2x2 grid with thick black panel borders and narrow white gutters, clean ink lines and screentone shading. Panels read left to right, top to bottom; the same two characters throughout: a middle-aged interviewer in a grey suit and an orange tabby cat in a tiny navy suit.",
  "elements": [
    {"label": "object", "caption": "Top-left panel: the interviewer behind a desk holds a resume while the cat sits upright on the chair opposite.", "bbox": [56, 56, 748, 492]},
    {"label": "text", "caption": "White speech bubble with a black outline, top of the first panel.", "text": "你的经验？", "bbox": [120, 80, 520, 190]},
    {"label": "object", "caption": "Top-right panel: the cat proudly holds up a paper with a crude drawing of a caught mouse.", "bbox": [788, 56, 1480, 492]},
    {"label": "text", "caption": "Bouncy white speech bubble, second panel.", "text": "三年捕鼠经验。", "bbox": [880, 84, 1400, 200]},
    {"label": "object", "caption": "Bottom-left panel: the interviewer presses a palm to his forehead with an exasperated half-smile.", "bbox": [56, 532, 748, 968]},
    {"label": "text", "caption": "White speech bubble with a thin outline, third panel.", "text": "我们要的是程序员…", "bbox": [104, 596, 640, 726]},
    {"label": "object", "caption": "Bottom-right panel: the cat wears round glasses and types on a laptop, the interviewer leaning in amused.", "bbox": [788, 532, 1480, 968]},
    {"label": "text", "caption": "Compact white bubble with short motion lines, fourth panel.", "text": "那我现学。", "bbox": [860, 700, 1240, 824]}
  ]
}
```

四格按 56 边距均分：(56,56,748,492) / (788,56,1480,492) / (56,532,748,968) / (788,532,1480,968)，
气泡放在各自格内上部；框不要压人物脸，字号按框高 60% 左右估算。

## 例 3：参考图 + 双主体四格

两张图分别绑一个主体（Picture 1 = 角色，Picture 2 = 道具）：

```json
{
  "quality_meta_year_safe": "masterpiece, best quality, anime illustration, safe",
  "count": "1girl",
  "appearance": "long brown hair, rabbit ears, white off-shoulder blouse, brown pinafore dress",
  "canvas": "multi_panel",
  "width": 1536,
  "height": 1024,
  "reference_images": ["girl.png", "repeater.png"],
  "nltags": "A four-panel full-color anime comic page in a 2x2 grid, warm room light, the girl and a small white portable cassette repeater interacting; panels read left to right, top to bottom.",
  "elements": [
    {"label": "object", "caption": "Top-left panel: she lifts the white repeater out of a cardboard box, dust motes in a sunbeam.", "bbox": [56, 56, 748, 492]},
    {"label": "text", "caption": "White rounded bubble with a dark outline.", "text": "还能用吗？", "bbox": [110, 80, 520, 190]},
    {"label": "object", "caption": "Top-right panel: close-up of her finger pressing play, the speaker grille emitting drawn sound waves.", "bbox": [788, 56, 1480, 492]},
    {"label": "text", "caption": "Jagged sound-effect bubble beside the speaker.", "text": "第一课…", "bbox": [830, 90, 1300, 200]},
    {"label": "object", "caption": "Bottom-left panel: she repeats after the machine with a puzzled face.", "bbox": [56, 532, 748, 968]},
    {"label": "text", "caption": "Small bubble pointing at the girl.", "text": "apple…?", "bbox": [96, 620, 400, 716]},
    {"label": "object", "caption": "Bottom-right panel: she hugs the repeater and laughs, ginkgo leaves past the window.", "bbox": [788, 532, 1480, 968]},
    {"label": "text", "caption": "Warm rounded bubble, fourth panel.", "text": "原来你才是最好的听众。", "bbox": [806, 700, 1462, 848]}
  ]
}
```

要点：参考图不是身份锁定——人物与道具的特征仍要写进 `appearance` / `nltags` 与每格 `caption`；
两张图的顺序决定 Picture 1 / Picture 2 的编号，提示词里按编号指代，主体才不会串。

## 常见调整

| 想要的效果 | 调整方式 |
|---|---|
| 元素总是漏（人数、发色、服装） | 把它们写成 `count` / `appearance` / `tags` 的标准 tag，别只写在句子里 |
| 画面平淡、像贴图 | 在 `nltags` 里补镜头、光线、材质、前景遮挡；别加更多质量词 |
| 某格内容跑偏 | 收紧该格 `object` 的 `caption`，只写这一格里看得见的东西 |
| 气泡文字缺笔画/糊 | 加高该 `text` 的框，或把长句拆成两个 `text` 元素 |
| 分格没画出来 | `canvas` 必须是 `multi_panel`，并在 `nltags` 里写明格数与格线样式 |
| 风格不统一 | 画风写进 `style`，配色与光线写进 `nltags`，每格 `caption` 只写内容 |
| 想更细的单格画面 | 去掉 `elements` 走单幅，一次一图，别硬塞四格 |
