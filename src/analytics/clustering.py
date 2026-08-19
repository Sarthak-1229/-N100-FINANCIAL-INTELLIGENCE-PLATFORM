"""
src/analytics/clustering.py
KMeans Clustering (Day 36)
Implements KMeans clustering with 5 clusters for company archetypes
"""

import pandas as pd
import numpy as np
import sqlite3
import os
import json
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt

# Ensure output directories exist
os.makedirs("output", exist_ok=True)
os.makedirs("reports", exist_ok=True)

def get_clustering_data():
    """
    Get data for clustering: return_on_equity_pct, debt_to_equity, revenue_cagr_5yr,
    free_cash_flow_cr, operating_profit_margin_pct for latest year
    Returns DataFrame with company_id and features
    """
    conn = sqlite3.connect("db/nifty100.db")

    # Get latest financial ratios data
    query = """
    SELECT
        fr.company_id,
        fr.return_on_equity_pct,
        fr.debt_to_equity,
        fr.revenue_cagr_5yr,
        fr.free_cash_flow_cr,
        fr.operating_profit_margin_pct
    FROM financial_ratios fr
    INNER JOIN (
        SELECT company_id, MAX(year) as max_year
        FROM financial_ratios
        GROUP BY company_id
    ) grouped ON fr.company_id = grouped.company_id AND fr.year = grouped.max_year
    """

    df = pd.read_sql(query, conn)
    conn.close()
    return df

def impute_missing_with_sector_median(df):
    """
    Impute missing values with sector median for each metric
    Returns DataFrame with imputed values
    """
    conn = sqlite3.connect("db/nifty100.db")

    # Get sector data
    sectors_df = pd.read_sql("SELECT company_id, broad_sector FROM sectors", conn)
    conn.close()

    # Merge sector data with features
    df_with_sector = df.merge(sectors_df, on="company_id", how="left")

    # Features to impute
    feature_cols = ['return_on_equity_pct', 'debt_to_equity', 'revenue_cagr_5yr',
                   'free_cash_flow_cr', 'operating_profit_margin_pct']

    # Impute missing values with sector median for each feature
    for col in feature_cols:
        if df_with_sector[col].isnull().any():
            # Compute sector medians
            sector_medians = df_with_sector.groupby('broad_sector')[col].median()

            # Fill missing values with sector median
            def fill_with_sector_median(row):
                if pd.isna(row[col]):
                    return sector_medians.get(row['broad_sector'], df_with_sector[col].median())
                else:
                    return row[col]

            df_with_sector[col] = df_with_sector.apply(fill_with_sector_median, axis=1)

    # Drop sector column and return
    df_imputed = df_with_sector.drop('broad_sector', axis=1)
    return df_imputed

def scale_features(df):
    """
    Apply StandardScaler to normalize all features to zero mean and unit variance
    Returns scaled features array and scaler object
    """
    # Exclude company_id for scaling
    feature_cols = ['return_on_equity_pct', 'debt_to_equity', 'revenue_cagr_5yr',
                   'free_cash_flow_cr', 'operating_profit_margin_pct']

    # Extract features
    X = df[feature_cols].values

    # Apply StandardScaler
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    return X_scaled, scaler

def perform_kmeans_clustering(X_scaled, n_clusters=5, random_state=42):
    """
    Run KMeans with n_clusters=5, random_state=42
    Returns KMeans model and cluster labels
    """
    kmeans = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10)
    cluster_labels = kmeans.fit_predict(X_scaled)
    return kmeans, cluster_labels

def generate_elbow_plot(X_scaled, max_clusters=10):
    """
    Generate elbow plot (inertia vs k from 2 to 10)
    Save as reports/elbow_plot.png
    """
    inertias = []
    K_range = range(2, max_clusters + 1)

    for k in K_range:
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        kmeans.fit(X_scaled)
        inertias.append(kmeans.inertia_)

    # Create elbow plot
    plt.figure(figsize=(10, 6))
    plt.plot(K_range, inertias, 'bo-', linewidth=2, markersize=8)
    plt.xlabel('Number of clusters (k)', fontsize=12)
    plt.ylabel('Inertia', fontsize=12)
    plt.title('Elbow Method for Optimal k', fontsize=14)
    plt.grid(True, alpha=0.3)

    # Save plot
    plt.tight_layout()
    plt.savefig("reports/elbow_plot.png", dpi=300, bbox_inches='tight')
    plt.close()

    return inertias

