import os
from whitebox_workflows import WbEnvironment

# 1️⃣ Setup Whitebox Workflows Environment
wbe = WbEnvironment()
wbe.verbose = True
wbe.max_procs = -1  # Use all CPU cores by default

# Paths
input_dem = "DEM/outputs/COP30_VRT_DEM.tif"
output_dir = "DEM/outputs"
os.makedirs(output_dir, exist_ok=True)

# 2️⃣ Load DEM
dem = wbe.read_raster(input_dem)

# 3️⃣ Fill Depressions
# Breaching + filling is recommended, but we'll just fill for now
dem_filled = wbe.fill_depressions(dem)
filled_path = os.path.join(output_dir, "dem_filled.tif")
wbe.write_raster(dem_filled, filled_path)

# 4️⃣ Compute Slope (degrees)
dem_slope = wbe.slope(dem_filled, units="degrees")
slope_path = os.path.join(output_dir, "dem_slope.tif")
wbe.write_raster(dem_slope, slope_path)

# 5️⃣ Compute Aspect
dem_aspect = wbe.aspect(dem_filled)
aspect_path = os.path.join(output_dir, "dem_aspect.tif")
wbe.write_raster(dem_aspect, aspect_path)

# 6️⃣ Compute Multidirectional Hillshade
dem_hillshade = wbe.multidirectional_hillshade(dem_filled, full_360_mode=True)
hillshade_path = os.path.join(output_dir, "dem_hillshade.tif")
wbe.write_raster(dem_hillshade, hillshade_path)

# 7️⃣ Compute D8 Flow Direction (pointer)
flow_dir = wbe.d8_pointer(dem_filled)
fdir_path = os.path.join(output_dir, "dem_flowdir.tif")
wbe.write_raster(flow_dir, fdir_path)

# 8️⃣ Compute D8 Flow Accumulation
flow_acc = wbe.qin_flow_accumulation(dem_filled, out_type="cells")
flowacc_path = os.path.join(output_dir, "dem_flowacc.tif")
wbe.write_raster(flow_acc, flowacc_path)

print("✅ DEM hydrological processing completed using Whitebox Workflows.")
