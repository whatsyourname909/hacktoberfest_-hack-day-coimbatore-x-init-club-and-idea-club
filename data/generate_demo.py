"""Regenerate the deterministic adversarial sales example used in the demo."""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REGIONS = [f"Area {i}" for i in range(1, 9)]
ROWS = []


def add(date: str, customer: str, product: str, region: str, revenue: int, unit_price: int) -> None:
    ROWS.append({"date": date, "customer": customer, "product": product, "region": region,
                 "units": revenue // unit_price, "unit_price": unit_price, "revenue": revenue})


# February: ₹10.0M total. The conspicuous departing customer is ₹164.8K (8% of the eventual decline).
add("2026-02-01", "Churned account", "Premium", "Area 1", 164_800, 200)
add("2026-02-01", "Existing accounts", "Premium", "Area 1", 460_200, 200)
for region in REGIONS[1:]:
    add("2026-02-01", "Existing accounts", "Premium", region, 625_000, 200)
for region in REGIONS:
    add("2026-02-01", "Existing accounts", "Value", region, 625_000, 50)

# March: ₹7.94M total. Seven areas decline by ₹288.4K each (14% of the net change); Area 8 declines by ₹41.2K.
for region in REGIONS[:7]:
    add("2026-03-01", "Existing accounts", "Premium", region, 300_000, 200)
add("2026-03-01", "Existing accounts", "Premium", "Area 8", 720_000, 200)
for region in REGIONS[:7]:
    add("2026-03-01", "Existing accounts", "Value", region, 661_600, 50)
add("2026-03-01", "Existing accounts", "Value", "Area 8", 488_800, 50)

pd.DataFrame(ROWS).to_csv(ROOT / "data" / "demo_sales.csv", index=False)
