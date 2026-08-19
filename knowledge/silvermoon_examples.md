# Silvermoon 示例

`tags` 固定使用英文自然语言完整句子。多角色时 `appearance` 留空、`tags` 不含角色外貌信息，外观在自然语言中逐角色分别描述。模型不支持文字/UI/气泡/LOGO。

## 1) 单角色竖构图

```json
{
  "aspect_ratio": "2:3",
  "quality_meta_year_safe": "masterpiece, best quality, highres, newest, year 2025, safe",
  "count": "1girl",
  "character": "shiroko (blue archive)",
  "series": "blue archive",
  "appearance": "medium-length silver hair, blue eyes, wolf ears, white sailor uniform, blue scarf",
  "tags": "A girl sits on a classroom desk, smiling at the viewer, shown from the waist up. Soft warm sunlight streams through the window, creating a cozy atmosphere."
}
```

## 2) 双角色，已知角色

```json
{
  "aspect_ratio": "1:1",
  "quality_meta_year_safe": "masterpiece, best quality, highres, newest, year 2025, safe",
  "count": "2girls",
  "character": "shiroko (blue archive), serika (blue archive)",
  "series": "blue archive",
  "appearance": "",
  "tags": "Two girls sit side by side on a classroom bench, smiling at the viewer. The girl with medium-length silver hair, blue eyes and wolf ears is Shiroko, wearing a white sailor uniform with a blue scarf. The girl with long black hair in a low ponytail, red eyes and cat ears is Serika, wearing a black sailor uniform with a blue ribbon. Warm sunlight fills the classroom with a friendly, cozy mood."
}
```

## 3) 双角色原创 + 画师风格

```json
{
  "aspect_ratio": "3:2",
  "quality_meta_year_safe": "masterpiece, best quality, highres, newest, year 2025, safe",
  "count": "2girls",
  "appearance": "",
  "artist": "@makihitsuji",
  "tags": "Two girls stand side by side in an ancient forest clearing, shown full body. The beastgirl warrior with short crimson red hair, amber eyes and wolf ears wears dark leather armor with fur trim and heavy boots, wielding a battle axe with a fierce grin. The elven mage with long silver-white hair, emerald green eyes and pointed ears wears a blue and white robe with glowing runes, holding a crystal staff with a serene smile. Dappled sunlight filters through the canopy with floating golden particles."
}
```

## 4) 三人场景 + 画师风格

```json
{
  "aspect_ratio": "3:2",
  "quality_meta_year_safe": "masterpiece, best quality, highres, newest, year 2025, safe",
  "count": "3girls",
  "appearance": "",
  "artist": "@makihitsuji",
  "tags": "Three kemonomimi girls relax together in a sunny flower meadow, sitting on a picnic blanket and sharing snacks, all smiling. The girl with long golden blonde hair, green eyes and fox ears wears a red plaid country dress with a white apron. The girl with short silver hair, blue eyes and wolf ears wears a black hoodie and denim shorts. The girl with pink twin-tails, amber eyes and cat ears wears a frilly white lolita dress with ribbon bows. Warm afternoon sunlight, cheerful carefree atmosphere."
}
```
