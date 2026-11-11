"""Seedance（火山方舟或结构相同的第三方）首帧/首尾帧生视频：提交、轮询、下载。

配置（.env.local，从当前目录往上找，或 --env 指定）：
  SEEDANCE_API_KEY  SEEDANCE_BASE_URL（如 https://ark.cn-beijing.volces.com）  SEEDANCE_MODEL（如 doubao-seedance-2-5-260628）
  SEEDANCE_PRICE_PER_SEC（选填，用于报价）
接口细节见 references/seedance-api.md。

用法：
  seedance.py run  --name shot04_v1 --prompt P.txt --first F.png [--last L.png] --duration 4 --out clips/ [--dry-run]
  seedance.py poll --name shot04_v1 --out clips/          只轮询已提交的任务并下载
可选：--resolution 720p  --audio 1|0  --env PATH  --model 模型名（覆盖 SEEDANCE_MODEL，比如临时换 2.0 mini；对应 key 不同就用 --env 指向另一份配置）
产物：clips/shot04_v1.mp4、clips/tasks/shot04_v1.json（任务信息）、shot04_v1.result.json（接口返回）。
同名任务已存在时拒绝重复提交；已存在的 mp4 不覆盖。key 只在内存里。
"""
import argparse, base64, json, sys, time, urllib.error, urllib.request
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from _env import find_env, load_env, mask, UA

def call(method, url, key, body=None, timeout=120):
    h = {"Authorization": f"Bearer {key}", "Content-Type": "application/json", "User-Agent": UA, "Accept": "application/json"}
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=data, method=method, headers=h), timeout=timeout) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, {"_raw": mask(e.read().decode("utf-8", "replace"), key)[:2000]}

def b64img(p):
    ext = Path(p).suffix.lower().lstrip(".").replace("jpg", "jpeg")
    return f"data:image/{ext};base64," + base64.b64encode(Path(p).read_bytes()).decode()

def build_body(a, model):
    content = [{"type": "text", "text": Path(a.prompt).read_text(encoding="utf-8")},
               {"type": "image_url", "role": "first_frame", "image_url": {"url": b64img(a.first)}}]
    if a.last:
        content.append({"type": "image_url", "role": "last_frame", "image_url": {"url": b64img(a.last)}})
    # 首帧/首尾帧模式下 ratio 只能是 adaptive，输出比例跟随首帧
    return {"model": model, "content": content, "ratio": "adaptive", "resolution": a.resolution,
            "duration": a.duration, "generate_audio": bool(a.audio), "watermark": False}

