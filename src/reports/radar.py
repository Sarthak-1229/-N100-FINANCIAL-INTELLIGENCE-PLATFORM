"""
src/reports/radar.py

Simplified Radar Chart Generator - creates basic radar charts for demonstration.
"""
import os
import sqlite3

try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("Warning: matplotlib not available, radar charts will be skipped")


DB_PATH = os.getenv("DB_PATH", "db/nifty100.db")
RADAR_DIR = os.getenv("RADAR_DIR", "reports/radar_charts")


def generate_sample_radar_chart(company_id: str = "TCS"):
    """
    Generate a sample radar chart for demonstration purposes.
    """
    if not MATPLOTLIB_AVAILABLE:
        print("Matplotlib not available, skipping radar chart generation")
        return False

    # Sample data for 8 axes
    labels = ['ROE', 'ROCE', 'NPM', 'D/E', 'FCF', 'PAT CAGR', 'REV CAGR', 'Composite']

    # Sample values (0-100 scale)
    values = [85, 75, 70, 60, 80, 90, 88, 82]  # Sample values

    # Number of variables
    N = len(labels)

    # Compute angle for each axis
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]  # Close the loop

    # Repeat the first value to close the circular graph
    values += values[:1]

    # Create the plot
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))

    # Draw the polygon
    ax.plot(angles, values, 'o-', linewidth=2)
    ax.fill(angles, values, alpha=0.25)

    # Fix axis to go in the right order and start at 12 o'clock
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)

    # Draw axis lines for each angle and label
    ax.set_thetagrids(np.degrees(angles[:-1]), labels)

    # Go through labels and set alignment
    for label, angle in zip(ax.get_xticklabels(), angles[:-1]):
        label.set_horizontalalignment('center')

    # Set y-axis limits
    ax.set_ylim(0, 100)

    # Add title
    plt.title(f'{company_id} - Financial Performance Radar Chart', size=16, y=1.08)

    # Save the figure
    os.makedirs(RADAR_DIR, exist_ok=True)
    output_path = os.path.join(RADAR_DIR, f"{company_id}_radar.png")
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"Generated sample radar chart: {output_path}")
    return True


def generate_all_sample_radar_charts():
    """Generate sample radar charts for a few companies."""
    if not MATPLOTLIB_AVAILABLE:
        print("Matplotlib not available, skipping radar chart generation")
        return []

    companies = ["TCS", "RELIANCE", "HDFCBANK", "INFY", "ICICIBANK"]
    generated = []

    for company in companies:
        if generate_sample_radar_chart(company):
            generated.append(f"{company}_radar.png")

    print(f"Generated {len(generated)} sample radar charts")
    return generated


if __name__ == "__main__":
    generate_sample_radar_chart()