import geopandas as gpd
import matplotlib.pyplot as plt
import os

# Load shapefile
shp_path = "rivers_overlap_basins/rivers_overlap_basin_1_interpolated_points_elevation_vu.shp"
gdf = gpd.read_file(shp_path)

# Filter invalid rows
gdf = gdf[gdf["Vu1"].notna()]
gdf = gdf[gdf["River_ID"].notna()]

# Create output folder
output_dir = "rivers_overlap_basins/basin_1_vu_zscore_maps"
os.makedirs(output_dir, exist_ok=True)

# Loop through each River_ID group
for river_id, group in gdf.groupby("River_ID"):
    if len(group) < 20:
        continue  # Skip short segments

    mean_vu = group["Vu1"].mean()
    std_vu = group["Vu1"].std()
    group["Vu_zscore"] = (group["Vu1"] - mean_vu) / std_vu

    # Plot
    fig, ax = plt.subplots(1, 1, figsize=(8, 5))
    group.plot(
        ax=ax,
        column="Vu_zscore",
        cmap="coolwarm",
        markersize=6,
        legend=True,
        legend_kwds={'label': "VU Z-score", 'shrink': 0.7}
    )
    ax.set_title(f"VU Z-score Anomaly Map - River ID {river_id}")
    ax.set_axis_off()
    plt.tight_layout()
    plt.savefig(f"{output_dir}/{river_id}_zscore_map.png", dpi=150)
    plt.close()

print("✅ VU z-score anomaly maps generated.")