def summary(body, e):
    s = dict(body); s["content"] = []
    for c in body["content"]:
        if c["type"] == "text":
            s["content"].append({"type": "text", "chars": len(c["text"])})
        else:
            s["content"].append({"type": c["type"], "role": c.get("role"), "base64_kb": len(c["image_url"]["url"]) // 1024})
    price = e.get("SEEDANCE_PRICE_PER_SEC")
    try:
        price = float(price) if price else None
    except ValueError:
        price = None
    if body["duration"] == -1:
        s["_quote"] = "duration=-1 由模型自选时长，无法预估金额"
    elif price is None:
        s["_quote"] = "未设置（或无法识别）SEEDANCE_PRICE_PER_SEC，报价前请问用户单价"
    else:
        s["_quote"] = f"{body['duration']} 秒 × {price} = {body['duration'] * price:.2f} 元（单价按 720p，以账单为准）"
        if body["resolution"] != "720p":
            s["_quote"] += f"；注意现在是 {body['resolution']}，实际单价不同，请向用户确认"
    s["_request_kb"] = len(json.dumps(body)) // 1024
    return s

def endpoint(e):
    return e["SEEDANCE_BASE_URL"].rstrip("/") + "/api/v3/contents/generations/tasks"

def submit(a, e, out):
    task_file = out / "tasks" / f"{a.name}.json"
    if task_file.exists():
        sys.exit(f"{task_file} 已存在，拒绝重复提交（换版本号或用 poll）")
    for f in [a.prompt, a.first] + ([a.last] if a.last else []):
        if not Path(f).is_file():
            sys.exit(f"找不到 {f}")
    body = build_body(a, e["SEEDANCE_MODEL"])
    print(json.dumps(summary(body, e), ensure_ascii=False, indent=1))
    if a.dry_run:
        print("dry-run：没有提交"); sys.exit(0)
    st, resp = call("POST", endpoint(e), e["SEEDANCE_API_KEY"], body)
    print("submit HTTP", st, json.dumps(resp, ensure_ascii=False)[:600])
    if st != 200 or "id" not in resp:
        sys.exit(1)
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text(json.dumps({"name": a.name, "task_id": resp["id"], "prompt": a.prompt, "first": a.first, "last": a.last,
                                     "duration": a.duration, "resolution": a.resolution, "audio": bool(a.audio),
                                     "model": e["SEEDANCE_MODEL"], "submitted_at": time.time()}, ensure_ascii=False, indent=2))

def save_result(out, name, resp):
    p = out / "tasks" / f"{name}.result.json"
    if p.exists():
        p = out / "tasks" / f"{name}.result.{int(time.time())}.json"
    p.write_text(json.dumps(resp, ensure_ascii=False, indent=2))

def poll(name, e, out, max_wait=1800):
    tf = out / "tasks" / f"{name}.json"
    if not tf.is_file():
        sys.exit(f"找不到 {tf}：这个名字还没提交过（检查 --name 和 --out）")
    meta = json.loads(tf.read_text())
    url = endpoint(e) + "/" + meta["task_id"]; t0 = time.time(); last = None
    while True:
        try:
            st, resp = call("GET", url, e["SEEDANCE_API_KEY"])
        except (OSError, ValueError) as err:  # 含 URLError、socket.timeout（3.9）、返回非 JSON
            print(f"查询网络错误，15 秒后重试：{err}", flush=True); time.sleep(15); continue
        status = resp.get("status")
        if status != last:
            print(f"[{int(time.time() - t0)}s] HTTP {st} status={status}", flush=True); last = status
        if status == "succeeded":
            break
        if status in ("failed", "cancelled", "expired") or (st >= 400 and st != 429):
            save_result(out, name, resp)
            sys.exit(f"任务失败：{json.dumps(resp, ensure_ascii=False)[:1500]}")
        if time.time() - t0 > max_wait:
            sys.exit("等待超时；稍后用 poll 继续")
        time.sleep(15)
    save_result(out, name, resp)
    dst = out / f"{name}.mp4"
    if dst.exists():
        sys.exit(f"{dst} 已存在，不覆盖")
    # 视频地址只保留 24 小时，拿到立刻下载
    with urllib.request.urlopen(urllib.request.Request(resp["content"]["video_url"], headers={"User-Agent": UA}), timeout=300) as r:
        dst.write_bytes(r.read())
    print("saved", dst, dst.stat().st_size, "bytes; usage:", json.dumps(resp.get("usage", {})), f"; {int(time.time() - t0)}s")

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["run", "poll"]); ap.add_argument("--name", required=True)
    ap.add_argument("--prompt"); ap.add_argument("--first"); ap.add_argument("--last")
    ap.add_argument("--duration", type=int); ap.add_argument("--resolution", default="720p"); ap.add_argument("--audio", type=int, default=1)
    ap.add_argument("--out", default="clips"); ap.add_argument("--env"); ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--model", help="覆盖 .env.local 的 SEEDANCE_MODEL")
    a = ap.parse_args()
    e = load_env(find_env(a.env))
    if a.model:
        e["SEEDANCE_MODEL"] = a.model
    for k in ("SEEDANCE_API_KEY", "SEEDANCE_BASE_URL", "SEEDANCE_MODEL"):
        if not e.get(k):
            sys.exit(f".env.local 缺 {k}")
    out = Path(a.out)
    if a.cmd == "run":
        if not (a.prompt and a.first and a.duration):
            sys.exit("run 需要 --prompt --first --duration")
        if not (a.duration == -1 or 4 <= a.duration <= 30):
            sys.exit("duration 只能是 4–30 或 -1（这是 2.5 的范围；其他模型以官方文档为准）")
        submit(a, e, out)
    poll(a.name, e, out)

if __name__ == "__main__":
    main()
