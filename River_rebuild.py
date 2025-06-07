import pandas as pd
import networkx as nx
from tqdm import tqdm
import os

# Load river CSV file
df = pd.read_csv("Rivers.csv")
assert 'HYRIV_ID' in df.columns, "Missing HYRIV_ID"
assert 'NEXT_DOWN' in df.columns, "Missing NEXT_DOWN"

# Build directed river network graph
G = nx.DiGraph()
edges = [(row['HYRIV_ID'], row['NEXT_DOWN']) for _, row in df.iterrows()
         if row['NEXT_DOWN'] != 0 and not pd.isnull(row['NEXT_DOWN'])]
G.add_edges_from(edges)

# Identify all source nodes
all_sources = [n for n in G.nodes if G.in_degree(n) == 0]

# Check for existing progress
processed_ids = set()
if os.path.exists("temp_RiverID_partial.csv"):
    processed_df = pd.read_csv("temp_RiverID_partial.csv")
    processed_ids = set(processed_df['HYRIV_ID'])

# Only process sources not already handled
sources_to_process = [s for s in all_sources if s not in processed_ids]

# Initialize output list
river_id_map = []
chunk_size = 200

# Process in chunks using BFS (faster and memory-safe)
for start in tqdm(range(0, len(sources_to_process), chunk_size), desc="Processing in chunks"):
    end = min(start + chunk_size, len(sources_to_process))
    chunk = sources_to_process[start:end]

    for i, source in enumerate(chunk, start=start):
        river_id = f"River_{i+1}"
        visited = set()
        queue = [(source, 0)]

        while queue:
            node, order = queue.pop(0)
            if node not in visited:
                visited.add(node)
                river_id_map.append({
                    'HYRIV_ID': node,
                    'River_ID': river_id,
                    'Order': order
                })
                for neighbor in G.successors(node):
                    queue.append((neighbor, order + 1))

    # Save to file incrementally
    partial_df = pd.DataFrame(river_id_map)
    partial_df.drop_duplicates(subset=['HYRIV_ID'], inplace=True)
    if not os.path.exists("temp_RiverID_partial.csv"):
        partial_df.to_csv("temp_RiverID_partial.csv", index=False, mode='w')
    else:
        partial_df.to_csv("temp_RiverID_partial.csv", index=False, mode='a', header=False)
    river_id_map.clear()  # reset for next chunk

# Merge full result
final_df = pd.read_csv("temp_RiverID_partial.csv")
df = df.merge(final_df, on='HYRIV_ID', how='left')
df.to_csv("Rivers_with_RiverID.csv", index=False)

# Clean up temp file
os.remove("temp_RiverID_partial.csv")

print("River ID assignment complete. Output saved to 'Rivers_with_RiverID.csv'")