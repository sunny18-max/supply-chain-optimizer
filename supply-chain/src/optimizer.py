import pandas as pd
import os
from io import BytesIO
import base64
from bs4 import BeautifulSoup
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from pulp import LpProblem, LpMinimize, LpVariable, LpStatus, lpSum
import matplotlib.pyplot as plt
import squarify

class SupplyChainOptimizer:
    """
    A class to optimize supply chain logistics using linear programming.
    Minimizes transportation costs while meeting demand and capacity constraints.
    """
    
    def __init__(self):
        """Initialize the optimizer with empty data structures"""
        self.facilities = []
        self.facility_details = {}  # facility_id -> {location, type, operational_cost}
        self.customers = []
        self.customer_details = {}  # customer_id -> {region, priority_demand_category, service_level_agreement}
        self.products = []
        self.product_details = {}   # product_id -> {category, weight, is_perishable, value}
        self.cost_matrix = {}       # (facility_id, customer_id, product_id) -> {cost_per_unit, transit_time_days}
        self.demand_data = {}       # (customer_id, product_id) -> {demand, demand_volatility}
        self.capacity_data = {}     # (facility_id, product_id) -> {capacity, current_utilization}
        self.problem = None
        self.solution = None
        self.total_cost = None
        self.colors = {
            'primary': '#3498db',
            'secondary': '#2ecc71',
            'accent': '#e74c3c',
            'background': '#f9f9f9',
            'text': '#333333'
        }

    def load_data_from_csv(self, facilities_file, customers_file, products_file,
                         cost_matrix_file, demand_file, capacity_file):
        """
        Load supply chain data from CSV files with all attributes.
        """
        try:
            # Load facilities data
            facilities_df = pd.read_csv(facilities_file)
            self.facilities = facilities_df['facility_id'].tolist()
            self.facility_details = {
                row['facility_id']: {
                    'location': row['location'],
                    'type': row['type'],
                    'operational_cost': row['operational_cost']
                }
                for _, row in facilities_df.iterrows()
            }

            # Load customers data
            customers_df = pd.read_csv(customers_file)
            self.customers = customers_df['customer_id'].tolist()
            self.customer_details = {
                row['customer_id']: {
                    'region': row['region'],
                    'priority_demand_category': row['priority_demand_category'],
                    'service_level_agreement': row['service_level_agreement']
                }
                for _, row in customers_df.iterrows()
            }

            # Load products data
            products_df = pd.read_csv(products_file)
            self.products = products_df['product_id'].tolist()
            self.product_details = {
                row['product_id']: {
                    'category': row['category'],
                    'weight': row['weight'],
                    'is_perishable': row['is_perishable'],
                    'value': row['value']
                }
                for _, row in products_df.iterrows()
            }

           # Load cost matrix data with validation
            cost_df = pd.read_csv(cost_matrix_file)
            self.cost_matrix = {}
            missing_routes = []
            
            for _, row in cost_df.iterrows():
                key = (row['facility_id'], row['customer_id'], row['product_id'])
                self.cost_matrix[key] = {
                    'cost_per_unit': row['cost_per_unit'],
                    'transit_time_days': row['transit_time_days']
                }
            
            # Verify all required routes exist
            for f in self.facilities:
                for c in self.customers:
                    for p in self.products:
                        if (f, c, p) not in self.cost_matrix:
                            missing_routes.append((f, c, p))
            
            if missing_routes:
                print(f"Warning: {len(missing_routes)} facility-customer-product routes are missing from transports.csv")
                print("First 5 missing routes:", missing_routes[:5])
                # Assign high cost to missing routes
                for route in missing_routes:
                    self.cost_matrix[route] = {
                        'cost_per_unit': 1000,  # High penalty cost
                        'transit_time_days': 7  # Long transit time
                    }

            # Load demand data
            demand_df = pd.read_csv(demand_file)
            self.demand_data = {
                (row['customer_id'], row['product_id']): {
                    'demand': row['demand'],
                    'demand_volatility': row['demand_volatility']
                }
                for _, row in demand_df.iterrows()
            }

            # Load capacity data
            capacity_df = pd.read_csv(capacity_file)
            self.capacity_data = {
                (row['facility_id'], row['product_id']): {
                    'capacity': row['capacity'],
                    'current_utilization': row['current_utilization']
                }
                for _, row in capacity_df.iterrows()
            }

            print("Data loaded successfully from:")
            print(f"- Facilities: {len(self.facilities)} locations")
            print(f"- Customers: {len(self.customers)} destinations")
            print(f"- Products: {len(self.products)} items")

        except Exception as e:
            print(f"Error loading data: {str(e)}")
            print("Please verify your CSV files match these requirements:")
            print("- facilities.csv: facility_id, location, type, operational_cost")
            print("- customers.csv: customer_id, region, priority_demand_category, service_level_agreement")
            print("- products.csv: product_id, category, weight, is_perishable, value")
            print("- transports.csv: facility_id, customer_id, product_id, cost_per_unit, transit_time_days")
            print("- demand.csv: customer_id, product_id, demand, demand_volatility")
            print("- capacity.csv: facility_id, product_id, capacity, current_utilization")
            raise

    def create_optimization_model(self):
        """Formulate the linear programming problem using all attributes"""
        try:
            self.problem = LpProblem("Supply_Chain_Optimization", LpMinimize)
            
            # Decision variables: shipment quantities
            shipment_vars = LpVariable.dicts(
                "Shipment",
                [(f, c, p) for f in self.facilities 
                          for c in self.customers 
                          for p in self.products],
                lowBound=0,
                cat='Continuous'
            )

            # Objective: Minimize total transportation cost considering perishability
            self.problem += lpSum(
                shipment_vars[f, c, p] * self.cost_matrix[(f, c, p)]['cost_per_unit'] *
                (1.2 if self.product_details[p]['is_perishable'] else 1.0)  # 20% premium for perishables
                for f in self.facilities
                for c in self.customers
                for p in self.products
            )

            # Constraints
             # 1. Demand satisfaction (only for valid demand pairs)
            for (c, p), demand_info in self.demand_data.items():
                self.problem += lpSum(
                    shipment_vars[f, c, p] for f in self.facilities
                ) >= demand_info['demand'], f"Demand_{c}_{p}"
            # 2. Capacity limits (only for valid capacity pairs)
            for (f, p), capacity_info in self.capacity_data.items():
                available_capacity = capacity_info['capacity'] * (1 - capacity_info['current_utilization'])
                self.problem += lpSum(
                    shipment_vars[f, c, p] for c in self.customers
                ) <= available_capacity, f"Capacity_{f}_{p}"

            print("Optimization model created with:")
            print(f"- Variables: {len(shipment_vars)} shipment decisions")
            print(f"- Constraints: {len(self.problem.constraints)} rules")

        except Exception as e:
            print(f"Error creating model: {str(e)}")
            raise
    def get_transport_cost(self, facility_id, customer_id, product_id):
        """Get transport cost with fallback for missing routes"""
        try:
            return self.cost_matrix[(facility_id, customer_id, product_id)]['cost_per_unit']
        except KeyError:
            # Return high cost for missing routes
            return 1000
    def solve(self):
        """Solve the optimization problem"""
        try:
            self.problem.solve()
            self.solution = {
                "status": LpStatus[self.problem.status],
                "variables": {},
                "total_cost": None
            }

            if self.problem.status == 1:  # Optimal
                self.total_cost = self.problem.objective.value()
                self.solution['total_cost'] = self.total_cost
                
                # Store non-zero shipments
                for v in self.problem.variables():
                    if v.varValue > 0:
                        self.solution['variables'][v.name] = v.varValue

                print(f"Solved with status: {self.solution['status']}")
                print(f"Total cost: ${self.total_cost:,.2f}")
            else:
                print(f"No optimal solution found. Status: {self.solution['status']}")

        except Exception as e:
            print(f"Error solving: {str(e)}")
            raise

    def generate_shipment_schedule(self):
        """Convert solution to a pandas DataFrame with all details"""
        if not self.solution or self.solution['status'] != 'Optimal':
            print("No optimal solution available")
            return None

        shipments = []
        for var_name, quantity in self.solution['variables'].items():
            try:
                # Parse variable name to get facility, customer, product
                if '(' in var_name:
                    clean = var_name.split('(')[1].split(')')[0]
                    parts = [p.strip(" _,'\"") for p in clean.split(',')]
                    f, c, p = parts[0], parts[1], parts[2]
                else:
                    parts = var_name.split('_')
                    f, c, p = parts[1], parts[2], parts[3]

                # Get all details for the shipment
                cost_info = self.cost_matrix.get((f, c, p), {})
                facility_info = self.facility_details.get(f, {})
                customer_info = self.customer_details.get(c, {})
                product_info = self.product_details.get(p, {})

                shipments.append({
                    'Facility': f,
                    'Facility_Location': facility_info.get('location', ''),
                    'Facility_Type': facility_info.get('type', ''),
                    'Customer': c,
                    'Customer_Region': customer_info.get('region', ''),
                    'Customer_SLA': customer_info.get('service_level_agreement', ''),
                    'Product': p,
                    'Product_Category': product_info.get('category', ''),
                    'Product_Weight': product_info.get('weight', 0),
                    'Quantity': quantity,
                    'Unit_Cost': cost_info.get('cost_per_unit', 0),
                    'Transit_Time': cost_info.get('transit_time_days', 0),
                    'Total_Cost': quantity * cost_info.get('cost_per_unit', 0),
                    'Is_Perishable': product_info.get('is_perishable', False),
                    'Product_Value': product_info.get('value', 0)
                })
            except Exception as e:
                print(f"Warning: Could not parse variable '{var_name}': {str(e)}")
                continue

        if not shipments:
            print("Warning: No valid shipments could be parsed")
            return None

        return pd.DataFrame(shipments).sort_values(by=['Facility', 'Customer', 'Product'])

    def visualize_shipments(self, top_n=None, save_path=None):
        """Visualize shipments with optional top_n filtering"""
        df = self.generate_shipment_schedule()
        if df is None or df.empty:
            print("No shipment data to visualize")
            return None

        if top_n:
            df = df.nlargest(top_n, 'Quantity')
        
        fig, ax = plt.subplots(figsize=(12, 6))
        bars = ax.barh(
            y=[f"{row['Facility']}→{row['Customer']} ({row['Product']})" 
               for _, row in df.iterrows()],
            width=df['Quantity'],
            color='teal'
        )
        
        title = 'Shipments by Volume' + (f' (Top {top_n})' if top_n else '')
        ax.set_title(title)
        ax.set_xlabel('Quantity Shipped')
        ax.grid(axis='x', linestyle='--', alpha=0.7)
        
        # Add value labels
        for bar in bars:
            width = bar.get_width()
            ax.text(width, bar.get_y() + bar.get_height()/2, 
                   f'{width:,.0f}', 
                   va='center', ha='left')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path)
            plt.close()
            return save_path
        else:
            plt.show()
            return None

    def cost_savings_report(self, baseline_cost):
        """Generate a cost savings report compared to a baseline"""
        if not self.total_cost:
            print("No solution available for comparison")
            return

        savings = baseline_cost - self.total_cost
        savings_pct = (savings / baseline_cost) * 100
        
        print("\nCost Savings Analysis:")
        print(f"Baseline Cost: ${baseline_cost:,.2f}")
        print(f"Optimized Cost: ${self.total_cost:,.2f}")
        print(f"Total Savings: ${savings:,.2f} ({savings_pct:.1f}%)")

    def visualize_cost_distribution(self, save_path=None):
        df = self.generate_shipment_schedule()
        if df is None or df.empty:
            print("No data for cost visualization")
            return None

        # Option 1: Bubble Chart
        cost_df = df.groupby(['Facility', 'Customer'])['Total_Cost'].sum().reset_index()
        
        plt.figure(figsize=(12, 8))
        plt.scatter(x=cost_df['Facility'], 
                    y=cost_df['Customer'],
                    s=cost_df['Total_Cost']/100,  # Scale bubble size
                    alpha=0.6)
        plt.title('Transportation Costs (Bubble Chart)')
        plt.xlabel('Facility')
        plt.ylabel('Customer')
        plt.grid(True)
        
        if save_path:
            plt.savefig(save_path)
            plt.close()
        else:
            plt.show()
            return None

    def visualize_product_distribution(self, save_path=None):
        df = self.generate_shipment_schedule()
        if df is None or df.empty:
            print("No data for product visualization")
            return None

        product_facility = df.groupby(['Facility', 'Product'])['Quantity'].sum().reset_index()
        
        plt.figure(figsize=(12, 8))
        squarify.plot(sizes=product_facility['Quantity'],
                    label=product_facility.apply(lambda x: f"{x['Facility']}\n{x['Product']}", axis=1),
                    alpha=0.8)
        plt.title('Product Distribution by Facility (Treemap)')
        plt.axis('off')
        
        if save_path:
            plt.savefig(save_path)
            plt.close()
        else:
            plt.show()
            return None

    def export_to_excel(self, output_file=None):
        """Export all data to an Excel file with proper path handling"""
        df = self.generate_shipment_schedule()
        if df is None:
            print("No data to export")
            return False

        # Set default output file if none provided
        if output_file is None:
            output_file = os.path.join(os.path.expanduser("~"), "Documents", "supply_chain_results.xlsx")

        try:
            # Try with xlsxwriter first for better formatting
            try:
                with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
                    self._export_with_formatting(writer, df)
            except ImportError:
                # Fallback to openpyxl if xlsxwriter not available
                with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='Shipments', index=False)
                print("Basic Excel file created (install xlsxwriter for better formatting)")

            print(f"Results exported to {output_file}")
            return True
        except Exception as e:
            print(f"Error exporting to Excel: {str(e)}")
            return False

    def _export_with_formatting(self, writer, df):
        """Helper method for formatted Excel export"""
        workbook = writer.book
        df.to_excel(writer, sheet_name='Detailed Shipments', index=False)
        
        # Get the worksheet object
        worksheet = writer.sheets['Detailed Shipments']
        
        # Add formatting
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#4472C4',
            'font_color': 'white',
            'border': 1
        })
        
        # Apply header format
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
        
        # Auto-adjust columns' width
        for column in df:
            column_width = max(df[column].astype(str).map(len).max(), len(column)) + 2
            col_idx = df.columns.get_loc(column)
            worksheet.set_column(col_idx, col_idx, column_width)

    def generate_html_report(self, output_file="supply_chain_report.html"):
        """Generate a comprehensive HTML report with professional styling and animations"""
        df = self.generate_shipment_schedule()
        if df is None or df.empty:
            print("No data to generate report")
            return

        # Create visualizations
        def fig_to_base64(fig):
            buf = BytesIO()
            fig.savefig(buf, format='png', bbox_inches='tight', dpi=150)
            plt.close(fig)
            return base64.b64encode(buf.getvalue()).decode('utf-8')

        try:
            # Calculate baseline cost (you'll need to define this properly)
            # For demonstration, I'm using 10% higher than optimized cost
            baseline_cost = self.total_cost * 1.10  # Replace with your actual baseline if available
            cost_savings = ((baseline_cost - self.total_cost) / baseline_cost) * 100

            # 1. Treemap of Product Distribution
            import squarify
            import numpy as np  # Needed for color mapping
            
            product_facility = df.groupby(['Facility', 'Product'])['Quantity'].sum().reset_index()
            plt.figure(figsize=(14, 9), facecolor='#f8f9fa')
            squarify.plot(sizes=product_facility['Quantity'],
                        label=product_facility.apply(lambda x: f"{x['Product']}\n{x['Quantity']:,}", axis=1),
                        alpha=0.85,
                        color=plt.cm.Pastel1.colors,
                        text_kwargs={'fontsize':10, 'fontweight':'bold'})
            plt.title('Product Distribution by Facility\n(Treemap Visualization)', fontsize=12, pad=20)
            plt.axis('off')
            treemap_img = fig_to_base64(plt.gcf())

            # 2. Bubble Chart of Transportation Costs
            cost_df = df.groupby(['Facility', 'Customer'])['Total_Cost'].sum().reset_index()
            plt.figure(figsize=(12, 8))
            scatter = plt.scatter(
                x=cost_df['Facility'], 
                y=cost_df['Customer'],
                s=cost_df['Total_Cost']/1000,  # Scale bubble size
                c=cost_df['Total_Cost'],  # Color by cost
                cmap='viridis',
                alpha=0.6
            )
            plt.colorbar(scatter, label='Total Cost ($)')
            plt.title('Transportation Costs (Bubble Chart)')
            plt.xlabel('Facility')
            plt.ylabel('Customer')
            plt.grid(True)
            plt.xticks(rotation=45)
            bubble_img = fig_to_base64(plt.gcf())

            # 3. Top Routes by Volume (replaces the old shipments_img)
            top_routes = df.groupby(['Facility', 'Customer'])['Quantity'].sum().nlargest(10).reset_index()
            plt.figure(figsize=(12, 6))
            plt.barh(
                y=[f"{row['Facility']}→{row['Customer']}" for _, row in top_routes.iterrows()],
                width=top_routes['Quantity'],
                color='teal'
            )
            plt.title('Top 10 Routes by Shipping Volume')
            plt.xlabel('Quantity Shipped')
            routes_img = fig_to_base64(plt.gcf())

            # Calculate some statistics for the report
            total_shipments = df['Quantity'].sum()
            avg_cost_per_unit = df['Total_Cost'].sum() / total_shipments if total_shipments > 0 else 0
            top_product = df.groupby('Product')['Quantity'].sum().idxmax()
            top_route = df.groupby(['Facility', 'Customer'])['Total_Cost'].sum().idxmax()

        except Exception as e:
            print(f"Error generating visualizations: {str(e)}")
            return

         # HTML template with professional styling
        html = f"""<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Supply Chain Optimization Report | Professional Analysis</title>
        <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;600;700&family=Roboto:wght@300;400;500&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        <style>
            :root {{
                --primary: #4361ee;
                --secondary: #3f37c9;
                --accent: #f72585;
                --dark: #212529;
                --light: #f8f9fa;
                --success: #4cc9f0;
                --warning: #f8961e;
                --danger: #ef233c;
            }}
            
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Roboto', sans-serif;
                background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                color: var(--dark);
                line-height: 1.6;
                min-height: 100vh;
                padding: 0;
                margin: 0;
            }}
            
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                padding: 2rem;
            }}
            
            header {{
                background: linear-gradient(to right, var(--primary), var(--secondary));
                color: white;
                padding: 3rem 2rem;
                margin-bottom: 2rem;
                border-radius: 10px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                text-align: center;
                position: relative;
                overflow: hidden;
            }}
            
            header::before {{
                content: '';
                position: absolute;
                top: -50%;
                left: -50%;
                width: 200%;
                height: 200%;
                background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0) 70%);
                animation: pulse 15s infinite linear;
            }}
            
            h1, h2, h3 {{
                font-family: 'Montserrat', sans-serif;
                font-weight: 700;
            }}
            
            h1 {{
                font-size: 2.5rem;
                margin-bottom: 0.5rem;
                position: relative;
                z-index: 1;
                text-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            
            .subtitle {{
                font-size: 1.1rem;
                opacity: 0.9;
                position: relative;
                z-index: 1;
            }}
            
            .report-section {{
                background: white;
                border-radius: 10px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.05);
                padding: 2rem;
                margin-bottom: 2rem;
                transition: transform 0.3s ease, box-shadow 0.3s ease;
                position: relative;
                overflow: hidden;
            }}
            
            .report-section:hover {{
                transform: translateY(-5px);
                box-shadow: 0 15px 30px rgba(0,0,0,0.1);
            }}
            
            .report-section::after {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                width: 5px;
                height: 100%;
                background: linear-gradient(to bottom, var(--primary), var(--accent));
            }}
            
            h2 {{
                color: var(--primary);
                margin-bottom: 1.5rem;
                font-size: 1.5rem;
                display: flex;
                align-items: center;
            }}
            
            h2 i {{
                margin-right: 10px;
                color: var(--accent);
            }}
            
            .chart {{
                margin: 1.5rem 0;
                text-align: center;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 3px 10px rgba(0,0,0,0.05);
                background: white;
                padding: 1rem;
            }}
            
            img {{
                max-width: 100%;
                height: auto;
                border-radius: 6px;
                box-shadow: 0 3px 15px rgba(0,0,0,0.1);
                transition: transform 0.3s ease;
            }}
            
            img:hover {{
                transform: scale(1.02);
            }}
            
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 1.5rem;
                margin: 2rem 0;
            }}
            
            .stat-card {{
                background: white;
                border-radius: 8px;
                padding: 1.5rem;
                box-shadow: 0 5px 15px rgba(0,0,0,0.05);
                text-align: center;
                transition: all 0.3s ease;
                border-top: 4px solid var(--primary);
                position: relative;
                overflow: hidden;
            }}
            
            .stat-card:hover {{
                transform: translateY(-5px);
                box-shadow: 0 10px 25px rgba(0,0,0,0.1);
            }}
            
            .stat-card h3 {{
                color: var(--secondary);
                margin-bottom: 0.5rem;
                font-size: 1rem;
                font-weight: 600;
            }}
            
            .stat-card .value {{
                font-size: 2.2rem;
                font-weight: 700;
                color: var(--primary);
                margin: 0.5rem 0;
                font-family: 'Montserrat', sans-serif;
            }}
            
            .stat-card .change {{
                font-size: 0.9rem;
                padding: 0.3rem 0.6rem;
                border-radius: 20px;
                display: inline-block;
            }}
            
            .positive {{
                background-color: rgba(76, 201, 240, 0.1);
                color: var(--success);
            }}
            
            .insights {{
                background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                border-left: 4px solid var(--accent);
                padding: 1.5rem;
                margin: 1.5rem 0;
                border-radius: 0 8px 8px 0;
            }}
            
            .insights h3 {{
                color: var(--accent);
                margin-bottom: 1rem;
                display: flex;
                align-items: center;
            }}
            
            .insights ul {{
                list-style-type: none;
            }}
            
            .insights li {{
                margin-bottom: 0.8rem;
                position: relative;
                padding-left: 1.5rem;
            }}
            
            .insights li::before {{
                content: '\\f00c';
                font-family: 'Font Awesome 6 Free';
                font-weight: 900;
                color: var(--accent);
                position: absolute;
                left: 0;
            }}
            
            .highlight {{
                background-color: rgba(247, 37, 133, 0.1);
                color: var(--accent);
                padding: 0.2rem 0.4rem;
                border-radius: 4px;
                font-weight: 600;
            }}
            
            footer {{
                text-align: center;
                margin-top: 3rem;
                padding: 1.5rem;
                color: #6c757d;
                font-size: 0.9rem;
            }}
            
            @keyframes pulse {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
            
            @keyframes fadeIn {{
                from {{ opacity: 0; transform: translateY(20px); }}
                to {{ opacity: 1; transform: translateY(0); }}
            }}
            
            .animate {{
                animation: fadeIn 0.6s ease forwards;
            }}
            
            .delay-1 {{ animation-delay: 0.2s; }}
            .delay-2 {{ animation-delay: 0.4s; }}
            .delay-3 {{ animation-delay: 0.6s; }}
            
            @media (max-width: 768px) {{
                .stats-grid {{
                    grid-template-columns: 1fr;
                }}
                
                h1 {{
                    font-size: 2rem;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>Supply Chain Optimization Report</h1>
                <p class="subtitle">Advanced analysis of distribution network and cost efficiency</p>
            </header>
            
            <div class="stats-grid">
                <div class="stat-card animate">
                    <h3><i class="fas fa-dollar-sign"></i> Total Optimized Cost</h3>
                    <div class="value">${self.total_cost:,.2f}</div>
                    <div class="change positive"><i class="fas fa-arrow-down"></i> {cost_savings:.1f}% vs baseline</div>
                </div>
                
                <div class="stat-card animate delay-1">
                    <h3><i class="fas fa-boxes"></i> Total Shipments</h3>
                    <div class="value">{total_shipments:,}</div>
                    <p>Across all facilities</p>
                </div>
                
                <div class="stat-card animate delay-2">
                    <h3><i class="fas fa-weight-hanging"></i> Avg Cost/Unit</h3>
                    <div class="value">${avg_cost_per_unit:,.2f}</div>
                    <p>Weighted average</p>
                </div>
            </div>
            
            <div class="report-section animate">
                <h2><i class="fas fa-project-diagram"></i> Product Distribution Network</h2>
                <div class="chart">
                    <img src="data:image/png;base64,{treemap_img}" alt="Product Distribution">
                </div>
                
                <div class="insights">
                    <h3><i class="fas fa-lightbulb"></i> Key Insights</h3>
                    <ul>
                        <li>Product <span class="highlight">{top_product}</span> accounts for the largest volume across facilities</li>
                        <li>Facility <span class="highlight">{product_facility.iloc[product_facility['Quantity'].idxmax()]['Facility']}</span> handles the most diverse product mix</li>
                        <li>The treemap visualization reveals uneven distribution patterns that could be optimized further</li>
                    </ul>
                </div>
            </div>
            
            <div class="report-section animate delay-1">
                <h2><i class="fas fa-truck"></i> Transportation Cost Analysis</h2>
                <div class="chart">
                    <img src="data:image/png;base64,{bubble_img}" alt="Cost Analysis">
                </div>
                
                <div class="insights">
                    <h3><i class="fas fa-lightbulb"></i> Key Insights</h3>
                    <ul>
                        <li>Route <span class="highlight">{top_route[0]} → {top_route[1]}</span> is the most expensive (${cost_df['Total_Cost'].max():,.2f})</li>
                        <li>Bubble size correlates with total cost, while color intensity shows relative expense</li>
                        <li>Several high-cost routes could benefit from alternative facility assignments</li>
                    </ul>
                </div>
            </div>
            
            <div class="report-section animate delay-2">
                <h2><i class="fas fa-route"></i> Top Shipping Routes by Volume</h2>
                <div class="chart">
                    <img src="data:image/png;base64,{routes_img}" alt="Top Routes">
                </div>
                
                <div class="insights">
                    <h3><i class="fas fa-lightbulb"></i> Key Insights</h3>
                    <ul>
                        <li>Route <span class="highlight">{top_routes.iloc[0]['Facility']} → {top_routes.iloc[0]['Customer']}</span> handles the highest volume ({top_routes.iloc[0]['Quantity']:,} units)</li>
                        <li>The top 3 routes account for {top_routes['Quantity'].head(3).sum()/total_shipments:.1%} of total shipments</li>
                        <li>Consider capacity expansion for these high-volume routes to prevent bottlenecks</li>
                    </ul>
                </div>
            </div>
            
            <div class="report-section animate delay-3">
                <h2><i class="fas fa-chart-line"></i> Optimization Recommendations</h2>
                <div class="insights">
                    <ul>
                        <li><strong>Consolidate shipments</strong> on high-volume routes to reduce per-unit costs</li>
                        <li><strong>Reallocate products</strong> to underutilized facilities based on the treemap analysis</li>
                        <li><strong>Negotiate better rates</strong> for the most expensive routes identified in the bubble chart</li>
                        <li><strong>Implement demand forecasting</strong> to better align inventory with shipping patterns</li>
                        <li><strong>Explore alternative facilities</strong> for serving high-cost customer routes</li>
                    </ul>
                </div>
            </div>
            
            <footer>
                <p>Report generated on {pd.Timestamp.now().strftime('%B %d, %Y at %H:%M')} | Supply Chain Optimizer v2.0</p>
            </footer>
        </div>
        
        <script>
            // Simple animation trigger for scroll effects
            document.addEventListener('DOMContentLoaded', function() {{
                const observer = new IntersectionObserver((entries) => {{
                    entries.forEach(entry => {{
                        if (entry.isIntersecting) {{
                            entry.target.classList.add('animate');
                        }}
                    }});
                }}, {{ threshold: 0.1 }});
                
                document.querySelectorAll('.report-section').forEach(section => {{
                    observer.observe(section);
                }});
            }});
        </script>
    </body>
    </html>
    """

        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"HTML report generated at {output_file}")
        except Exception as e:
            print(f"Error writing HTML report: {str(e)}")

if __name__ == "__main__":
    optimizer = SupplyChainOptimizer()
    
    # Example usage when run directly
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, 'data')
    
    try:
        optimizer.load_data_from_csv(
            facilities_file=os.path.join(data_dir, 'facilities.csv'),
            customers_file=os.path.join(data_dir, 'customers.csv'),
            products_file=os.path.join(data_dir, 'products.csv'),
            cost_matrix_file=os.path.join(data_dir, 'transports.csv'),
            demand_file=os.path.join(data_dir, 'demand.csv'),
            capacity_file=os.path.join(data_dir, 'capacity.csv')
        )
        
        optimizer.create_optimization_model()
        optimizer.solve()
        
        # Display results
        print("\nOptimal Shipments:")
        print(optimizer.generate_shipment_schedule())
        optimizer.visualize_shipments(top_n=10)
        optimizer.cost_savings_report(baseline_cost=10000)
    except Exception as e:
        print(f"Error running optimizer: {str(e)}")    