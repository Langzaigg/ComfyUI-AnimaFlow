# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **人设库 `/anima/characters`（2026-09-30）**: 新增 `characters/` 包（`store.py` JSON 文件存储：进程内锁 + 原子写 + `.bak` + 按 mtime 自动重载 + revision/ETag；`routes.py` aiohttp 路由），接口 `GET|POST /anima/characters`、`GET|PUT|PATCH|DELETE /anima/characters/{id}`、`POST /anima/characters/match`、`POST /anima/characters/import`（merge / replace）、`GET /anima/characters/schema`。人设字段：name/aliases/tag_name/series/count/tags/description/outfits/artist/labels/nsfw/source/extra（自然语言只有 description 一个字段，绘制注意也写在里面；早期草案的 notes 读取时并入 description，personality 丢弃）。数据默认存 `data/characters.json`（新增 gitignore，含私人设定不进仓库），可用 `ANIMATOOL_CHARACTERS_FILE` 覆盖。供 Web 画图前端与聊天机器人等下游共用。

- **fuse 1.1 / Turbo LoRA 1.1 横评与转正（2026-09-18）**: `examples/anima29_newmodels_test.py` + 融合/重映射脚本 `merge_sm29t_fuse_turbo.py` / `merge_sm29_fuse_turbo.py` / `merge_fuse29aes_turbo.py` / `remap_turbo_v4_lora_29b.py`，14 场景（含新单人例 s11_tuchan_autumn / s12_tuchan_coat 兔酱秋装）× 多模型同 seed 横评。结论：silvermoon29_turbo × turbo1.1 融合比例 0.3 为甜区（3.5 第一/2 垫底），改走旧 fuse 参数（8 步 cfg1.2+文字负面）无稳定收益；r030 + silvermoon_turbo 官方参数（10 步 cfg1 euler a+normal 无负面）转正为新 fuse。报告：`examples/results/anima29_newmodels_20260918_101609/report.md`。
- **fuse v1.1 工作流**: `fuse` 预设换用融合 UNET `anima29b-sm29t-fuse1.1.safetensors`（[SilvermoonMix Anima Evolved](https://civitai.com/models/2639339/silvermoonmix-anima-evolved) v2329B Turbo × anima-turbo-v1.1 按 0.3/0.7 加权，非官方衍生），采样 10 步、cfg 固定 1.0、Euler a + normal、无负面；`knowledge/fuse_expert.md` 与 `schemas/tool_schema_fuse.json` 重写（neg 字段改为惰性说明，cfg 字段移除）。
- **fuse1.0 工作流（已过期）**: 旧 fuse（`anima29b-p1-turbo1.1.safetensors`，8 步 euler+sgm_uniform，内置文字类负面 cfg 1.2）平移为 `fuse1.0` 并标记 `deprecated: true`；schema/knowledge 快照为 `tool_schema_fuse10.json` / `fuse10_expert.md`。
- **silvermoon_turbo 工作流**: 新增 `silvermoon_turbo` workflow（v2329B Turbo 变体 `silvermoonmixAnima_v2329BTurbo.safetensors`：10 步（8-12）、cfg 1.0（写 neg 默认 1.2）、Euler a + normal、默认无负面）；新增 `schemas/tool_schema_silvermoon_turbo.json` 与 `knowledge/silvermoon_turbo_expert.md`，两处 WORKFLOWS 注册表与 generate 分发已同步。
- **Turbo LoRA v1.1（anima29_turbo）**: 默认 LoRA 换为 `anima29b-turbolora1.1.safetensors`（[Turbo-ANIMA](https://civitai.com/models/2619830/turbo-for-anima-less-steps) v4 的 2.9B 免补丁重映射版，非官方衍生；`examples/remap_turbo_v4_lora_29b.py` 生成，1362 键/1248 重映射），强度 0.8 与采样参数不变，不再需要 loraPatch 运行时补丁。
- **v1.1 衍生模型发布**: Hugging Face 仓库 <https://huggingface.co/Langzaigg/anima29b-turbo1.1-unofficial>（fuse 融合 UNET v1.1 + Turbo LoRA v1.1 双产物，CircleStone 非商业许可）。

### Changed

- **silvermoon 升级 v2329B**: `silvermoonmixAnima_v23` → `silvermoonmixAnima_v2329B.safetensors`，24 步（20-28）cfg 4.5（4-5）Euler a + normal，默认无负面（官方建议）。
- **cyberreal 升级 v7.0 Turbo**: `cyberrealisticAnima_v60AestheticV11` → `cyberrealisticAnima_v70Turbo_bf16.safetensors`（基于 Anima Turbo V1.1；[CyberRealistic Anima (Civitai)](https://civitai.com/models/2668799/cyberrealistic-anima)），官方推荐 cfg 1-1.5 / steps 8-12：预设改为 10 步、cfg 1.0（写 neg 默认 1.2）、euler；旧版内置 baseline 负面取消（负面默认惰性）；提示词写法（score_N + 风格槽）不变。`knowledge/cyberreal_expert.md` 与 `schemas/tool_schema_cyberreal.json` 已同步。
- **turbo/aesthetic 模型文件名数字更新**: `anima-turbo-v1.1.safetensors` / `anima-aesthetic-v1.1.safetensors`。
- **测试注册表收敛**: `examples/model_test/models.py` 移除引用已清理探针 checkpoint 的条目（sm29t/sm29 融合比例探针、fuse29aes、v23 对照、旧 fuse 强度/采样探针、v2.9/v3 LoRA 探针等）；`fuse` 描述更新、`fuse1.0` 标记 `deprecated: true`、`exp29_turbov4` 改用 turbolora1.1。

### Removed

- **未转正探针 checkpoint 清理**: 融合探针 `anima29_fuse_turbo_r080/r090/r100`、`sm29t_fuse_turbo_r050/r080`、`sm29_fuse_turbo_r080`、`anima29b-aes-turbo1.1`，旧模型 `silvermoonmixAnima_v23`、`anima29B_v10_int8`、`cyberrealisticAnima_v60AestheticV11`（被 v7.0 Turbo 取代），已移除工作流的旧模型 `miaomiaoHarem_anima15` / `miaomiaoHarem_anima8Step10` / `novaAnimeAM_v40` / `nyaIrisAnima` / `anima-kirazuri-v4`（kira/nova/miao 工作流 2026-08-28 已移除，测试注册表 kira 死条目一并删除），旧 LoRA `Turbo-ANIMA-v2.9`、`anima29b-turbo-v2.9-remap`、`Turbo-ANIMA-v3`、`Anima-2.9B_Turbo-BF16`、`Turbo-ANIMA-v4`（28 块原版）、`kirazuri-anima-turbo-v4-8step`——均无现役预设引用，共释放约 71GB。

### Changed

- **README 重写**: 精简为快速入口（安装 / 三种接入 / 工作流一览与选型 / 文档导航），详细参数与故障排查移至 wiki；新增「工作流特点与选型」章节与同 prompt 同 seed 的多人兽耳娘场景六工作流对比例图（`assets/example_picnic_compare.webp`）；测试脚本与生成结果（`examples/` 测试代码、`outputs/`）不再进 git，仅保留 `examples/requests/` 与 `examples/loras/` 示例。

### Added

- **Anima 2.9B 工作流**: 新增 `anima29` / `anima29_turbo` workflow，使用 `anima29B_v10.safetensors`（Anima base 的 28→40 层扩展微调，知识截止 2026-07）。
  - 参数：Euler + sgm_uniform, CFG 3.5-5, steps 28-50 默认 30；turbo 变体加载 `Anima-2.9B_Turbo-BF16.safetensors` LoRA（strength 1.0），CFG 固定 1，steps 8-12 默认 8。
  - `_V2_MODEL_PRESETS` 新增 `anima29` / `anima29_turbo` 两个预设；`_inject_v2` 支持预设级 LoRA（`lora` / `lora_strength`，可被 payload 覆盖）。
  - 新增文件：`knowledge/anima29_expert.md`；注册入口：包 `__init__.py` 与 `servers/http_server.py` 均已注册并分发。
  - int8 量化预设（`anima29_int8` / `anima29_int8_turbo`）在 XPU 上实测更慢且加载不稳定（曾致 ComfyUI 崩溃），已从预设与测试注册表移除；确需量化版时可在 anima29 工作流下用 payload `unet_name` 手动覆盖。
- **可复用模型测试框架**: `examples/model_test/`（场景库 `scenes.py` + 模型注册表 `models.py` + 运行器 `runner.py`），测试结果统一保存到 `examples/results/<run_name>_<时间戳>/`（prompts.json / summary.json / images/），新模型测试只需在注册表加条目后选定场景运行。首个使用案例：`examples/anima29_compare_test.py`。
- **cfg=1 时保留负面提示词（可选，三种互斥）**: payload 传 `neg_scale`（PerpNegGuider，>1，推荐 1.5-3.0）/ `nag_scale`（内核 NAGuidance，推荐 4-6）/ `anima_nag_scale`（ComfyUI-Anima-NAG 插件，推荐 2.0，Anima 系首选）之一即可让 cfg=1 的 turbo 工作流（turbo_v1 / anima29_turbo 等）下负面提示词生效；PerpNeg 每步多约 2 次前向，NAG 系为模型补丁开销更小。`schemas/tool_schema_simple.json` 已新增对应参数。对比测试：`examples/anima29_negprobe_test.py`。
- **工作流弃用标记与查询接口**: `turbo`(0.2) / `kira` / `kira_turbo` / `nova` / `miao` / `miao_turbo` 标记 `deprecated`；`GET /anima/workflows`（ComfyUI 路由）与 `GET /workflows`（独立 FastAPI）现在返回每个工作流的一句话描述、弃用状态与相关接口（generate / schema / knowledge）。
- **角色测试场景修正与扩充**: `scenes.py` 的 `s2_cpk_trio` 修正超时空辉夜姬角色要点（辉夜金瞳+月牙镂空黑T恤，彩叶不写死瞳色，八千代蓝紫长发）；新增 `s10_ananta_requiem`（异环 Neverness to Everness 的安魂曲/Lacrimosa）；复测脚本 `examples/anima29_charfix_test.py`（s2 修正版 + s10 + s3_rossi）。
- **cfg=1 负面引导对比测试（第二轮）**: 新增 `np_text` / `np_detail` 探针场景与 `examples/anima29_negprobe2_test.py`，对 turbo_v1 / anima29_turbo × baseline/perpneg/nag_core/anima_nag 共 16 张对比；结论：场景级概念（text/sign）三方案全部压制失败，PerpNeg 仅对简单属性词（blush）在 turbo_v1 上有效但有改构图/引入反义元素副作用，内核 NAG 全无效，Anima-NAG 仅个别部分生效——turbo（cfg=1）下推荐正向写法规避负词。报告：`examples/results/anima29_negprobe2_20260818_113417/report.md`。
- **新提示词规范全场景复测**: `examples/turbo_newrule_compare_test.py`（anima29_turbo / turbo_v1 × 14 场景，含 4 个 NSFW）、`examples/anima29_year2025_probe_test.py`（year 2025 vs 2026 探针，6 场景）与 `examples/anima29_noyear_probe_test.py`（无年份探针，质量前缀仅 `<rating>`，6 场景）。结论：anima29_turbo 去掉质量词后 10 个同 seed 对照场景 0 劣化（1 优 2 平偏优 7 平）；turbo_v1 同 seed 全部可复现；year 2025 与 2026 基本无差别（仅一个 NSFW 场景 2025 版出文字伪影）；无年份组三方对比 5/6 场景与 2025/2026 版近乎逐像素同构、角色还原（含 2026 新番/新游）不依赖年份词，NSFW 场景文字伪影与是否写年份无关（2025 版与无年份版各出一次伪签名，2026 版两批均干净，样本小仅作倾向）——默认仍保留 `year 2026`。报告：`examples/results/newrule_compare_20260818_145526/report.md`。
- **Silvermoon vs Anima 2.9B Turbo 全场景对比**: `examples/silvermoon_vs29_compare_test.py`（silvermoon 20 步现行默认 × 14 场景，同 seed 对照 anima29_turbo 8 步）。结论：silvermoon 10 胜 2 负 2 平——指令遵循/角色还原/画师画风全面占优（复杂构图 s9 与多人归属优势最明显），anima29_turbo 胜在环境氛围与速度（~8-16s vs ~26-49s/张）；文字伪影双方均有发作，silvermoon 靠精简负面大部分场景压住，anima29_turbo 无负面反而发作更频繁。历史 2026-08-13 的 silvermoon 图经 PNG 元数据确认为旧默认 25 步，本轮为 20 步首次受控对比。报告：`examples/results/silvermoon_vs29_20260818_160327/report.md`。
- **Silvermoon vs Anima 2.9B（非turbo）全场景对比**: anima29（30 步 cfg4）侧复用 2026-08-17 历史出图 10 场景（旧质量词前缀）+ `examples/anima29_fill_test.py` 新前缀补缺 4 场景（cpk1/cpk2/sm_single/sm_dual）。结论：silvermoon 11 胜 2 负 1 平——指令遵循/角色还原继续全面占优且比 anima29 快约 2 倍（26-49s vs 66-114s/张）；anima29 胜在暖调氛围与画师贴合（s1、s6）；霓虹夜景乱码是双方共同弱项。综合本批两轮对比：指令遵循/还原优先选 silvermoon，速度优先 anima29_turbo，anima29 系画风氛围优先选 anima29。报告：`examples/results/silvermoon_vs29_20260818_160327/report_vs_anima29.md`。
- **rdbt v2.0 LoRA 探针（测试专用，未落 API）**: `examples/anima29_rdbt_probe_test.py` + `examples/model_test` 新增 kind=custom 生成钩子，注册 `anima29_rdbt`（base→distilled addon 双 LoRA）/ `anima29_rdbt_base`（仅 base）两个变体（cfg=1，16 步，提示词结构与 anima29_turbo 共通），12 场景 × 4 配置（对照 anima29_turbo 8 步与 anima29 30 步）同 seed 对比。结论：distilled addon 12/12 场景一致提升（仅 base 普遍发灰软糊、要素漂移，不可用）；rdbt 双 LoRA 同 cfg=1 档 10/12 场景胜 turbo，8/12 场景追平或反超 30 步裸模型（含全部 NSFW 场景），耗时 ~17-31s/张（turbo 的 2 倍、30 步的 1/3-1/4），为当前 anima29 系性价比最优配置；建议后续正式落入插件 API。报告：`examples/results/anima29_rdbt_probe_20260818_210509/report.md`。
- **rdbt 仅 base LoRA 步数收敛性追测（20/25 步）**: `examples/anima29_rdbt_basesteps_test.py <steps>`（参数化步数探针，替代已删除的 base20 专用脚本）；models.py 新增 `anima29_rdbt_base20` / `anima29_rdbt_base25` 变体。结论：20 步未收敛（人工目检后中止，`anima29_rdbt_base20_20260818_213625`）；25 步 7/12 场景收敛、3/12 改善但未完全、2/12（s3/s10）与 16 步逐像素级一致（残余软糊为 base LoRA 固有油画风而非步数问题），且 25 步单 LoRA 仍追不平 16 步双 LoRA 并更慢（~40-47s/张）——仅 base 在任何步数下都不值得用。结果目录：`anima29_rdbt_base25_20260818_214239`，结论已并入 rdbt 探针报告第四节之二。
- **测试注册表收敛**：`examples/model_test/models.py` 仅保留 `anima29_rdbt`（双 LoRA 16 步）为可用状态，`anima29_rdbt_base` / `anima29_rdbt_base20` / `anima29_rdbt_base25` 三个单 LoRA 变体标记 `deprecated: true`（仍可显式复测，runner 会打印弃用警告）。
- **anima29_rdbt 工作流正式落入插件 API**: 新增 `anima29_rdbt` workflow（rdbt v2.0 双 LoRA：`rdbt_v2.0_base_anima2.9b_p1_lora.safetensors` → `rdbt_v2.0_distilled_addon_anima2.9b_p1_lora.safetensors` 串联，cfg 固定 1，steps 8-32 默认 16，euler + sgm_uniform）。`_V2_MODEL_PRESETS` 新增预设并支持 `lora_addon` 第二 LoRA 串联（`_inject_v2` 内与 `_inject_loras` 同构的链式注入）；新增 `schemas/tool_schema_anima29_rdbt.json` 与 `knowledge/anima29_rdbt_expert.md`（提示词规范与 anima29 系一致：year 2026 前缀、无质量词、不写负面）；两处 WORKFLOWS 注册表与 generate 分发（`__init__.py` / `servers/http_server.py`）已同步，下次重启 ComfyUI 生效；测试注册表 `anima29_rdbt` 已切换到官方预设路径。

- **Silvermoon 工作流**: 新增 `silvermoon` workflow，使用 `silvermoonmixAnima_v23.safetensors` 完整 UNET。
  - 参数：Euler a + normal, CFG 4-5, steps 20-30。步数实测 20 步已收敛且更高步数文字伪影增多，默认 20 步。
  - 默认精简负面 `text, letters, sign, logo, watermark, signature, ui, interface`；nsfw/explicit 分级时自动追加 `mosaic, censored`。
  - 新增文件：`schemas/tool_schema_silvermoon.json`、`knowledge/silvermoon_expert.md`、`knowledge/silvermoon_examples.md`。
  - 注册入口：包 `__init__.py`（ComfyUI 路由）与 `servers/http_server.py`（独立 FastAPI 服务）均已注册并分发。
  - 新增测试脚本与报告：`examples/silvermoon_nova_compare_test.py`、`examples/silvermoon_nova_compare_report.md`、`examples/silvermoon_steps_test.py`、`examples/silvermoon_steps_report.md`。
- **anima29_turbo Turbo LoRA 强度探针（0.7 / 0.5）**: `examples/anima29_turbo_lorastrength_test.py` + 注册表变体 `anima29_turbo_s07` / `anima29_turbo_s05`（payload 级 `lora_strength` 覆盖，executor 零改动），12 场景（含 4 NSFW）× 0.7/0.5，同 seed 对照 1.0 基准。结论：12/12 场景排序一致为 1.0 ≥ 0.7 > 0.5——0.7 全场景可用平替（差异在种子噪声范围内，无速度收益）但无下调理由；0.5 全部劣化（5 轻微 / 7 明显），普遍出现欠收敛（发灰、对比度降、线条变肉、上色变薄）并伴随指令稳定性损失（瞳色错 ×3、狼尾丢失、武器畸形、构图噱头失败、文字伪影失控 ×2）——默认强度维持 1.0，0.7 为安全下限，0.5 不可用。报告：`examples/results/anima29_turbo_lstrength_20260819_090216/report.md`。
- **AuraAnima 2.9B qpolaP101 Int8 W8a8 量化冒烟测试**: `examples/auranima29_smoke_test.py` + 注册表 6 个 custom 变体（`auranima29_speed_*` euler+simple 10 步 / `auranima29_prec_*` er_sde+beta 12 步，cfg 5，各配 `anime color` / `photo real` / `real skin` 风格质量标签，payload `unet_name` 覆盖 + 注入后改采样参数绕过预设钳制）；scenes.py 新增 `s4r_noartist`（s4 同 seed 去画师对照）。结论：量化版无 artifacts 且速度与 BF16 同档（~2.7 s/步，12 张全无异常）；风格标签三档全部有效（ac=动画平涂，pr/rs=真人写实）；prec 方案 2:1 综合优胜（rs 风格下有乱码文字风险时 speed 更稳）；画师 tag 3/3 组生效显著且优先级高于 pr/rs 写实标签。报告：`examples/results/auranima29_smoke_20260819_092133/report.md`。
- **AuraAnima 2.9B Int8 完整场景测试（4 组 × 12 场景）**: `examples/auranima29_full_test.py`；runner 新增模型级 `strip_artist`（build_payload 剥掉场景 artist 字段），注册表新增 `auranima29_speed_pr_na` / `auranima29_prec_pr_na`（photo real 无画师）；rs 风格弃用，保留 ac（带画师）与 pr（无画师）两条路线 × speed/prec 双方案。评估标准含速度权衡（prec ≈ 1.7× speed 耗时，需实质提升才判值）。结论：prec_ac 11/12 质量第一、9/12 性价比第一——提升落在氛围要素/细节密度/指令修复；speed_ac 3/12 性价比胜（简单场景 s5/s10 仅抛光、复杂构图噱头 s9 prec 构图反而漂移）；pr_na 路线与角色/画师驱动场景结构性错配 0/12 推荐（真人化丢动画特征），speed_pr_na 塑料感/恐怖谷频发全部垫底；48 张量化 artifacts 全无。生产档位建议：默认 prec_ac，批量/简单/复杂构图用 speed_ac，原创写实用 prec_pr_na。报告：`examples/results/auranima29_full_20260819_094553/report.md`。
- **aura / aura-speed 工作流正式落入插件 API**: 新增 `aura`（精度重视：er_sde+beta，steps 8-30 默认 12）与 `aura-speed`（速度重视：euler+simple，steps 8-30 默认 10）两个 workflow，共用 AuraAnima 2.9B qpolaP101 Int8 W8a8 量化模型（`auranima29B_qpolaP101Int8W8a8.safetensors`），cfg 4.0-5.0 可调默认 5.0（负面正常生效）。`_V2_MODEL_PRESETS` 新增两预设（config.py 新增 AURA_* 常量）；新增 `schemas/tool_schema_aura.json` / `tool_schema_aura_speed.json` 与 `knowledge/aura_expert.md` / `aura_speed_expert.md`（按唯一工作流视角分文件）：风格质量标签三选一——`photo real`（默认，用户无指定时用）/ `anime color` / `real skin`，写实路线禁带画师 tag，版权角色还原建议 anime color；两处 WORKFLOWS 注册表与 generate 分发（`__init__.py` / `servers/http_server.py`）已同步，下次重启 ComfyUI 生效。
- **anima29_turbo 默认 LoRA 强度定案 0.8**: `examples/anima29_turbo_lstrength08_test.py` 补测 0.8（注册表 `anima29_turbo_s08`），与 0.7/1.0 同 seed 三方对比（聚焦锐利程度与签名/文字伪影）。结论：0.8 获 7/12 场景最优（1.0 为 5/12，0.7 为 0），锐利度保住 1.0 九成以上且伪影发作最少（2 处 vs 1.0 与 0.7 各 4 处）——`_V2_MODEL_PRESETS["anima29_turbo"]` 的 `lora_strength` 默认改为 0.8（payload 仍可覆盖）。报告：`examples/results/anima29_turbo_lstrength08_20260819_104351/report.md`。
- **fuse 工作流**: 新增 `fuse` workflow（turbo v1.0（实为 turbo 1.1）与 Anima 2.9B preview1 经 AnimaModelMerge 融合的 UNET `anima29b-p1-turbo1.1.safetensors`，turbo 权重 0.8，euler + sgm_uniform，steps 8-12 默认 8，cfg 1.0-1.6）。内置文字类默认负面（text/letters/sign/logo/watermark/signature/username/artist name）并默认以 cfg 1.2 采样使其生效，角落假签名/@用户名水印/logo 类伪影显著减少（对内容型文字如霓虹招牌无效）；payload 填 `neg` 会替换内置负面。新增 `schemas/tool_schema_fuse.json` 与 `knowledge/fuse_expert.md`；两处 WORKFLOWS 与 generate 分发已同步。融合强度定案：r080 与 r100 全场景横评 SFW 持平、NSFW 解剖细节略优，100% 放大细节对比同档，取 0.8 转正为独立模型。横评与探针报告：`examples/results/turbo_fusion_full_20260827_122034/report.md`、`turbo_fusion_v2_20260827_134448/report.md`、`turbo_fusion_neg_20260827_141033/report.md`、`turbo_fusion_r080_20260827_165552/report.md`。
- **fuse 融合强度 NSFW 复评（r080/r090/r100）**: `examples/turbo_fusion_r090_test.py` 追加 r090（turbo 权重 0.9）变体，三权重 × cfg1.2/cfg1.0 裸奔 × 4 NSFW 场景同 seed 对比。结论：马赛克/黑条 24 张全程零发作；假签名/logo 的决定性因素是 cfg 1.2 负面分支而非配比（cfg1.0 裸奔三权重在画师场景全部发作、程度相当，cfg1.2 全部干净）；人体解剖细节三方同档，0.9 无可辨收益——维持 r080 转正不变，`anima29b-p1-turbo1.1.safetensors` 内容与 fuse 预设均不动。报告：`examples/results/turbo_fusion_r090_20260828_093043/report.md`。
- **turbo 系 cfg 1.2 负面分支**: turbo_v1 / anima29_turbo / fuse / anima29_rdbt 的 cfg 范围统一为 1.0-1.6；payload 不写 `neg` 时默认 cfg 1.0（负面惰性），写 `neg` 时默认 cfg 1.2 使负面生效（预设级 `cfg_neg`；fuse 因内置负面常驻，默认即 1.2）。v2.9 LoRA 对照探针：cfg1.2+文字类负面 2 胜 5 平 0 负、零副作用。报告：`examples/results/turbo29_neg_20260827_143016/report.md`。
- **Turbo-ANIMA-v2.9 LoRA 离线重映射产物**: `examples/remap_turbo_lora_29b.py` 按 2.9B 深度扩展布局（28→40 块，插入索引 2,5,8,11,14,17,21,24,27,30,33,36）把 28 块 Turbo LoRA 离线重写为 40 块布局 `anima29b-turbo-v2.9-remap.safetensors`，免 ComfyUI-Anima-2.9B-loraPatch 运行时补丁；全场景 A/B（`examples/lora_remap_ab_test.py`，6 场景含 3 NSFW）同 seed 逐像素一致，耗时同档。报告：`examples/results/lora_remap_ab_20260828_105803/report.md`。测试注册表条目 `anima29_turboani29_remap`（payload `lora_name` 覆盖即用）。
- **fuse / 重映射 LoRA 发布工程（非官方拼接/重映射衍生）**: Hugging Face 仓库已发布 <https://huggingface.co/Langzaigg/anima29b-turbo-unofficial>（本地工程 `D:\ComfyUI\dev\huggingface\anima29b-turbo-unofficial\`，融合 UNET + 重映射 LoRA 双产物）；Civitai 拆分为两个独立工程 `D:\ComfyUI\dev\civitai\anima29b-p1-turbo1.1-unofficial-merge\`（完整模型，fuse 工作流同款）与 `D:\ComfyUI\dev\civitai\anima29b-turbo-v2.9-remap-unofficial\`（LoRA，配合原版 2.9B），各含示例图（PNG 内嵌工作流）与说明文档；许可遵循上游 CircleStone Labs Non-Commercial License。

### Changed

- **cfg=1 负面提示词规范收敛**: 依据 negprobe 两轮对比实测，所有 cfg=1 turbo 工作流（turbo_v1 / anima29_turbo / miao_turbo / kira_turbo / turbo）的 knowledge 与 schema 统一改为"不要写负面，不想要的元素用正向写法规避（不提及、用正向描述替代），仅 nsfw/explicit 分级时在 `tags` 末尾保留无码提示词 `no mosaic, uncensored`"；`neg_scale` / `nag_scale` / `anima_nag_scale` 三个引导参数降级标注为实验性（压制力有限，仅留作后续模型复测）。
- **MIGRATION.md 新增 2026-08-18 版本说明**: 汇总 Anima 2.9B 双工作流、弃用标记、int8 移除与 cfg=1 负面规范；补充 `/workflows` 发现 API 的返回结构说明与"下游服务免适配接入约定"（动态拉取 workflows/schema/knowledge，不硬编码工作流清单与提示词规则）。
- **Anima 2.9B 提示词规则修正**: `anima29` / `anima29_turbo` 的质量前缀改为避免一切质量/分数标签（masterpiece、best quality、score_N 等都不用），只保留年份 + 安全标签（如 `year 2026, safe`）；角色/作品/画师标签避免下划线（写 `hatsune miku` 而非 `hatsune_miku`，其余标签带下划线影响不大）。已同步 `knowledge/anima29_expert.md`、`schemas/tool_schema_simple.json` 字段描述与测试注册表 `examples/model_test/models.py` 的 anima29 质量前缀。
- **knowledge/schema 按"唯一工作流"视角拆分**: 共享文件中不再为某个工作流写条件特例，规则有出入即拆成独立文件。schema 拆分：`tool_schema_simple.json`（aesthetic_v1 / kira / nova / miao，cfg>1，移除实验性引导参数）、`tool_schema_simple_turbo.json`（turbo_v1 / miao_turbo，cfg=1 不写负面 + 实验性参数）、`tool_schema_anima29.json` / `tool_schema_anima29_turbo.json`（无质量词前缀、无下划线规则；turbo 版不写负面 + 实验性参数）。knowledge 拆分：新增 `turbo_v1_expert.md` / `turbo_v1_examples.md` / `kira_turbo_expert.md` / `anima29_turbo_expert.md`，`simple_expert.md` / `kira_expert.md` / `anima29_expert.md` 收回为各自单一工作流视图。两处 WORKFLOWS 注册表（`__init__.py` / `servers/http_server.py`）已同步，下次重启 ComfyUI 生效。
- **anima29_turbo 默认 Turbo LoRA 更换**: `Anima-2.9B_Turbo-BF16.safetensors` → `Turbo-ANIMA-v2.9.safetensors`（strength 0.8 不变）。横评结论：v2.9 与 v3 的强度甜点均为 0.8，v2.9@0.8 综合最优（v3@1.0 仅 SFW 可试）。报告：`examples/results/turbo_fusion_full_20260827_122034/report.md`、`turbo_fusion_v2_20260827_134448/report.md`。
- **移除 cfg=1 实验性负面引导参数**: `neg_scale` / `nag_scale` / `anima_nag_scale` 及其附属调参（nag_alpha/nag_tau 等）从 executor 与全部 tool schema 删除——turbo 系已有 cfg 1.2 原生负面分支，三个实验参数完成复测使命退役。payload 再传这些字段会被忽略。
- **NSFW 提示词规则简化**: 现役 turbo 系工作流（turbo_v1 / anima29_turbo / fuse / anima29_rdbt）不再要求在 `tags` 末尾写 `no mosaic, uncensored`；需要排除的元素写 `neg`（默认 cfg 1.2 生效），不需要则留空（默认 cfg 1.0）。
- **工作流 description 统一口径**: 两处 WORKFLOWS 注册表与全部 tool schema 的顶层 description 统一为 turbo 系 / 非 turbo 系 / 写实系三种口径的工具介绍，不再逐工作流解释差异（选型信息仍在 README/wiki）；miao_turbo 随之拆出独立 `tool_schema_miao_turbo.json`（原与 turbo_v1 共享 `tool_schema_simple_turbo.json`，后者规则已按 turbo_v1 的 cfg 1.2 分支更新）。

### Removed

- **6 个废弃工作流彻底移除**: `turbo`(0.2) / `kira` / `kira_turbo` / `nova` / `miao` / `miao_turbo`（2026-08-18 起标记 deprecated）从 WORKFLOWS 注册表（`__init__.py` / `servers/http_server.py`）、generate 分发与 `_V2_MODEL_PRESETS` 删除，调用返回 400 未知 workflow。配套清理：Turbo 0.2 专属兼容端点（`POST /anima/generate_turbo`、`GET /anima/schema_turbo`、`GET /anima/knowledge_turbo`）移除（turbo_v1 / aesthetic_v1 兼容端点保留）；executor 删除 `generate_turbo` / `generate_kira` / `_inject_kira` / `_inject_turbo`（引用从未加载模板的死代码）/ `_history_failed` 与 `KIRA_*` / `NOVA_*` / `MIAO_*` 常量，`_inject_unified` 收回为纯 base 注入；资源文件删除 `tool_schema_turbo.json` / `tool_schema_kira_turbo.json` / `tool_schema_miao_turbo.json`、turbo/kira/nova/miao 各 expert/examples 知识文件与孤儿模板 `workflow_template_turbo.json`（`tool_schema_simple.json` 等共用资源保留）；wiki（API-Reference / Model-Comparison / Installation）与 MIGRATION.md 同步。迁移建议见 MIGRATION.md 2026-08-28 节。

## [1.0.0] - 2026-02-03

### Added

- Initial release
- **MCP Server**: Native image display in Cursor/Claude chat window
- **ComfyUI HTTP API**: Routes `/anima/health`, `/anima/schema`, `/anima/knowledge`, `/anima/generate`
- **Standalone HTTP Server**: FastAPI-based server for external integrations
- **CLI Tool**: Command-line interface for batch generation
- **Structured Prompt System**: Quality/Artist/Character/Tags/Environment fields
- **Aspect Ratio Support**: 14 presets from 21:9 to 9:21, auto-calculates ~1MP resolution
- **Expert Knowledge Base**: Anima prompting guidelines, artist list, examples

### Technical Details

- Uses `circlestone-labs/Anima` model (2B params, anime/illustration focused)
- Requires Qwen3 tokenizer (`qwen_3_06b_base.safetensors`) and VAE (`qwen_image_vae.safetensors`)
- Artist tags must use `@` prefix (e.g., `@fkey, @jima`)
- Safety labels required: `safe`, `sensitive`, `nsfw`, `explicit`
