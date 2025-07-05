#!/usr/bin/env python
# coding: utf-8

import streamlit as st
import numpy as np
import numpy_financial as npf
import pandas as pd

# --- PAGE SETUP ---
st.set_page_config(page_title="Property Buy vs Rent Calculator", layout="wide")
st.title("🏠 Should You Buy a House in London?... tl;dr No 🥲")
st.markdown(
    """
    This tool helps you compare buying vs renting over a fixed time period.
    It explains costs, risks, and potential gains so you can make an informed decision.
    """
)


# --- HELPER FUNCTIONS --- Interest rates depending on price
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
deposit = st.slider("Deposit (£)", 0, house_price, 100_000, step=10_000)
interest_rate = st.slider("Mortgage Interest Rate (%)", 0.5, 10.0, 4.25, step=0.05)
term_years = st.slider("Loan Term (years)", 5, 40, 25)

loan_amount = house_price - deposit
monthly_rate = interest_rate / 100 / 12
n_payments = term_years * 12
monthly_payment = npf.pmt(monthly_rate, n_payments, -loan_amount)

st.metric("Monthly Mortgage Payment", f"£{monthly_payment:,.0f}")

# --- RENTAL COMPARISON ---
st.header("2. Rental Market Comparison")
rent_monthly = st.slider("Monthly Rent (£)", 500, 5000, 2250, step=50)
gross_yield = st.slider("Gross Rental Yield (%)", 1.0, 10.0, 4.5)
net_yield = st.slider("Net Rental Yield (%)", 0.5, 6.0, 2.5)

st.markdown("""
**Why Gross and Net Yields Matter:**

- Landlords aim to earn a net profit (net yield) after costs.
- The gap between gross and net yield shows the hidden costs of owning.
- Even renters care about yields because they influence:
    - how high rents might go
    - whether renting is truly cheaper than buying
""")

# --- FEES ---
st.header("3. Buying Costs & Fees")
remortgage_times = st.slider("Number of Remortgages (every 5 years typical)", 0, 10, 5)
transaction_fees = st.number_input("Transaction Fees (£)", value=15_000, step=1000)
stamp_duty = calculate_stamp_duty(house_price)
st.metric("Stamp Duty (Estimated)", f"£{stamp_duty:,.0f}")
renovation_costs = st.number_input("Renovation Costs (£, optional)", value=0, step=1000)
renovation_uplift = st.slider("Estimated % Uplift from Renovations", 0.0, 50.0, 0.0, step=1.0)

fees_total = transaction_fees + stamp_duty + renovation_costs

# --- RISK WHEEL ---
st.header("🌀 Risk Wheel – Choose Your Market Scenario")

risk_scenario = st.selectbox(
    "Pick a scenario to simulate:",
    [
        "Base Case (steady market)",
        "Interest Rate Spike / Asset Crash",
        "Interest Rates Drop / Asset Boom",
        "Major Structural Repairs"
    ]
)

# Adjust parameters based on scenario
if risk_scenario == "Interest Rate Spike / Asset Crash":
    appreciation_rate_adj = -5
    interest_rate += 2
    st.warning("Simulating market crash: lower appreciation, higher mortgage rate.")
elif risk_scenario == "Interest Rates Drop / Asset Boom":
    appreciation_rate_adj = 3
    interest_rate = max(0.5, interest_rate - 1)
    st.success("Simulating asset boom: higher appreciation, lower mortgage rate.")
elif risk_scenario == "Major Structural Repairs":
    appreciation_rate_adj = 0
    renovation_costs += 50_000
    fees_total = transaction_fees + stamp_duty + renovation_costs
    st.warning("Added £50,000 structural repair cost.")
else:
    appreciation_rate_adj = 0
    st.info("Base case scenario selected.")

# --- UNRECOVERABLE COSTS ---
st.header("4. Unrecoverable Cost Comparison")

interest_paid = (monthly_payment * n_payments) - loan_amount
mortgage_unrecoverable = interest_paid + fees_total
rent_unrecoverable = rent_monthly * 12 * term_years * (1 - (net_yield / gross_yield))

st.metric("Unrecoverable Cost of Mortgage (£)", f"£{mortgage_unrecoverable:,.0f}")
st.metric("Unrecoverable Cost of Renting (£)", f"£{rent_unrecoverable:,.0f}")

# --- CAPITAL APPRECIATION ---
st.header("5. Property Appreciation & ROI")

sale_year = st.slider("House Sale Year", 1, 50, 5)
appreciation_rate = st.slider("Annual Property Appreciation (%)", -5.0, 10.0, 2.6)

# Adjust for risk scenario
adjusted_appreciation_rate = appreciation_rate + appreciation_rate_adj

sale_value = house_price * ((1 + (adjusted_appreciation_rate / 100)) ** sale_year)
sale_value *= (1 + renovation_uplift / 100)

sale_fees = sale_value * 0.03  # Assume 3% sale fee
net_proceeds = sale_value - sale_fees - loan_amount
irr_before_tax = npf.irr([-deposit - fees_total] + [0]*(sale_year-1) + [net_proceeds])

# Calculate ROI relative to total outlay
total_outlay = deposit + fees_total
roi = (net_proceeds - total_outlay) / total_outlay

# Compare owning vs renting
buy_net_result = net_proceeds - mortgage_unrecoverable
difference_vs_rent = buy_net_result + rent_unrecoverable

st.metric("Expected Sale Value (£)", f"£{sale_value:,.0f}")
st.metric("IRR Before Tax", f"{irr_before_tax*100:.2f}%")
st.metric("Return on Investment (ROI)", f"{roi*100:.2f}%")

# --- SUMMARY ---
st.header("6. Plain-English Summary")

summary_text = f"""
- **Buying costs (including interest and fees):** £{mortgage_unrecoverable:,.0f}
- **Renting costs over {term_years} years:** £{rent_unrecoverable:,.0f}
- **Estimated sale value:** £{sale_value:,.0f}
- **Cash left after selling:** £{net_proceeds:,.0f}
- **Estimated IRR:** {irr_before_tax*100:.2f}%
- **ROI based on total cash invested:** {roi*100:.2f}%

**Net financial outcome vs renting:** {"Ahead" if difference_vs_rent > 0 else "Behind"} by £{abs(difference_vs_rent):,.0f}
"""

st.markdown(summary_text)

# --- DATA VISUALISATION ---
st.header("7. Historical Appreciation Data")

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



