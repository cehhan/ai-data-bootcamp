#!/bin/bash

# Read JSON files
KPI=$(cat data/kpi_output.json)
DAILY=$(cat data/daily_data.json)
SPARK=$(cat data/sparkline_data.json)

# Extract values from KPI JSON
TOTAL_SALES=$(echo "$KPI" | grep -o '"totalSales":\s*[0-9.]*' | head -1 | grep -o '[0-9.]*')
TOTAL_PROFIT=$(echo "$KPI" | grep -o '"totalProfit":\s*[0-9.]*' | head -1 | grep -o '[0-9.]*')
TOTAL_ORDERS=$(echo "$KPI" | grep -o '"totalOrders":\s*[0-9]*' | head -1 | grep -o '[0-9]*')
TOTAL_RETURNED=$(echo "$KPI" | grep -o '"totalReturned":\s*[0-9]*' | head -1 | grep -o '[0-9]*')
REGRESSION=$(echo "$KPI" | grep -o '"regression":\s*{[^}]*}')

echo "✓ Data extracted:"
echo "  Total Sales: $TOTAL_SALES"
echo "  Total Profit: $TOTAL_PROFIT"
echo "  Total Orders: $TOTAL_ORDERS"
echo "  Total Returned: $TOTAL_RETURNED"
