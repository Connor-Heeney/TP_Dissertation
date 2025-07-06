import os
import geopandas as gpd
from shapely.geometry import MultiLineString, LineString
from shapely.ops import unary_union
from tqdm import tqdm

# Path to input and output
input_streams = "DEM/outputs/streams_vectorized_final.shp"
output_cleaned = "DEM/outputs/streams_cleaned_final.shp"

# --- Load ---
print("🔄 Merging stream segments...")
gdf = gpd.read_file(input_streams)

# Fix CRS if missing
if gdf.crs is None:
    print("⚠️  CRS missing. Setting to EPSG:32646")
    gdf.set_crs(epsg=32646, inplace=True)

# Merge all geometries into a single MultiLineString
merged = unary_union(gdf.geometry)

# If merged is a LineString, convert to MultiLineString
if isinstance(merged, LineString):
    merged = MultiLineString([merged])

# Create a GeoDataFrame with individual LineStrings and assign IDs
print("🧩 Rebuilding stream segments...")
cleaned_segments = []
for i, segment in enumerate(tqdm(merged.geoms, desc="Assigning River_IDs")):
    cleaned_segments.append({"geometry": segment, "River_ID": i + 1})

cleaned_gdf = gpd.GeoDataFrame(cleaned_segments, crs=gdf.crs)

# Save to file
cleaned_gdf.to_file(output_cleaned)

print(f"\n✅ Cleaned stream network saved to: {output_cleaned}")
print(f"📏 Total segments: {len(cleaned_gdf)}")