import arcpy

# --------------------------------------------------
# 設定
# --------------------------------------------------

map_name = "mp_RESONAC_Goi"                 # 実際のマップ名を指定
raster_layer_name = "RESONAC_Goi_DEM1A.tif" # 実際の標高ラスターレイヤ名を指定

# --- 標高区間の境界と刻み幅の設定 ---
min_elev = 2.5       # 下限標高 (m)

# 各区間の上限境界 (m) と 刻み幅 (m)
bound_class1 = 5.0    # 第1区間 上限境界
step_class1  = 0.05   # 第1区間 刻み幅

bound_class2 = 6.0    # 第2区間 上限境界
step_class2  = 0.2    # 第2区間 刻み幅

bound_class3 = 8.0   # 第3区間 上限境界
step_class3  = 0.5    # 第3区間 刻み幅

bound_class4 = 10.0   # 第4区間 上限境界
step_class4  = 1.0    # 第4区間 刻み幅

bound_class5 = 14.0   # 第5区間 上限境界
step_class5  = 2.0    # 第5区間 刻み幅

max_elev     = 15.0   # 上限標高 (m) ※この標高以上を一括して最終クラスにします
step_class6  = 2.0    # 第5区間上限 ～ 上限標高(max_elev) までの刻み幅

# Figure Space（数字と同じ幅の空白）
FIGURE_SPACE = "\u2007"

# --------------------------------------------------
# 数値を小数点以下2桁＋Figure Spaceで右詰めする関数
# --------------------------------------------------

def pad_number(value, width):
    """
    数値を小数点以下2桁の文字列に変換し、
    左側を U+2007 FIGURE SPACE で埋める。
    """
    text = f"{value:.2f}"
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
# クラス境界を作成（冒頭の設定を反映）
# --------------------------------------------------

# 各区間の設定リスト: (区間の上限境界, 刻み幅)
intervals = [
    (bound_class1, step_class1), # min_elev ～ 第1境界
    (bound_class2, step_class2), # 第1境界  ～ 第2境界
    (bound_class3, step_class3), # 第2境界  ～ 第3境界
    (bound_class4, step_class4), # 第3境界  ～ 第4境界
    (bound_class5, step_class5), # 第4境界  ～ 第5境界
    (max_elev,     step_class6), # 第5境界  ～ 上限標高(max_elev)
]

breaks = []
current = min_elev

for bound, step in intervals:
    target = min(bound, max_elev)
    if current < target:
        # 刻み数を算出して整数ループで回す（浮動小数点誤差と無限ループを防止）
        num_steps = int(round((target - current) / step))
        for i in range(1, num_steps + 1):
            val = round(current + i * step, 2)
            if val <= target:
                breaks.append(val)
        if not breaks or breaks[-1] < target:
            breaks.append(round(target, 2))
        current = target
    if current >= max_elev:
        break

# 重複を排除して昇順に並べ替え
breaks = sorted(list(set(breaks)))

# --------------------------------------------------
# max_elev以上を一括する最終クラスを追加
# --------------------------------------------------

# ラスターの最大値がmax_elev以下の場合は、上限値重複によるエラーを防ぐため微小値を加算
if raster_max > max_elev:
    final_upper = round(raster_max, 2)
else:
    final_upper = round(max_elev + 0.01, 2)

all_breaks = breaks + [final_upper]

print("\n通常クラス境界:")
print(breaks)

print(f"\n最終クラス: {max_elev:.2f} m 以上")
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

# 表示上の最大幅を設定（小数点以下2桁の書式に合わせて測定）
label_width = max(len(f"{x:.2f}") for x in [min_elev, max_elev] + all_breaks)

# ラベルの下限値を min_elev で初期化
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