# CyberRealistic Anima（v7.0 Turbo）提示词专家知识

写实向微调的 Anima（v7.0 Turbo 基于 Anima Turbo V1.1）：默认出半写实/写实 leaning 的画面，肤质、面部与眼睛细节更强，
不需要堆叠大量质量词也能得到完成度高的结果。标签与自然语言理解能力与 Anima 本体一致。

## 提示词方式

- **混合写法效果最好**：Danbooru/Gelbooru 标签 + 简短自然语言描述混用。纯 tag 也行，但混合写法最不容易被误读。
- **不要写过短的提示词**（结果不稳定）。纯自然语言至少写两句。
- 标签小写、用空格、不用下划线（`blue eyes, long hair`）；只有 score 类标签保留下划线。
- 多角色：先点名角色，再逐个描述外貌与动作，否则模型会混淆归属。
- 同一标签在 Danbooru 与 Gelbooru 写法不同时，用 Gelbooru 版本。

## 风格槽（最后的位置决定画风）

质量/风格标签的**最后一个**决定整体风格，换画风只换它：

- `realistic` / `real life`：写实 leaning（本模型默认定位）
- `anime`：默认二次元插画
- `anime screencap`：TV 动画截图感
- `@画师名`：指定画师风格（必须带 @，否则效果很弱；写实风下强画师会明显接管画面，慎用）

## 质量标签

两套体系可任意组合：

- 人类评分：`masterpiece, best quality, highres, ...`
- 美学评分：`score_9, score_8, ... score_1`（注意是 `score_8`，不是 Pony 的 `score_8_up`）

实用基线：

- 正面（真实感，默认）：`masterpiece, best quality, highres, score_8, score_9, <安全分级>, real life, realistic`
- 正面（半真实，更偏二次元）：`masterpiece, best quality, highres, score_7, score_8, <安全分级>, realistic`
- 负面（一般留空）：默认 cfg 1.0 下负面惰性不生效；要压制顽固属性（如乱码文字、低质元素）时填写，默认以 cfg 1.2 生效，
  可用官方 baseline：`worst quality, low quality, sketch, score_1, score_2, score_3, censored`

score 越高越精致；降到 `score_6, score_7` 会略偏"动漫感"。改 score 要搭配风格槽一起用。

## 标签顺序

`[质量/元数据/年份/安全 + 风格槽] [1girl/1boy 等] [角色 (from 作品)] [@画师] [通用标签]`

段内顺序无所谓。角色搭配人数标签（1girl），必要时用 from 带作品名
（如 `hyuuga hinata from boruto: naruto next generations`）。

## 采样参数

- 官方推荐（v7.0 Turbo）：steps 8-12（默认 10），cfg 1-1.5（默认 1.0），euler。
- turbo 系规则：默认 cfg 1.0 下负面惰性；写 neg 时默认以 cfg 1.2 使负面生效。
- 分辨率越高细节越好：推荐 1024x1536 / 768x1024 档位，不要超过约 2MP。

## 安全分级

默认按 safe 处理，用安全标签（`safe` / `sensitive` / `nsfw` / `explicit`）引导内容分级；
提示词信息不足时模型会自由发挥，分级标签要写明确。

## 实测注意点

- 衣物/招牌上偶尔自发出现乱码文字，在意时负面写 `text, watermark, logo, signature`（默认以 cfg 1.2 生效）。
- 写实风下去掉画师 tag 更稳；画面会被强画师风格接管。
- NSFW 提示词：正面强调 `uncensored, detailed anatomy`；有打码/审查倾向时把审查类词写进 `neg`（默认以 cfg 1.2 生效）：`censored, mosaic, mosaic censoring, bar censor, black bar, pixelated, censored genitalia`。
