"""共用：从 .env.local 读配置（不打印值），遮挡密钥。"""
import re
from pathlib import Path

def find_env(explicit=None):
    if explicit:
        p = Path(explicit).expanduser()
        if not p.is_file():
            raise SystemExit(f"找不到 {p}")
        return p
    d = Path.cwd().resolve()
    for p in [d, *d.parents]:
        if (p / ".env.local").is_file():
            return p / ".env.local"
    raise SystemExit("当前目录及上级目录都没有 .env.local；用 --env 指定")

def load_env(path):
    out = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):]
        k, v = line.split("=", 1)
        v = v.strip()
        if v[:1] in ("'", '"') and v[:1] in v[1:]:
            v = v[1:v.index(v[0], 1)]          # 引号包住的值原样保留
        elif " #" in v:
            v = v.split(" #", 1)[0].strip()    # 去掉行内注释
        out[k.strip()] = v
    return out

_SECRET = re.compile(r"(sk-|tg-|Bearer\s+)[A-Za-z0-9_\-\.]{8,}")

def mask(text, *secrets):
    for s in secrets:
        if s:
            text = text.replace(s, "<hidden>")
    return _SECRET.sub(lambda m: m.group(1) + "<hidden>", text)

# 有些服务商前面有 Cloudflare，会拦 Python urllib 的默认 UA（错误码 1010），所以用 OpenAI SDK 风格的 UA
UA = "OpenAI/Python 1.99.0"
