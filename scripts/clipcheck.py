"""视频片段抽帧检查（Pillow、numpy、ffmpeg）。
  clipcheck.py CLIP.mp4 --first F.png --last L.png --out check/
输出（在 check/<片段名>/ 下）：
  <名字>_sheet.png         每 0.5 秒一帧的总表（带时间）
  <名字>_first_vs_ref.png  片段第一帧 vs 首帧原图；<名字>_last_vs_ref.png 同理
  终端：尺寸/帧率/时长/音轨、每 0.5 秒平均亮度（看是否越来越暗）、
        帧间差最大的几处（定位"结尾突然跳到尾帧"之类的突跳，给出帧号和倍数）、每 0.25 秒音频响度 dBFS
输出放在 OUT/<名字>/ 下，已存在时报错（加 --force 覆盖）。
这些都只是静帧和数字。动作手感、声音内容必须让用户亲自看、亲自听。
"""
import argparse, json, shutil, subprocess, tempfile
from pathlib import Path
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageStat

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("clip"); ap.add_argument("--first"); ap.add_argument("--last"); ap.add_argument("--out", default="check"); ap.add_argument("--force", action="store_true")
a = ap.parse_args()
stem = Path(a.clip).stem; out = Path(a.out) / stem
if out.exists() and not a.force:
    raise SystemExit(f"{out} 已存在，不覆盖（加 --force）")
out.mkdir(parents=True, exist_ok=True)
probe = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", a.clip], capture_output=True, text=True).stdout)
v = [s for s in probe["streams"] if s["codec_type"] == "video"][0]; aud = [s for s in probe["streams"] if s["codec_type"] == "audio"]
print(f"video {v['width']}x{v['height']} fps={v.get('r_frame_rate')} dur={float(probe['format']['duration']):.2f}s; audio streams={len(aud)}")

tmp = Path(tempfile.mkdtemp(dir=out))
subprocess.run(["ffmpeg", "-v", "error", "-i", a.clip, "-vf", "fps=2", str(tmp / "f_%03d.png")], check=True)
frames = sorted(tmp.glob("f_*.png"))
try:
    font = ImageFont.truetype("/System/Library/Fonts/STHeiti Medium.ttc", 22)
except OSError:
    font = ImageFont.load_default()
tw, cols = 480, 4; th = round(tw * int(v['height']) / int(v['width']))  # 按原比例缩略，竖屏不变形
sheet = Image.new("RGB", (tw * cols, th * ((len(frames) + cols - 1) // cols)), "black"); d = ImageDraw.Draw(sheet)
for i, f in enumerate(frames):
    x, y = (i % cols) * tw, (i // cols) * th
    sheet.paste(Image.open(f).convert("RGB").resize((tw, th)), (x, y)); d.rectangle([x, y, x + 70, y + 28], fill="black"); d.text((x + 4, y + 2), f"{i * 0.5:.1f}s", font=font, fill="white")
sheet.save(out / f"{stem}_sheet.png")
print("亮度/0.5s:", [round(ImageStat.Stat(Image.open(f).convert("L")).mean[0]) for f in frames])

raw = subprocess.run(["ffmpeg", "-v", "error", "-i", a.clip, "-vf", "scale=320:180", "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True).stdout
g = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 180, 320).astype(np.int16)
dd = np.abs(np.diff(g, axis=0)).mean(axis=(1, 2)); med = float(np.median(dd)) + 1e-6
top = np.argsort(dd)[-3:][::-1]
print(f"帧间差中位数 {med:.2f}；最大几处：" + "，".join(f"#{int(i)}→#{int(i) + 1} {dd[i]:.1f}（{dd[i] / med:.0f}×）" for i in top))
print("  提示：某处远大于中位数且不是第 0–1 帧（2.5 第一帧过锐），多半是突跳，逐帧看那一段。")

if aud:
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", a.clip, "-ac", "1", "-ar", "16000", "-f", "s16le", "-"], capture_output=True).stdout
    x = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768; seg = 4000
    print("音频 dBFS/0.25s:", " ".join(f"{20 * np.log10(np.sqrt(np.mean(x[i:i + seg] ** 2)) + 1e-9):.0f}" for i in range(0, len(x) - seg + 1, seg)))

def grab(args, dst):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args, str(dst)], check=True); return dst
def cmp(img, ref, label):
    A = Image.open(img).convert("RGB"); R = Image.open(ref).convert("RGB").resize(A.size)
    m = ImageStat.Stat(ImageChops.difference(A, R).convert("L")).mean[0]
    pair = Image.new("RGB", (A.width * 2 + 10, A.height), "white"); pair.paste(R, (0, 0)); pair.paste(A, (A.width + 10, 0))
    pair.resize((pair.width // 2, pair.height // 2)).save(out / f"{stem}_{label}_vs_ref.png")
    print(f"{label} 帧 vs 原图：平均差 {m:.1f}（0=完全一样，<5 正常）")
if a.first:
    cmp(grab(["-i", a.clip, "-vf", "select=eq(n\\,0)", "-vframes", "1"], tmp / "first.png"), a.first, "first")
if a.last:
    cmp(grab(["-sseof", "-0.3", "-i", a.clip, "-update", "1"], tmp / "last.png"), a.last, "last")
shutil.rmtree(tmp, ignore_errors=True)
print("输出目录:", out)
