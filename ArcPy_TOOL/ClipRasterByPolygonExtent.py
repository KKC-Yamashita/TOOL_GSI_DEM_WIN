import os
import arcpy

# --------------------------------------------------
# 設定
# --------------------------------------------------
map_name = "mp_OgiCity"
raster_layer_name = "DEM5m結合"
polygon_layer_name = "Admin_OgiCity_bbox_1km"

output_folder = (
    r"D:\ArcGIS_Project\2609_OgiCity_Saga\01_GSI_DATA\01_DEM5A\02_Tiff"
)
output_tif_name = "DEM5A_OgiCity.tif"

# --------------------------------------------------
# ArcGIS Proプロジェクト・レイヤー取得
# --------------------------------------------------
aprx = arcpy.mp.ArcGISProject("CURRENT")
maps = aprx.listMaps(map_name)

if not maps:
    raise RuntimeError(f"マップ '{map_name}' が見つかりません。")

m = maps[0]

raster_layers = m.listLayers(raster_layer_name)
polygon_layers = m.listLayers(polygon_layer_name)

if not raster_layers or not polygon_layers:
    raise RuntimeError("指定したラスターまたはポリゴンレイヤーが見つかりません。")

raster_lyr = raster_layers[0]
polygon_lyr = polygon_layers[0]

# 出力先パスの設定と既存ファイル削除
os.makedirs(output_folder, exist_ok=True)
output_tif = os.path.join(output_folder, output_tif_name)

if arcpy.Exists(output_tif):
    arcpy.management.Delete(output_tif)

# --------------------------------------------------
# クリップ処理 (ArcPyが自動で座標系変換・Extent計算を行います)
# --------------------------------------------------
print("ラスターをクリップしています...")

arcpy.management.Clip(
    in_raster=raster_lyr,
    rectangle="#",  # in_template_dataset を指定する場合 "#" で自動適用されます
    out_raster=output_tif,
    in_template_dataset=polygon_lyr,  # 切り出し枠にポリゴンレイヤーをそのまま指定
    nodata_value="",
    clipping_geometry="NONE",  # 矩形で切る場合は "NONE"、ポリゴン外形なら "CLIPPING_GEOMETRY"
    maintain_clipping_extent="NO_MAINTAIN_EXTENT",
)

print(f"処理が完了しました: {output_tif}")