import geopandas as gpd
import pandas as pd
import numpy as np
import os

# Load shapefile
shp_path = "rivers_overlap_basins/rivers_overlap_basin_1_interpolated_points_50_elevation_vu.shp"
gdf = gpd.read_file(shp_path)

# Check columns
required_cols = ["River_ID", "Order", "Elevation1", "Vu1"]
for col in required_cols:
    if col not in gdf.columns:
        raise ValueError(f"Missing required column: {col}")

# Compute cumulative distance per river
def compute_cumulative_distance(coords):
    dists = [0]
    for i in range(1, len(coords)):
        dist = coords[i].distance(coords[i - 1])
        dists.append(dists[-1] + dist)
    return dists

summary_rows = []

for river_id, group in gdf.groupby("River_ID"):
    if len(group) < 20:
        continue

    group_sorted = group.sort_values("Order").reset_index(drop=True)
    coords = group_sorted.geometry
    distances = compute_cumulative_distance(coords)
    group_sorted["Distance_m"] = distances

    river_length_km = distances[-1] / 1000 if distances else 0
    elev = group_sorted["Elevation1"]
    vu = group_sorted["Vu1"]

    summary_rows.append({
        "River_ID": river_id,
        "Num_Points": len(group_sorted),
        "River_Length_km": round(river_length_km, 2),
        "Elevation_Min": elev.min(),
        "Elevation_Max": elev.max(),
        "Elevation_Change": elev.max() - elev.min(),
        "Elevation_Mean": elev.mean(),
        "VU_Min": vu.min(),
        "VU_Max": vu.max(),
        "VU_Mean": vu.mean(),
        "VU_Std": vu.std(),
        "VU_Range": vu.max() - vu.min(),
        "VU_Anomalies": ((vu < -2) | (vu > 2)).sum()  # Count outliers
    })

# Convert to DataFrame and export
summary_df = pd.DataFrame(summary_rows)
output_path = "rivers_overlap_basins/basin_1_summary.csv"
summary_df.to_csv(output_path, index=False)

print(f"✅ Summary table saved to {output_path}")
