#!/usr/bin/env python
# coding: utf-8

import streamlit as st
import numpy as np
import numpy_financial as npf
import pandas as pd
import random

# --- PAGE SETUP ---
st.set_page_config(page_title="Property Buy vs Rent Calculator", layout="wide")
st.title("🏠 Should You Buy a House in London?... tl;dr generally, no 🥲")
st.markdown("""
This app helps you compare buying vs renting in clear financial terms.

It calculates:
- how much cash you'd keep after buying & selling
- how much total rent you'd pay instead
- whether buying is cheaper than renting
- the opportunity cost of tying up your deposit
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
base_interest_rate = st.slider("Mortgage Interest Rate (%)", 0.5, 10.0, 4.25, step=0.05)
term_years = st.slider("Loan Term (years)", 5, 40, 25)

loan_amount = house_price - deposit
n_payments = term_years * 12

base_monthly_rate = base_interest_rate / 100 / 12
base_monthly_payment = npf.pmt(base_monthly_rate, n_payments, -loan_amount) if loan_amount > 0 else 0

st.metric(
    "Estimated Monthly Mortgage Payment (before risk adjustments)",
    f"£{base_monthly_payment:,.0f}"
)

# --- RENTAL SCENARIO ---
st.header("2. Rental Scenario")

rent_monthly = st.slider("Monthly Rent (£)", 500, 5000, 2250, step=50)
rent_growth = st.slider("Expected Annual Rent Increase (%)", 0.0, 10.0, 3.0, step=0.5)

# --- FEES & COSTS ---
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

# --- MARKET SCENARIO ---
st.header("5. Market Scenario or Manual Settings")

use_risk_scenario = st.checkbox("Enable Random or Manual Risk Scenario?", value=False)

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

monthly_rate = risk_interest_rate / 100 / 12
monthly_payment = npf.pmt(monthly_rate, n_payments, -loan_amount) if loan_amount > 0 else 0

st.metric("Monthly Mortgage Payment", f"£{monthly_payment:,.0f}")

# --- SALE CALCULATIONS ---
st.header("6. Property Appreciation & Sale")

sale_year = st.slider("House Sale Year", 1, 50, 5)
appreciation_rate = st.slider("Expected Annual Property Appreciation (%)", -5.0, 10.0, 2.6)
sale_fee_rate = st.slider("Sale Fee (% of sale value)", 0.0, 5.0, 3.0, step=0.1)

# Calculate future house value
adjusted_appreciation_rate = appreciation_rate + appreciation_rate_adj
sale_value = house_price * ((1 + adjusted_appreciation_rate / 100) ** sale_year)
sale_value *= (1 + renovation_uplift / 100)

sale_fees = sale_value * (sale_fee_rate / 100)

# --- MORTGAGE PRINCIPAL & INTEREST ---
principal_remaining = loan_amount
total_interest_paid = 0

for _ in range(sale_year * 12):
    interest_month = principal_remaining * monthly_rate
    principal_payment = monthly_payment - interest_month
    total_interest_paid += interest_month
    principal_remaining -= principal_payment
    if principal_remaining <= 0:
        principal_remaining = 0
        break

# --- TOTAL BUYING COSTS ---
actual_remortgages = max(0, (sale_year - 1) // 5)
total_remortgage_costs = actual_remortgages * remortgage_cost
transaction_fees = base_transaction_fees + total_remortgage_costs
total_maintenance_cost = annual_maintenance_cost * sale_year

buying_costs_total = (
    stamp_duty
    + renovation_costs
    + transaction_fees
    + total_maintenance_cost
    + total_interest_paid
)

# --- NET GAIN FROM BUYING ---
gross_proceeds = sale_value - sale_fees - principal_remaining

net_cash_after_buying = gross_proceeds - buying_costs_total

# ROI and IRR
roi = (net_cash_after_buying - deposit) / deposit if deposit > 0 else 0.0

irr_before_tax = npf.irr(
    [-deposit - (buying_costs_total - total_interest_paid)] + [0]*(sale_year-1) + [gross_proceeds]
)

# --- RENT CALCULATION ---
total_rent_paid = 0
current_rent = rent_monthly

for year in range(sale_year):
    total_rent_paid += current_rent * 12
    current_rent *= (1 + rent_growth / 100)

# --- DIFFERENCE CALCULATION ---
# Cost of renting = total rent
# Cost of buying = net cash position minus your deposit
net_cost_of_buying = deposit - net_cash_after_buying

difference_vs_rent = total_rent_paid - net_cost_of_buying

# --- OPPORTUNITY COST ---
alt_investment_rate = st.slider("Alternative Annual Investment Return (%)", 0.0, 10.0, 4.0, step=0.5)
alt_investment_value = deposit * ((1 + alt_investment_rate / 100) ** sale_year)

opportunity_cost = alt_investment_value - deposit
difference_adjusted = difference_vs_rent - opportunity_cost

# --- RESULTS ---
st.header("7. Results")

st.metric("Total Interest Paid", f"£{total_interest_paid:,.0f}")
st.metric("Gross Sale Proceeds (after fees and mortgage)", f"£{gross_proceeds:,.0f}")
st.metric("Net Cash After Buying (sale minus costs and interest)", f"£{net_cash_after_buying:,.0f}")
st.metric("Total Rent Paid Over Period", f"£{total_rent_paid:,.0f}")
st.metric("Difference vs Renting (positive = buying cheaper)", f"£{difference_vs_rent:,.0f}")
st.metric("Difference Adjusted for Opportunity Cost", f"£{difference_adjusted:,.0f}")

# --- SUMMARY ---
st.header("8. Plain-English Summary")

summary_text = f"""
- **Buying costs (stamp duty, fees, renovations, maintenance, interest):** £{buying_costs_total:,.0f}
- **Gross proceeds from selling house:** £{gross_proceeds:,.0f}
- **Net cash position after buying:** £{net_cash_after_buying:,.0f}
- **Total rent paid over {sale_year} years:** £{total_rent_paid:,.0f}
- **Estimated IRR on buying:** {irr_before_tax*100:.2f}%
- **ROI on cash invested:** {roi*100:.2f}%
"""

if net_cash_after_buying > deposit:
    summary_text += f"\n✅ Buying leaves you £{net_cash_after_buying - deposit:,.0f} ahead of your initial deposit."
else:
    summary_text += f"\n❌ Buying results in a loss of £{deposit - net_cash_after_buying:,.0f} vs your deposit."

if difference_vs_rent > 0:
    summary_text += f"\n\n✅ Buying is £{difference_vs_rent:,.0f} cheaper than renting over {sale_year} years."
else:
    summary_text += f"\n\n❌ Renting is £{abs(difference_vs_rent):,.0f} cheaper than buying over {sale_year} years."

summary_text += f"\n\n- **Potential alternative investment value:** £{alt_investment_value:,.0f}"
summary_text += f"\n- **Opportunity cost of tying up deposit:** £{opportunity_cost:,.0f}"
summary_text += f"\n- **Adjusted difference (after considering missed investment gains):** £{difference_adjusted:,.0f}"

st.markdown(summary_text)

# --- HISTORICAL DATA ---
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
