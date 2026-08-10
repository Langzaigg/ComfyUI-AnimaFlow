# UltraReal 提示词示例（碧蓝档案角色实拍）

## 1) 白子（Shiroko）教室自拍 —— 现代手机质感

```json
{
  "tags": "@smartphone_photo @amateur_photo @candid_photo @available_light",
  "nltags": "A medium close-up selfie of Shiroko from Blue Archive. She has short silver-grey hair and grey wolf ears, and wears a black scarf over a blue-and-white school uniform with a blue necktie. She holds the phone at arm's length with one hand and looks at the camera with a calm, expressionless face. The background is a sunlit classroom with wooden desks and a green chalkboard, slightly blurred.",
  "quality_meta_year_safe": "@sfw @2025 score_8",
  "aspect_ratio": "1:1"
}
```

## 2) 芹香（Serika）拉面店打工 —— 胶片质感

```json
{
  "tags": "@film_photo @amateur_photo @posed_photo @available_light",
  "nltags": "A full-body photo of Serika from Blue Archive standing in front of a small ramen shop. She has long dark blue hair tied in twin-tails and red eyes, and wears a beige work apron over a blue-and-white school uniform. She is holding a serving tray with both hands and smiling awkwardly at the camera. Warm afternoon sunlight, a noren curtain and a wooden signboard visible behind her.",
  "quality_meta_year_safe": "@sfw @2015 score_8",
  "aspect_ratio": "2:3"
}
```

## 3) 白子 + 芹香 双人放学自拍 —— 多人场景写法

多人时逐角色分别描述外观与动作，用角色名 + 位置（"Shiroko, on the left..."）区分，避免外观串扰：

```json
{
  "tags": "@smartphone_photo @amateur_photo @candid_photo @available_light",
  "nltags": "A candid photo of Shiroko and Serika from Blue Archive in a classroom after school. Shiroko, on the left, has short silver-grey hair and grey wolf ears, wearing a black scarf over a blue-and-white school uniform with a blue necktie, a calm expression on her face, holding up a smartphone to take a selfie of the two. Serika, on the right, has long dark blue twin-tails and red eyes, wearing a beige cardigan over the same uniform, pouting with her arms crossed. Late afternoon sunlight comes through the windows, with wooden desks and a green chalkboard behind them.",
  "quality_meta_year_safe": "@sfw @2025 score_8",
  "aspect_ratio": "1:1",
  "cfg": 4.0,
  "steps": 28
}
```

## 4) 芹香 夜景直闪 —— 复古数码相机 lo-fi

故意做旧：低 score + 卡片机 + 直闪 + 早年份：

```json
{
  "tags": "@compact_digital_photo @amateur_photo @candid_photo @direct_flash",
  "nltags": "An overexposed night snapshot of Serika from Blue Archive outside a convenience store. She has long dark blue twin-tails and red eyes, wearing a blue-and-white school uniform with a beige cardigan, caught mid-motion as she turns toward the flash. Harsh direct flash lighting, slight red-eye, visible digital noise and washed-out colors, dark parking lot background.",
  "quality_meta_year_safe": "@sfw @2005 score_6",
  "aspect_ratio": "3:4"
}
```

## 5) 白子 对镜自拍 —— mirror selfie

```json
{
  "tags": "@smartphone_photo @amateur_photo @mirror_reflection @posed_photo @available_light",
  "nltags": "A mirror selfie of Shiroko from Blue Archive in a bedroom. She has short silver-grey hair and grey wolf ears, wearing a black scarf and a blue-and-white school uniform. She holds her phone up with one hand to cover part of her face, body angled slightly to the mirror. Soft daylight from a window, a messy bed and posters visible in the reflection.",
  "quality_meta_year_safe": "@sfw @2025 score_8",
  "aspect_ratio": "3:4"
}
```

## 填写要点

- `quality_meta_year_safe`：高清干净 → `score_8/9`；lo-fi 粗糙 → `score_6/7` + 卡片机/手机 + 早年份
- 年份与相机匹配：`@2005` 配 `@compact_digital_photo`，`@2025` 配 `@smartphone_photo`
- `nltags`：以角色名开头，把角色当作照片本人直接展开外观描述；多人场景禁止把两人外观混写，逐角色分别描述
- `steps` / `cfg` / `sampler_name` / `scheduler` 一般用默认值即可
