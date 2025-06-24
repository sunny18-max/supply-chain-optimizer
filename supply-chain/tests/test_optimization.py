import pytest
from src.optimizer import SupplyChainOptimizer

def test_optimization_model():
    optimizer = SupplyChainOptimizer()
    
    # Setup test case with proper demand data structure
    optimizer.facilities = ['F1']
    optimizer.customers = ['C1']
    optimizer.products = ['P1']
    optimizer.cost_matrix = {('F1', 'C1'): 10}
    optimizer.demand_data = {('C1', 'P1'): 100}  # Correct demand format
    optimizer.capacity_data = {('F1', 'P1'): 150}
    
    optimizer.create_optimization_model()
    optimizer.solve()
    
    assert optimizer.solution['status'] == 'Optimal'
    assert optimizer.total_cost == pytest.approx(1000, 0.1)