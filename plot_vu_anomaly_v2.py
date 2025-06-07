import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
from shapely.geometry import Point
from scipy.signal import savgol_filter

# Load data
points_path = "rivers_overlap_basins/rivers_overlap_basin_1_interpolated_points_50_elevation_vu.shp"
basin_path = "hybas4_selected_subbasin_1.shp"
gdf = gpd.read_file(points_path)
basin = gpd.read_file(basin_path)

# Ensure CRS match
gdf = gdf.to_crs(basin.crs)

# Calculate z-score if not already present
if "Vu_zscore" not in gdf.columns:
    gdf["Vu_zscore"] = (gdf["Vu1"] - gdf["Vu1"].mean()) / gdf["Vu1"].std()

# Setup output folder
output_dir = "rivers_overlap_basins/basin_1_plots/basin_1_vu_zscore_maps"
os.makedirs(output_dir, exist_ok=True)

# Select main river by most points
main_river_id = gdf.groupby("River_ID").size().idxmax()
main_river = gdf[gdf["River_ID"] == main_river_id].sort_values("Order").reset_index(drop=True)

# Compute cumulative distance
coords = main_river.geometry.values
dists = [0]
for i in range(1, len(coords)):
    dists.append(dists[-1] + coords[i].distance(coords[i - 1]))
main_river["Distance_km"] = np.array(dists) / 1000

# Smooth elevation and VU using Savitzky-Golay
window = 21 if len(main_river) >= 21 else (len(main_river) // 2 * 2 + 1)
main_river["Elevation_smooth"] = savgol_filter(main_river["Elevation1"], window, 3)
main_river["Vu_smooth"] = savgol_filter(main_river["Vu1"], window, 3)

# Flag anomalous zones
main_river["Anomaly"] = np.where(np.abs(main_river["Vu_zscore"]) > 2, "Anomaly", "Normal")
critical_points = main_river[main_river["Anomaly"] == "Anomaly"]

# Plot annotated profile
fig, ax1 = plt.subplots(figsize=(10, 5))
ax1.plot(main_river["Distance_km"], main_river["Elevation_smooth"], color="blue", label="Elevation (m)")
ax1.set_xlabel("Distance (km)")
ax1.set_ylabel("Elevation (m)", color="blue")
ax1.tick_params(axis='y', labelcolor="blue")

ax2 = ax1.twinx()
ax2.plot(main_river["Distance_km"], main_river["Vu_smooth"], color="red", linestyle="dashed", label="VU (mm/year)")
ax2.scatter(critical_points["Distance_km"], critical_points["Vu_smooth"], color="black", s=20, label="VU Anomaly")
ax2.set_ylabel("VU (mm/year)", color="red")
ax2.tick_params(axis='y', labelcolor="red")

plt.title(f"Smoothed River Profile with Anomalies: River_{main_river_id}")
fig.legend(loc="lower right")
plt.tight_layout()
plt.savefig(os.path.join(output_dir, f"river_{main_river_id}_profile_annotated.png"))
plt.close()

# Plot spatial anomaly map with black points for anomalies
fig, ax = plt.subplots(figsize=(10, 6))
basin.boundary.plot(ax=ax, color='black', linewidth=1)
gdf.plot(ax=ax, column="Vu_zscore", cmap="coolwarm", vmin=-3, vmax=3, markersize=3, legend=True)
critical_points.plot(ax=ax, color='black', markersize=10, label="Main River Anomalies")

plt.title("VU Z-score Anomalies in Basin 1")
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(output_dir, "basin_1_zscore_map_with_anomalies.png"))
plt.close()
