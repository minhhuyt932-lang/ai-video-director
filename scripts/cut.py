"""按剪辑表（JSON）出片：按帧剪切、推近、定格、只调彩度亮度、BT.601→BT.709、lanczos 放大、轻微锐化、拼接、响度标准化。
  cut.py edit.json OUT.mp4

edit.json 示例：
{
  "fps": 24, "size": "1920x1080", "loudnorm": true, "music": null,
  "segments": [
    {"clip": "clips/shot01_v1.mp4", "start": 24, "end": 114},
    {"clip": "clips/shot02_v1.mp4", "start": 30, "end": 105, "eq": "eq=gamma=1.08"},
    {"clip": "clips/shot02_v1.mp4", "start": 106, "end": 121, "zoom": 1.1, "center": [0.45, 0.42], "eq": "eq=gamma=1.08"},
    {"clip": "clips/shot05_v1.mp4", "start": 6, "end": 111, "freeze": 15}
  ]
}
字段：start/end 为帧号（end 不含）；zoom+center 做推近（跳切时把跳过去的那段推近 1.1 倍，看起来像有意剪的）；
freeze 为定格帧数（声音会继续用原片后面的音频，不够再补静音，并在最后 0.6 秒淡出）；eq 只放彩度/亮度/gamma。
music：可选 {"file": "music.mp3", "start": 秒, "gain_db": -14}，会垫在片段声音下面并在结尾淡出。
相对路径按 edit.json 所在目录解析。不覆盖已有文件。没有音轨的片段（--audio 0 生成的）自动补静音。
"""
import argparse, json, subprocess, sys
from pathlib import Path

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("edit_json"); ap.add_argument("out")
args = ap.parse_args()
spec_path = Path(args.edit_json); OUT = Path(args.out)
if OUT.exists():
    sys.exit(f"{OUT} 已存在，不覆盖")
spec = json.loads(spec_path.read_text(encoding="utf-8")); base = spec_path.parent
FPS = spec.get("fps", 24); W, H = map(int, spec.get("size", "1920x1080").split("x")); segs = spec["segments"]
def rp(p): return str((base / p).resolve()) if not Path(p).is_absolute() else p
def probe(c):
    j = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", c], capture_output=True, text=True).stdout)
    v = [s for s in j["streams"] if s["codec_type"] == "video"][0]; n, d = map(int, v["r_frame_rate"].split("/"))
    return float(j["format"]["duration"]), any(s["codec_type"] == "audio" for s in j["streams"]), n / d
clips = sorted({rp(s["clip"]) for s in segs}); idx = {c: i for i, c in enumerate(clips)}; info = {c: probe(c) for c in clips}
cdur = {c: info[c][0] for c in clips}
for c in clips:
    if abs(info[c][2] - FPS) > 0.01:
        print(f"警告：{Path(c).name} 帧率 {info[c][2]:.3f} ≠ {FPS}，按帧号剪切会和声音错位，先统一帧率")
inputs = sum([["-i", c] for c in clips], []); fc = []; pairs = []
for k, s in enumerate(segs):
    c = rp(s["clip"]); i = idx[c]; a, b = s["start"], s["end"]; z = s.get("zoom", 1.0); cx, cy = s.get("center", [0.5, 0.5]); fr = s.get("freeze", 0)
    v = f"[{i}:v]trim=start_frame={a}:end_frame={b},setpts=PTS-STARTPTS"
    if z != 1.0:
        v += f",crop=iw/{z}:ih/{z}:iw*{cx}*(1-1/{z}):ih*{cy}*(1-1/{z})"
    v += f",scale={W}:{H}:flags=lanczos:in_color_matrix=bt601:out_color_matrix=bt709,unsharp=5:5:0.35:5:5:0,setsar=1,format=yuv420p"
    if s.get("eq"):
        v += "," + s["eq"]
    if fr:
        v += f",tpad=stop_mode=clone:stop={fr}"
    fc.append(v + f"[v{k}]")
    dur = (b - a + fr) / FPS; aend = min(a / FPS + dur, cdur[c]) if fr else b / FPS
    fade = f"afade=t=out:st={dur - 0.6:.3f}:d=0.6" if fr else f"afade=t=out:st={dur - 0.01:.3f}:d=0.01"
    src = f"[{i}:a]atrim=start={a / FPS}:end={aend},asetpts=PTS-STARTPTS,aresample=48000," if info[c][1] else f"anullsrc=r=48000:cl=stereo,atrim=end={dur},"
    fc.append(f"{src}apad=whole_dur={dur},atrim=end={dur},afade=t=in:d=0.01,{fade}[a{k}]")
    pairs.append(f"[v{k}][a{k}]")
fc.append("".join(pairs) + f"concat=n={len(segs)}:v=1:a=1[v][amix0]")
total = sum((s["end"] - s["start"] + s.get("freeze", 0)) / FPS for s in segs); alast = "[amix0]"
m = spec.get("music")
if m:
    inputs += ["-i", rp(m["file"])]; mi = len(clips)
    fc.append(f"[{mi}:a]atrim=start={m.get('start', 0)}:end={m.get('start', 0) + total},asetpts=PTS-STARTPTS,aresample=48000,"
              f"volume={m.get('gain_db', -14)}dB,afade=t=out:st={total - 1:.3f}:d=1[mus]")
    fc.append("[amix0][mus]amix=inputs=2:duration=first:normalize=0[amix1]"); alast = "[amix1]"
fc.append(f"{alast}{'loudnorm=I=-16:TP=-1.5:LRA=11,' if spec.get('loudnorm', True) else ''}aresample=48000[a]")
subprocess.run(["ffmpeg", "-v", "error", *inputs, "-filter_complex", ";".join(fc), "-map", "[v]", "-map", "[a]",
                "-c:v", "libx264", "-preset", "slow", "-crf", "14", "-r", str(FPS),
                "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
                "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(OUT)], check=True)
print(f"saved {OUT}（{total:.3f} 秒）。抽查每个切点前后 3 帧，动态和声音请用户亲自确认。")
