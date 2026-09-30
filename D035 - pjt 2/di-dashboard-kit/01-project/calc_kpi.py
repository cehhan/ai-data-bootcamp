#!/usr/bin/env python3
import csv
from datetime import datetime
from collections import defaultdict
import math

# CSV 파일 읽기
orders = []
with open('data/temp_orders.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        orders.append(row)

# Returns 읽기
returns_set = set()
with open('data/temp_returns.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row.get('Returned') == 'Yes':
            returns_set.add(row['Order ID'])

print("=" * 60)
print("STEP 2 — KPI 계산")
print("=" * 60)

# 기본 통계
print(f"\n데이터 개요:")
print(f"  - 총 주문 건수: {len(orders):,}")
print(f"  - 반품된 주문: {len(returns_set):,}")

# 날짜 범위
dates = [datetime.strptime(o['Order Date'], '%m/%d/%Y') for o in orders]
min_date, max_date = min(dates), max(dates)
print(f"  - 기간: {min_date.strftime('%Y-%m-%d')} ~ {max_date.strftime('%Y-%m-%d')}")

# Category별 집계
category_data = defaultdict(lambda: {
    'sales': 0.0,
    'profit': 0.0,
    'orders': set(),
    'orders_returned': 0,
    'discounts': [],
})

for order in orders:
    cat = order['Category']
    order_id = order['Order ID']
    sales = float(order['Sales'])
    profit = float(order['Profit'])
    discount = float(order['Discount'])

    category_data[cat]['sales'] += sales
    category_data[cat]['profit'] += profit
    category_data[cat]['orders'].add(order_id)
    category_data[cat]['discounts'].append(discount)

    if order_id in returns_set:
        category_data[cat]['orders_returned'] += 1

# chData 생성 (이익률 내림차순)
chData = []
for cat, data in category_data.items():
    unique_orders = len(data['orders'])
    margin = data['profit'] / data['sales'] if data['sales'] > 0 else 0
    discount_avg = sum(data['discounts']) / len(data['discounts']) if data['discounts'] else 0

    chData.append({
        'ch': cat,
        'sales': data['sales'],
        'profit': data['profit'],
        'margin': margin,
        'discountAvg': discount_avg,
        'orders': unique_orders,
        'ordersReturned': data['orders_returned'],
    })

# 이익률로 정렬
chData.sort(key=lambda x: x['margin'], reverse=True)

print(f"\n카테고리별 KPI (이익률 내림차순):")
print("-" * 100)
for item in chData:
    print(f"{item['ch']:20} | 매출: ${item['sales']:>12,.2f} | 이익: ${item['profit']:>10,.2f} | " +
          f"이익률: {item['margin']*100:>6.2f}% | 주문: {item['orders']:>6,} | " +
          f"할인률: {item['discountAvg']*100:>5.2f}% | 반품: {item['ordersReturned']:>4}")

# 전체 KPI
total_sales = sum(item['sales'] for item in chData)
total_profit = sum(item['profit'] for item in chData)
total_orders = sum(item['orders'] for item in chData)
total_returned = sum(item['ordersReturned'] for item in chData)
total_margin = total_profit / total_sales if total_sales > 0 else 0
aov = total_sales / total_orders if total_orders > 0 else 0
return_rate = total_returned / total_orders if total_orders > 0 else 0

print("\n" + "=" * 100)
print("전체 KPI:")
print(f"  총매출: ${total_sales:,.2f}")
print(f"  총이익: ${total_profit:,.2f}")
print(f"  이익률: {total_margin*100:.2f}%")
print(f"  주문건수: {total_orders:,}")
print(f"  객단가(AOV): ${aov:.2f}")
print(f"  반품률: {return_rate*100:.2f}%")

# 선형회귀: 할인율 vs 이익률
print("\n" + "=" * 100)
print("선형회귀 분석 (할인율 vs 이익률):")
print("-" * 100)

# Sub-Category 단위로 분석 (시뮬레이터에 사용)
sub_category_data = defaultdict(lambda: {
    'sales': 0.0,
    'profit': 0.0,
    'orders': set(),
    'discounts': [],
})

for order in orders:
    subcat = order['Sub-Category']
    order_id = order['Order ID']
    sales = float(order['Sales'])
    profit = float(order['Profit'])
    discount = float(order['Discount'])

    sub_category_data[subcat]['sales'] += sales
    sub_category_data[subcat]['profit'] += profit
    sub_category_data[subcat]['orders'].add(order_id)
    sub_category_data[subcat]['discounts'].append(discount)

# Sub-Category별 계산
x_vals = []  # 할인율
y_vals = []  # 이익률
subcat_items = []

for subcat, data in sub_category_data.items():
    if data['sales'] > 0:
        x = sum(data['discounts']) / len(data['discounts']) if data['discounts'] else 0
        y = data['profit'] / data['sales']
        x_vals.append(x)
        y_vals.append(y)
        subcat_items.append({
            'name': subcat,
            'discount_avg': x,
            'margin': y,
            'sales': data['sales'],
            'profit': data['profit'],
        })

# 선형회귀 계산
n = len(x_vals)
if n > 1:
    mean_x = sum(x_vals) / n
    mean_y = sum(y_vals) / n

    numerator = sum((x_vals[i] - mean_x) * (y_vals[i] - mean_y) for i in range(n))
    denominator = sum((x_vals[i] - mean_x) ** 2 for i in range(n))

    slope = numerator / denominator if denominator != 0 else 0
    intercept = mean_y - slope * mean_x

    print(f"회귀식: 이익률 = {intercept:.6f} + {slope:.6f} × 할인율")
    print(f"즉, newMargin = {intercept:.6f} + {slope:.6f} × newDiscount")
else:
    slope, intercept = 0, 0
    print("표본 부족 (2개 이상 필요)")

# Sub-Category별 적자 확인
print("\n" + "=" * 100)
print("Sub-Category 적자 분석 (카테고리 합계에 묻힐 수 있는 인사이트):")
print("-" * 100)

negatives = [item for item in subcat_items if item['profit'] < 0]
negatives.sort(key=lambda x: x['profit'])

if negatives:
    for item in negatives[:5]:  # 상위 5개 적자
        print(f"{item['name']:25} | 매출: ${item['sales']:>10,.0f} | 이익: ${item['profit']:>10,.2f} | 이익률: {item['margin']*100:>7.2f}%")
else:
    print("적자 Sub-Category 없음")

# JSON 형식 출력 (다음 스텝에서 사용)
print("\n" + "=" * 100)
print("STEP 3에서 사용할 JSON 데이터:")
print("-" * 100)

import json

output_data = {
    'chData': [
        {
            'ch': item['ch'],
            'sales': round(item['sales'], 2),
            'profit': round(item['profit'], 2),
            'discountAvg': round(item['discountAvg'], 4),
            'orders': item['orders'],
            'ordersReturned': item['ordersReturned'],
        }
        for item in chData
    ],
    'totals': {
        'totalSales': round(total_sales, 2),
        'totalProfit': round(total_profit, 2),
        'totalOrders': total_orders,
        'totalReturned': total_returned,
    },
    'regression': {
        'slope': round(slope, 6),
        'intercept': round(intercept, 6),
    },
    'date_range': {
        'start': min_date.strftime('%Y-%m-%d'),
        'end': max_date.strftime('%Y-%m-%d'),
    }
}

print(json.dumps(output_data, indent=2))

# 파일로 저장
with open('data/kpi_output.json', 'w', encoding='utf-8') as f:
    json.dump(output_data, f, indent=2, ensure_ascii=False)

print("\n✓ KPI 데이터 저장 완료: data/kpi_output.json")
