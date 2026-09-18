# Anima 2.9B Turbo（anima29B_v10 + anima29b-turbolora1.1 LoRA）提示词规范

Anima base 的层扩展微调（28→40 层，~2.9B 参数，追加 1.7M 二次元/插画样本，知识截止 2026-07），
再加载 Turbo LoRA v1.1（`anima29b-turbolora1.1`，Turbo-ANIMA-v4 的 2.9B 重映射版，非官方衍生；
原始出处 <https://civitai.com/models/2619830/turbo-for-anima-less-steps>）做快速生成。

## 字段规则

| 字段 | 写法 |
|------|------|
| `quality_meta_year_safe` | `year 2026, <safe/sensitive/nsfw/explicit>`。**避免一切质量标签与 score**：masterpiece / great quality / best quality / very aesthetic / score_N 等一律不要（训练数据无 score 标签，质量词对本模型只会引入噪声）；保留年份/时期标签。 |
| `count` | `1girl` / `2girls` / `1boy` / `1other` |
| `character` / `series` | 角色名可带作品 `yunli (honkai star rail)`，角色名必须紧跟作品/版权标签，否则模型可能张冠李戴。多人逗号分隔。**避免下划线**：写 `hatsune miku` 而非 `hatsune_miku`（角色/作品标签对下划线最敏感）。 |
| `artist` | `@` 开头，如 `@wlop`。基础画风仅比 base 略好，**仍建议显式给 @画师标签**来锚定画风。画师标签同样**避免下划线**。 |
| `appearance` | 逗号分隔的标准 Danbooru 标签（发色、瞳色、服装），只填有明确指代的标准 tag，不要编造；没有合适 tag 的外貌细节写到 tags 的自然语言中。仅单角色使用，多角色必须留空。带下划线的标准 tag 可接受（其他标签也尽量避免 `_`，但影响不大）。 |
| `tags` | **英文自然语言完整句子**，写动作、表情、构图、场景、氛围与光影。**提示词越详细越好**：至少 2-3 句写足细节，短提示常生成平淡的简单背景。多角色时禁止写角色外貌，外貌逐角色分别描述。 |
| `neg` | **一般留空**（默认 cfg 1.0，负面不进采样）；需要排除特定元素时填写，填写后默认以 cfg 1.2 使负面生效，见下方"负面提示词"一节。 |
| `aspect_ratio` | `16:9` `3:2` `1:1` `2:3` `9:16`，默认 `1:1` |

## 多角色

- `appearance` 必须留空
- `tags` 的自然语言只写共性姿势/构图，角色与其外貌/服装就近归属，逐角色分别描述："The girl with crimson hair and wolf ears..."
- 共处式描述，不用位置分割词（"On the left... On the right..."）

## 采样参数

steps 8-12（默认 8），cfg 1.0-1.6（无 neg 默认 1.0，填写 neg 后默认 1.2），euler + sgm_uniform。

## 分辨率

官方推荐 812x1216 / 1152x1536 / 1536x1536（1536 不太稳）。约 70% 训练算力在 1024px，
默认 `aspect_ratio`（~1MP，如 2:3 → 848x1264）即可，与推荐档位接近。

## 负面提示词

默认留空：cfg 1.0 时负面不进采样。首选仍是**正向写法规避**——不想要的元素不要提及（模型常把否定词也当成概念引入），用正向描述替代（如要无文字背景就简化场景、写 `simple background`）。

正向写法管不住的元素（如角落假签名、水印、logo 类伪影）写进 `neg`：填写后默认以 cfg 1.2 采样、负面生效；cfg 可在 1.0-1.6 内显式调整。

## 模型限制

不支持生成文字/LOGO/UI/对话框/气泡。`tags` 中禁止 text, sign, letter, ui, interface, hud, menu, button, dialog, speech bubble, thought bubble, logo。
