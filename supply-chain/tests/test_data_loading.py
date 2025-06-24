import pytest
import pandas as pd
import os
from src.optimizer import SupplyChainOptimizer

@pytest.fixture
def sample_data(tmp_path):
    # Create test CSV files
    facilities_path = os.path.join(tmp_path, "facilities.csv")
    pd.DataFrame({
        'facility_id': ['F1', 'F2'],
        'location': ['Loc1', 'Loc2']
    }).to_csv(facilities_path, index=False)

    demand_path = os.path.join(tmp_path, "demand.csv")
    pd.DataFrame({
        'customer_id': ['C1', 'C1'],
        'product_id': ['P1', 'P2'],
        'demand': [100, 50]
    }).to_csv(demand_path, index=False)

    return {
        'facilities_path': facilities_path,
        'demand_path': demand_path
    }

def test_data_loading(sample_data):
    optimizer = SupplyChainOptimizer()
    
    # Test loading with proper error handling
    optimizer.load_data_from_csv(
        sample_data['facilities_path'],
        'nonexistent.csv',  # Should raise FileNotFoundError
        'nonexistent.csv',
        'nonexistent.csv',
        sample_data['demand_path'],
        'nonexistent.csv'
    )
    
    # Verify loaded data
    assert 'F1' in optimizer.facilities
    assert ('C1', 'P1') in optimizer.demand_data