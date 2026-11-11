# AI 视频总导演（ai-video-director）

[English](README.md) | **简体中文**

一个 [Claude Code](https://claude.com/claude-code) skill：让 Claude Code 当总导演，带你从一个想法做到 AI 短片成片。

- **Claude Code**：写故事和分镜、写所有提示词、检查每张图和每段视频、用 ffmpeg/Python 做后期
- **ChatGPT 图像 API（gpt-image-2，OpenAI 兼容）**：画设定图和每个镜头的首尾帧（也支持 Codex 生图）
- **Seedance（火山方舟官方或结构相同的第三方中转）**：把首尾帧变成视频片段

核心思路：**把错误挡在花钱之前**。文字里能发现的错，不留到图上；图上能发现的错，不留到视频上。每一步都有门槛和独立的审核 agent，提交视频前先报价，你同意了才花钱。

## 流程

| 步 | 做什么 | 门槛 |
|---|---|---|
| 1 | 想法 → 完整剧情 → 逐镜头故事 | 审核 agent 通过 + 你确认 |
| 2 | 分镜：镜头语言、构图、配色 | 你确认 |
| 3 | 定画风，画设定图 | 你确认画风 |
| 4 | 画每个镜头的首尾帧 | 先写后画 + 首尾帧检查 |
| 5 | 写视频提示词 | 审核 agent 通过 + 你同意报价 |
| 6 | 提交 Seedance 生成 | 抽帧检查 |
| 7 | 后期：拼接、转场、调色、放大 | 抽查切点 |
| 8 | 全片复核、交付、沉淀经验 | 你亲自看、亲自听后确认 |

详细规则见 [SKILL.md](SKILL.md) 和 [references/](references/)。

## 安装

把整个目录放进 Claude Code 的 skills 目录之一：

```bash
# 所有项目可用
git clone <本仓库地址> ~/.claude/skills/ai-video-director
```

```bash
# 只在某个项目里用
git clone <本仓库地址> <你的项目>/.claude/skills/ai-video-director
```

装好后在 Claude Code 里说"我有个想法想拍成片子"，或输入 `/ai-video-director`。

## 环境要求

- Python 3.9+（只有 `imagegen.py --codex-config` 需要 3.11+）
- [ffmpeg](https://ffmpeg.org/)（含 ffprobe），`clipcheck.py` 和 `cut.py` 要用
- Python 包：Pillow、numpy

在你的视频项目目录里建虚拟环境：

```bash
python3 -m venv .venv && .venv/bin/pip install -r ~/.claude/skills/ai-video-director/requirements.txt
```

## 配置 API

把 [assets/env.local.example](assets/env.local.example) 复制到你的视频项目根目录，改名为 `.env.local` 后填写：

| 变量 | 含义 |
|---|---|
| `SEEDANCE_API_KEY` | Seedance key，官方或第三方（必填） |
| `SEEDANCE_BASE_URL` | 接口地址，官方是 `https://ark.cn-beijing.volces.com`（必填） |
| `SEEDANCE_MODEL` | 模型名，如 `doubao-seedance-2-5-260628`（必填） |
| `SEEDANCE_PRICE_PER_SEC` | 720p 每秒单价，用于提交前报价（选填） |
| `IMAGE_API_KEY` | 图像 API key（必填，或用 `--codex-config`） |
| `IMAGE_BASE_URL` | 默认 `https://api.openai.com/v1` |
| `IMAGE_MODEL` | 默认 `gpt-image-2` |

**`.env.local` 不要提交到 git。** 脚本运行时自己读取 key，只放在内存里，不打印、不写日志。

> 文档里的模型名和价格是 2026-11 的数据，可能已过时，请以服务商的官方文档和账单为准。

### 🔑 还没有 API key？

推荐 [TokensGrid](https://www.tokensgrid.com)：一站式打通所有模型 API，一个账号搞定生图、视频等各家模型。拿到地址和 key 后，填进上表对应的 `*_BASE_URL` 和 `*_API_KEY` 即可。

## 脚本

| 脚本 | 做什么 |
|---|---|
| `scripts/imagegen.py` | 调图像 API 生图或带参考图改图；`models` 列出可用图像模型 |
| `scripts/contrast_check.py` | 检查配色转黑白后主体和背景能不能分开 |
| `scripts/frames_util.py` | 裁成精确画幅、推拉镜头首尾帧缩放、差分和叠图 |
| `scripts/seedance.py` | 提交首帧/首尾帧任务、轮询、下载；`--dry-run` 只看请求概要和报价 |
| `scripts/clipcheck.py` | 抽帧总表、首尾帧对比、亮度变化、突跳帧定位、音频响度 |
| `scripts/cut.py` | 按 JSON 剪辑表出片：剪切、推近、定格、调色、放大到 1080p、配乐、响度标准化 |

每个脚本加 `-h` 都能看用法。所有脚本都不会覆盖已有文件。

### 关于 User-Agent

`scripts/_env.py` 把请求的 User-Agent 设成 OpenAI Python SDK 的样式。原因是有些第三方服务商前面有 Cloudflare，会拦截 Python urllib 的默认 UA（错误码 1010）。这样做只是为了兼容，不影响请求内容。

## 注意

- 生成视频按秒计费。这个 skill 每次提交前都会报价，并等你同意。它不会替你充值或购买额度。
- Claude 只能看静帧，看不到真实的动态，也听不到声音。动作手感和声音请你亲自看、亲自听。

## 致谢与许可

工作流参考自 [Eian（@EianLu）](https://x.com/EianLu) 的文章[《Claude code/Codex+Seedance AI视频：从一个想法到成片的全流程》](https://x.com/EianLu/status/2118317430665613741)（2026-11）。

本仓库的代码（`scripts/`）以 [MIT License](LICENSE) 发布。`references/` 里标注为"原文提示词"的内容版权归原作者所有，不在 MIT 许可范围内。
