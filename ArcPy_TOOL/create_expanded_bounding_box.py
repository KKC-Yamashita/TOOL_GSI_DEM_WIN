import arcpy
import sys

# 設定
tgt_plgn = r"D:\ArcGIS_Project\2609_OgiCity_Saga\02_NLID_DATA\02_AdminArea\Admin_OgiCity.shp"
out_plgn = r"D:\ArcGIS_Project\2609_OgiCity_Saga\02_NLID_DATA\02_AdminArea\Admin_OgiCity_bbox_1km.shp"
expand_dist = 1000  # 拡張する距離（メートル）

# 1. アクティブなマップから座標系（空間参照）を取得
try:
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    active_map = aprx.activeMap
    if active_map is None:
        print("エラー: アクティブなマップが見つかりません。ArcGIS Proでマップを開いた状態で実行してください。")
        sys.exit()
    map_sr = active_map.spatialReference
except Exception as e:
    print(f"プロジェクトまたはマップの取得に失敗しました: {e}")
    sys.exit()

# 2. マップの座標系が投影座標系（平面直角座標系含む）かチェック
if map_sr.type != "Projected":
    print(f"【警告】現在のマップ座標系（{map_sr.name}）は平面直角座標系（投影座標系）ではありません。処理を中止します。")
    sys.exit()

print(f"マップの座標系: {map_sr.name}")

# 3. 入力データを読み込み、マップの座標系に変換したジオメトリを取得
geometries = []
with arcpy.da.SearchCursor(tgt_plgn, ["SHAPE@"]) as cursor:
    for row in cursor:
        geom = row[0]
        if geom:
            # 入力データの座標系からマップの座標系へ変換
            geometries.append(geom.projectAs(map_sr))

if not geometries:
    print("エラー: 入力データに有効なジオメトリが存在しません。")
    sys.exit()

# 4. 全ジオメトリから全体の最小・最大座標を取得し、1km外側に拡張
x_min = min(g.extent.XMin for g in geometries) - expand_dist
y_min = min(g.extent.YMin for g in geometries) - expand_dist
x_max = max(g.extent.XMax for g in geometries) + expand_dist
y_max = max(g.extent.YMax for g in geometries) + expand_dist

# 5. 拡張座標からポリゴン作成（マップの座標系を指定）
point_array = arcpy.Array([
    arcpy.Point(x_min, y_min),
    arcpy.Point(x_min, y_max),
    arcpy.Point(x_max, y_max),
    arcpy.Point(x_max, y_min),
    arcpy.Point(x_min, y_min)
])

expanded_bbox = arcpy.Polygon(point_array, map_sr)

# 6. 出力
arcpy.management.CopyFeatures([expanded_bbox], out_plgn)

print(f"1km外側に拡張した矩形を {out_plgn} に作成しました。")