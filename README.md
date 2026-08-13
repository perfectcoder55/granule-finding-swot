# SWOT × Gagua Ridge 測站 資料搜尋工具

根據海床測站（傾斜度/溫度儀）記錄的時間與座標，搜尋 ML01 上的 SWOT L3 KaRIn Expert 資料（`/home/donnee/SWOT/v300_expert`），列出可用於比對的資料檔，並可選擇性做初步視覺化。

## 檔案

| 檔案 | 用途 |
|---|---|
| `find_swot_granules.py` | 核心工具：時間+空間搜尋，輸出可用檔案清單 |
| `visualize_station_swot.py` | 延伸工具：測站+SWOT軌跡覆蓋圖、SSHA 空間分布圖 |

兩者皆需在 ML01 上執行（資料只存在 ML01），並先啟用 pyeddy 環境：

```bash
ssh <user>@140.112.69.80
conda activate pyeddy
```

## `find_swot_granules.py` — 搜尋可用資料檔

### 參數

| 參數 | 說明 | 必填 |
|---|---|---|
| `--start`, `--end` | 搜尋時間區間，格式 `YYYY-MM-DDTHH:MM:SS` | 是 |
| `--tz-offset` | `--start`/`--end` 相對 UTC 的時區偏移（小時）。測站記錄若為台灣當地時間請填 `8`；SWOT 檔案時間本身為 UTC，不需再手動換算 | 否（預設 0，即輸入已是 UTC）|
| `--lat`, `--lon`, `--radius` | 測站座標 + 搜尋半徑（度），三者搭配使用 | 二選一 |
| `--lon-min`, `--lon-max`, `--lat-min`, `--lat-max` | 經緯度範圍框 | 二選一 |
| `--data-dir` | SWOT 資料根目錄 | 否（預設 `/home/donnee/SWOT/v300_expert`）|

`--lat/--lon` 與 `--lon-min/.../--lat-max` 二選一，不可同時省略。

### 範例

**用測站座標搜尋**（測站記錄為台灣當地時間，換算 UTC 由程式處理）：

```bash
python3 find_swot_granules.py \
  --start 2023-10-08T16:00:00 --end 2023-10-08T17:00:00 --tz-offset 8 \
  --lat 21.8063 --lon 123.7828 --radius 0.5
```

**用經緯度範圍框搜尋**（輸入時間已是 UTC）：

```bash
python3 find_swot_granules.py \
  --start 2023-10-08T08:00:00 --end 2023-10-08T09:00:00 \
  --lon-min 122.0 --lon-max 125.0 --lat-min 20.0 --lat-max 23.0
```

### 輸出

```
搜尋區間: 2023-09-30 16:00:00 ~ 2023-10-15 16:00:00 UTC (輸入視為 UTC+8)
搜尋範圍: lat 21.306~22.306  lon 123.283~124.283

找到 2 個可用的 SWOT granule：

cycle=004 pass=381 v3.0  2023-10-05 09:38:53 ~ 10:30:19 UTC  命中點數=1557/680340
  /home/donnee/SWOT/v300_expert/cycle_004/SWOT_L3_LR_SSH_Expert_004_381_20231005T093853_20231005T103019_v3.0.nc
cycle=004 pass=450 v3.0  2023-10-07 20:48:43 ~ 21:40:10 UTC  命中點數=1690/680340
  /home/donnee/SWOT/v300_expert/cycle_004/SWOT_L3_LR_SSH_Expert_004_450_20231007T204843_20231007T214010_v3.0.nc
```

找不到符合條件的檔案時會直接說明，不會誤判為錯誤。

### 使用上的重要提醒

- **SWOT Science Phase 是 21 天重複軌道**，同一測站通常只有少數幾條固定 pass 會經過。若指定的時間區間太窄（例如只圈住測站部署當下 30 分鐘），很可能找不到剛好重疊的 overpass——這是正常現象，不是程式錯誤。建議先用較寬的時間範圍（例如測站部署日 ±10~15 天）找出實際經過測站的 pass，再回頭比對確切時間差。
- **部分 granule 可能整批資料缺漏**（`quality_flag=102 / no_data`），屬於 SWOT 資料本身偶發的傳輸/處理缺口，與搜尋工具無關。`visualize_station_swot.py` 已加入自動避開此類壞檔的邏輯。

## `visualize_station_swot.py` — 覆蓋圖 + SSHA 視覺化

```bash
python3 visualize_station_swot.py \
  --lat 21.8063 --lon 123.7828 --station-name TT1 \
  --start 2023-10-01T00:00:00 --end 2023-10-16T00:00:00 \
  --tz-offset 8 --pad 3.0 \
  --out-dir ~/swot_viz
```

輸出兩張圖到 `--out-dir`：
- `coverage_map.png`：測站位置 + 命中的 SWOT pass 軌跡疊圖
- `ssha_cycle<C>_pass<P>.png`：離目標時間最近、且有效資料點最多的 granule 的 SSHA 空間分布（已套用 `quality_flag<=3` 篩選，標出測站位置）

需要本機下載圖檔查看時（在 Mac 上，**非** ML01 連線中）：

```bash
scp "<user>@140.112.69.80:~/swot_viz/*.png" ./本機資料夾/
```
