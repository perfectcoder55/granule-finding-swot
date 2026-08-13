## 檔案
find_swot_granules.py：時間+空間搜尋，輸出可用檔案清單
需在 ML01 上執行，並先啟用 pyeddy 環境：

```bash
ssh <user>@id
conda activate pyeddy
```

find_swot_granules.py 用法：

  # 測站座標 + 半徑(度) 搜尋；--tz-offset 8 表示 --start/--end 是台灣當地時間
  python3 find_swot_granules.py \
      --start 2023-10-08T16:00:00 --end 2023-10-08T17:00:00 --tz-offset 8 \
      --lat 21.8063 --lon 123.7828 --radius 0.5

  # 經緯度範圍框搜尋（輸入時間已是 UTC，不需要 --tz-offset）
  python3 find_swot_granules.py \
      --start 2023-10-08T08:00:00 --end 2023-10-08T09:00:00 \
      --lon-min 122.0 --lon-max 125.0 --lat-min 20.0 --lat-max 23.0


