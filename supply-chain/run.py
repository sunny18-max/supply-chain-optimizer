import os
from src.optimizer import SupplyChainOptimizer

def main():
    optimizer = SupplyChainOptimizer()
    
    # Get the directory where run.py is located
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, 'data')
    
    try:
        print("Loading supply chain data...")
        optimizer.load_data_from_csv(
            facilities_file=os.path.join(data_dir, 'facilities.csv'),
            customers_file=os.path.join(data_dir, 'customers.csv'),
            products_file=os.path.join(data_dir, 'products.csv'),
            cost_matrix_file=os.path.join(data_dir, 'transports.csv'),
            demand_file=os.path.join(data_dir, 'demand.csv'),
            capacity_file=os.path.join(data_dir, 'capacity.csv')
        )
        
        print("Creating optimization model...")
        optimizer.create_optimization_model()
        
        print("Solving optimization problem...")
        optimizer.solve()
        
        print("\nGenerating reports...")
        optimizer.export_to_excel()
        optimizer.generate_html_report()
        
        print("\nOptimization completed successfully!")
        print(f"Total optimized cost: ${optimizer.total_cost:,.2f}")
        
    except Exception as e:
        print(f"\nError running optimizer: {str(e)}")
        raise

if __name__ == "__main__":
    main()