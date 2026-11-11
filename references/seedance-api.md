# Seedance 2.5 接口要点（首帧 / 首尾帧生视频）

整理自火山方舟《Doubao Seedance 2.5 教程》（2026-11）。第三方中转的结构和官方一样，只是 `BASE` 和 key 不同。
官方文档是前端渲染，网页抓取工具只能拿到空壳；要查最新版，用浏览器打开后取页面文本。
脚本：`scripts/seedance.py`（提交、轮询、下载，带 `--dry-run` 报价）。

## 接口
- 创建任务：`POST {BASE}/api/v3/contents/generations/tasks`
- 查询任务：`GET {BASE}/api/v3/contents/generations/tasks/{id}`
- 请求头：`Authorization: Bearer <key>`、`Content-Type: application/json`
- 官方 `BASE` = `https://ark.cn-beijing.volces.com`；第三方填自己的地址（`.env.local` 的 `SEEDANCE_BASE_URL`）。

## 首尾帧请求体
```json
{
  "model": "doubao-seedance-2-5-260628",
  "content": [
    {"type": "text", "text": "七段式提示词……"},
    {"type": "image_url", "role": "first_frame", "image_url": {"url": "data:image/png;base64,...."}},
    {"type": "image_url", "role": "last_frame",  "image_url": {"url": "data:image/png;base64,...."}}
  ],
  "ratio": "adaptive",
  "resolution": "720p",
  "duration": 5,
  "generate_audio": true,
  "watermark": false
}
```
- 只给首帧就去掉 `last_frame` 那一项。
- **首帧 / 首尾帧模式下 `ratio` 只能是 `adaptive`**，输出比例跟随首帧图片；填 `16:9` 会异步报错 `InvalidParameter.TaskTypeConstraint`。所以首帧本身就要裁成目标比例。
- `resolution`：`480p` / `720p`（默认）/ `1080p`（10bit、H.265，部分播放器不兼容）。720p 16:9 输出 1280×720。
- `duration`：4–30 的整数秒，或 `-1`（模型自选）。
- `generate_audio`：是否生成声音（台词、音效）。写了"没有音乐"也可能混进音乐，用户要亲自听。
- `watermark`：默认 `false`。`output_format` 可选 `mp4`（默认）或 `mov`。
- 图片可用 URL、base64 data URL 或素材 ID。单张 < 30 MB，宽高 300–6000 px，宽高比 0.4–2.5，整个请求体 ≤ 64 MB。
- 不支持直接上传含真人人脸的参考图（3D 卡通角色没问题）。

## 查询结果
- `status`：`queued` → `running` → `succeeded` / `failed`（另有 `cancelled`、`expired`）。
- 成功后视频地址在 `content.video_url`，**只保留 24 小时**，最多下载 100 次，拿到立刻下载。
- `usage.completion_tokens` 可用于核对计费。任务 ID 7 天有效。
- 实测：720p、4–6 秒的片段，每条大约 3–5 分钟出结果。

## 限流
- 个人账号：同时处理最多 3 个任务（多的排队），每分钟最多创建 180 个；查询接口每秒 20 次。超限返回 429。
- 一次并行提交 2–3 条最合适。

## 提示词里的声音写法（2.5）
音乐用 `()`，音效用 `<>`，台词用 `{}`，字幕用 `【】`。例：`妈妈清楚地说一句台词：{异议！}`。非中文台词在前面写明语言。
七段式提示词的【画风】【镜头】等段落标题实测没有被当成字幕（5/5 条）；如果出现字幕，把标题改成"画风："再重拍。

## 其他能力（本工作流一般用不到）
全模态参考（`role: reference_image/reference_video/reference_audio`）、视频编辑（`ratio` 必须 `adaptive`、`duration` 必须 `-1`）、视频延长、样片模式（`draft: true` 只能 480p，再用 draft 任务 ID 生成 1080p）。需要时再查官方文档。
