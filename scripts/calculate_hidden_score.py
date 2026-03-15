"""
Step 2 & 3: hidden score を計算し、穴場候補を抽出してGeoJSONで保存する。

hidden_score = poi_density * 0.4 + pedestrian_space * 0.4 + station_distance_score * 0.2

station_distance_score: 駅から200m〜500mの範囲で高スコア
"""

import json
import math
from pathlib import Path

import numpy as np

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
ANALYSIS_DIR = Path(__file__).resolve().parent.parent / "analysis"
DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"

# グリッドセルサイズ (度): 約100m
CELL_SIZE = 0.001

# 各都市の設定
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
        "radius": 1500,
    },
}

# 有名観光地の座標リスト (半径150m以内を除外)
FAMOUS_SPOTS = [
    # Shibuya
    (35.6595, 139.7004),  # スクランブル交差点
    (35.6590, 139.7006),  # ハチ公像
    (35.6614, 139.6981),  # SHIBUYA109
    (35.6620, 139.6995),  # 渋谷ヒカリエ
    (35.6642, 139.6985),  # 渋谷ストリーム
    (35.6580, 139.6945),  # 代々木公園入口
    # Namba
    (34.6685, 139.5025),  # 道頓堀
    (34.6627, 135.5013),  # なんば駅周辺
    # Sakae
    (35.1709, 136.9084),  # 栄交差点
]
FAMOUS_RADIUS_M = 150


def haversine(lat1, lon1, lat2, lon2):
    """2地点間の距離をメートルで返す。"""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def load_geojson(path):
    """GeoJSONファイルを読み込む。"""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def station_distance_score(dist_m):
    """駅からの距離に基づくスコア (0-1)。200m〜500mで最大。"""
    if dist_m < 100:
        return 0.1  # 駅前すぎる
    elif dist_m < 200:
        return 0.5
    elif dist_m <= 500:
        return 1.0  # 最適距離
    elif dist_m <= 800:
        return 0.6
    else:
        return 0.3  # 遠すぎる


def is_near_famous_spot(lat, lon):
    """有名観光地の近くかどうかを判定する。"""
    for flat, flon in FAMOUS_SPOTS:
        if haversine(lat, lon, flat, flon) < FAMOUS_RADIUS_M:
            return True
    return False


def min_station_distance(lat, lon, stations):
    """最寄り駅までの距離を返す。"""
    if not stations:
        return 1000  # 駅データがなければデフォルト
    return min(
        haversine(lat, lon, s["geometry"]["coordinates"][1], s["geometry"]["coordinates"][0])
        for s in stations
    )


