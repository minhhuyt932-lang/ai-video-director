"""首尾帧工具（Pillow）。
  frames_util.py fit   IN OUT [--size 1664x936]       居中裁成目标比例并缩放（生图常给 1672×941 之类的近似尺寸）
  frames_util.py zoom  IN OUT --center 0.54,0.46 --z 1.4
                       以相对坐标为中心放大 z 倍，中心点在画面里的相对位置不变（推近：尾帧=首帧放大；拉远：首帧=尾帧放大）
  frames_util.py diff  A B OUT                         差分图（自动拉伸对比度），检查首尾帧不该变的区域
  frames_util.py blend A B OUT                         50% 叠加
同一镜头的首帧和尾帧必须同尺寸。输出文件已存在时报错（新版本用新文件名），确需覆盖加 --force。
竖屏 9:16 用 --size 936x1664 之类。
"""
import argparse
from PIL import Image, ImageChops, ImageOps

def fit(im, tw, th):
    w, h = im.size
    if w / h > tw / th:
        nw = round(h * tw / th); x0 = (w - nw) // 2; im = im.crop((x0, 0, x0 + nw, h))
    else:
        nh = round(w * th / tw); y0 = (h - nh) // 2; im = im.crop((0, y0, w, y0 + nh))
    return im.resize((tw, th), Image.LANCZOS)

def zoom(im, cx, cy, z):
    w, h = im.size; cw, ch = w / z, h / z
    x0, y0 = cx * w * (1 - 1 / z), cy * h * (1 - 1 / z)
    return im.crop((round(x0), round(y0), round(x0 + cw), round(y0 + ch))).resize((w, h), Image.LANCZOS)

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("cmd", choices=["fit", "zoom", "diff", "blend"]); ap.add_argument("a"); ap.add_argument("b"); ap.add_argument("out", nargs="?")
ap.add_argument("--size", default="1664x936"); ap.add_argument("--center", default="0.5,0.5"); ap.add_argument("--z", type=float, default=1.0)
ap.add_argument("--force", action="store_true")
a = ap.parse_args()
from pathlib import Path
_dst = a.out if a.cmd in ("diff", "blend") else a.b
if not _dst:
    raise SystemExit("缺少输出路径")
if Path(_dst).exists() and not a.force:
    raise SystemExit(f"{_dst} 已存在，不覆盖（换新文件名，或加 --force）")
if a.cmd == "fit":
    tw, th = map(int, a.size.lower().split("x")); fit(Image.open(a.a).convert("RGB"), tw, th).save(a.b)
elif a.cmd == "zoom":
    cx, cy = map(float, a.center.split(",")); zoom(Image.open(a.a).convert("RGB"), cx, cy, a.z).save(a.b)
else:
    A, B = Image.open(a.a).convert("RGB"), Image.open(a.b).convert("RGB")
    if A.size != B.size:
        raise SystemExit(f"尺寸不一致：{A.size} vs {B.size}")
    (ImageOps.autocontrast(ImageChops.difference(A, B).convert("L")) if a.cmd == "diff" else Image.blend(A, B, 0.5)).save(a.out)
print("ok", a.cmd, a.out or a.b)
