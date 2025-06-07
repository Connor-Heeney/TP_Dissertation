import pandas as pd
import networkx as nx
from tqdm import tqdm
import os

# Load your river CSV file (update the path as needed)
df = pd.read_csv("Rivers.csv")

# Ensure required columns exist
assert 'HYRIV_ID' in df.columns, "Missing HYRIV_ID"
assert 'NEXT_DOWN' in df.columns, "Missing NEXT_DOWN"

# Create a directed graph of the river network
G = nx.DiGraph()

# Add edges to graph
edges = [(row['HYRIV_ID'], row['NEXT_DOWN']) for _, row in df.iterrows()
         if row['NEXT_DOWN'] != 0 and not pd.isnull(row['NEXT_DOWN'])]
G.add_edges_from(edges)

# Identify source nodes (no upstream)
sources = [n for n in G.nodes if G.in_degree(n) == 0]

# Prepare to store results
river_id_map = []
chunk_size = 200  # adjust as needed
output_path = "Rivers_with_RiverID.csv"

# Process in chunks
for start in tqdm(range(0, len(sources), chunk_size), desc="Processing in chunks"):
    end = min(start + chunk_size, len(sources))
    for i, source in enumerate(sources[start:end], start=start):
        river_id = f"River_{i+1}"
        try:
            for path in nx.single_source_shortest_path(G, source).values():
                for order, segment in enumerate(path):
                    river_id_map.append({
                        'HYRIV_ID': segment,
                        'River_ID': river_id,
                        'Order': order
                    })
        except Exception as e:
            print(f"Error processing source {source}: {e}")

    # Save intermediate results every chunk
    partial_df = pd.DataFrame(river_id_map)
    partial_df.drop_duplicates(subset=['HYRIV_ID'], inplace=True)
    partial_df.to_csv("temp_RiverID_partial.csv", index=False)

# Final merge
river_df = pd.read_csv("temp_RiverID_partial.csv")
df = df.merge(river_df, on='HYRIV_ID', how='left')
df.to_csv(output_path, index=False)

print(f"Saved full river table with River_ID to {output_path}")
if os.path.exists("temp_RiverID_partial.csv"):
    os.remove("temp_RiverID_partial.csv")