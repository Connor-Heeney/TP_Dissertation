import geopandas as gpd
import matplotlib.pyplot as plt
import os
from tqdm import tqdm
from pyproj import Geod
import pandas as pd

# Load shapefile
shapefile_path = "rivers_overlap_basins/rivers_overlap_basin_1_interpolated_points_elevation_vu.shp"
gdf = gpd.read_file(shapefile_path)

# Ensure required columns
required_cols = ["River_ID", "Order", "Elevation1", "Vu1"]
missing = [col for col in required_cols if col not in gdf.columns]
if missing:
    raise ValueError(f"Missing columns: {missing}")

# Create geodesic calculator
geod = Geod(ellps="WGS84")

# Folder to save plots
plots_folder = "rivers_overlap_basins/basin_1_plots"
os.makedirs(plots_folder, exist_ok=True)

def compute_cumulative_distance(group):
    distances = [0]
    coords = list(group.geometry.apply(lambda p: (p.x, p.y)))
    for i in range(1, len(coords)):
        lon1, lat1 = coords[i - 1]
        lon2, lat2 = coords[i]
        _, _, d = geod.inv(lon1, lat1, lon2, lat2)
        distances.append(distances[-1] + d / 1000.0)  # in km
    return distances

def compute_profiles(gdf):
    for river_id, group in tqdm(gdf.groupby("River_ID"), desc="Generating river profiles"):
        if len(group) < 20:
            continue

        group_sorted = group.sort_values("Order").reset_index(drop=True)
        group_sorted = group_sorted.dropna(subset=["Elevation1", "Vu1"])

        if len(group_sorted) < 10:
            continue

        # Compute distance
        group_sorted["Distance_km"] = compute_cumulative_distance(group_sorted)

        # Smoothing window
        window = max(5, len(group_sorted) // 20)
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

