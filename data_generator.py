import pandas as pd
import random
import os

def generate_default_dataset() -> pd.DataFrame:
    """Generates a highly realistic and diverse retail inventory dataset
    for demonstration and analysis.
    
    The dataset includes stockout items, critical shortages, overstocked items,
    and healthy items to demonstrate the multi-agent system's capabilities.
    """
    categories = {
        "Electronics": [
            ("Apex Wireless Earbuds", 79.99, 12, "VoltTech Solutions"),
            ("Quantum Smartwatch", 149.99, 15, "VoltTech Solutions"),
            ("Aura Bluetooth Speaker", 45.00, 10, "SoundWave Ltd"),
            ("Titan Power Bank 20k", 29.99, 8, "PowerUp Industries"),
            ("Nebula LED Projector", 249.99, 20, "OptiCore Systems"),
            ("Viper Gaming Mouse", 59.99, 6, "VoltTech Solutions")
        ],
        "Apparel": [
            ("Classic Denim Jeans", 49.99, 14, "Apex Loom Co"),
            ("Organic Cotton T-Shirt", 19.99, 10, "Apex Loom Co"),
            ("Thermal Hooded Jacket", 89.99, 21, "Vanguard Apparel"),
            ("Activewear Running Shoes", 110.00, 15, "AeroStride Gear"),
            ("Breathe-Fit Socks (5-pack)", 15.00, 7, "Apex Loom Co"),
            ("Sleek Leather Belt", 35.00, 10, "Vanguard Apparel")
        ],
        "Home & Kitchen": [
            ("Elite Drip Coffee Maker", 89.95, 12, "BrewMaster Appliance"),
            ("Rapid Air Fryer 5.5L", 119.99, 18, "BrewMaster Appliance"),
            ("Pro-Series Chef Knife Set", 149.99, 25, "Krupp Cutlery"),
            ("PowerBlender 1200W", 79.99, 10, "AquaFlow Corp"),
            ("RoboVac Smart Vacuum", 299.99, 20, "Cleansy Ltd"),
            ("Ceramic Dinnerware (16pc)", 69.99, 15, "Krupp Cutlery")
        ],
        "Beauty & Personal Care": [
            ("HydraGlow Face Moisturizer", 24.00, 8, "Lumina Cosmetics"),
            ("UV-Shield Sunscreen SPF 50", 18.50, 10, "Lumina Cosmetics"),
            ("Keratin Repair Shampoo", 16.00, 6, "Natura Essence"),
            ("Velvet Matte Lipstick", 22.00, 8, "Lumina Cosmetics"),
            ("Anti-Aging Retinol Serum", 45.00, 12, "Natura Essence"),
            ("Gentle Foaming Face Wash", 12.99, 7, "Natura Essence")
        ],
        "Office Supplies": [
            ("A5 Bullet Journal (Hardcover)", 14.99, 5, "PaperCraft Press"),
            ("Ergonomic Mesh Office Chair", 199.99, 25, "SteelForm Furniture"),
            ("Dual-Tip Brush Pens (24-set)", 24.99, 7, "PaperCraft Press"),
            ("Acrylic Desk Organizer", 18.00, 8, "ClearView Plastics"),
            ("Magnetic Desktop Whiteboard", 35.00, 12, "ClearView Plastics"),
            ("Premium Heavy Duty Stapler", 16.50, 6, "SteelForm Furniture")
        ]
    }
    
    random.seed(42)  # For deterministic output
    data = []
    
    # We want to create specific scenarios:
    # 1. Stockout: Current stock is 0
    # 2. Critical Shortage: Current stock < Safety Stock
    # 3. Reorder Warning: Current stock < Reorder Point
    # 4. Overstock: Current stock > Reorder Point * 3
    # 5. Healthy: Current Stock is at a good level
    
    scenarios = [
        "Stockout", "Critical Shortage", "Reorder Warning", "Overstock", "Healthy", "Healthy"
    ]
    
    product_idx = 1001
    
    for category, products in categories.items():
        for product_name, price, avg_lead_time, supplier in products:
            daily_sales = round(random.uniform(1.5, 12.0), 2)
            
            # Mathematical calculations for inventory limits
            # Safety stock is usually set to cover demand variability (e.g. 5 days of average sales)
            safety_stock = int(daily_sales * 5) + 1
            # Reorder point = (daily sales * lead time) + safety stock
            reorder_point = int(daily_sales * avg_lead_time) + safety_stock
            
            # Determine current stock based on scenario
            scenario = random.choice(scenarios)
            
            if scenario == "Stockout":
                current_stock = 0
            elif scenario == "Critical Shortage":
                current_stock = random.randint(1, max(2, safety_stock - 1))
            elif scenario == "Reorder Warning":
                current_stock = random.randint(safety_stock, max(safety_stock + 1, reorder_point - 1))
            elif scenario == "Overstock":
                current_stock = random.randint(reorder_point * 3, reorder_point * 5)
            else: # Healthy
                current_stock = random.randint(reorder_point + 10, reorder_point * 2)
                
            unit_cost = round(price * random.uniform(0.4, 0.6), 2)
            
            data.append({
                "Product ID": f"SKU-{product_idx}",
                "Product Name": product_name,
                "Category": category,
                "Current Stock": current_stock,
                "Reorder Point": reorder_point,
                "Safety Stock": safety_stock,
                "Daily Sales Rate": daily_sales,
                "Unit Cost": unit_cost,
                "Lead Time (days)": avg_lead_time,
                "Supplier Name": supplier
            })
            product_idx += 1
            
    df = pd.DataFrame(data)
    return df

if __name__ == "__main__":
    df = generate_default_dataset()
    output_path = os.path.join(os.path.dirname(__file__), "sample_inventory.csv")
    df.to_csv(output_path, index=False)
    print(f"Sample dataset generated successfully at {output_path}!")
    print(f"Total Rows: {len(df)}")
    print(df.head())
