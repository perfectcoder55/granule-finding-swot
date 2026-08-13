#!/usr/bin/env python3
"""
視覺化：測站位置 + SWOT 軌跡覆蓋範圍 + 實際 SSHA 空間分布。

依賴 find_swot_granules.py 中的搜尋邏輯（需放在同一目錄或可 import 的路徑）。

用法範例（在 ML01 上執行，因為資料只在 ML01）：
  conda activate pyeddy
  python3 visualize_station_swot.py \
      --lat 21.8063 --lon 123.7828 --station-name TT1 \
      --start 2023-10-08T08:00:00 --end 2023-10-08T09:00:00 \
      --pad 3.0 --out-dir ~/swot_viz

輸出：
  <out-dir>/coverage_map.png        測站 + 搜尋範圍內找到的所有 pass 軌跡疊圖
  <out-dir>/ssha_<cycle>_<pass>.png 離目標時間最近的 granule 的 SSHA 空間分布圖（標出測站）
"""
import argparse
import os
import sys
from datetime import timedelta

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import colors
from netCDF4 import Dataset
import cartopy.crs as ccrs
import cartopy.feature as cfeature

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from find_swot_granules import find_time_candidates, check_spatial, norm360, parse_time  # noqa: E402


def count_valid_quality(fpath, lon_min_n, lon_max_n, lat_min, lat_max, quality_max=3):
    """回傳該檔案在指定範圍內、quality_flag <= quality_max 的有效點數。"""
    with Dataset(fpath) as ds:
        lat = np.ma.filled(ds.variables["latitude"][:].astype(float), np.nan)
        lon = np.ma.filled(ds.variables["longitude"][:].astype(float), np.nan)
        qflag = np.ma.filled(ds.variables["quality_flag"][:].astype(float), 255)
        lon_n = norm360(lon)
        lat_mask = (lat >= lat_min) & (lat <= lat_max)
        if lon_min_n <= lon_max_n:
            lon_mask = (lon_n >= lon_min_n) & (lon_n <= lon_max_n)
        else:
            lon_mask = (lon_n >= lon_min_n) | (lon_n <= lon_max_n)
        region = lat_mask & lon_mask
        return int(np.count_nonzero(region & (qflag <= quality_max)))


def read_latlon(fpath, thin=3):
    with Dataset(fpath) as ds:
        lat = np.ma.filled(ds.variables["latitude"][::thin, ::thin].astype(float), np.nan)
        lon = np.ma.filled(ds.variables["longitude"][::thin, ::thin].astype(float), np.nan)
    return lat, lon


def plot_coverage_map(station_lat, station_lon, station_name, results, lon_min, lon_max, lat_min, lat_max, out_path):
    fig = plt.figure(figsize=(8, 7))
    proj = ccrs.PlateCarree()
    ax = fig.add_subplot(1, 1, 1, projection=proj)
    ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=proj)
    ax.add_feature(cfeature.LAND, facecolor="lightgray", zorder=0)
    ax.add_feature(cfeature.COASTLINE, linewidth=0.7)
    gl = ax.gridlines(draw_labels=True, linestyle=":", linewidth=0.5, color="gray")
    gl.top_labels = False
    gl.right_labels = False

    cmap = plt.get_cmap("tab10")
    import matplotlib.lines as mlines

    legend_handles = []
    for i, r in enumerate(results):
        fpath, cycle, pas, fbeg, fend = r[0], r[1], r[2], r[3], r[4]
        lat, lon = read_latlon(fpath, thin=3)
        lon_shift = np.where(lon > 180, lon - 360, lon)
        color = cmap(i % 10)
        ax.scatter(lon_shift, lat, s=2, color=color, transform=proj)
        legend_handles.append(
            mlines.Line2D([], [], color=color, marker="o", linestyle="",
                          markersize=6, label=f"cycle{cycle} pass{pas} ({fbeg:%Y-%m-%d %H:%M})")
        )

    ax.plot(station_lon, station_lat, marker="*", markersize=16, markerfacecolor="yellow",
            markeredgecolor="k", zorder=200, transform=proj)
    legend_handles.append(
        mlines.Line2D([], [], color="none", marker="*", markersize=12,
                      markerfacecolor="yellow", markeredgecolor="k", label=station_name)
    )

    ax.set_title(f"SWOT coverage near {station_name} ({station_lat:.4f}N, {station_lon:.4f}E)", fontsize=12, weight="bold")
    ax.legend(handles=legend_handles, fontsize=7, loc="upper right")
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close(fig)
    print(f"已存: {out_path}")


