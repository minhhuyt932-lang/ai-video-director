"""配色明暗检查：把画面转成黑白后，主体和紧挨着的背景能不能分开。
  contrast_check.py palette.json
palette.json 示例：
{"colors": {"son": "#F6D86B", "sofa": "#3F5D6C", "skin": "#EDBE9F", "wall": "#A8876A"},
 "pairs": [["son", "sofa"], ["skin", "wall"]]}
亮度按 0.299R+0.587G+0.114B（0–255）。差 < 40 视为分不开，要调色（常见：肤色和米色墙、浅色衣服和浅色沙发）。
"""
import argparse, json
ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("palette_json")
spec = json.load(open(ap.parse_args().palette_json, encoding="utf-8")); C = spec["colors"]
def L(h): r, g, b = (int(h[i:i + 2], 16) for i in (1, 3, 5)); return round(0.299 * r + 0.587 * g + 0.114 * b)
bad = 0
for a, b in spec["pairs"]:
    d = abs(L(C[a]) - L(C[b])); bad += d < 40
    print(f"{a} {C[a]}（{L(C[a])}） vs {b} {C[b]}（{L(C[b])}）：差 {d}{'  ⚠️ 偏弱' if d < 40 else ''}")
print("全部通过" if not bad else f"{bad} 组偏弱，改色后再画草图")
