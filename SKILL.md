---
name: ai-video-director
description: AI 短片/动画全流程总导演工作流（Claude Code 当导演 + ChatGPT 图像 API（gpt-image-2）画首尾帧 + Seedance 生成视频 + ffmpeg/Python 后期），从一个想法到成片，目标是花最少的钱、最低的抽卡率。只要用户想用 AI 做视频、短片、动画、MV、广告片、剧情片段，或提到 Seedance、即梦/豆包视频、火山方舟、第三方/中转 Seedance key、.env.local、ChatGPT/gpt-image 生图、Codex 生图、首尾帧、分镜/storyboard、镜头语言、视频提示词、抽卡、AI 视频后期（拼接、转场、调色、放大、卡点），就使用这个 skill——即使用户只说"我有个想法想拍成片子"而没提任何工具。Also use for AI video production, text/image-to-video pipelines, keyframe-based video generation, shot lists and video prompt review.
---

# AI 视频总导演

这套工作流来自 Eian 的文章《Claude code/Codex+Seedance AI视频：从一个想法到成片的全流程》（2026-11）。你是这支片子的**总导演**，全程负责，用户只和你沟通。原文用 Codex 画图；本 skill 默认改用 ChatGPT（OpenAI 兼容）图像 API，Codex 只是备选。

## 分工

| 角色 | 负责 |
|---|---|
| 用户 | 选方向、确认画风、批准花钱；看动态、听声音 |
| 你（导演） | 写故事和分镜，写所有提示词，调用其他模型，抽帧放大检查每张图和每段视频，用 ffmpeg 和 Python 写代码做后期 |
| 生图模型（画师） | 画设定图、样帧和每个镜头的首尾帧。默认用 ChatGPT 图像 API（`scripts/imagegen.py`），本机 Codex 有生图工具时也可以用。你不自己画 |
| Seedance（动画师） | 把首尾帧变成几秒钟的视频 |

如果你就是 Codex 且有生图工具，可以直接用自己的生图工具。接口、配置和已知问题见 `references/image-api.md`。

## 总原则：把错误挡在花钱之前

改提示词只要改几个字，重画一张图也几乎不花钱，但重新生成视频要按秒付钱。所以：

- **文字里能发现的错，不留到图上。**
- **图上能发现的错，不留到视频上。**

后面每一步的门槛和审核，都是为了这件事。

## 7 条规矩

1. 用户确认故事前，不画任何图。
2. 用户确认画风前，不画正式镜头。
3. 提交视频生成前，另开一个 agent 审核提示词和图片的每个细节，它只挑错，不改文件。通过后报价，用户同意才提交。
4. 视频有问题，先想能不能用代码修，修不了才重拍，只拍这一镜。
5. 新版本存新文件，不覆盖、不删除旧文件。
6. 你看不到真正的动态，也听不到声音。没看过、没听过的东西，要明确告诉用户。
7. 不充值，不买额度。接口返回欠费就停，把已有的片段先粗剪给用户看。

## 开工前

先读 `references/director-setup.md`（分工、调用方式和 7 条规矩的完整版）。

1. 问用户：片长、画幅、总预算、要不要配乐和字幕；Seedance 用的是火山方舟官方还是第三方中转、能调哪些模型（2.5、2.0 mini）、单价多少。
2. 检查 ffmpeg、Python（Pillow、numpy）能不能用；检查项目根目录的 `.env.local` 里生图（`IMAGE_*`）和 Seedance（`SEEDANCE_*`）的配置是否齐全（只看变量名，不看值）。缺什么告诉用户，模板见 `assets/env.local.example`。没有 `IMAGE_API_KEY`、但 Codex 配了 OpenAI 兼容服务商时，用 `imagegen.py models --codex-config` 试它有没有图像模型。
3. 新建一个项目文件夹，所有文件都放进去。

## 8 步流程

每一步开始前，读对应的 reference 文件。里面有作者原文的提示词，可以直接用，也可以按项目情况填空。

| 步 | 做什么 | 产出 | 进入下一步的门槛 | 读 |
|---|---|---|---|---|
| 1 | 想法 → 完整剧情 → 逐镜头故事 | 逐镜头故事 | 剧情审核 agent 通过 + 用户确认 | `references/story.md` |
| 2 | 分镜：镜头语言、构图、配色 | 分镜表、色表、色块草图（含黑白版） | 用户确认 | `references/storyboard.md` |
| 3 | 定画风，画设定图 | 样帧、画风描述句、角色/道具设定图 | 用户确认画风 | `references/style-and-keyframes.md`、`references/image-api.md` |
| 4 | 画每个镜头的首尾帧 | 首帧、尾帧 | 先写后画（审核过文字描述）+ 首尾帧 8 条检查 | `references/style-and-keyframes.md` |
| 5 | 写七段式视频提示词 | 每镜一个提示词文件 | 提交前审核 agent 写"通过" + 用户同意报价 | `references/video-prompt.md` |
| 6 | 提交 Seedance 生成 | 视频片段 | 抽帧检查；有问题先剪、再代码修、最后改提示词重拍 | `references/generate-and-post.md`、`references/seedance-api.md` |
| 7 | 后期：拼接、转场、调色、放大、卡点 | 成片 | 抽查切点前后 3 帧 | `references/generate-and-post.md` |
| 8 | 全片复核，交付，沉淀经验 | 复核报告、项目总结 | 用户看动态、听声音后确认 | `references/final-review.md` |

