import geopandas as gpd
import pandas as pd
import numpy as np
from tqdm import tqdm
import networkx as nx
from shapely.geometry import Point
from collections import defaultdict
import gc

# Paths
streams_path = "DEM/outputs/streams_cleaned_final.shp"
basin_paths = [
    "D:/Dissertation/Core/hybas4_selected_subbasin_1.shp",
    "D:/Dissertation/Core/hybas4_selected_subbasin_2.shp", 
    "D:/Dissertation/Core/hybas4_selected_subbasin_3.shp",
    "D:/Dissertation/Core/hybas4_selected_subbasin_4.shp"
]
output_path = "DEM/outputs/streams_reconstructed_topo.shp"

def load_basin_data(basin_paths):
    """Load and combine all basin shapefiles"""
    print("Loading basin data...")
    
    basins = []
    for i, path in enumerate(basin_paths, 1):
        try:
            basin = gpd.read_file(path)
            basin['basin_group'] = i
            basins.append(basin)
            print(f"Loaded basin {i}: {len(basin)} features")
        except Exception as e:
            print(f"Warning: Could not load {path}: {e}")
    
    if basins:
        combined_basins = pd.concat(basins, ignore_index=True)
        print(f"Total basins loaded: {len(combined_basins)}")
        return combined_basins
    else:
        raise ValueError("No basin files could be loaded")

def fast_extract_endpoints(geometries, precision=6):
    """Ultra-fast coordinate extraction using vectorized operations"""
    print("Fast coordinate extraction...")
    
    # Get all coordinates as a single array
    coords_df = geometries.get_coordinates()
    
    # Group by geometry index
    grouped = coords_df.groupby(level=0)
    
    start_coords = []
    end_coords = []
    
    print("Processing coordinate groups...")
    for geom_idx in tqdm(range(len(geometries)), desc="Extracting endpoints"):
        if geom_idx in grouped.groups:
            coords = grouped.get_group(geom_idx).values
            start = coords[0]
            end = coords[-1]
            
            # Round coordinates
            start_rounded = (round(start[0], precision), round(start[1], precision))
            end_rounded = (round(end[0], precision), round(end[1], precision))
            
            start_coords.append(start_rounded)
            end_coords.append(end_rounded)
        else:
            # Handle missing geometry
            start_coords.append((0, 0))
            end_coords.append((0, 0))
    
    return start_coords, end_coords

def process_basin_chunk(basin_streams, starting_river_id):
    """Process a single basin efficiently"""
    
    if len(basin_streams) == 0:
        return basin_streams
    
    print(f"Processing basin with {len(basin_streams)} segments...")
    
    # Reset index
    basin_streams = basin_streams.reset_index(drop=True)
    
    # Fast coordinate extraction
    start_coords, end_coords = fast_extract_endpoints(basin_streams.geometry)
    
    # Calculate lengths
    print("Calculating lengths...")
    lengths = basin_streams.geometry.length.values
    
    # Build simple connectivity using dictionary
    print("Building connectivity...")
    coord_to_segments = defaultdict(list)
    
    for i in tqdm(range(len(basin_streams)), desc="Building coord map"):
        start = start_coords[i]
        end = end_coords[i]
        coord_to_segments[start].append(i)
        coord_to_segments[end].append(i)
    
    # Use Union-Find for connected components
    print("Finding connected components...")
    parent = list(range(len(basin_streams)))
    
    def find(x):
        root = x
        while parent[root] != root:
            root = parent[root]
        # Path compression
        while parent[x] != x:
            next_x = parent[x]
            parent[x] = root
            x = next_x
        return root
    
    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py
    
    # Connect segments
    for coord, segments in tqdm(coord_to_segments.items(), desc="Connecting segments"):
        if len(segments) > 1:
            for i in range(1, len(segments)):
                union(segments[0], segments[i])
    
    # Assign river IDs
    print("Assigning river IDs...")
    river_id_map = {}
    current_id = starting_river_id
    river_ids = np.zeros(len(basin_streams), dtype=int)
    
    for i in range(len(basin_streams)):
        root = find(i)
        if root not in river_id_map:
            river_id_map[root] = current_id
            current_id += 1
        river_ids[i] = river_id_map[root]
    
    # Simple cumulative distance calculation
    print("Calculating cumulative distances...")
    cumulative_distances = np.zeros(len(basin_streams))
    
    # Group by river ID
    for river_id in np.unique(river_ids):
        if river_id == 0:
            continue
            
        river_mask = river_ids == river_id
        river_indices = np.where(river_mask)[0]
        
        if len(river_indices) == 1:
            cumulative_distances[river_indices[0]] = lengths[river_indices[0]]
        else:
            # Simple cumulative sum approach
            river_lengths = lengths[river_indices]
            cumulative_sum = np.cumsum(river_lengths)
            cumulative_distances[river_indices] = cumulative_sum
    
    # Add results to dataframe
    basin_streams['River_ID'] = river_ids
    basin_streams['cumulative_distance'] = cumulative_distances
    basin_streams['length'] = lengths
    
    return basin_streams, current_id

