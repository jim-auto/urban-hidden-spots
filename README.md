# Urban Hidden Spots

都市データ（OpenStreetMap）を利用して「人はいるが有名ではない都市の穴場スポット」を自動推定し、インタラクティブマップとして可視化するツールです。

## Live Demo

[GitHub Pages で地図を見る](https://jim-auto.github.io/urban-hidden-spots/)

## コンセプト

```
hidden_spot = 人がそこそこいる × 歩行者空間 × 駅から少し離れている × 有名観光地ではない
```

## アルゴリズム

### Hidden Score の計算

各エリアをグリッドセル（約100m四方）に分割し、以下の3つの特徴量からスコアを算出します。

| 特徴量 | 重み | 説明 |
|--------|------|------|
| `poi_density` | 0.4 | 半径150m以内のPOI（カフェ、レストラン、ショップ等）の密度 |
| `pedestrian_space` | 0.4 | 半径150m以内の歩行者空間（歩行者天国、歩道）の数 |
| `station_distance_score` | 0.2 | 最寄り駅からの距離（200m〜500mで最大スコア） |

```
hidden_score = poi_density × 0.4 + pedestrian_space × 0.4 + station_distance_score × 0.2
```

スコアはログスケール正規化により分布を平滑化しています。

### フィルタリング

- POI数が3未満のセルは除外
- 有名観光地（スクランブル交差点、道頓堀など）から150m以内のセルは除外

### 駅距離スコア

| 距離 | スコア |
|------|--------|
| 0 - 80m | 0.2 (駅前すぎる) |
| 80 - 150m | 0.7 |
| **150 - 500m** | **1.0 (最適)** |
| 500 - 800m | 0.6 |
| 800m+ | 0.3 |

## 対象都市（9都市）

| 都市 | エリア |
|------|--------|
| 東京 | 新宿、渋谷、池袋、上野 |
| 神奈川 | 横浜 |
| 愛知 | 名駅、栄 |
| 大阪 | 梅田、難波 |

## データ規模

- 穴場スポット: 1,350件
- 有名スポット（比較用）: 43件

## セットアップ

```bash
pip install -r requirements.txt
```

## 使い方

### 全ステップを一括実行

```bash
python scripts/run_all.py
```

### 個別実行

```bash
# Step 1: OSMデータ取得
python scripts/fetch_osm_data.py

# Step 2-3: Hidden Score計算 & 穴場候補抽出
python scripts/calculate_hidden_score.py
```

### 地図を確認

`docs/index.html` をブラウザで開くか、GitHub Pages で公開します。

## 技術スタック

- **Python** - データ取得・分析
- **OpenStreetMap (Overpass API / Nominatim)** - 地理データソース（座標は7桁精度で検証済み）
- **NumPy** - 数値計算
- **Leaflet.js** - インタラクティブ地図表示
- **GitHub Pages** - ホスティング

## ディレクトリ構成

```
urban-hidden-spots/
├── data/                  # OSMから取得した生データ (GeoJSON)
│   ├── <city>_poi.geojson
│   └── <city>_stations.geojson
├── analysis/              # スコア計算結果
│   ├── <city>_hidden_spots.geojson
│   └── all_hidden_spots.geojson
├── scripts/
│   ├── fetch_osm_data.py          # Step 1: データ取得
│   ├── calculate_hidden_score.py  # Step 2-3: スコア計算 & 抽出
│   └── run_all.py                 # 一括実行
├── docs/
│   ├── index.html                 # Leaflet地図 (GitHub Pages)
│   ├── hidden_spots.geojson       # 穴場スポット表示用データ
│   └── famous_spots.geojson       # 有名スポット表示用データ
├── requirements.txt
└── README.md
```

## 地図の見方

- マーカーの**色**と**サイズ**がHidden Scoreを表します
  - オレンジ (大): スコア 0.7+ — 最も穴場度が高い
  - 黄色 (中): スコア 0.3 - 0.7
  - 緑 (小): スコア 0.3 未満
- 星マーカーは有名スポット（比較用）を示します
- マーカーをクリックするとスコアの内訳ポップアップが表示されます（POI詳細、最寄り駅、カテゴリ内訳、周辺スポット名を含む）
- 「?」ボタンでHidden Scoreの説明モーダルを表示できます
- 上部のボタンで都市を切り替えられます

## ライセンス

MIT

地図データ: &copy; [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors
