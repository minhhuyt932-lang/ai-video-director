"""调用 OpenAI 兼容的图像接口（ChatGPT 图像 API，如 gpt-image-2）生图或改图。

配置（.env.local，从当前目录往上找，或 --env 指定）：
  IMAGE_API_KEY   必填
  IMAGE_BASE_URL  选填，默认 https://api.openai.com/v1（第三方填自己的 /v1 地址）
  IMAGE_MODEL     选填，默认 gpt-image-2
备选：--codex-config 直接用 ~/.codex/config.toml 里当前 model_provider 的地址和 key。

用法：
  imagegen.py models                                   列出服务商的图像模型（只读）
  imagegen.py gen --prompt-file P.txt --out OUT.png    文生图
  imagegen.py gen --prompt-file P.txt --out OUT.png --ref A.png --ref B.png
                                                       附参考图走 edits 接口（局部改图时一般只附要改的那一张原图）
  可选：--size 2048x1152  --quality high  --model gpt-image-2
注意：key 只在内存里用；不覆盖已有文件；服务商可能自行把 quality 降成 medium/low，返回尺寸也可能和请求不同。
"""
import argparse, base64, json, mimetypes, os, sys, urllib.error, urllib.request, uuid
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from _env import find_env, load_env, mask, UA

def config(a):
    if a.codex_config:
        try:
            import tomllib  # Python 3.11+；只有用 --codex-config 时才需要
        except ImportError:
            raise SystemExit("--codex-config 需要 Python 3.11 以上；请改用 .env.local 的 IMAGE_*")
        cfg = tomllib.load(open(Path.home() / ".codex" / "config.toml", "rb"))
        name = cfg.get("model_provider", "openai")
        p = cfg.get("model_providers", {}).get(name, {})
        key = p.get("experimental_bearer_token") or (os.environ.get(p["env_key"], "") if p.get("env_key") else "")
        if not key:
            raise SystemExit(f"~/.codex/config.toml 的 {name} 没有 experimental_bearer_token，env_key 指向的环境变量也为空；请改用 .env.local")
        return p.get("base_url", "https://api.openai.com/v1").rstrip("/"), key, a.model or "gpt-image-2"
    e = load_env(find_env(a.env))
    if not e.get("IMAGE_API_KEY"):
        raise SystemExit(".env.local 缺 IMAGE_API_KEY（或加 --codex-config）")
    return (e.get("IMAGE_BASE_URL") or "https://api.openai.com/v1").rstrip("/"), e["IMAGE_API_KEY"], a.model or e.get("IMAGE_MODEL") or "gpt-image-2"

def req(method, url, key, data=None, headers=None, timeout=600):
    h = {"Authorization": f"Bearer {key}", "User-Agent": UA, "Accept": "application/json"}
    h.update(headers or {})
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=data, method=method, headers=h), timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()

def multipart(fields, files):
    b = uuid.uuid4().hex; out = bytearray()
    for k, v in fields.items():
        out += f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    for k, path in files:
        ct = mimetypes.guess_type(path)[0] or "application/octet-stream"
        out += f'--{b}\r\nContent-Disposition: form-data; name="{k}"; filename="{Path(path).name}"\r\nContent-Type: {ct}\r\n\r\n'.encode()
        out += Path(path).read_bytes() + b"\r\n"
    out += f"--{b}--\r\n".encode()
    return bytes(out), f"multipart/form-data; boundary={b}"

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["models", "gen"])
    ap.add_argument("--prompt-file"); ap.add_argument("--out"); ap.add_argument("--ref", action="append", default=[])
    ap.add_argument("--size", default="2048x1152"); ap.add_argument("--quality", default="high"); ap.add_argument("--model")
    ap.add_argument("--env"); ap.add_argument("--codex-config", action="store_true")
    a = ap.parse_args()
    base, key, model = config(a)
    print(f"base_url={base} model={model}")
    if a.cmd == "models":
        st, body = req("GET", f"{base}/models", key)
        if st != 200:
            sys.exit(f"HTTP {st} {mask(body.decode('utf-8', 'replace'), key)[:800]}")
        ids = sorted(m.get("id", "") for m in json.loads(body).get("data", []))
        print("图像模型:", [i for i in ids if any(s in i.lower() for s in ("image", "dall", "seedream", "flux", "imagen"))])
        return
    if not (a.prompt_file and a.out):
        sys.exit("gen 需要 --prompt-file 和 --out")
    out = Path(a.out)
    if out.exists():
        sys.exit(f"{out} 已存在，不覆盖；请换新版本号")
    prompt = Path(a.prompt_file).read_text(encoding="utf-8")
    if a.ref:
        data, ct = multipart({"model": model, "prompt": prompt, "size": a.size, "quality": a.quality, "n": "1"},
                             [("image[]", r) for r in a.ref])
        st, body = req("POST", f"{base}/images/edits", key, data, {"Content-Type": ct})
    else:
        payload = {"model": model, "prompt": prompt, "size": a.size, "quality": a.quality, "n": 1}
        st, body = req("POST", f"{base}/images/generations", key, json.dumps(payload).encode(), {"Content-Type": "application/json"})
    if st != 200:
        sys.exit(f"HTTP {st} {mask(body.decode('utf-8', 'replace'), key)[:1500]}")
    d = json.loads(body); item = d["data"][0]
    if item.get("b64_json"):
        img = base64.b64decode(item["b64_json"])
    else:
        # 图片地址通常在 CDN 上：下载时不带鉴权头，免得把 key 发给别的主机
        try:
            with urllib.request.urlopen(urllib.request.Request(item["url"], headers={"User-Agent": UA}), timeout=300) as r:
                img = r.read()
        except urllib.error.URLError as e:
            sys.exit(f"图片下载失败：{e}")
    out.parent.mkdir(parents=True, exist_ok=True); out.write_bytes(img)
    meta = {k: v for k, v in d.items() if k in ("size", "quality", "usage")}
    print("saved", out, len(img), "bytes", json.dumps(meta))

if __name__ == "__main__":
    main()