def assign_cluster_names(cluster_centers_scaled, scaler, feature_names):
    """
    Assign descriptive names to clusters based on their financial profiles
    Returns list of cluster names
    """
    # Inverse transform to get original scale values
    cluster_centers_original = scaler.inverse_transform(cluster_centers_scaled)
    centers_df = pd.DataFrame(cluster_centers_original, columns=feature_names)

    # Define cluster names based on typical financial profiles
    # We'll analyze the centers to assign appropriate names

    cluster_names = []
    for i in range(len(cluster_centers_original)):
        center = centers_df.iloc[i]

        # Simple heuristic-based naming
        roe = center['return_on_equity_pct']
        de = center['debt_to_equity']
        revenue_cagr = center['revenue_cagr_5yr']
        fcf = center['free_cash_flow_cr']
        opm = center['operating_profit_margin_pct']

        # Assign names based on characteristics
        if roe > 100:
            name = "Data Outlier"
        elif roe > 25 and de < 1.0 and fcf > 0 and opm > 20:
            name = "High-Quality Compounders"
        elif de > 4.0 and fcf < 0:  # High leverage, negative FCF
            name = "Highly Leveraged Growth"
        elif roe > 15 and de < 0.5 and fcf > 0 and 5 <= revenue_cagr <= 15:
            name = "Steady Performers"
        elif de > 2.0 and revenue_cagr > 15:
            name = "Aggressive Growth"
        elif roe < 10 and de < 0.3:
            name = "Conservative Low-Yield"
        elif fcf < 0 and roe > 10:
            name = "Growth Investing (Negative FCF)"
        else:
            name = "Balanced"

        cluster_names.append(name)

    return cluster_names

def calculate_distances_to_centroids(X_scaled, kmeans_model):
    """
    Calculate distance of each point to its assigned centroid
    Returns array of distances
    """
    # Get cluster labels
    labels = kmeans_model.labels_

    # Get centroids
    centroids = kmeans_model.cluster_centers_

    # Calculate distances
    distances = np.zeros(len(X_scaled))
    for i, label in enumerate(labels):
        distances[i] = np.linalg.norm(X_scaled[i] - centroids[label])

    return distances

def save_cluster_labels(df, cluster_labels, cluster_names, distances):
    """
    Generate output/cluster_labels.csv with columns:
    company_id, cluster_id (0-4), cluster_name, distance_from_centroid
    """
    # Create results DataFrame
    results_df = pd.DataFrame({
        'company_id': df['company_id'],
        'cluster_id': cluster_labels,
        'cluster_name': [cluster_names[label] for label in cluster_labels],
        'distance_from_centroid': distances
    })

    # Sort by company_id for consistency
    results_df = results_df.sort_values('company_id').reset_index(drop=True)

    # Save to CSV
    results_df.to_csv("output/cluster_labels.csv", index=False)

    return results_df

def main():
    """Main function to run KMeans clustering"""
    print("Starting KMeans Clustering (Day 36)...")

    # Step 1: Get clustering data
    print("1. Loading clustering data...")
    df = get_clustering_data()
    print(f"   Loaded data for {len(df)} companies")
    print(f"   Missing values before imputation: {df.isnull().sum().sum()}")

    # Step 2: Impute missing values with sector median
    print("2. Imputing missing values with sector median...")
    df_imputed = impute_missing_with_sector_median(df)
    print(f"   Missing values after imputation: {df_imputed.isnull().sum().sum()}")

    # Step 3: Scale features
    print("3. Scaling features with StandardScaler...")
    X_scaled, scaler = scale_features(df_imputed)
    print(f"   Features scaled. Shape: {X_scaled.shape}")

    # Step 4: Perform KMeans clustering
    print("4. Running KMeans clustering (k=5, random_state=42)...")
    kmeans_model, cluster_labels = perform_kmeans_clustering(X_scaled, n_clusters=5, random_state=42)
    print(f"   Clustering completed. Inertia: {kmeans_model.inertia_:.2f}")

    # Step 5: Generate elbow plot
    print("5. Generating elbow plot...")
    inertias = generate_elbow_plot(X_scaled, max_clusters=10)
    print(f"   Elbow plot saved to reports/elbow_plot.png")
    print(f"   Inertias for k=2 to 10: {[round(x, 2) for x in inertias]}")

    # Step 6: Assign cluster names
    print("6. Assigning descriptive cluster names...")
    feature_names = ['return_on_equity_pct', 'debt_to_equity', 'revenue_cagr_5yr',
                    'free_cash_flow_cr', 'operating_profit_margin_pct']
    cluster_names = assign_cluster_names(kmeans_model.cluster_centers_, scaler, feature_names)
    print(f"   Cluster names: {cluster_names}")

    # Step 7: Calculate distances to centroids
    print("7. Calculating distances to centroids...")
    distances = calculate_distances_to_centroids(X_scaled, kmeans_model)

    # Step 8: Save cluster labels
    print("8. Saving cluster labels...")
    results_df = save_cluster_labels(df_imputed, cluster_labels, cluster_names, distances)
    print(f"   Cluster labels saved to output/cluster_labels.csv")

    # Print summary
    print("\n" + "="*50)
    print("CLUSTERING SUMMARY")
    print("="*50)
    cluster_summary = results_df['cluster_name'].value_counts()
    for cluster_name, count in cluster_summary.items():
        print(f"{cluster_name}: {count} companies")
    print("="*50)

    print("\nClustering completed successfully!")
    return results_df

if __name__ == "__main__":
    main()