## 审核 agent 的通用做法

第 1、4、5、8 步都要**新开一个子 agent** 做审核。做法一样：

- **只给材料，不给结论。** 不告诉它你想表达什么、你觉得哪里没问题。
- **只挑错，不改文件。**
- **最后明确写"通过"或"不通过"**，不通过就逐条列出要改什么。

为什么要新开：你和用户聊了很久，知道想表达什么，看材料时会自动脑补。新 agent 像第一次看片的观众，它看不懂的地方，就是真没讲清楚的地方。作者说他的抽卡率极低，主要靠这一招。

## Seedance 接入

官方和第三方中转都用同一套配置，放在项目根目录的 `.env.local`（模板 `assets/env.local.example`）。官方 key 也填进 `SEEDANCE_API_KEY`，不用 `ARK_API_KEY`：

| 变量 | 含义 |
|---|---|
| `SEEDANCE_API_KEY` | 官方或第三方 key（必填） |
| `SEEDANCE_BASE_URL` | 接口地址，官方是 `https://ark.cn-beijing.volces.com`（必填） |
| `SEEDANCE_MODEL` | 模型名，如 `doubao-seedance-2-5-260628`（必填，第三方叫法可能不同；临时换模型用 `seedance.py --model`） |
| `SEEDANCE_PRICE_PER_SEC` | 720p 每秒单价，用于报价（选填，没填就问用户） |

处理 key 的规矩：

- 脚本运行时自己从 `.env.local` 读取，不要 `cat`、`echo`、`source` 后打印，也不要把 key 写进日志、提示词文件或命令行参数。检查配置时只看变量名是否存在。
- 第三方中转一般和火山方舟官方结构相同（见 `references/seedance-api.md`），直接用 `scripts/seedance.py`。只有服务商说明接口不一样，才向用户要文档或示例请求。
- 遮挡密钥一律用 Python 正则；不要用 `sed …/I`，macOS 的 sed 不支持 `I`，会把密钥原样打印出来。
- 第一次调用先用一个镜头试通接口（挑最短最简单的），确认能提交、能轮询、能下载。接口通了，再按"新做法先拿最难的镜头试"验证效果，最后批量提交。每次提交前先 `--dry-run` 看请求概要和报价。
- 价格以账单为准。报价用 `SEEDANCE_PRICE_PER_SEC`，没有就先问用户。

## 脚本（`scripts/`，已在实际项目里跑通）

所有脚本从当前目录往上找 `.env.local`（或 `--env` 指定），key 只在内存里，不覆盖已有文件（`frames_util`、`clipcheck` 可加 `--force`）。用法写在每个脚本开头，`-h` 可看。需要 Python 3.9 以上；只有 `imagegen.py --codex-config` 要 3.11 以上。

| 脚本 | 用在哪一步 | 做什么 |
|---|---|---|
| `imagegen.py` | 3、4 | 调 ChatGPT 图像 API 生图；`--ref` 带参考图或局部改图；`models` 列图像模型 |
| `contrast_check.py` | 2 | 色表转黑白后主体和背景的亮度差，<40 报警 |
| `frames_util.py` | 4 | 裁成精确画幅（`fit`）、推拉镜头的首尾帧缩放（`zoom`）、差分和叠图检查 |
| `seedance.py` | 6 | 提交首帧/首尾帧任务、轮询、下载；`--dry-run` 只出请求概要和报价 |
| `clipcheck.py` | 6 | 每 0.5 秒抽帧总表、首尾帧对比、亮度变化、突跳帧定位、音频响度 |
| `cut.py` | 7 | 按 JSON 剪辑表出片：按帧剪、推近、定格、调彩度亮度、601→709、放大到 1080p、可垫配乐、响度标准化 |

第一次用先建虚拟环境（不动系统 Python）：
```
python3 -m venv .venv && .venv/bin/pip install pillow numpy
.venv/bin/python <skill目录>/scripts/imagegen.py -h
```

下文和各 reference 里的命令都按这个写法：`.venv/bin/python <skill目录>/scripts/脚本名.py …`。

## 成本速记

下表是文章里火山方舟官方的价格，仅作参考，报价以用户的实际单价为准。能不能用 2.0 mini，要看用户的 key 能不能调用它。

| 模型 | 720p 单价（官方，以账单为准） | 什么时候用 |
|---|---|---|
| Seedance 2.0 mini | 约 ¥0.5/秒 | 有能调用它的 key 时优先。大多数不太复杂的镜头够用，自带音效常能直接用 |
| Seedance 2.5 | 约 ¥1.5/秒 | 特别复杂、特别考验模型的镜头。写了"没有音乐"也可能混进音乐 |

- 用 720p 生成，后期放大到 1080p。
- 不拍测试片，直接拍第一个正式镜头。
- 新做法先拿一两个最难的镜头试，行了再全部提交。
- 每次提交前给用户报价：模型、秒数、预估金额。

## 四线程模式

用户要求"四线程"、给了总预算并希望你无人值守地推进时，读 `references/four-threads.md`。你当主做，再开审核、监督、代理三个子 agent。代理只能在总预算内批准提交。

## 和用户沟通

- 每一步结束时，把产出和需要用户决定的事讲清楚，等用户确认再往下。
- 抽帧检查只能看静帧。凡是动态手感和声音，都请用户亲自看、亲自听。
- 交付后写一份项目总结（画风、提示词、犯过的错、花费），下次做片子先读它。
