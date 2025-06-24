import pandas as pd

def validate_data(facilities, customers, products, costs, demand, capacity):
    """Validate input data for consistency"""
    errors = []
    
    # Check for missing facilities in cost matrix
    cost_facilities = set(costs['facility_id'].unique())
    missing = set(facilities['facility_id']) - cost_facilities
    if missing:
        errors.append(f"Facilities missing from cost matrix: {missing}")
    
    # Check demand vs capacity
    total_demand = demand.groupby('product_id')['demand'].sum()
    total_capacity = capacity.groupby('product_id')['capacity'].sum()
    
    for product in total_demand.index:
        if total_demand[product] > total_capacity.get(product, 0):
            errors.append(f"Insufficient capacity for product {product}")
    
    return errors

def save_shipment_schedule(df, path):
    """Save shipment schedule with additional formatting"""
    writer = pd.ExcelWriter(path, engine='xlsxwriter')
    df.to_excel(writer, index=False)
    
    workbook = writer.book
    worksheet = writer.sheets['Sheet1']
    
    # Add formatting
    money_fmt = workbook.add_format({'num_format': '$#,##0.00'})
    worksheet.set_column('E:F', 12, money_fmt)
    
    writer.close()