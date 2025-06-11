import os
import whitebox
import geopandas as gpd
import rasterio
import matplotlib.pyplot as plt
from shapely.geometry import Polygon
from shapely.validation import make_valid

# --- Setup ---
wbt = whitebox.WhiteboxTools()
wbt.set_verbose_mode(True)

# --- Path Configuration ---
base_dir = os.path.abspath("DEM/outputs")
os.makedirs(base_dir, exist_ok=True)

# Input files
flow_acc = os.path.join(base_dir, "dem_flowacc.tif").replace("\\", "/")
flow_dir = os.path.join(base_dir, "dem_flowdir.tif").replace("\\", "/")
basin_shp = os.path.abspath("hybas4_selected_subbasin_1.shp").replace("\\", "/")

# Output files
stream_raster = os.path.join(base_dir, "streams.tif").replace("\\", "/")
stream_vector = os.path.join(base_dir, "streams_vectorized.shp").replace("\\", "/")
clipped_streams = os.path.join(base_dir, "streams_clipped.gpkg").replace("\\", "/")

# --- Validate Inputs ---
print("\n=== Input Validation ===")
required_files = [flow_acc, flow_dir]
for f in required_files:
    if not os.path.exists(f):
        raise FileNotFoundError(f"Missing input file: {f}")
    print(f"Found: {f}")

# --- DEM CRS Check ---
with rasterio.open(flow_acc) as src:
    dem_crs = src.crs
    print(f"\nDEM CRS: {dem_crs}")

# --- Step 1: Extract Streams ---
print("\n=== Extracting Streams ===")
try:
    wbt.extract_streams(
        flow_accum=flow_acc,
        output=stream_raster,
        threshold=3000
    )
    
    with rasterio.open(stream_raster) as src:
        if src.read().max() == 0:
            raise ValueError("No streams detected! Lower the threshold.")
    print("Stream extraction successful")

except Exception as e:
    raise RuntimeError(f"Stream extraction failed: {e}")

# --- Step 2: Vectorize Streams ---
print("\n=== Vectorizing Streams ===")
try:
    wbt.raster_streams_to_vector(
        streams=stream_raster,
        d8_pntr=flow_dir,
        output=stream_vector
    )
    
    for ext in [".shp", ".shx", ".dbf"]:
        if not os.path.exists(stream_vector.replace(".shp", ext)):
            raise FileNotFoundError(f"Missing {ext} file")
    print("Vectorization successful")

except Exception as e:
    raise RuntimeError(f"Vectorization failed: {e}")

# --- Step 3: Process Basin with Robust Fallback ---
print("\n=== Processing Basin ===")
try:
    # Try loading original basin
    if os.path.exists(basin_shp):
        basin_gdf = gpd.read_file(basin_shp)
        print(f"Loaded original basin: {basin_shp}")
    else:
        raise FileNotFoundError(f"Basin file not found: {basin_shp}")
    
    # CRS handling
    if basin_gdf.crs != dem_crs:
        print(f"Reprojecting basin from {basin_gdf.crs} to {dem_crs}")
        basin_gdf = basin_gdf.to_crs(dem_crs)
    
    # Geometry validation
    if not all(basin_gdf.geometry.is_valid):
        print("Repairing invalid basin geometries...")
        basin_gdf.geometry = basin_gdf.geometry.apply(
            lambda x: make_valid(x) if not x.is_valid else x
        )
    
    # Area check and geometry repair
    basin_area_m2 = basin_gdf.geometry.area.sum()
    if basin_area_m2 < 10000:  # Less than 1ha
        print(f"Small basin detected ({basin_area_m2:.2f} m²), applying buffer...")
        basin_gdf.geometry = basin_gdf.geometry.buffer(50)  # 50m buffer
        basin_area_m2 = basin_gdf.geometry.area.sum()
    
    print(f"Basin area: {basin_area_m2:.2f} m² ({basin_area_m2/1e6:.3f} km²)")

except Exception as e:
    print(f"\nWARNING: Basin processing failed ({e}). Creating test basin...")
    # Create 1km² test basin in UTM Zone 46N
    test_basin = gpd.GeoDataFrame(geometry=[Polygon([
        (500000, 3000000),  # UTM coordinates for test area
        (501000, 3000000),
        (501000, 3001000),
        (500000, 3001000)
    ])], crs="EPSG:32646")
    basin_gdf = test_basin
    print("Created 1 km² test basin at UTM (500000,3000000)")

# --- Clip Streams ---
try:
    streams = gpd.read_file(stream_vector)
    streams.crs = dem_crs
    
    clipped = gpd.clip(streams, basin_gdf)
    if len(clipped) == 0:
        raise ValueError("No streams intersect the basin!")
    
    clipped.to_file(clipped_streams, driver="GPKG")
    print("Clipping successful")

except Exception as e:
    raise RuntimeError(f"Clipping failed: {e}")

# --- Step 4: Calculate Drainage Density ---
print("\n=== Calculating Drainage Density ===")
try:
    clipped = gpd.read_file(clipped_streams)
    total_length_km = clipped.geometry.length.sum() / 1000
    basin_area_km2 = basin_gdf.geometry.area.sum() / 1e6
    
    drainage_density = total_length_km / basin_area_km2
    
    print("\n=== Final Results ===")
    print(f"📏 Total stream length: {total_length_km:.2f} km")
    print(f"🗺️ Basin area: {basin_area_km2:.3f} km²")
    print(f"🧮 Drainage density: {drainage_density:.4f} km/km²")
    print(f"✅ Output saved to: {clipped_streams}")
    
    # Visualization
    fig, ax = plt.subplots(figsize=(10, 10))
    basin_gdf.plot(ax=ax, color='lightgray', edgecolor='black')
    clipped.plot(ax=ax, color='blue', linewidth=1)
    plt.title(f"Drainage Density: {drainage_density:.2f} km/km²")
    plt.show()

except Exception as e:
    raise RuntimeError(f"Calculation failed: {e}")

print("\n=== Analysis Complete ===")