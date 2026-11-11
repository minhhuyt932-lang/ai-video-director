# 生图接口：ChatGPT（OpenAI 兼容）图像 API

画设定图、样帧和首尾帧，默认直接调 OpenAI 兼容的图像接口（如 `gpt-image-2`），用 `scripts/imagegen.py`。不需要 Codex。
本机装了 Codex 且它的会话里**有**生图工具时，也可以用 Codex（见 `director-setup.md` 的备选）。注意：Codex 走第三方服务商时通常**没有**生图工具，会直接回复"画不了"。

## 配置（项目根目录 `.env.local`）

| 变量 | 含义 |
|---|---|
| `IMAGE_API_KEY` | 必填。OpenAI 官方 key，或第三方 OpenAI 兼容服务的 key |
| `IMAGE_BASE_URL` | 选填，默认 `https://api.openai.com/v1`。第三方填它的 `/v1` 地址 |
| `IMAGE_MODEL` | 选填，默认 `gpt-image-2` |

没有单独的图像 key、但 Codex 配了一个 OpenAI 兼容的第三方服务商时，可以加 `--codex-config`，直接用 `~/.codex/config.toml` 里当前服务商的地址和 key。先用 `imagegen.py models` 确认它有图像模型。

## 两种调用

| 场景 | 接口 | 命令 |
|---|---|---|
| 只有文字 | `POST /images/generations`（JSON） | `.venv/bin/python <skill目录>/scripts/imagegen.py gen --prompt-file p.txt --out a.png` |
| 带参考图（画风样帧、设定图、色块草图）或局部改图 | `POST /images/edits`（multipart，多张图用 `image[]`） | `.venv/bin/python <skill目录>/scripts/imagegen.py gen --prompt-file p.txt --out b.png --ref style.png --ref sheet.png --ref sketch.png` |

- 带参考图时在提示词里写清每张图管什么：哪张定画风、哪张定长相、哪张只定构图（"不要照抄色块、参考线和文字"）。
- 局部改图：一般只附要改的那一张原图（`--ref` 第一张就是被改的图），提示词开头写"保持其他一切不变，只改下面几处"。改完用差分图检查（`frames_util.py diff`）；只改一小块时，把改好的那块贴回原图。
- 返回是 base64，脚本直接存 png，不覆盖已有文件（新版本用新文件名）。

## 已知情况
- **尺寸不一定准**：请求 `2048x1152`，实际常给 `1672x941`。提交 Seedance 前用 `frames_util.py fit` 裁成精确比例，首尾帧尺寸一致。
- **质量会被降**：请求 `quality=high`，服务商可能返回 medium 或 low（看脚本打印的 `quality`）。细节不够就换服务商或重试。
- **Cloudflare 1010**：有的服务商前面有 Cloudflare，会拦 Python urllib 默认的 User-Agent，脚本用的是 OpenAI SDK 风格的 UA（`_env.py` 的 `UA`）。
- **返回图片地址而不是 base64 时**：脚本下载图片不带鉴权头，免得把 key 发给存图的主机。
- **画面里冒出小字**（如眼镜腿上的商标）：提示词写"no text, no logo"仍可能出现，放大检查，用代码涂掉。
- **手里多出东西**（如手指间夹一根细棍）：设定图和首尾帧都要放大看手，只重画那一格再贴回。
- key 只在脚本内存里用。检查配置只看变量名；遮挡密钥用 Python 正则，不要用 `sed …/I`（macOS 的 sed 不支持，会原样打印）。
