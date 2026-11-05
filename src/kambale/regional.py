"""Regional 1:1,000,000 geology polygons used as map background and plausibility context only.

The polygons are copied (as WKT) into regional_geology_context so that figure code never reads the shapefile.
They do not verify any local contact, lithology or graphite occurrence.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import geopandas as gpd
from shapely.geometry import MultiPoint, Point

from kambale.config import REGIONAL_SHP

SCALE_NOTE = "1:1,000,000 regional map; context only; not local geology or verified contacts"
EXPECTED_CRS_EPSG = 32630


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract_context(collars_utm: list[tuple[float, float]], buffer_m: float,
                    shp: Path = REGIONAL_SHP) -> tuple[str, list[dict], dict]:
    """Return (source_sha256, polygon rows, summary) for polygons intersecting the collar buffer."""
    source_hash = file_sha256(shp)
    layer = gpd.read_file(shp)
    if layer.crs is None or layer.crs.to_epsg() != EXPECTED_CRS_EPSG:
        raise ValueError(f"regional layer CRS is {layer.crs}; expected EPSG:{EXPECTED_CRS_EPSG}")
    hull = MultiPoint([Point(x, y) for x, y in collars_utm]).convex_hull.buffer(buffer_m)
    candidates = layer.sindex.query(hull, predicate="intersects")
    rows = []
    for index in candidates:
        feature = layer.iloc[int(index)]
        geom = feature.geometry
        centroid = geom.centroid
        rows.append({
            "feature_index": int(index),
            "geo_symbol": str(feature["GEO_SYMBOL"]),
            "stratigraphy": None if feature["Stratigrap"] in (None, "None") else str(feature["Stratigrap"]),
            "legend_text": None if feature["Legend_Tex"] in (None, "None") else str(feature["Legend_Tex"]),
            "metamorphism": None if feature["Metamorpho"] in (None, "None") else str(feature["Metamorpho"]),
            "geom_wkt": geom.wkt,
            "centroid_e_m": round(centroid.x, 3),
            "centroid_n_m": round(centroid.y, 3),
            "intersects_collar_buffer": 1,
            "scale_note": SCALE_NOTE,
        })
    rows.sort(key=lambda r: r["feature_index"])
    inside = {}
    for x, y in collars_utm:
        point = Point(x, y)
        for row in rows:
            if row["geo_symbol"] and _contains(row["geom_wkt"], point):
                inside[(x, y)] = row["geo_symbol"]
                break
    summary = {
        "n_polygons": len(rows),
        "codes": sorted({r["geo_symbol"] for r in rows}),
        "collars_inside": len(inside),
        "n_collars": len(collars_utm),
        "symbols_at_collars": sorted(set(inside.values())),
    }
    return source_hash, rows, summary


def _contains(wkt: str, point: Point) -> bool:
    from shapely import wkt as shapely_wkt
    return shapely_wkt.loads(wkt).contains(point)


def distance_to_symbol_m(collars_utm: list[tuple[float, float]], symbol: str,
                         shp: Path = REGIONAL_SHP) -> dict[tuple[float, float], float]:
    """Distance from each collar to the nearest polygon with the given GEO_SYMBOL (0 if inside)."""
    layer = gpd.read_file(shp)
    subset = layer[layer["GEO_SYMBOL"] == symbol]
    union = subset.geometry.union_all()
    return {(x, y): float(Point(x, y).distance(union)) for x, y in collars_utm}
