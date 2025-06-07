import geopandas as gpd
import matplotlib.pyplot as plt
import os
import pandas as pd

# File paths
faults_path = "faults/faults_singlepart.shp"
basin_path = "hybas4_selected_subbasin_1.shp"
points_path = "rivers_overlap_basins/rivers_overlap_basin_1_interpolated_points_50_elevation_vu.shp"

# Load datasets
faults = gpd.read_file(faults_path)
basin = gpd.read_file(basin_path).explode(index_parts=False)
points = gpd.read_file(points_path)

# Ensure consistent CRS
faults = faults.to_crs(basin.crs)
points = points.to_crs(basin.crs)

# Clip faults to basin extent
faults_clipped = gpd.clip(faults, basin)

# Classify faults (basic parser from attribute)
def classify_fault(text):
    text = str(text).lower()
    if "reverse" in text:
        return "Reverse"
    elif "normal" in text:
        return "Normal"
    elif "left" in text:
        return "Left Lateral"
    elif "right" in text:
        return "Right Lateral"
    elif "strike" in text:
        return "Strike-Slip"
    else:
        return "Other"

# Apply classification based on 'Fea_En' or fallback field
fault_field = "Fea_En" if "Fea_En" in faults_clipped.columns else faults_clipped.columns[0]
faults_clipped["Fault_Type"] = faults_clipped[fault_field].apply(classify_fault)

# Ensure Vu_zscore exists
if "Vu_zscore" not in points.columns:
    points["Vu_zscore"] = (points["Vu1"] - points["Vu1"].mean()) / points["Vu1"].std()

# Plot
fig, ax = plt.subplots(figsize=(12, 8))
basin.boundary.plot(ax=ax, color="black", linewidth=1)
points.plot(ax=ax, column="Vu_zscore", cmap="coolwarm", markersize=3, legend=True, vmin=-3, vmax=3)
faults_clipped.plot(ax=ax, column="Fault_Type", legend=True, linewidth=1.2)

plt.title("Basin 1: Fault Types and Vertical Velocity Anomalies")
plt.tight_layout()

# Save output
output_path = "basin1_faults_vu_overlay.png"
plt.savefig(output_path, dpi=300)
plt.close()

print(f"✅ Overlay plot saved to: {output_path}")