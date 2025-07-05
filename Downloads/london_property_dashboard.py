#!/usr/bin/env python
# coding: utf-8

import streamlit as st
import numpy as np
import numpy_financial as npf
import pandas as pd

# --- PAGE SETUP ---
st.set_page_config(page_title="Property Buy vs Rent Calculator", layout="wide")
st.title("🏠 Should You Buy a House in London?... tl;dr generally, no 🥲")
st.markdown("""
This app helps you compare buying vs renting.

It calculates:
- your true cash left after buying
- total rent paid over time
- a clear, single difference between the two options
""")

# --- HELPER FUNCTIONS ---
def calculate_stamp_duty(price):
    bands = [
        (125_000, 0.00),
        (250_000, 0.02),
        (925_000, 0.05),
        (1_500_000, 0.10),
        (float('inf'), 0.12)
    ]

    tax = 0.0
    lower_limit = 0.0

    for upper_limit, rate in bands:
        if price > upper_limit:
            taxed_amount = upper_limit - lower_limit
            tax += taxed_amount * rate
            lower_limit = upper_limit
        else:
            taxed_amount = price - lower_limit
            tax += taxed_amount * rate
            break

    return tax

# --- USER INPUTS ---
st.header("1. Property & Loan Details")

house_price = st.slider("Total House Price (£)", 100_000, 2_000_000, 600_000, step=10_000)
deposit = st.slider("Deposit (£)", 0, house_price, 60_000, step=10_000)
interest_rate = st.slider("Mortgage Interest Rate (%)", 0.5, 10.0, 4.25, step=0.05)
term_years = st.slider("Loan Term (years)", 5, 40, 25)

loan_amount = house_price - deposit
n_payments = term_years * 12

base_monthly_rate = interest_rate / 100 / 12
base_monthly_payment = npf.pmt(base_monthly_rate, n_payments, -loan_amount) if loan_amount > 0 else 0

st.metric("Estimated Monthly Mortgage Payment (before sale)", f"£{base_monthly_payment:,.0f}")

# --- RENTAL COMPARISON ---
st.header("2. Rental Scenario")

rent_monthly = st.slider("Monthly Rent (£)", 500, 5000, 2250, step=50)
rent_growth = st.slider("Expected Annual Rent Increase (%)", 0.0, 10.0, 3.0, step=0.5)

# --- FEES ---
st.header("3. Buying Costs & Fees")

remortgage_cost = st.number_input("Estimated Cost per Remortgage (£)", value=1_500, step=100)
base_transaction_fees = st.number_input("Other Transaction Fees (legal, searches etc.) (£)", value=7_500, step=500)

stamp_duty = calculate_stamp_duty(house_price)
st.metric("Stamp Duty (Estimated)", f"£{stamp_duty:,.0f}")

renovation_costs = st.number_input("Renovation Costs (£, optional)", value=0, step=1000)
renovation_uplift = st.slider("Estimated % Uplift from Renovations", 0.0, 50.0, 0.0, step=1.0)

# --- OWNERSHIP COSTS ---
st.header("4. Annual Ownership Costs")

annual_maintenance_rate = st.slider("Annual Maintenance Cost (% of property value)", 0.0, 2.0, 0.5, step=0.1)
annual_maintenance_cost = house_price * (annual_maintenance_rate / 100)

# --- APPRECIATION AND SALE ---
st.header("5. Property Sale & Outcomes")

sale_year = st.slider("House Sale Year", 1, 50, 5)
appreciation_rate = st.slider("Expected Annual Property Appreciation (%)", -5.0, 10.0, 2.6)
sale_fee_rate = st.slider("Sale Fee (% of sale value)", 0.0, 5.0, 3.0, step=0.1)

# Calculate sale price
sale_value = house_price * ((1 + appreciation_rate / 100) ** sale_year)
sale_value *= (1 + renovation_uplift / 100)

sale_fees = sale_value * (sale_fee_rate / 100)

