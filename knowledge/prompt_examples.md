# Base 1.0 示例

`tags` 只写标准 Danbooru 标签，无法标签化的内容放 `nltags` 自然语言描述，不编造不标准 tag。多角色时 `appearance` 留空、`tags` 不含角色外貌，外观在 `nltags` 逐角色分别描述。

## 1) 竖构图 9:16

```json
{
  "aspect_ratio": "9:16",
  "quality_meta_year_safe": "masterpiece, best quality, score_7, highres, newest, year 2025, sensitive",
  "count": "1girl",
  "character": "shiroko (blue archive)",
  "series": "blue archive",
  "appearance": "long silver hair, wolf ears, blue eyes, school uniform, necktie",
  "artist": "",
  "style": "anime illustration, vibrant colors",
  "tags": "upper body, looking at viewer, smile",
  "environment": "school, cherry blossoms, sunlight",
  "neg": "worst quality, low quality, score_1, score_2, score_3, artist name, blurry, jpeg artifacts, chromatic aberration, bad anatomy, bad hands, bad feet, missing fingers, extra fingers, text, watermark, logo, nsfw, explicit"
}
```

## 2) 横构图 16:10

```json
{
  "aspect_ratio": "16:10",
  "quality_meta_year_safe": "masterpiece, best quality, score_7, highres, newest, year 2025, sensitive",
  "count": "1girl",
  "character": "",
  "series": "",
  "appearance": "short hair, brown hair, red eyes, school uniform",
  "artist": "",
  "style": "anime illustration, vibrant colors",
  "tags": "full body, dynamic pose, running, wind, motion blur",
  "environment": "sunset, backlight, dust particles",
  "neg": "worst quality, low quality, score_1, score_2, score_3, artist name, blurry, jpeg artifacts, chromatic aberration, bad anatomy, bad hands, bad feet, extra fingers, missing fingers, text, watermark, logo, nsfw, explicit"
}
```

## 3) 超宽 21:9

```json
{
  "aspect_ratio": "21:9",
  "quality_meta_year_safe": "masterpiece, best quality, score_7, highres, newest, year 2025, sensitive",
  "count": "1girl",
  "character": "",
  "series": "",
  "appearance": "long hair, white dress",
  "artist": "@guweiz",
  "style": "painterly, atmospheric perspective",
  "tags": "wide shot, small figure, landscape, mountains, river, clouds",
  "environment": "golden hour, volumetric light, haze",
  "neg": "worst quality, low quality, score_1, score_2, score_3, artist name, blurry, jpeg artifacts, chromatic aberration, bad anatomy, bad hands, bad feet, extra fingers, missing fingers, text, watermark, logo, nsfw, explicit"
}
```

## 4) 双角色 1:1

```json
{
  "aspect_ratio": "1:1",
  "quality_meta_year_safe": "masterpiece, best quality, score_7, highres, newest, year 2025, sensitive",
  "count": "2girls",
  "character": "shiroko (blue archive), serika (blue archive)",
  "series": "blue archive",
  "appearance": "",
  "artist": "",
  "style": "anime illustration, soft lighting, detailed",
  "tags": "looking at viewer, smile, friends, leaning on each other",
  "nltags": "Shiroko has medium-length silver hair, wolf ears and blue eyes, wearing a white sailor uniform with a blue scarf. Serika has long black hair, cat ears and red eyes, wearing a black sailor uniform with a blue ribbon. The two girls are leaning on each other.",
  "environment": "classroom window, sunset, warm light",
  "neg": "worst quality, low quality, score_1, score_2, score_3, artist name, blurry, jpeg artifacts, chromatic aberration, bad anatomy, bad hands, bad feet, extra fingers, missing fingers, text, watermark, logo, nsfw, explicit"
}
```

## 5) 三角色 16:9

```json
{
  "aspect_ratio": "16:9",
  "quality_meta_year_safe": "masterpiece, best quality, score_7, highres, newest, year 2025, sensitive",
  "count": "3girls",
  "character": "hatsune miku (vocaloid), kagamine rin (vocaloid), kagamine len (vocaloid)",
  "series": "vocaloid",
  "appearance": "",
  "artist": "",
  "style": "anime illustration, soft shading",
  "tags": "group shot, looking at viewer, smile, singing, concert",
  "nltags": "Hatsune Miku has long aqua twintails and aqua eyes, wearing a teal sleeveless dress, black thighhighs and a headset microphone. Kagamine Rin has short blonde hair and blue eyes, wearing an orange sleeveless top, white shorts and a white hair bow, with a headset microphone. Kagamine Len has short blonde hair and blue eyes, wearing a white button-up shirt, black shorts and a yellow necktie, with a headset microphone.",
  "environment": "stage lights, colorful background",
  "neg": "worst quality, low quality, score_1, score_2, score_3, artist name, blurry, jpeg artifacts, chromatic aberration, bad anatomy, bad hands, bad feet, extra fingers, missing fingers, text, watermark, logo, nsfw, explicit"
}
```

## 6) 原创双角色纯自然语言 1:1

```json
{
  "aspect_ratio": "1:1",
  "quality_meta_year_safe": "masterpiece, best quality, score_7, highres, newest, year 2025, safe",
  "count": "2girls",
  "character": "",
  "series": "",
  "appearance": "",
  "artist": "@makihitsuji",
  "style": "fantasy illustration, detailed, soft lighting",
  "tags": "full body, group shot, standing side by side, magic effects, forest background",
  "nltags": "Two girls stand side by side in an ancient forest. The beastgirl warrior has short crimson red hair, amber golden eyes, and large wolf ears on top of her head. She wears dark leather armor with fur trim and wields a large battle axe. Beside her, the elven mage has long silver-white hair flowing down her back, bright emerald green eyes, and pointed ears. She wears elegant blue and white robes with glowing magical runes and holds a crystal staff.",
  "environment": "ancient forest, dappled sunlight, magical particles, mist",
  "neg": "worst quality, low quality, score_1, score_2, score_3, artist name, blurry, jpeg artifacts, chromatic aberration, bad anatomy, bad hands, bad feet, extra fingers, missing fingers, text, watermark, logo, nsfw, explicit"
}
```