def main():
    print("=== Fast Basin-Based Stream Network Analysis ===")
    
    # Load streams
    print("\n1. Loading stream segments...")
    streams_gdf = gpd.read_file(streams_path)
    streams_gdf = streams_gdf[streams_gdf.geometry.type == "LineString"].copy()
    streams_gdf = streams_gdf.reset_index(drop=True)
    print(f"Loaded {len(streams_gdf)} stream segments")
    
    # Load basins
    print("\n2. Loading basin data...")
    basins_gdf = load_basin_data(basin_paths)
    
    # Assign streams to basins
    print("\n3. Assigning streams to basins...")
    if streams_gdf.crs != basins_gdf.crs:
        print(f"Reprojecting basins from {basins_gdf.crs} to {streams_gdf.crs}")
        basins_gdf = basins_gdf.to_crs(streams_gdf.crs)
    
    print("Performing spatial join...")
    streams_with_basins = gpd.sjoin(streams_gdf, basins_gdf, how='left', predicate='intersects')
    
    # Handle streams without basins
    no_basin_count = streams_with_basins['basin_group'].isna().sum()
    if no_basin_count > 0:
        print(f"Warning: {no_basin_count} streams don't intersect any basin")
        streams_with_basins['basin_group'] = streams_with_basins['basin_group'].fillna(0)
    
    # Basin summary
    print(f"\nBasin assignment summary:")
    basin_summary = streams_with_basins.groupby('basin_group').size()
    for basin_id, count in basin_summary.items():
        print(f"  Basin {basin_id}: {count} stream segments")
    
    # Process each basin
    print("\n4. Processing basins...")
    all_results = []
    current_river_id = 1
    
    basin_groups = streams_with_basins.groupby('basin_group')
    
    for basin_id, basin_streams in basin_groups:
        print(f"\n--- Processing Basin {basin_id} ---")
        
        if len(basin_streams) == 0:
            continue
        
        # Process this basin
        basin_result, next_river_id = process_basin_chunk(basin_streams.copy(), current_river_id)
        current_river_id = next_river_id
        
        all_results.append(basin_result)
        
        print(f"Basin {basin_id} complete: {basin_result['River_ID'].nunique()} river networks")
        
        # Memory cleanup
        del basin_result
        gc.collect()
    
    # Combine results
    print("\n5. Combining results...")
    final_streams = pd.concat(all_results, ignore_index=True)
    
    # Summary
    print("\n=== RESULTS SUMMARY ===")
    print(f"Total stream segments: {len(final_streams)}")
    print(f"Total river networks: {final_streams['River_ID'].nunique()}")
    print(f"Average segments per river: {len(final_streams) / final_streams['River_ID'].nunique():.2f}")
    print(f"Max cumulative distance: {final_streams['cumulative_distance'].max():.2f}")
    print(f"Segments with distance > 0: {(final_streams['cumulative_distance'] > 0).sum()}")
    
    # Basin summary
    print(f"\nRiver networks per basin:")
    basin_river_summary = final_streams.groupby('basin_group')['River_ID'].nunique()
    for basin_id, river_count in basin_river_summary.items():
        print(f"  Basin {basin_id}: {river_count} river networks")
    
    # Save results
    print(f"\n6. Saving results to {output_path}")
    columns_to_keep = ['geometry', 'River_ID', 'cumulative_distance', 'length', 'basin_group']
    available_columns = [col for col in columns_to_keep if col in final_streams.columns]
    final_streams[available_columns].to_file(output_path)
    
    # Sample results
    print("\nSample results:")
    sample_cols = ['River_ID', 'basin_group', 'length', 'cumulative_distance']
    available_sample_cols = [col for col in sample_cols if col in final_streams.columns]
    print(final_streams[available_sample_cols].head(10))
    
    print("\n=== COMPLETE ===")

if __name__ == "__main__":
    main()