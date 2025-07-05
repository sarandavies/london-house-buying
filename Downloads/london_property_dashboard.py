#!/usr/bin/env python
# coding: utf-8

import streamlit as st
import numpy as np
import numpy_financial as npf
import pandas as pd
import random

# --- PAGE SETUP ---
st.set_page_config(page_title="Property Buy vs Rent Calculator", layout="wide")
st.title("🏠 Should You Buy a House in London?... tl;dr generally no 🥲")
st.markdown("""
This app helps you compare buying vs renting.  
It covers costs, risks, and potential gains so you can play out different scenarios.
""")

# --- HELPER FUNCTIONS ---
def calculate_stamp_duty(price):
    """
    Calculates stamp duty based on UK tax bands.
    """
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
deposit = st.slider("Deposit (£)", 0, house_price, 100_000, step=10_000)
base_interest_rate = st.slider("Mortgage Interest Rate (%)", 0.5, 10.0, 4.25, step=0.05)
term_years = st.slider("Loan Term (years)", 5, 40, 25)

loan_amount = house_price - deposit
n_payments = term_years * 12

# --- RENTAL COMPARISON ---
st.header("2. Rental Market Comparison")

st.markdown("""
While buying can protect you from certain costs, renting can also be a safe haven:
- No maintenance or repair costs
- Flexibility to leave if prices drop
- However, rent may increase over time.
""")

rent_monthly = st.slider("Current Monthly Rent (£)", 500, 5000, 2250, step=50)

rent_growth_rate = st.slider(
    "Expected Annual Rent Increase (%)",
    -2.0, 10.0, 3.0, step=0.1
)

# --- FEES ---
st.header("3. Buying Costs & Fees")

st.markdown("""
💡 **Why Remortgaging Matters**

- Most mortgages have a fixed rate for 2–5 years.
- After that, you usually remortgage to avoid high variable rates.
- Each remortgage costs legal, valuation, and arrangement fees.
- Over decades, these costs add up significantly.
""")

remortgage_cost_per_time = st.number_input(
    "Estimated Cost per Remortgage (£)",
    value=1_500,
    step=100
)

base_transaction_fees = st.number_input(
    "Other Transaction Fees (e.g. legal, searches) (£)",
    value=7_500,
    step=500
)

stamp_duty = calculate_stamp_duty(house_price)
st.metric("Stamp Duty (Estimated)", f"£{stamp_duty:,.0f}")

renovation_costs = st.number_input("Renovation Costs (£, optional)", value=0, step=1000)
renovation_uplift = st.slider(
    "Estimated % Uplift from Renovations (e.g. 2-5% conservative for minor works)",
    0.0, 50.0, 0.0, step=1.0
)

# --- ANNUAL OWNERSHIP COSTS ---
st.header("4. Annual Ownership Costs")

st.markdown("""
💡 **Why Annual Maintenance Matters**

Owning a property comes with hidden costs:
- repairs
- upkeep
- insurance
- unexpected replacements (boiler, roof, etc.)

Even without major renovations, a typical rule of thumb is:
- **0.5% to 1% of property value per year**

This can add £3–10k/year in London, depending on property size and age.
""")

annual_maintenance_rate = st.slider(
    "Estimated Annual Maintenance Cost (% of property value)",
    0.0, 2.0, 0.5, step=0.1
)
annual_maintenance_cost = house_price * (annual_maintenance_rate / 100)

# --- RISK WHEEL ---
st.header("🌀 Market Scenario or Manual Settings")

use_risk_scenario = st.checkbox("Enable Random or Manual Risk Scenario?", value=False)

# Default adjustments
appreciation_rate_adj = 0
risk_interest_rate = base_interest_rate

if use_risk_scenario:
    scenarios = [
        "Base Case (steady market)",
        "Interest Rate Spike / Asset Crash",
        "Interest Rates Drop / Asset Boom",
        "Major Structural Repairs"
    ]

    spin_wheel = st.checkbox("Spin the wheel randomly?", value=True)

    if spin_wheel:
        risk_scenario = random.choice(scenarios)
        st.write(f"**Random scenario selected:** {risk_scenario}")
    else:
        risk_scenario = st.selectbox(
            "Or manually choose a scenario:",
            scenarios
        )

    if risk_scenario == "Interest Rate Spike / Asset Crash":
        appreciation_rate_adj = -5
        risk_interest_rate = base_interest_rate + 2
        st.warning("Simulating market crash: lower appreciation, higher mortgage rate.")
    elif risk_scenario == "Interest Rates Drop / Asset Boom":
        appreciation_rate_adj = 3
        risk_interest_rate = max(0.5, base_interest_rate - 1)
        st.success("Simulating asset boom: higher appreciation, lower mortgage rate.")
    elif risk_scenario == "Major Structural Repairs":
        appreciation_rate_adj = 0
        renovation_costs += 50_000
        st.warning("Added £50,000 structural repair cost.")
    else:
        appreciation_rate_adj = 0
        risk_interest_rate = base_interest_rate
