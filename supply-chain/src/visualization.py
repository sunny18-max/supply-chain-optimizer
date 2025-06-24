import matplotlib.pyplot as plt
import pandas as pd

def plot_cost_distribution(shipment_df, save_path=None):
    """Plot distribution of shipment costs"""
    plt.figure(figsize=(10, 6))
    shipment_df['Total_Cost'].plot(kind='hist', bins=20, edgecolor='black')
    plt.title('Distribution of Shipment Costs')
    plt.xlabel('Cost ($)')
    plt.ylabel('Frequency')
    
    if save_path:
        plt.savefig(save_path)
    return plt.gcf()

def generate_network_graph(shipment_df, facilities, customers):
    """Generate a network visualization of shipments"""
    import networkx as nx
    
    G = nx.DiGraph()
    
    # Add nodes
    for _, row in facilities.iterrows():
        G.add_node(row['facility_id'], type='facility', location=row['location'])
    
    for _, row in customers.iterrows():
        G.add_node(row['customer_id'], type='customer', region=row['region'])
    
    # Add edges
    for _, row in shipment_df.iterrows():
        if row['Quantity'] > 0:
            G.add_edge(
                row['Facility'], row['Customer'],
                weight=row['Quantity'],
                cost=row['Total_Cost']
            )
    
    return G