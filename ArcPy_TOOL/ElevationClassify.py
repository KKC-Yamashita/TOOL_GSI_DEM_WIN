import arcpy

# --------------------------------------------------
# 設定
# --------------------------------------------------

map_name = "Ashiya_JGD2011_II"            # 実際のマップ名を指定
raster_layer_name = "Ashiya_DEM1A.tif"    # 実際の標高ラスターレイヤ名を指定

# 標高の最小値と最大値の設定（追加部分）
min_elev = -1.0   # 分類の開始標高（ここを変更すれば動的に追従します）
max_elev = 50.0  # この標高以上を一括して1クラスにする（浮動小数点数）

# Figure Space（数字と同じ幅の空白）
FIGURE_SPACE = "\u2007"

# --------------------------------------------------
# 数値を小数点以下1桁＋Figure Spaceで右詰めする関数
# --------------------------------------------------

def pad_number(value, width):
    """
    数値を小数点以下1桁の文字列に変換し、
    左側を U+2007 FIGURE SPACE で埋める。
    """
    text = f"{value:.1f}"
    return FIGURE_SPACE * max(0, width - len(text)) + text


# --------------------------------------------------
# 現在のArcGIS Proプロジェクトを取得
# --------------------------------------------------

aprx = arcpy.mp.ArcGISProject("CURRENT")

maps = aprx.listMaps(map_name)
if not maps:
    raise RuntimeError(f"マップ '{map_name}' が見つかりません。")

m = maps[0]

layers = m.listLayers(raster_layer_name)
if not layers:
    raise RuntimeError(f"マップ '{map_name}' 内に レイヤー '{raster_layer_name}' が見つかりません。")

lyr = layers[0]

# --------------------------------------------------
# ラスターの実際の最大標高を取得
# --------------------------------------------------

raster_max = float(
    arcpy.management.GetRasterProperties(lyr, "MAXIMUM").getOutput(0)
)

print(f"ラスター最大標高: {raster_max:.2f} m")

# --------------------------------------------------
# クラス境界を作成
# --------------------------------------------------

breaks = []

# min_elev～3m：0.2m刻み（変更部分）
# min_elev から 3.0m までのステップ数を自動計算します
steps = int(round((3.0 - min_elev) / 0.2))
breaks += [
    round(min_elev + (i + 1) * 0.2, 1)
    for i in range(steps)
    if round(min_elev + (i + 1) * 0.2, 1) <= max_elev
]

# 3～10m：1m刻み（4mから開始）
breaks += [
    float(x) for x in range(4, 11, 1)
    if x <= max_elev
]

# 10～20m：2m刻み
breaks += [
    float(x) for x in range(12, 21, 2)
    if x <= max_elev
]

# 20～50m：5m刻み
breaks += [
    float(x) for x in range(25, 51, 5)
    if x <= max_elev
]

# 50～100m：10m刻み
breaks += [
    float(x) for x in range(60, 101, 10)
    if x <= max_elev
]

# 100m以上：50m刻み
breaks += [
    float(x) for x in range(150, int(max_elev) + 1, 50)
]

# max_elev が境界値に含まれていなければ追加
if not breaks or breaks[-1] != max_elev:
    breaks.append(max_elev)

# --------------------------------------------------
# max_elev以上を一括する最終クラスを追加
# --------------------------------------------------

final_upper = max(raster_max, max_elev)
all_breaks = breaks + [final_upper]

print("\n通常クラス境界:")
print(breaks)

print(f"\n最終クラス: {max_elev:.1f} m 以上")
print(f"内部的な最終上限値: {final_upper:.2f} m")
print(f"クラス数: {len(all_breaks)}")

# --------------------------------------------------
# ラスターを「分類」表示にする
# --------------------------------------------------

sym = lyr.symbology

if not hasattr(sym, "colorizer"):
    raise RuntimeError("指定したレイヤーはラスターではありません。")

if sym.colorizer.type != "RasterClassifyColorizer":
    sym.updateColorizer("RasterClassifyColorizer")

sym.colorizer.classificationField = "Value"
sym.colorizer.breakCount = len(all_breaks)

# --------------------------------------------------
# 手動分類境界を設定
# --------------------------------------------------

class_breaks = sym.colorizer.classBreaks

# 表示上の最大幅を設定（変更部分）
# 桁数を揃えるため、min_elev(マイナスの場合は符号含む)とmax_elevで文字数が多い方を基準幅にします
label_width = max(len(f"{max_elev:.1f}"), len(f"{min_elev:.1f}"))

# ラベルの下限値を min_elev で初期化（変更部分）
lower = min_elev

for i, (brk, upper) in enumerate(zip(class_breaks, all_breaks)):

    # 分類上限値
    brk.upperBound = upper

    # 最終クラス
    if i == len(all_breaks) - 1:
        max_text = pad_number(max_elev, label_width)
        brk.label = f"{max_text} m 以上"

    # 通常クラス
    else:
        lower_text = pad_number(lower, label_width)
        upper_text = pad_number(upper, label_width)
        brk.label = f"{lower_text} ～ {upper_text} m"

    lower = upper

# --------------------------------------------------
# レイヤーへ反映
# --------------------------------------------------

lyr.symbology = sym

# --------------------------------------------------
# 設定結果を確認
# --------------------------------------------------

print("\n設定したクラス:")
print("-" * 30)
for brk in sym.colorizer.classBreaks:
    print(brk.label)
print("-" * 30)

print("\n標高クラス分けを設定しました。")