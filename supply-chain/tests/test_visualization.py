import pandas as pd
from src.visualization import plot_cost_distribution

def test_plot_generation(tmp_path):
    test_df = pd.DataFrame({
        'Total_Cost': [100, 200, 300, 400, 500]
    })
    
    output_file = tmp_path / "test_plot.png"
    plot_cost_distribution(test_df, save_path=output_file)
    
    assert output_file.exists()