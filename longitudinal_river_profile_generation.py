import geopandas as gpd
import matplotlib.pyplot as plt
import os
from tqdm import tqdm
import numpy as np

# Load shapefile
shp_path = "rivers_overlap_basins/rivers_overlap_basin_1_interpolated_points_elevation_vu.shp"
gdf = gpd.read_file(shp_path)

# Ensure required columns are present
required_cols = ["River_ID", "Order", "Elevation1", "Vu1"]
missing = [col for col in required_cols if col not in gdf.columns]
if missing:
    raise ValueError(f"Missing columns: {missing}")

# Sort and compute cumulative distance
def compute_cumulative_distance(coords):
    dists = [0]
    for i in range(1, len(coords)):
        dist = coords[i].distance(coords[i - 1])
        dists.append(dists[-1] + dist)
    return dists

def compute_profiles(gdf):
    plots_folder = "rivers_overlap_basins/basin_1_plots"
    os.makedirs(plots_folder, exist_ok=True)

    for river_id, group in tqdm(gdf.groupby("River_ID"), desc="Generating river profiles"):
        if len(group) < 20:
            continue

        group_sorted = group.sort_values("Order").reset_index(drop=True)
        coords = group_sorted.geometry
        dists = compute_cumulative_distance(coords)
        group_sorted["Distance_km"] = np.array(dists) / 1000  # convert m to km

        # Apply rolling smoothing
        window = 11 if len(group_sorted) >= 11 else max(3, len(group_sorted) // 2 * 2 + 1)
        group_sorted["Elevation_smooth"] = group_sorted["Elevation1"].rolling(window, center=True).mean()
        group_sorted["Vu_smooth"] = group_sorted["Vu1"].rolling(window, center=True).mean()

        # Plot
        fig, ax1 = plt.subplots(figsize=(10, 5))
        ax1.plot(group_sorted["Distance_km"], group_sorted["Elevation_smooth"], color="blue", label="Elevation (m)")
        ax1.set_xlabel("Distance (km)")
        ax1.set_ylabel("Elevation (m)", color="blue")
        ax1.tick_params(axis='y', labelcolor="blue")

        ax2 = ax1.twinx()
        ax2.plot(group_sorted["Distance_km"], group_sorted["Vu_smooth"], color="red", linestyle="dashed", label="VU (mm/year)")
        ax2.set_ylabel("VU (mm/year)", color="red")
        ax2.tick_params(axis='y', labelcolor="red")

        plt.title(f"Smoothed River Profile: {river_id}")
        plt.tight_layout()
        plt.savefig(f"{plots_folder}/{river_id}_profile.png")
        plt.close()

compute_profiles(gdf)
print("✅ Smoothed longitudinal profiles generated from shapefile.")

