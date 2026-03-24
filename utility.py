def get_week_label(row):
    day = row['Date'].day
    month_str = row['Date'].strftime('%b')
    year = row['Date'].year
    
    # Define the boundaries based on your logic
    if day <= 7:
        return f"Week 1 ({month_str} 01 - {month_str} 07)"
    elif day <= 14:
        return f"Week 2 ({month_str} 08 - {month_str} 14)"
    elif day <= 21:
        return f"Week 3 ({month_str} 15 - {month_str} 21)"
    else:
        # Find the last day of the month dynamically
        last_day = row['Date'].days_in_month
        return f"Week 4+ ({month_str} 22 - {month_str} {last_day})"


PRODUCT_COLORS = {
    # DIESELS
    "Diesel": "#1f77b4",          
    "DIESEL 350LPM": "#4e79a7",   
    "DIESEL 500LPM": "#76b7b2",   
    "DIESEL 850LPM": "#a0cbe8",   
    
    # LUBRICANTS & OILS
    "SAE 10": "#ff7f0e",          
    "SAE 30": "#ffbb78",          
    "SAE 15W40": "#8c564b",       
    "SAE 85W140": "#d62728",      
    "GEAR OIL MEROPA 320": "#c49c94", 
    "HYDRAULIC OIL RANDO 68": "#e377c2", 
    
    # SPECIALTY FLUIDS
    "Coolant": "#2ca02c",         
    "Water": "#9edae5",           
    "Waste": "#7f7f7f",           
    
    # GREASE
    "Grease": "#bcbd22",          
    "MPG Arctic Grease": "#dbdb8d", 
    "MPG Summer Grease": "#17becf" 
}

PRODUCT_LABEL_COLORS = {
    "Diesel": "white",
    "DIESEL 350LPM": "white",
    "DIESEL 500LPM": "white",
    "DIESEL 850LPM": "black", 
    "SAE 10": "white",
    "SAE 30": "black",        
    "SAE 15W40": "white",
    "SAE 85W140": "white",
    "GEAR OIL MEROPA 320": "black", 
    "HYDRAULIC OIL RANDO 68": "black", 
    "Coolant": "white",
    "Water": "black",          
    "Waste": "white",
    "Grease": "black",        
    "MPG Arctic Grease": "black", 
    "MPG Summer Grease": "black"  
}