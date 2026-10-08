import pandas as pd
import numpy as np
import os
import json
from datetime import datetime, timedelta

def set_seed(seed=42):
    np.random.seed(seed)

def generate_marketing():
    set_seed(42)
    dates = pd.date_range(start='2026-01-01', end='2026-06-30', freq='D')
    channels = ['Social', 'Search', 'Email', 'Display']
    campaign_types = ['Brand', 'Performance', 'Retargeting']
    
    data = []
    for d in dates:
        for c in channels:
            for ct in campaign_types:
                # Baseline
                impressions = np.random.randint(1000, 5000)
                ctr = np.random.uniform(0.01, 0.05)
                cvr = np.random.uniform(0.05, 0.15)
                cpc = np.random.uniform(0.5, 2.0)
                
                # Feb -> Mar conversion rate improvement (campaign launch)
                if d.month >= 3:
                    cvr *= 1.5
                    
                # Search aggressive bidding causing CPA spike
                if c == 'Search' and d.month >= 3:
                    cpc *= 3.0 # Higher spend
                    impressions = int(impressions * 1.5)
                    
                # Social organic growth
                if c == 'Social':
                    growth_factor = 1.0 + (d.month - 1) * 0.2
                    impressions = int(impressions * growth_factor)
                    
                # Display collapsed
                if c == 'Display' and d.month >= 3:
                    impressions = int(impressions * 0.1)
                
                clicks = int(impressions * ctr)
                conversions = int(clicks * cvr)
                spend = clicks * cpc
                
                data.append([d, c, ct, impressions, clicks, conversions, spend])
                
    df = pd.DataFrame(data, columns=['date', 'channel', 'campaign_type', 'impressions', 'clicks', 'conversions', 'spend'])
    df.to_csv('demo_marketing.csv', index=False)
    print(f"demo_marketing.csv generated with {len(df)} rows.")

def generate_hr():
    set_seed(42)
    dates = pd.date_range(start='2025-07-01', end='2026-06-01', freq='MS')
    departments = ['Engineering', 'Sales', 'Marketing', 'Operations', 'Support']
    seniority = ['Junior', 'Mid', 'Senior']
    
    data = []
    for d in dates:
        for dept in departments:
            for sen in seniority:
                # Data quality issue: Support missing some months
                if dept == 'Support' and d.month in [11, 12, 1]:
                    continue
                    
                headcount = np.random.randint(20, 100)
                new_hires = np.random.randint(0, 5)
                base_attrition = np.random.uniform(0.0, 0.05)
                
                # Attrition jump Q2 2026 (Apr-Jun)
                if d.year == 2026 and d.month in [4, 5, 6]:
                    base_attrition *= 3.0
                    
                # Engineering highest spike (senior)
                if dept == 'Engineering' and sen == 'Senior' and d.year == 2026 and d.month in [4, 5, 6]:
                    base_attrition *= 2.5
                    
                # Sales stable
                if dept == 'Sales' and d.year == 2026 and d.month in [4, 5, 6]:
                    base_attrition = np.random.uniform(0.0, 0.05)
                    
                departures = int(headcount * base_attrition)
                voluntary_departures = int(departures * 0.8)
                
                data.append([d, dept, sen, headcount, new_hires, departures, voluntary_departures])
                
    df = pd.DataFrame(data, columns=['date', 'department', 'seniority', 'headcount', 'new_hires', 'departures', 'voluntary_departures'])
    df.to_csv('demo_hr.csv', index=False)
    print(f"demo_hr.csv generated with {len(df)} rows.")

def generate_ecommerce():
    set_seed(42)
    dates = pd.date_range(start='2026-01-01', end='2026-04-30', freq='W-MON')
    devices = ['Desktop', 'Mobile', 'Tablet']
    sources = ['Organic', 'Paid', 'Direct', 'Referral']
    
    data = []
    for d in dates:
        for dev in devices:
            for src in sources:
                sessions = np.random.randint(500, 2000)
                cvr = np.random.uniform(0.02, 0.08)
                aov = np.random.uniform(50, 150)
                return_rate = np.random.uniform(0.05, 0.10)
                
                # April trends
                if d.month == 4:
                    # Revenue dropped sharply (handled by less traffic/lower CVR)
                    return_rate *= 2.0 # Return rate increased across all channels
                    
                    if dev == 'Mobile' and src == 'Paid':
                        sessions = int(sessions * 0.1) # Collapsed ad budget
                        
                orders = int(sessions * cvr)
                revenue = orders * aov
                returns = int(orders * return_rate)
                
                data.append([d, dev, src, sessions, orders, revenue, returns])
                
    df = pd.DataFrame(data, columns=['date', 'device', 'traffic_source', 'sessions', 'orders', 'revenue', 'returns'])
    df.to_csv('demo_ecommerce.csv', index=False)
    print(f"demo_ecommerce.csv generated with {len(df)} rows.")

if __name__ == '__main__':
    # Ensure working directory is correct
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    generate_marketing()
    generate_hr()
    generate_ecommerce()
    print("Done generating CSVs.")
