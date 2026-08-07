# 示例

`tags` 以标准 Danbooru 标签为主，没有符合的标准 tag 时用英文自然语言句子补充，不编造不标准 tag。多角色时 `appearance` 留空、`tags` 不含角色外貌标签，外观在自然语言部分逐角色分别描述。

## 1) 单角色竖构图

```json
{
  "aspect_ratio": "2:3",
  "quality_meta_year_safe": "masterpiece, best quality, sensitive",
  "count": "1girl",
  "character": "shiroko (blue archive)",
  "series": "blue archive",
  "appearance": "medium-length silver hair, blue eyes, wolf ears, white sailor uniform, blue scarf",
  "tags": "sitting, on desk, looking at viewer, smile, upper body, classroom, window, sunlight. Soft warm sunlight streams through the window, creating a cozy atmosphere.",
  "neg": "worst quality, low quality, artist name, blurry, jpeg artifacts, chromatic aberration, bad anatomy, bad hands, bad feet, extra fingers, missing fingers, text, watermark, logo, nsfw, explicit"
}
```

## 2) 双角色，已知角色

```json
{
  "aspect_ratio": "1:1",
  "quality_meta_year_safe": "masterpiece, best quality, sensitive",
  "count": "2girls",
  "character": "shiroko (blue archive), serika (blue archive)",
  "series": "blue archive",
  "appearance": "",
  "tags": "sitting, side by side, looking at viewer, smile, classroom, sunlight. The girl with medium-length silver hair, blue eyes and wolf ears is Shiroko, wearing a white sailor uniform with a blue scarf. The girl with long black hair in a low ponytail, red eyes and cat ears is Serika, wearing a black sailor uniform with a blue ribbon. They are sitting together on a classroom bench with friendly smiles.",
  "neg": "worst quality, low quality, artist name, blurry, jpeg artifacts, chromatic aberration, bad anatomy, bad hands, bad feet, extra fingers, missing fingers, text, watermark, logo, nsfw, explicit"
}
```

## 3) 双角色原创，横构图，explicit

```json
{
  "aspect_ratio": "3:2",
  "quality_meta_year_safe": "masterpiece, best quality, explicit",
  "count": "2girls",
  "appearance": "",
  "artist": "@makihitsuji",
  "tags": "standing, side by side, full body, forest, sunlight. Two girls stand side by side in an ancient forest clearing. The beastgirl warrior with short crimson red hair, amber eyes and wolf ears wears dark leather armor with fur trim and heavy boots, wielding a battle axe with a fierce grin. The elven mage with long silver-white hair, emerald green eyes and pointed ears wears a blue and white robe with glowing runes and pointed shoes, holding a crystal staff with a serene smile. Dappled sunlight filters through the canopy with floating golden particles.",
  "neg": "worst quality, low quality, artist name, blurry, jpeg artifacts, chromatic aberration, bad anatomy, bad hands, bad feet, extra fingers, missing fingers, text, watermark, logo, safe, sensitive, censored, mosaic"
}
```
