#!/usr/bin/env python
# coding: utf-8

# In[5]:


import streamlit as st
import numpy as np
import numpy_financial as npf
import pandas as pd

# --- PAGE SETUP ---
st.set_page_config(page_title="London Property Buy vs Rent Calculator", layout="wide")
st.title("🏠 Should You Buy a House in London?")
st.markdown("This tool helps you compare the cost of buying vs renting over a fixed time period, with explanations for each section.")

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

# --- FEES ---
st.header("3. Buying Costs & Fees")
remortgage_times = st.slider("Number of Remortgages (every 5 years typical)", 0, 10, 5)
transaction_fees = st.number_input("Transaction Fees (£)", value=15_000, step=1000)
stamp_duty = st.number_input("Stamp Duty (£)", value=17_500, step=1000)
renovation_costs = st.number_input("Renovation Costs (£, optional)", value=0, step=1000)

fees_total = transaction_fees + stamp_duty + renovation_costs

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
sale_value = house_price * ((1 + (appreciation_rate / 100)) ** sale_year)
sale_fees = sale_value * 0.03  # Assume 3% sale fee

net_proceeds = sale_value - sale_fees - loan_amount
irr_before_tax = npf.irr([-deposit - fees_total] + [0]*(sale_year-1) + [net_proceeds])

st.metric("Expected Sale Value (£)", f"£{sale_value:,.0f}")
st.metric("IRR Before Tax", f"{irr_before_tax*100:.2f}%")

# --- SUMMARY ---
st.header("6. Summary")
st.write(f"- Buying incurs £{mortgage_unrecoverable:,.0f} in unrecoverable costs.")
st.write(f"- Renting incurs £{rent_unrecoverable:,.0f} in comparable unrecoverable costs.")
st.write(f"- Net proceeds after {sale_year} years: £{net_proceeds:,.0f}.")
st.write(f"- Estimated IRR (before tax): {irr_before_tax*100:.2f}%.")

# --- DATA VISUALISATION (Optional) ---
st.header("7. Historical Appreciation Data")
historical = pd.DataFrame({
    "Start Year": [2000, 2005, 2010, 2015, 2020],
    "End Year":   [2005, 2010, 2015, 2020, 2025],
    "Start Price": [163577, 282548, 290200, 531000, 486000],
    "End Price":   [282548, 290200, 531000, 486000, 552000],
    "London Return %": [11.6, 0.5, 12.8, -1.8, 2.6]
})

st.dataframe(historical)

st.line_chart(historical.set_index("End Year")["London Return %"])

# --- FOOTER ---
st.caption("This model is for educational and illustrative purposes only. Always seek financial advice for personal decisions.")

