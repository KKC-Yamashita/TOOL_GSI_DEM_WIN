# -*- coding: utf-8 -*-
"""
DEM5A FG-GML XML ZIP群 -> 指定緯度経度範囲 GeoTIFF
"""

from pathlib import Path
import zipfile
import tempfile
import xml.etree.ElementTree as ET

import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.merge import merge


# ==================================================
# 設定
# ==================================================
tgt_folder = Path(r"D:\ArcGIS_Project\2604_Kumamoto_Hikawa\03_GSI\02_CONV_JGD2011\22_DEM5A")
out_tif = Path(r"D:\ArcGIS_Project\2604_Kumamoto_Hikawa\03_GSI\04_DEM5A_RASTER\DEM5A_Hikawa.tif")

# 切り出し範囲：経度・緯度
min_lon = 130.6000
min_lat = 32.5166
max_lon = 130.7333
max_lat = 32.6333

nodata = -9999.0
out_crs = "EPSG:6668"   # JGD2011 緯度経度


# ==================================================
# 関数
# ==================================================
def get_text(root, tag_end):
    for elem in root.iter():
        if elem.tag.endswith(tag_end):
            return elem.text
    return None


def parse_pos(text):
    return [float(v) for v in text.split()]


def intersects(b1, b2):
    l1, btm1, r1, t1 = b1
    l2, btm2, r2, t2 = b2
    return not (r1 < l2 or r2 < l1 or t1 < btm2 or t2 < btm1)


def parse_dem_xml(xml_bytes):
    root = ET.fromstring(xml_bytes)

    lower = parse_pos(get_text(root, "lowerCorner"))
    upper = parse_pos(get_text(root, "upperCorner"))

    # FG-GMLでは多くの場合 lowerCorner = 緯度 経度
    lat_min, lon_min = lower
    lat_max, lon_max = upper

    low_x, low_y = map(int, get_text(root, "low").split())
    high_x, high_y = map(int, get_text(root, "high").split())

    nx = high_x - low_x + 1
    ny = high_y - low_y + 1

    start_text = get_text(root, "startPoint")
    if start_text:
        sx, sy = map(int, start_text.split())
    else:
        sx, sy = 0, 0

    tuple_text = get_text(root, "tupleList")
    if tuple_text is None:
        return None

    arr = np.full((ny, nx), nodata, dtype=np.float32)

    values = []
    for line in tuple_text.splitlines():
        line = line.strip()
        if not line:
            continue

        parts = line.split(",")

        try:
            z = float(parts[-1])
        except Exception:
            z = nodata

        values.append(z)

    start_index = sy * nx + sx

    for i, z in enumerate(values):
        idx = start_index + i
        if idx >= nx * ny:
            break

        row = idx // nx
        col = idx % nx

        arr[row, col] = z

    dx = (lon_max - lon_min) / (nx - 1)
    dy = (lat_max - lat_min) / (ny - 1)

    transform = from_origin(
        lon_min - dx / 2.0,
        lat_max + dy / 2.0,
        dx,
        dy
    )

    bounds = (lon_min, lat_min, lon_max, lat_max)

    return arr, transform, bounds


# ==================================================
# メイン処理
# ==================================================
def main():
    clip_bounds = (min_lon, min_lat, max_lon, max_lat)

    zip_paths = sorted(tgt_folder.glob("*.zip"))

    if not zip_paths:
        raise RuntimeError(f"ZIPファイルが見つかりません: {tgt_folder}")

    print(f"[INFO] ZIP files: {len(zip_paths)}")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        tile_paths = []

        for zip_idx, zip_path in enumerate(zip_paths, start=1):
            print(f"\n[ZIP] {zip_idx}/{len(zip_paths)} {zip_path.name}")

            with zipfile.ZipFile(zip_path, "r") as zf:
                xml_names = [
                    n for n in zf.namelist()
                    if n.lower().endswith(".xml")
                ]

                print(f"  XML files: {len(xml_names)}")

                for xml_idx, name in enumerate(xml_names, start=1):
                    xml_bytes = zf.read(name)

                    parsed = parse_dem_xml(xml_bytes)
                    if parsed is None:
                        continue

                    arr, transform, bounds = parsed

                    if not intersects(bounds, clip_bounds):
                        continue

                    tmp_tif = tmpdir / f"tile_{len(tile_paths):05d}.tif"

                    with rasterio.open(
                        tmp_tif,
                        "w",
                        driver="GTiff",
                        height=arr.shape[0],
                        width=arr.shape[1],
                        count=1,
                        dtype="float32",
                        crs=out_crs,
                        transform=transform,
                        nodata=nodata,
                        compress="lzw"
                    ) as dst:
                        dst.write(arr, 1)

                    tile_paths.append(tmp_tif)

                    print(f"  [PICK] {xml_idx}/{len(xml_names)} {name}")

        if not tile_paths:
            raise RuntimeError("指定範囲に交差するXMLが見つかりませんでした。")

        print(f"\n[INFO] picked tiles: {len(tile_paths)}")

        srcs = [rasterio.open(p) for p in tile_paths]

        mosaic, out_transform = merge(
            srcs,
            bounds=clip_bounds,
            nodata=nodata
        )

        meta = srcs[0].meta.copy()
        meta.update({
            "driver": "GTiff",
            "height": mosaic.shape[1],
            "width": mosaic.shape[2],
            "transform": out_transform,
            "crs": out_crs,
            "nodata": nodata,
            "compress": "lzw",
            "dtype": "float32"
        })

        out_tif.parent.mkdir(parents=True, exist_ok=True)

        with rasterio.open(out_tif, "w", **meta) as dst:
            dst.write(mosaic)

        for src in srcs:
            src.close()

    print("\n[DONE]")
    print(f"Saved: {out_tif}")


if __name__ == "__main__":
    main()