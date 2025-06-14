{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": 5,
   "id": "026e79c9-f760-4617-b56a-799a6ac09d38",
   "metadata": {},
   "outputs": [
    {
     "data": {
      "text/plain": [
       "DeltaGenerator()"
      ]
     },
     "execution_count": 5,
     "metadata": {},
     "output_type": "execute_result"
    }
   ],
   "source": [
    "import streamlit as st\n",
    "import numpy as np\n",
    "import numpy_financial as npf\n",
    "import pandas as pd\n",
    "\n",
    "# --- PAGE SETUP ---\n",
    "st.set_page_config(page_title=\"London Property Buy vs Rent Calculator\", layout=\"wide\")\n",
    "st.title(\"🏠 Should You Buy a House in London?\")\n",
    "st.markdown(\"This tool helps you compare the cost of buying vs renting over a fixed time period, with explanations for each section.\")\n",
    "\n",
    "# --- USER INPUTS ---\n",
    "st.header(\"1. Property & Loan Details\")\n",
    "house_price = st.slider(\"Total House Price (£)\", 100_000, 2_000_000, 600_000, step=10_000)\n",
    "deposit = st.slider(\"Deposit (£)\", 0, house_price, 100_000, step=10_000)\n",
    "interest_rate = st.slider(\"Mortgage Interest Rate (%)\", 0.5, 10.0, 4.25, step=0.05)\n",
    "term_years = st.slider(\"Loan Term (years)\", 5, 40, 25)\n",
    "\n",
    "loan_amount = house_price - deposit\n",
    "monthly_rate = interest_rate / 100 / 12\n",
    "n_payments = term_years * 12\n",
    "monthly_payment = npf.pmt(monthly_rate, n_payments, -loan_amount)\n",
    "\n",
    "st.metric(\"Monthly Mortgage Payment\", f\"£{monthly_payment:,.0f}\")\n",
    "\n",
    "# --- RENTAL COMPARISON ---\n",
    "st.header(\"2. Rental Market Comparison\")\n",
    "rent_monthly = st.slider(\"Monthly Rent (£)\", 500, 5000, 2250, step=50)\n",
    "gross_yield = st.slider(\"Gross Rental Yield (%)\", 1.0, 10.0, 4.5)\n",
    "net_yield = st.slider(\"Net Rental Yield (%)\", 0.5, 6.0, 2.5)\n",
    "\n",
    "# --- FEES ---\n",
    "st.header(\"3. Buying Costs & Fees\")\n",
    "remortgage_times = st.slider(\"Number of Remortgages (every 5 years typical)\", 0, 10, 5)\n",
    "transaction_fees = st.number_input(\"Transaction Fees (£)\", value=15_000, step=1000)\n",
    "stamp_duty = st.number_input(\"Stamp Duty (£)\", value=17_500, step=1000)\n",
    "renovation_costs = st.number_input(\"Renovation Costs (£, optional)\", value=0, step=1000)\n",
    "\n",
    "fees_total = transaction_fees + stamp_duty + renovation_costs\n",
    "\n",
    "# --- UNRECOVERABLE COSTS ---\n",
    "st.header(\"4. Unrecoverable Cost Comparison\")\n",
    "interest_paid = (monthly_payment * n_payments) - loan_amount\n",
    "mortgage_unrecoverable = interest_paid + fees_total\n",
    "rent_unrecoverable = rent_monthly * 12 * term_years * (1 - (net_yield / gross_yield))\n",
    "\n",
    "st.metric(\"Unrecoverable Cost of Mortgage (£)\", f\"£{mortgage_unrecoverable:,.0f}\")\n",
    "st.metric(\"Unrecoverable Cost of Renting (£)\", f\"£{rent_unrecoverable:,.0f}\")\n",
    "\n",
    "# --- CAPITAL APPRECIATION ---\n",
    "st.header(\"5. Property Appreciation & ROI\")\n",
    "sale_year = st.slider(\"House Sale Year\", 1, 50, 5)\n",
    "appreciation_rate = st.slider(\"Annual Property Appreciation (%)\", -5.0, 10.0, 2.6)\n",
    "sale_value = house_price * ((1 + (appreciation_rate / 100)) ** sale_year)\n",
    "sale_fees = sale_value * 0.03  # Assume 3% sale fee\n",
    "\n",
    "net_proceeds = sale_value - sale_fees - loan_amount\n",
    "irr_before_tax = npf.irr([-deposit - fees_total] + [0]*(sale_year-1) + [net_proceeds])\n",
    "\n",
    "st.metric(\"Expected Sale Value (£)\", f\"£{sale_value:,.0f}\")\n",
    "st.metric(\"IRR Before Tax\", f\"{irr_before_tax*100:.2f}%\")\n",
    "\n",
    "# --- SUMMARY ---\n",
    "st.header(\"6. Summary\")\n",
    "st.write(f\"- Buying incurs £{mortgage_unrecoverable:,.0f} in unrecoverable costs.\")\n",
    "st.write(f\"- Renting incurs £{rent_unrecoverable:,.0f} in comparable unrecoverable costs.\")\n",
    "st.write(f\"- Net proceeds after {sale_year} years: £{net_proceeds:,.0f}.\")\n",
    "st.write(f\"- Estimated IRR (before tax): {irr_before_tax*100:.2f}%.\")\n",
    "\n",
    "# --- DATA VISUALISATION (Optional) ---\n",
    "st.header(\"7. Historical Appreciation Data\")\n",
    "historical = pd.DataFrame({\n",
    "    \"Start Year\": [2000, 2005, 2010, 2015, 2020],\n",
    "    \"End Year\":   [2005, 2010, 2015, 2020, 2025],\n",
    "    \"Start Price\": [163577, 282548, 290200, 531000, 486000],\n",
    "    \"End Price\":   [282548, 290200, 531000, 486000, 552000],\n",
    "    \"London Return %\": [11.6, 0.5, 12.8, -1.8, 2.6]\n",
    "})\n",
    "\n",
    "st.dataframe(historical)\n",
    "\n",
    "st.line_chart(historical.set_index(\"End Year\")[\"London Return %\"])\n",
    "\n",
    "# --- FOOTER ---\n",
    "st.caption(\"This model is for educational and illustrative purposes only. Always seek financial advice for personal decisions.\")"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3 (ipykernel)",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.12.7"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 5
}
