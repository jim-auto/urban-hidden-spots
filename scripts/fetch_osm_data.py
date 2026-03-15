"""
Step 1: OpenStreetMap Overpass API からPOI・歩行者空間・駅データを取得し、GeoJSONで保存する。
"""

import json
import time
import requests
from pathlib import Path

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# 対象都市の定義 (name, lat, lon, radius_m)
CITIES = {
    "tokyo_shibuya": {
        "name": "Tokyo (Shibuya)",
        "lat": 35.6580,
        "lon": 139.7016,
        "radius": 1500,
    },
    "osaka_namba": {
        "name": "Osaka (Namba)",
        "lat": 34.6627,
        "lon": 135.5013,
        "radius": 1500,
    },
    "nagoya_sakae": {
        "name": "Nagoya (Sakae)",
        "lat": 35.1709,
        "lon": 136.9084,
        "radius": 2000,
    },
}

# POI・歩行者空間を取得するクエリ
POI_QUERY_TEMPLATE = """
[out:json][timeout:60];
(
  node["highway"="pedestrian"](around:{radius},{lat},{lon});
  way["highway"="pedestrian"](around:{radius},{lat},{lon});
  node["highway"="footway"](around:{radius},{lat},{lon});
  way["highway"="footway"](around:{radius},{lat},{lon});
  node["leisure"="park"](around:{radius},{lat},{lon});
  way["leisure"="park"](around:{radius},{lat},{lon});
  node["shop"](around:{radius},{lat},{lon});
  node["amenity"="cafe"](around:{radius},{lat},{lon});
  node["amenity"="restaurant"](around:{radius},{lat},{lon});
);
out center body;
"""

# 駅を取得するクエリ
STATION_QUERY_TEMPLATE = """
[out:json][timeout:30];
(
  node["railway"="station"](around:{radius},{lat},{lon});
  node["station"="subway"](around:{radius},{lat},{lon});
);
out body;
"""


def query_overpass(query: str) -> dict:
    """Overpass APIにクエリを送信し、結果を返す。"""
    resp = requests.post(OVERPASS_URL, data={"data": query}, timeout=120)
    resp.raise_for_status()
    return resp.json()


def elements_to_geojson(elements: list) -> dict:
    """Overpass APIのelementsをGeoJSON FeatureCollectionに変換する。"""
    features = []
    for el in elements:
        # way の場合は center 座標を使う
        lat = el.get("lat") or el.get("center", {}).get("lat")
        lon = el.get("lon") or el.get("center", {}).get("lon")
        if lat is None or lon is None:
            continue

        tags = el.get("tags", {})
        # 要素の種類を判定
        category = _categorize(tags)

        feature = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {
                "osm_id": el.get("id"),
                "osm_type": el.get("type"),
                "name": tags.get("name", ""),
                "category": category,
                "tags": tags,
            },
        }
        features.append(feature)

    return {"type": "FeatureCollection", "features": features}


def _categorize(tags: dict) -> str:
    """タグからカテゴリを判定する。"""
    if tags.get("highway") in ("pedestrian", "footway"):
        return "pedestrian_space"
    if tags.get("leisure") == "park":
        return "park"
    if tags.get("shop"):
        return "shop"
    if tags.get("amenity") == "cafe":
        return "cafe"
    if tags.get("amenity") == "restaurant":
        return "restaurant"
    if tags.get("railway") == "station" or tags.get("station"):
        return "station"
    return "other"


def fetch_city_data(city_key: str, city_info: dict, output_dir: Path):
    """指定都市のPOI・駅データを取得してGeoJSONとして保存する。"""
    print(f"Fetching POI data for {city_info['name']}...")
    poi_query = POI_QUERY_TEMPLATE.format(
        lat=city_info["lat"],
        lon=city_info["lon"],
        radius=city_info["radius"],
    )
    poi_result = query_overpass(poi_query)
    poi_geojson = elements_to_geojson(poi_result.get("elements", []))

    poi_path = output_dir / f"{city_key}_poi.geojson"
    with open(poi_path, "w", encoding="utf-8") as f:
        json.dump(poi_geojson, f, ensure_ascii=False, indent=2)
    print(f"  Saved {len(poi_geojson['features'])} POI features -> {poi_path}")

    # レートリミット回避
    time.sleep(2)

    print(f"Fetching station data for {city_info['name']}...")
    station_query = STATION_QUERY_TEMPLATE.format(
        lat=city_info["lat"],
        lon=city_info["lon"],
        radius=city_info["radius"],
    )
    station_result = query_overpass(station_query)
    station_geojson = elements_to_geojson(station_result.get("elements", []))

    station_path = output_dir / f"{city_key}_stations.geojson"
    with open(station_path, "w", encoding="utf-8") as f:
        json.dump(station_geojson, f, ensure_ascii=False, indent=2)
    print(f"  Saved {len(station_geojson['features'])} stations -> {station_path}")

    time.sleep(2)


def main():
    output_dir = Path(__file__).resolve().parent.parent / "data"
    output_dir.mkdir(exist_ok=True)

    for city_key, city_info in CITIES.items():
        fetch_city_data(city_key, city_info, output_dir)

    print("\nAll data fetched successfully.")


if __name__ == "__main__":
    main()
