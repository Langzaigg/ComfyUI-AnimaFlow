# Kira 示例

适用于 kira 与 kira-turbo。`tags` 使用英文自然语言完整句子（至少 2-3 句、写足细节），不要用标签堆叠。多角色时 `appearance` 留空，外观在自然语言中逐角色分别描述。

## 1) 单角色战斗场景（kira-turbo 默认参数即可）

```json
{
  "aspect_ratio": "1:1",
  "quality_meta_year_safe": "masterpiece, best quality, very aesthetic, sensitive",
  "count": "1girl",
  "character": "yukikaze (azur lane)",
  "series": "azur lane",
  "appearance": "long white hair, red eyes, fox ears, hair ribbon, white dress",
  "tags": "A girl charges across the ocean surface amid a naval battle, her rigging cannons firing, torpedoes streaking through the water. Explosions and black smoke rise in the background under a cloudy blue sky. Dynamic action pose with splashing waves."
}
```

## 2) 单角色风格化（painterly + 传统媒介）

```json
{
  "aspect_ratio": "2:3",
  "quality_meta_year_safe": "masterpiece, best quality, very aesthetic, absurdres, safe",
  "count": "1girl",
  "appearance": "long black hair, purple eyes, white dress, straw hat",
  "tags": "A painterly watercolor illustration of a girl standing in a blooming flower field, her white dress and long hair gently lifted by the wind. She is smiling softly at the viewer. Soft warm afternoon light with a dreamy atmosphere, rendered in a traditional watercolor medium with visible blending."
}
```

## 3) 双角色，已知角色

```json
{
  "aspect_ratio": "16:9",
  "quality_meta_year_safe": "masterpiece, best quality, very aesthetic, sensitive",
  "count": "2girls",
  "character": "shiroko (blue archive), serika (blue archive)",
  "series": "blue archive",
  "appearance": "",
  "tags": "Two girls are sitting together on a classroom bench, looking at the viewer with friendly smiles. The girl with medium-length silver hair, blue eyes and wolf ears is Shiroko, wearing a white sailor uniform with a blue scarf. The girl with long black hair in a low ponytail, red eyes and cat ears is Serika, wearing a black sailor uniform with a blue ribbon. Soft warm sunlight streams through the window, creating a cozy atmosphere."
}
```
