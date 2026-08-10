# UltraReal 字段填写规范

## tags（必选）

@ 开头的标签，空格分隔。从下面两组中挑选组合：

相机/技术（选一个）：

- `@smartphone_photo` — 现代手机质感，轻微计算摄影处理
- `@compact_digital_photo` — 2000 年代卡片数码相机感
- `@film_photo` — 胶片质感，有机颗粒
- `@vhs_screencap` — 录像带截图，扫描线
- `@dslr_photo` — 专业单反，干净锐利

灯光/风格（可多选）：

- `@available_light` — 自然光
- `@direct_flash` — 硬直闪（夜景派对/数码感）
- `@candid_photo` — 抓拍 / `@posed_photo` — 摆拍
- `@mirror_reflection` — 对镜自拍
- `@underexposed` / `@overexposed` — 欠曝 / 过曝
- `@amateur_photo` / `@professional_photo`

## nltags（必选）

- 用**英文完整句子**描述人物、服装、姿势、表情、背景与光影，2-4 句写足细节
- **不要逗号分隔的标签堆叠**（tag-soup），本模型按自然语言段落训练
- 以角色名开头（"A selfie of Shiroko from Blue Archive..."），把角色当作照片本人来写
- 角色外观必须写进自然语言里（真实系模型不认识 booru 角色标签）：发色、发型、瞳色、标志性配饰（如白子的狼耳与黑围巾、芹香的深蓝双马尾）
- 多人场景逐角色分别描述外观与动作，可用角色名 + 位置（"Shiroko, on the left..."）区分

## quality_meta_year_safe（必选）

安全等级 + 模拟拍摄年份 + 质量分，空格分隔：

- 安全等级（必须明确）：`@sfw` 或 `@nsfw`
- 年份：`@1995` `@2000` `@2005` `@2010` `@2020` `@2025`
- 质量分：`score_5` ~ `score_9`

搭配建议：

- 高清干净：`score_8` / `score_9` + `@dslr_photo` / `@film_photo`
- 故意 lo-fi 粗糙感：`score_6` / `score_7` + `@smartphone_photo` / `@compact_digital_photo`
- 年份与相机保持一致更有说服力：如 `@compact_digital_photo` 配 `@2005`，`@smartphone_photo` 配 `@2025`

## neg（可选，一般留空）

默认已内置：`score_1, score_2, score_3, score_4, worst quality, low quality, blurry, jpeg artifacts, bad anatomy, bad hands, bad feet, extra fingers, missing fingers, text, watermark, logo` + 安全对立约束（正面 @sfw → 负面自动加 @nsfw，反之亦然）。

## 采样参数（可选）

- `sampler_name` / `scheduler`：默认 `er_sde` + `simple`，不要改（实测质量/指令遵循最佳且最快）。
- `steps`：默认 28。20 步已可用，28 步细节更稳；40 步提升有限、耗时线性增加。
- `cfg`：默认 4.0。3 更自然松散，4 均衡，5-6 更贴提示词但对比度/饱和度加重，复杂场景建议不超过 5。

## aspect_ratio（可选）

`16:9` `3:2` `4:3` `1:1` `3:4` `2:3` `9:16`，默认 `1:1`。竖屏（3:4 / 9:16）适合自拍与全身照。