else:
    appreciation_rate_adj = 0
    risk_interest_rate = base_interest_rate

# --- MONTHLY PAYMENT ---
monthly_rate = risk_interest_rate / 100 / 12
monthly_payment = npf.pmt(monthly_rate, n_payments, -loan_amount)
st.metric("Estimated Monthly Mortgage Payment", f"£{monthly_payment:,.0f} (subject to market volatility)")

# --- CAPITAL APPRECIATION ---
st.header("5. Property Appreciation & ROI")

sale_year = st.slider("House Sale Year", 1, 50, 5)
appreciation_rate = st.slider("Expected Annual Property Appreciation (%)", -5.0, 10.0, 2.6)

# Remortgaging scaled to actual ownership period
actual_remortgages = max(0, (sale_year - 1) // 5)
total_remortgage_costs = actual_remortgages * remortgage_cost_per_time

transaction_fees = base_transaction_fees + total_remortgage_costs
total_maintenance_cost = annual_maintenance_cost * sale_year

fees_total = (
    transaction_fees
    + stamp_duty
    + renovation_costs
    + total_maintenance_cost
)

adjusted_appreciation_rate = appreciation_rate + appreciation_rate_adj

sale_value = house_price * ((1 + adjusted_appreciation_rate / 100) ** sale_year)
sale_value *= (1 + renovation_uplift / 100)

sale_fee_rate = st.slider("Sale Fee (% of sale value)", 0.0, 5.0, 3.0, step=0.1)
sale_fees = sale_value * (sale_fee_rate / 100)

gross_proceeds = sale_value - sale_fees - loan_amount

# Calculate interest paid over actual hold period
principal_remaining = loan_amount
total_interest_paid = 0

for _ in range(sale_year * 12):
    interest_month = principal_remaining * monthly_rate
    principal_payment = monthly_payment - interest_month
    total_interest_paid += interest_month
    principal_remaining -= principal_payment
    if principal_remaining <= 0:
        break

net_proceeds = gross_proceeds - fees_total
final_cash_after_sale = net_proceeds - total_interest_paid

roi = (final_cash_after_sale - deposit) / deposit if deposit > 0 else 0.0

irr_before_tax = npf.irr(
    [-deposit - fees_total] + [0] * (sale_year - 1) + [net_proceeds]
)

# --- RENT COST WITH GROWTH ---
total_rent_cost = 0
annual_rent = rent_monthly * 12

for year in range(1, sale_year + 1):
    annual_rent *= (1 + rent_growth_rate / 100)
    total_rent_cost += annual_rent

# --- UNRECOVERABLE COSTS ---
st.header("6. Unrecoverable Cost Comparison")

mortgage_unrecoverable = total_interest_paid + fees_total

st.metric("Unrecoverable Cost of Mortgage (£)", f"£{mortgage_unrecoverable:,.0f}")
st.metric("Total Rent Paid Over Period (£)", f"£{total_rent_cost:,.0f}")

# --- PROPERTY METRICS ---
st.header("7. Property Financial Metrics")

col1, col2 = st.columns(2)

with col1:
    st.metric("Expected Sale Value (£)", f"£{sale_value:,.0f}")
    st.metric("Gross Proceeds After Sale (£)", f"£{gross_proceeds:,.0f}")
    st.metric("Net Proceeds After Costs (£)", f"£{final_cash_after_sale:,.0f}")
    st.metric("IRR Before Tax", f"{irr_before_tax*100:.2f}%")
    st.metric("Return on Investment (ROI)", f"{roi*100:.2f}%")

# --- OPPORTUNITY COST ---
with col2:
    st.header("Alternative Investment Scenario")

    alt_investment_return = st.slider(
        "Alternative Annual Investment Return (%)",
        0.0, 10.0, 4.0, step=0.5
    )
    invested_alt = deposit * ((1 + alt_investment_return / 100) ** sale_year)

    st.metric("Potential Alternative Investment (£)", f"£{invested_alt:,.0f}")

# --- SUMMARY ---
st.header("8. Plain-English Summary")

difference_vs_rent = final_cash_after_sale - total_rent_cost

summary_text = f"""
- **Buying costs (fees, renovations, maintenance):** £{fees_total:,.0f}
- **Total interest paid over {sale_year} years:** £{total_interest_paid:,.0f}
- **Gross proceeds after sale fees and mortgage payoff:** £{gross_proceeds:,.0f}
- **Net cash after deducting all costs and interest:** £{final_cash_after_sale:,.0f}
- **Estimated IRR:** {irr_before_tax*100:.2f}%
- **ROI based on cash invested:** {roi*100:.2f}%
- **Total rent paid over same period (with growth):** £{total_rent_cost:,.0f}
- **Potential alternative investment value:** £{invested_alt:,.0f}

**Net financial outcome vs renting:** {"Up" if difference_vs_rent > 0 else "Down"} by £{abs(difference_vs_rent):,.0f}
"""

st.markdown(summary_text)

# --- DATA VISUALISATION ---
st.header("9. Historical Appreciation Data")

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
