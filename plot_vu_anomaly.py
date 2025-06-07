import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
import os

# Paths
points_fp = "rivers_overlap_basins/rivers_overlap_basin_1_interpolated_points_50_elevation_vu.shp"
basin_fp = "hybas4_selected_subbasin_1.shp"

# Load data
points_gdf = gpd.read_file(points_fp)
basin_gdf = gpd.read_file(basin_fp)

# Fix any invalid geometries in basin
basin_gdf["geometry"] = basin_gdf["geometry"].buffer(0)

# Match CRS
points_gdf = points_gdf.to_crs(basin_gdf.crs)

# Clip points
clipped_points = gpd.clip(points_gdf, basin_gdf)

# Calculate Vu z-score
vu_mean = clipped_points["Vu1"].mean()
vu_std = clipped_points["Vu1"].std()
clipped_points["Vu_zscore"] = (clipped_points["Vu1"] - vu_mean) / vu_std

# Plot
fig, ax = plt.subplots(figsize=(10, 6))
norm = Normalize(vmin=-3, vmax=3)

clipped_points.plot(
    ax=ax,
    column="Vu_zscore",
    cmap="coolwarm",
    markersize=5,
    legend=True,
    norm=norm
)

basin_gdf.boundary.plot(ax=ax, edgecolor='black')
ax.set_title("VU Z-score Anomalies in Basin 1")
ax.set_axis_off()
plt.tight_layout()
plt.savefig("rivers_overlap_basins/basin_1_vu_zscore_map.png", dpi=300)
plt.show()