# --- MORTGAGE CALCULATIONS ---
# Track balance and interest paid
principal_remaining = loan_amount
total_interest_paid = 0

for _ in range(sale_year * 12):
    interest_month = principal_remaining * base_monthly_rate
    principal_payment = base_monthly_payment - interest_month
    total_interest_paid += interest_month
    principal_remaining -= principal_payment
    if principal_remaining <= 0:
        principal_remaining = 0
        break

# --- BUYING COSTS TOTAL ---
actual_remortgages = max(0, (sale_year - 1) // 5)
total_remortgage_costs = actual_remortgages * remortgage_cost
transaction_fees = base_transaction_fees + total_remortgage_costs
total_maintenance_cost = annual_maintenance_cost * sale_year

buying_costs = (
    stamp_duty
    + renovation_costs
    + transaction_fees
    + total_maintenance_cost
)

gross_proceeds = sale_value - sale_fees - principal_remaining

net_cash_from_sale = gross_proceeds - buying_costs - total_interest_paid

roi = (net_cash_from_sale - deposit) / deposit if deposit > 0 else 0.0

irr_before_tax = npf.irr(
    [-deposit - buying_costs] + [0] * (sale_year - 1) + [gross_proceeds]
)

# --- RENT CALCULATION ---
total_rent_paid = 0
current_rent = rent_monthly

for year in range(sale_year):
    total_rent_paid += current_rent * 12
    current_rent *= (1 + rent_growth / 100)

# --- COMPARISON ---
difference = net_cash_from_sale - total_rent_paid

# --- RESULTS ---
st.header("6. Results")

st.metric("Total Interest Paid", f"£{total_interest_paid:,.0f}")
st.metric("Net Cash After Buying (sale proceeds minus all costs)", f"£{net_cash_from_sale:,.0f}")
st.metric("Total Rent Paid Over Period", f"£{total_rent_paid:,.0f}")
st.metric("Difference (Buying minus Renting)", f"£{difference:,.0f}")

# --- SUMMARY ---
st.header("7. Plain-English Summary")

if net_cash_from_sale >= 0:
    net_text = f"Buying leaves you with £{net_cash_from_sale:,.0f} in cash after all costs and interest."
else:
    net_text = f"Buying results in a loss of £{abs(net_cash_from_sale):,.0f} after all costs and interest."

if difference > 0:
    compare_text = f"✅ Buying is £{difference:,.0f} better than renting over {sale_year} years."
else:
    compare_text = f"❌ Renting is £{abs(difference):,.0f} cheaper than buying over {sale_year} years."

summary_text = f"""
- **Buying costs (stamp duty, fees, renovations, maintenance):** £{buying_costs:,.0f}
- **Total interest paid over {sale_year} years:** £{total_interest_paid:,.0f}
- **Gross proceeds from selling house:** £{gross_proceeds:,.0f}
- **Net cash after buying:** {net_text}
- **Total rent paid over same period:** £{total_rent_paid:,.0f}
- **Estimated IRR on buying:** {irr_before_tax*100:.2f}%
- **ROI on cash invested:** {roi*100:.2f}%
- {compare_text}
"""

st.markdown(summary_text)

# --- DATA VISUALISATION ---
st.header("8. Historical Appreciation Data")

historical = pd.DataFrame({
    "Start Year": [2000, 2005, 2010, 2015, 2020],
    "End Year":   [2005, 2010, 2015, 2020, 2025],
    "Start Price": [163577, 282548, 290200, 531000, 486000],
    "End Price":   [282548, 290200, 531000, 486000, 552000],
    "London Return %": [11.6, 0.5, 12.8, -1.8, 2.6]
})

historical["End Year"] = historical["End Year"].astype(str)

st.dataframe(historical)
st.line_chart(historical.set_index("End Year")["London Return %"])

# --- FOOTER ---
st.caption("I made this dashboard for fun - This model is for educational and illustrative purposes only. Always seek financial advice for personal decisions.")
