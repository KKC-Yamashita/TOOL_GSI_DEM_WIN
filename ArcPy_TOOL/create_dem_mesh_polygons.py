import os
import zipfile
import xml.etree.ElementTree as ET
import arcpy

# --------------------------------------------------
# 設定
# --------------------------------------------------

# ZIPファイル、またはZIPが格納されているフォルダパス
target_path = r"D:\ArcGIS_Project\2610_JERA名古屋\01_GSI_DATA\01_DEM5A\01_ORG"

# 出力するShapefileのパス
output_shp = r"D:\ArcGIS_Project\2610_JERA名古屋\dem_mesh_polygons.shp"

# 空間参照（JGD2011 経緯度: 6668 / 平面直角座標系等に変える場合は適宜指定）
spatial_ref = arcpy.SpatialReference(6668)

# --------------------------------------------------
# 対象ZIPファイルのリストアップ
# --------------------------------------------------

zip_files = []
if os.path.isfile(target_path) and target_path.lower().endswith(".zip"):
    zip_files.append(target_path)
elif os.path.isdir(target_path):
    zip_files = [
        os.path.join(target_path, f)
        for f in os.listdir(target_path)
        if f.lower().endswith(".zip")
    ]
else:
    raise FileNotFoundError("指定されたファイルまたはフォルダが見つかりません。")

print(f"対象ZIPファイル数: {len(zip_files)} 件")

# --------------------------------------------------
# 全ZIPからXMLのメッシュ情報・境界座標を抽出
# --------------------------------------------------

mesh_records = []
seen_meshes = set()  # 重複登録防止用

for zpath in zip_files:
    zip_name = os.path.basename(zpath)
    with zipfile.ZipFile(zpath, "r") as zf:
        xml_names = [f for f in zf.namelist() if f.lower().endswith(".xml")]

        for xname in xml_names:
            try:
                content = zf.read(xname)
                root = ET.fromstring(content)

                # メッシュコードの取得
                mesh_code = None
                for elem in root.iter():
                    if elem.tag.endswith("mesh"):
                        mesh_code = elem.text.strip()
                        break

                # XMLタグから取れない場合のファイル名フォールバック
                if not mesh_code:
                    base_name = os.path.basename(xname)
                    parts = base_name.split("-")
                    if len(parts) >= 5:
                        mesh_code = f"{parts[2]}{parts[3]}{parts[4]}"

                # 同一メッシュの重複があればスキップ
                if mesh_code in seen_meshes:
                    continue

                # Envelope (lowerCorner, upperCorner) の取得
                lower_elem = None
                upper_elem = None
                for elem in root.iter():
                    if elem.tag.endswith("lowerCorner"):
                        lower_elem = elem
                    elif elem.tag.endswith("upperCorner"):
                        upper_elem = elem

                if lower_elem is not None and upper_elem is not None:
                    lat_min, lon_min = map(float, lower_elem.text.strip().split())
                    lat_max, lon_max = map(float, upper_elem.text.strip().split())

                    mesh_records.append({
                        "mesh_code": mesh_code,
                        "xml_name": os.path.basename(xname),
                        "zip_name": zip_name,
                        "lon_min": lon_min,
                        "lat_min": lat_min,
                        "lon_max": lon_max,
                        "lat_max": lat_max
                    })
                    seen_meshes.add(mesh_code)

            except Exception as e:
                print(f"スキップ ({xname}): {e}")

print(f"抽出されたメッシュ数（ポリゴン数）: {len(mesh_records)} 件")

# --------------------------------------------------
# Shapefile の新規作成
# --------------------------------------------------

out_dir = os.path.dirname(os.path.abspath(output_shp))
out_name = os.path.basename(output_shp)
os.makedirs(out_dir, exist_ok=True)

if arcpy.Exists(output_shp):
    arcpy.management.Delete(output_shp)

arcpy.management.CreateFeatureclass(
    out_path=out_dir,
    out_name=out_name,
    geometry_type="POLYGON",
    spatial_reference=spatial_ref
)

# 属性フィールドの追加
arcpy.management.AddField(output_shp, "MeshCode", "TEXT", field_length=15)
arcpy.management.AddField(output_shp, "XMLName", "TEXT", field_length=60)
arcpy.management.AddField(output_shp, "ZIPName", "TEXT", field_length=60)

# --------------------------------------------------
# ポリゴンジオメトリと属性の書き込み
# --------------------------------------------------

fields = ["SHAPE@", "MeshCode", "XMLName", "ZIPName"]

with arcpy.da.InsertCursor(output_shp, fields) as cursor:
    for rec in mesh_records:
        pt_sw = arcpy.Point(rec["lon_min"], rec["lat_min"])
        pt_se = arcpy.Point(rec["lon_max"], rec["lat_min"])
        pt_ne = arcpy.Point(rec["lon_max"], rec["lat_max"])
        pt_nw = arcpy.Point(rec["lon_min"], rec["lat_max"])

        ring = arcpy.Array([pt_sw, pt_se, pt_ne, pt_nw, pt_sw])
        polygon = arcpy.Polygon(ring, spatial_ref)

        cursor.insertRow([polygon, rec["mesh_code"], rec["xml_name"], rec["zip_name"]])

print(f"Shapefile を作成しました:\n -> {output_shp}")