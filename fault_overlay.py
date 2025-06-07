import geopandas as gpd
import matplotlib.pyplot as plt
import os
import pandas as pd
import numpy as np
from shapely.geometry import LineString, MultiLineString

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

# Identify proper attribute field
possible_fields = ["Fea_En", "NAME", "Type", "description"]
fault_field = next((f for f in possible_fields if f in faults_clipped.columns), None)
if not fault_field:
    raise ValueError("❌ Could not find a suitable fault description field.")

# Apply classification
faults_clipped["Fault_Type"] = faults_clipped[fault_field].apply(classify_fault)

# Ensure Vu_zscore exists
if "Vu_zscore" not in points.columns:
    points["Vu_zscore"] = (points["Vu1"] - points["Vu1"].mean()) / points["Vu1"].std()

# Identify main river
main_river_id = points.groupby("River_ID").size().idxmax()
main_river = points[points["River_ID"] == main_river_id].sort_values("Order").reset_index(drop=True)

# Detect anomalies
main_river["Anomaly"] = np.where(main_river["Vu_zscore"].abs() > 2, "Anomaly", "Normal")
critical_points = main_river[main_river["Anomaly"] == "Anomaly"]

# Output directory
output_dir = "figures/basin_1"
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, "faults_vu_overlay.png")

# Define fault colors
fault_colors = {
    "Reverse": "firebrick",
    "Normal": "cornflowerblue",
    "Left Lateral": "orange",
    "Right Lateral": "green",
    "Strike-Slip": "purple",
    "Other": "grey"
}

# Plot
fig, ax = plt.subplots(figsize=(12, 8))
basin.boundary.plot(ax=ax, color="black", linewidth=1)
points.plot(ax=ax, column="Vu_zscore", cmap="coolwarm", markersize=3, legend=True, vmin=-3, vmax=3)

# Faults by type
for ftype, color in fault_colors.items():
    subset = faults_clipped[faults_clipped["Fault_Type"] == ftype]
    if not subset.empty:
        subset.plot(ax=ax, linewidth=1.5, color=color, label=ftype)

# Dissolve main river and plot
main_river_line = main_river.unary_union
if isinstance(main_river_line, (LineString, MultiLineString)):
    gpd.GeoSeries([main_river_line], crs=points.crs).plot(ax=ax, color="#005f99", linewidth=2.5, label="Main River")

# Overlay anomaly points
critical_points.plot(ax=ax, color="black", markersize=20, label="Main River Anomalies")

# Final layout
ax.legend(title="Fault Type", loc="upper left")
plt.title("Basin 1: Fault Types, Main River and VU Anomalies")
plt.tight_layout()
plt.savefig(output_path, dpi=300)
plt.close()

print(f"✅ Overlay plot saved to: {output_path}")
