# 示例

`tags` 固定使用英文自然语言完整句子。多角色时 `appearance` 留空、`tags` 不含角色外貌信息，外观在自然语言中逐角色分别描述。

## 1) 单角色竖构图

```json
{
  "aspect_ratio": "2:3",
  "quality_meta_year_safe": "masterpiece, best quality, sensitive",
  "count": "1girl",
  "character": "shiroko (blue archive)",
  "series": "blue archive",
  "appearance": "medium-length silver hair, blue eyes, wolf ears, white sailor uniform, blue scarf",
  "tags": "A girl sits on a classroom desk, smiling at the viewer, shown from the waist up. Soft warm sunlight streams through the window, creating a cozy atmosphere.",
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
  "tags": "Two girls sit side by side on a classroom bench, smiling at the viewer. The girl with medium-length silver hair, blue eyes and wolf ears is Shiroko, wearing a white sailor uniform with a blue scarf. The girl with long black hair in a low ponytail, red eyes and cat ears is Serika, wearing a black sailor uniform with a blue ribbon. Warm sunlight fills the classroom with a friendly, cozy mood.",
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
  "tags": "Two girls stand side by side in an ancient forest clearing, shown full body. The beastgirl warrior with short crimson red hair, amber eyes and wolf ears wears dark leather armor with fur trim and heavy boots, wielding a battle axe with a fierce grin. The elven mage with long silver-white hair, emerald green eyes and pointed ears wears a blue and white robe with glowing runes, holding a crystal staff with a serene smile. Dappled sunlight filters through the canopy with floating golden particles.",
  "neg": "worst quality, low quality, artist name, blurry, jpeg artifacts, chromatic aberration, bad anatomy, bad hands, bad feet, extra fingers, missing fingers, text, watermark, logo, safe, sensitive, censored, mosaic"
}
```
