# AI Video Director (ai-video-director)

**English** | [简体中文](README.zh-CN.md)

A [Claude Code](https://claude.com/claude-code) skill that makes Claude Code the director of your AI short film, taking you from a single idea to a finished cut.

- **Claude Code** writes the story and storyboard, writes every prompt, inspects every image and clip, and does post-production with ffmpeg/Python
- **ChatGPT Image API (gpt-image-2, OpenAI-compatible)** draws reference sheets and the first/last keyframes of every shot (Codex image generation also supported)
- **Seedance** (official Volcengine Ark, or a third-party relay with the same API) turns keyframes into video clips

The core idea: **catch mistakes before they cost money.** A mistake you can spot in text never makes it into an image; a mistake you can spot in an image never makes it into a video. Every step has a gate and an independent review agent, and every video submission is quoted first and only goes out with your approval.

> Note: `SKILL.md` and `references/` are written in Chinese. Claude reads them fine and will talk to you in whatever language you use.

## Workflow

| Step | What happens | Gate |
|---|---|---|
| 1 | Idea → full plot → shot-by-shot story | Review agent passes + you approve |
| 2 | Storyboard: camera language, composition, color | You approve |
| 3 | Lock the art style, draw reference sheets | You approve the style |
| 4 | Draw first/last keyframes for every shot | Write before drawing + keyframe checklist |
| 5 | Write video prompts | Review agent passes + you accept the quote |
| 6 | Submit to Seedance | Frame-by-frame check |
| 7 | Post: assembly, transitions, grading, upscaling | Spot-check every cut |
| 8 | Full review, delivery, lessons learned | You watch and listen, then sign off |

See [SKILL.md](SKILL.md) and [references/](references/) for the full rules.

## Install

Put the whole directory in one of Claude Code's skills folders:

```bash
# Available in all projects
git clone <repo-url> ~/.claude/skills/ai-video-director
```

```bash
# Only in one project
git clone <repo-url> <your-project>/.claude/skills/ai-video-director
```

Then tell Claude Code something like "I have an idea I want to turn into a short film", or type `/ai-video-director`.

## Requirements

- Python 3.9+ (3.11+ only for `imagegen.py --codex-config`)
- [ffmpeg](https://ffmpeg.org/) (with ffprobe), used by `clipcheck.py` and `cut.py`
- Python packages: Pillow, numpy

Create a virtual environment in your video project:

```bash
python3 -m venv .venv && .venv/bin/pip install -r ~/.claude/skills/ai-video-director/requirements.txt
```

## API configuration

Copy [assets/env.local.example](assets/env.local.example) to your video project's root as `.env.local` and fill it in:

| Variable | Meaning |
|---|---|
| `SEEDANCE_API_KEY` | Seedance key, official or third-party (required) |
| `SEEDANCE_BASE_URL` | API base URL; official is `https://ark.cn-beijing.volces.com` (required) |
| `SEEDANCE_MODEL` | Model name, e.g. `doubao-seedance-2-5-260628` (required) |
| `SEEDANCE_PRICE_PER_SEC` | 720p price per second, used for quotes (optional) |
| `IMAGE_API_KEY` | Image API key (required, or use `--codex-config`) |
| `IMAGE_BASE_URL` | Defaults to `https://api.openai.com/v1` |
| `IMAGE_MODEL` | Defaults to `gpt-image-2` |

**Never commit `.env.local`.** The scripts read keys at runtime and keep them in memory only; they never print or log them.

> Model names and prices in the docs are as of 2026-11 and may be outdated. Always check your provider's documentation and billing.

### 🔑 Don't have API keys yet?

Try [TokensGrid](https://www.tokensgrid.com): one-stop access to all major model APIs, so a single account covers image, video and more. Once you have the base URL and key, put them in the matching `*_BASE_URL` and `*_API_KEY` variables above.

## Scripts

| Script | What it does |
|---|---|
| `scripts/imagegen.py` | Generate images, or edit with reference images; `models` lists available image models |
| `scripts/contrast_check.py` | Check whether subject and background stay distinguishable in grayscale |
| `scripts/frames_util.py` | Crop to exact aspect ratio, zoom keyframes for push-in/pull-out shots, diff and blend |
| `scripts/seedance.py` | Submit first-frame / first+last-frame jobs, poll, download; `--dry-run` shows the request summary and quote only |
| `scripts/clipcheck.py` | Contact sheet, first/last frame comparison, brightness drift, jump-frame detection, audio loudness |
| `scripts/cut.py` | Render from a JSON edit list: trim, push-in, freeze, grade, upscale to 1080p, music bed, loudness normalization |

Every script supports `-h`. None of them overwrite existing files.

### About the User-Agent

`scripts/_env.py` sets the User-Agent to the OpenAI Python SDK style. Some third-party providers sit behind Cloudflare, which blocks Python urllib's default UA (error 1010). This is purely for compatibility and does not change the request content.

## Heads-up

- Video generation is billed per second. The skill quotes every submission and waits for your approval. It never tops up or buys credits for you.
- Claude only sees still frames: it cannot see real motion or hear sound. Please watch and listen yourself.

## Credits & license

The workflow is based on the article [*Claude code/Codex+Seedance AI视频：从一个想法到成片的全流程*](https://x.com/EianLu/status/2118317430665613741) (2026-11) by [Eian (@EianLu)](https://x.com/EianLu).

The code in this repository (`scripts/`) is released under the [MIT License](LICENSE). Content in `references/` marked as "原文提示词" (original prompts) is quoted from the article above, remains the property of its author, and is not covered by the MIT License.
