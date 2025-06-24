from optimizer import SupplyChainOptimizer
from visualization import plot_cost_distribution
from utils import validate_data, save_shipment_schedule
import pandas as pd
import os

def run_optimization():
    print("Initializing Supply Chain Optimizer...")
    
    # Load data
    facilities = pd.read_csv('data/facilities.csv')
    customers = pd.read_csv('data/customers.csv')
    products = pd.read_csv('data/products.csv')
    costs = pd.read_csv('data/transport_costs.csv')
    demand = pd.read_csv('data/demand.csv')
    capacity = pd.read_csv('data/capacity.csv')
    
    # Validate data
    errors = validate_data(facilities, customers, products, costs, demand, capacity)
    if errors:
        print("Data validation errors found:")
        for error in errors:
            print(f"- {error}")
        return
    
    # Run optimization
    optimizer = SupplyChainOptimizer()
    optimizer.load_data_from_csv(
        'data/facilities.csv',
        'data/customers.csv',
        'data/products.csv',
        'data/transport_costs.csv',
        'data/demand.csv',
        'data/capacity.csv'
    )
    
    optimizer.create_optimization_model()
    optimizer.solve()
    
    # Generate outputs
    os.makedirs('outputs/shipment_schedules', exist_ok=True)
    os.makedirs('outputs/visualizations', exist_ok=True)
    
    shipment_schedule = optimizer.generate_shipment_schedule()
    save_shipment_schedule(
        shipment_schedule,
        'outputs/shipment_schedules/optimal_plan.xlsx'
    )
    
    plot_cost_distribution(
        shipment_schedule,
        'outputs/visualizations/cost_distribution.png'
    )
    
    print("\nOptimization complete! Results saved in outputs/ directory")

if __name__ == "__main__":
    run_optimization()