def compute_hidden_scores(city_key, city_info):
    """指定都市のhidden scoreを計算する。"""
    poi_path = DATA_DIR / f"{city_key}_poi.geojson"
    station_path = DATA_DIR / f"{city_key}_stations.geojson"

    if not poi_path.exists():
        print(f"  Skipping {city_key}: POI data not found at {poi_path}")
        return []

    poi_data = load_geojson(poi_path)
    features = poi_data.get("features", [])

    stations = []
    if station_path.exists():
        station_data = load_geojson(station_path)
        stations = station_data.get("features", [])
    print(f"  Loaded {len(features)} POIs, {len(stations)} stations")

    # カテゴリ別に分類
    pois = [f for f in features if f["properties"]["category"] not in ("pedestrian_space",)]
    pedestrian_features = [f for f in features if f["properties"]["category"] == "pedestrian_space"]

    # グリッドベースの分析
    center_lat = city_info["lat"]
    center_lon = city_info["lon"]
    radius_deg = city_info["radius"] / 111000  # おおよその度数変換

    grid_results = []

    lat_min = center_lat - radius_deg
    lat_max = center_lat + radius_deg
    lon_min = center_lon - radius_deg
    lon_max = center_lon + radius_deg

    lat_steps = np.arange(lat_min, lat_max, CELL_SIZE)
    lon_steps = np.arange(lon_min, lon_max, CELL_SIZE)

    for glat in lat_steps:
        for glon in lon_steps:
            cell_center_lat = glat + CELL_SIZE / 2
            cell_center_lon = glon + CELL_SIZE / 2

            # 有名スポットの近くは除外
            if is_near_famous_spot(cell_center_lat, cell_center_lon):
                continue

            # POI密度: セルの半径150m以内のPOIを収集
            nearby_pois = [
                p for p in pois
                if haversine(
                    cell_center_lat,
                    cell_center_lon,
                    p["geometry"]["coordinates"][1],
                    p["geometry"]["coordinates"][0],
                ) < 150
            ]
            poi_count = len(nearby_pois)

            # カテゴリ別に集計
            from collections import Counter
            cat_counts = Counter(p["properties"]["category"] for p in nearby_pois)

            # 名前付きPOIを収集 (上位5件)
            named_pois = [
                p["properties"]["name"]
                for p in nearby_pois
                if p["properties"].get("name")
            ][:5]

            # 歩行者空間: セルの半径150m以内の歩行者空間の数
            ped_count = sum(
                1
                for p in pedestrian_features
                if haversine(
                    cell_center_lat,
                    cell_center_lon,
                    p["geometry"]["coordinates"][1],
                    p["geometry"]["coordinates"][0],
                )
                < 150
            )

            # 最低限のPOIがないセルはスキップ
            if poi_count < 3:
                continue

            # 正規化 (0-1)
            poi_density = min(poi_count / 20.0, 1.0)
            ped_score = min(ped_count / 5.0, 1.0)

            # 最寄り駅
            dist = 1000
            nearest_station = ""
            for s in stations:
                d = haversine(cell_center_lat, cell_center_lon,
                              s["geometry"]["coordinates"][1], s["geometry"]["coordinates"][0])
                if d < dist:
                    dist = d
                    nearest_station = s["properties"].get("name", "")
            dist_score = station_distance_score(dist)

            # hidden_score 計算
            hidden_score = poi_density * 0.4 + ped_score * 0.4 + dist_score * 0.2

            grid_results.append(
                {
                    "lat": round(cell_center_lat, 6),
                    "lon": round(cell_center_lon, 6),
                    "poi_density": round(poi_density, 3),
                    "pedestrian_space": round(ped_score, 3),
                    "station_distance_score": round(dist_score, 3),
                    "station_distance_m": round(dist, 1),
                    "hidden_score": round(hidden_score, 3),
                    "poi_count": poi_count,
                    "ped_count": ped_count,
                    "city": city_info["name"],
                    "nearest_station": nearest_station,
                    "poi_breakdown": dict(cat_counts),
                    "nearby_names": named_pois,
                }
            )

    # スコア上位を抽出
    grid_results.sort(key=lambda x: x["hidden_score"], reverse=True)
    return grid_results


def results_to_geojson(results, top_n=30):
    """上位N件をGeoJSON FeatureCollectionとして返す。"""
    features = []
    for r in results[:top_n]:
        feature = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [r["lon"], r["lat"]]},
            "properties": {
                "location_name": f"Hidden Spot ({r['city']})",
                "lat": r["lat"],
                "lon": r["lon"],
                "hidden_score": r["hidden_score"],
                "poi_density": r["poi_density"],
                "pedestrian_space": r["pedestrian_space"],
                "station_distance_score": r["station_distance_score"],
                "station_distance_m": r["station_distance_m"],
                "poi_count": r["poi_count"],
                "ped_count": r.get("ped_count", 0),
                "city": r["city"],
                "nearest_station": r.get("nearest_station", ""),
                "poi_breakdown": r.get("poi_breakdown", {}),
                "nearby_names": r.get("nearby_names", []),
            },
        }
        features.append(feature)
    return {"type": "FeatureCollection", "features": features}


def main():
    ANALYSIS_DIR.mkdir(exist_ok=True)
    DOCS_DIR.mkdir(exist_ok=True)

    all_results = []

    for city_key, city_info in CITIES.items():
        print(f"Computing hidden scores for {city_info['name']}...")
        results = compute_hidden_scores(city_key, city_info)
        print(f"  Found {len(results)} candidate cells")

        if results:
            # 都市別に保存
            city_geojson = results_to_geojson(results, top_n=20)
            city_path = ANALYSIS_DIR / f"{city_key}_hidden_spots.geojson"
            with open(city_path, "w", encoding="utf-8") as f:
                json.dump(city_geojson, f, ensure_ascii=False, indent=2)
            print(f"  Saved top spots -> {city_path}")

            all_results.extend(results[:20])

    # 全都市統合版を保存 (docs/に配置してGitHub Pagesで使う)
    combined_geojson = results_to_geojson(all_results, top_n=len(all_results))
    combined_path = DOCS_DIR / "hidden_spots.geojson"
    with open(combined_path, "w", encoding="utf-8") as f:
        json.dump(combined_geojson, f, ensure_ascii=False, indent=2)
    print(f"\nSaved combined hidden spots ({len(combined_geojson['features'])} spots) -> {combined_path}")

    # analysis/ にも保存
    analysis_combined = ANALYSIS_DIR / "all_hidden_spots.geojson"
    with open(analysis_combined, "w", encoding="utf-8") as f:
        json.dump(combined_geojson, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