def plot_ssha_field(fpath, cycle, pas, station_lat, station_lon, lon_min, lon_max, lat_min, lat_max, out_path, var="ssha_filtered"):
    with Dataset(fpath) as ds:
        lat = np.ma.filled(ds.variables["latitude"][:].astype(float), np.nan)
        lon = np.ma.filled(ds.variables["longitude"][:].astype(float), np.nan)
        ssha = np.ma.filled(ds.variables[var][:].astype(float), np.nan)
        qflag = np.ma.filled(ds.variables["quality_flag"][:].astype(float), 255)

    lon_shift = np.where(lon > 180, lon - 360, lon)
    region_mask = (
        (lat >= lat_min) & (lat <= lat_max) & (lon_shift >= lon_min) & (lon_shift <= lon_max)
    )
    good_mask = region_mask & (qflag <= 3) & np.isfinite(ssha)

    proj = ccrs.PlateCarree()
    fig = plt.figure(figsize=(7, 6))
    ax = fig.add_subplot(1, 1, 1, projection=proj)
    ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=proj)
    ax.add_feature(cfeature.LAND, facecolor="lightgray", zorder=100)
    ax.add_feature(cfeature.COASTLINE, linewidth=0.7, zorder=101)
    gl = ax.gridlines(draw_labels=True, linestyle=":", linewidth=0.5, color="gray")
    gl.top_labels = False
    gl.right_labels = False

    if not np.any(good_mask):
        ax.text(0.5, 0.5, "No valid (quality_flag<=3) SSHA points in region",
                ha="center", va="center", transform=ax.transAxes)
    else:
        vmax = np.nanpercentile(np.abs(ssha[good_mask]), 95)
        sc = ax.scatter(
            lon_shift[good_mask], lat[good_mask], c=ssha[good_mask], s=3,
            cmap="RdBu_r", norm=colors.Normalize(vmin=-vmax, vmax=vmax), transform=proj,
        )
        cbar = fig.colorbar(sc, ax=ax, label=f"{var} [m]")

    ax.plot(station_lon, station_lat, marker="*", markersize=16, markerfacecolor="yellow",
            markeredgecolor="k", zorder=200, transform=proj)
    ax.set_title(f"cycle{cycle} pass{pas}  {var}  (quality_flag<=3)", fontsize=11, weight="bold")
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close(fig)
    print(f"已存: {out_path}")


def main():
    ap = argparse.ArgumentParser(description="視覺化測站位置與 SWOT 覆蓋/SSHA")
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--tz-offset", type=float, default=0.0, help="輸入時間相對 UTC 的偏移(小時)，台灣當地時間填 8")
    ap.add_argument("--lat", type=float, required=True)
    ap.add_argument("--lon", type=float, required=True)
    ap.add_argument("--station-name", default="station")
    ap.add_argument("--radius", type=float, default=0.5, help="搜尋半徑(度)，決定哪些 granule 算命中")
    ap.add_argument("--pad", type=float, default=3.0, help="視覺化地圖的顯示範圍padding(度)，以測站為中心")
    ap.add_argument("--data-dir", default="/home/donnee/SWOT/v300_expert")
    ap.add_argument("--out-dir", default="./swot_viz")
    ap.add_argument("--var", default="ssha_filtered", choices=["ssha_filtered", "ssha_unfiltered", "ssha_unedited"])
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    tz_delta = timedelta(hours=args.tz_offset)
    from datetime import datetime
    t_start = datetime.fromisoformat(args.start) - tz_delta
    t_end = datetime.fromisoformat(args.end) - tz_delta
    t_mid = t_start + (t_end - t_start) / 2

    lat_min, lat_max = args.lat - args.radius, args.lat + args.radius
    lon_min, lon_max = args.lon - args.radius, args.lon + args.radius
    lon_min_n, lon_max_n = norm360(lon_min), norm360(lon_max)

    candidates = find_time_candidates(args.data_dir, t_start, t_end)
    print(f"[時間篩選] 候選檔案數: {len(candidates)}")

    results = []
    for fpath, cycle, pas, fbeg, fend, version in candidates:
        n_match, n_total = check_spatial(fpath, lon_min_n, lon_max_n, lat_min, lat_max)
        if n_match > 0:
            results.append((fpath, cycle, pas, fbeg, fend, version, n_match))

    print(f"[空間篩選] 命中檔案數: {len(results)}")
    if not results:
        print("找不到符合條件的檔案，無法視覺化。請放寬時間範圍或半徑。")
        return

    map_lon_min, map_lon_max = args.lon - args.pad, args.lon + args.pad
    map_lat_min, map_lat_max = args.lat - args.pad, args.lat + args.pad
    plot_coverage_map(
        args.lat, args.lon, args.station_name, results,
        map_lon_min, map_lon_max, map_lat_min, map_lat_max,
        os.path.join(args.out_dir, "coverage_map.png"),
    )

    scored = []
    for r in results:
        fpath, cycle, pas, fbeg, fend = r[0], r[1], r[2], r[3], r[4]
        n_valid = count_valid_quality(fpath, lon_min_n, lon_max_n, lat_min, lat_max)
        time_diff = abs((fbeg + (fend - fbeg) / 2 - t_mid).total_seconds())
        scored.append((n_valid, -time_diff, r))
        print(f"  候選 cycle={cycle} pass={pas} 有效點(quality<=3)={n_valid} 時間差={time_diff/3600:.1f}hr")

    # 優先挑有效資料點最多的 granule，同分則挑時間最接近的
    scored.sort(key=lambda t: (t[0], t[1]), reverse=True)
    n_valid_best, _, best = scored[0]
    fpath, cycle, pas = best[0], best[1], best[2]
    print(f"[選定 granule] cycle={cycle} pass={pas} 有效點={n_valid_best} -> {fpath}")
    if n_valid_best == 0:
        print("警告: 所有候選 granule 在此區域都沒有有效(quality_flag<=3)資料，SSHA 圖將會是空的")
    plot_ssha_field(
        fpath, cycle, pas, args.lat, args.lon,
        map_lon_min, map_lon_max, map_lat_min, map_lat_max,
        os.path.join(args.out_dir, f"ssha_cycle{cycle}_pass{pas}.png"),
        var=args.var,
    )


if __name__ == "__main__":
    main()
