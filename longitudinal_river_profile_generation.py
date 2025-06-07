import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# === Load CSV ===
csv_path = "rivers_overlap_basins/rivers_overlap_basin_1_interpolated_points_elevation_vu.csv"
df = pd.read_csv(csv_path)

# === Clean and prepare ===
df = df.dropna(subset=['River_ID', 'Order', 'Elevation1', 'Vu1'])
df['Order'] = df['Order'].astype(int)
df['River_ID'] = df['River_ID'].astype(str)

# === Output folder ===
output_dir = Path("rivers_overlap_basins/basin_1_plots")
output_dir.mkdir(parents=True, exist_ok=True)

# === Plot for each river ===
for river_id, group in df.groupby("River_ID"):
    group = group.sort_values("Order")
    
    fig, ax1 = plt.subplots(figsize=(10, 5))
    ax2 = ax1.twinx()

    ax1.plot(group["Order"], group["Elevation1"], color='tab:blue', label='Elevation (m)')
    ax2.plot(group["Order"], group["Vu1"], color='tab:red', linestyle='--', label='VU (mm/year)')

    ax1.set_xlabel("Stream Order")
    ax1.set_ylabel("Elevation (m)", color='tab:blue')
    ax2.set_ylabel("VU (mm/year)", color='tab:red')
    ax1.tick_params(axis='y', labelcolor='tab:blue')
    ax2.tick_params(axis='y', labelcolor='tab:red')

    plt.title(f"River Profile: {river_id}")
    fig.tight_layout()

    plot_path = output_dir / f"{river_id}_profile.png"
    plt.savefig(plot_path)
    plt.close(fig)

print("River profiles saved to:", output_dir)
