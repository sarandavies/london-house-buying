import streamlit as st
import numpy as np
import numpy_financial as npf
import pandas as pd
import random


# ============================================================
# PAGE SETUP
# ============================================================

st.set_page_config(
    page_title="London Buy vs Rent Calculator",
    layout="wide"
)

st.title("🏠 London Buy vs Rent Calculator")

st.markdown(
    """
Compare buying a London property with renting and investing the cash you would
otherwise put into the purchase.

The model works month by month so that both options start with the same financial
resources and differences in housing costs are invested (or withdrawn) over time.
"""
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def calculate_standard_sdlt(
    price: float,
    additional_property: bool = False
) -> float:

    bands = [
        (125_000, 0.00),
        (250_000, 0.02),
        (925_000, 0.05),
        (1_500_000, 0.10),
        (float("inf"), 0.12),
    ]

    surcharge = 0.05 if additional_property else 0.0

    tax = 0.0
    lower = 0.0

    for upper, rate in bands:

        taxable = max(
            0.0,
            min(price, upper) - lower
        )

        tax += taxable * (rate + surcharge)

        if price <= upper:
            break

        lower = upper

    return tax


def calculate_sdlt(
    price: float,
    first_time_buyer: bool,
    additional_property: bool
) -> float:

    if (
        first_time_buyer
        and not additional_property
        and price <= 500_000
    ):

        return max(
            0.0,
            price - 300_000
        ) * 0.05

    return calculate_standard_sdlt(
        price,
        additional_property
    )


def payment_for_balance(
    balance: float,
    annual_rate_pct: float,
    remaining_months: int
) -> float:

    if balance <= 0 or remaining_months <= 0:
        return 0.0

    monthly_rate = annual_rate_pct / 100 / 12

    if monthly_rate == 0:
        return balance / remaining_months

    return float(
        npf.pmt(
            monthly_rate,
            remaining_months,
            -balance
        )
    )


# ============================================================
# MARKET SCENARIOS
# ============================================================

MARKET_SCENARIOS = {

    "Steady market": {

        "description": (
            "A relatively normal environment with modest property growth, "
            "moderate rent increases and broadly stable mortgage rates."
        ),

        "property_growth_path": [
            2.5
        ],

        "post_fix_rate": 4.5,
        "rent_growth": 3.0,
        "service_charge_growth": 3.0,
    },


    "Housing boom": {

        "description": (
            "Strong housing demand pushes prices higher, mortgage rates ease "
            "and rents continue to grow."
        ),

        "property_growth_path": [
            6.0,
            5.0,
            4.0,
            3.5,
            3.0,
        ],

        "post_fix_rate": 3.5,
        "rent_growth": 4.0,
        "service_charge_growth": 3.5,
    },


    "Financial / housing crash": {

        "description": (
            "A severe first-year property correction followed by a weak period "
            "and gradual recovery. Refinancing also becomes more expensive."
        ),

        "property_growth_path": [
            -15.0,
            -3.0,
            0.0,
            2.0,
            2.5,
        ],

        "post_fix_rate": 6.5,
        "rent_growth": 1.5,
        "service_charge_growth": 4.0,
    },


    "Stagflation / high rates": {

        "description": (
            "House prices barely grow while mortgage rates, rents and service "
            "charges remain relatively high."
        ),

        "property_growth_path": [
            0.0,
            0.5,
            1.0,
            1.5,
            2.0,
        ],

        "post_fix_rate": 6.0,
        "rent_growth": 5.0,
        "service_charge_growth": 5.0,
    },


    "Rate-cut recovery": {

        "description": (
            "A sluggish first couple of years followed by stronger property "
            "growth as borrowing costs fall."
        ),

        "property_growth_path": [
            0.0,
            1.0,
            3.5,
            4.0,
            3.0,
        ],

        "post_fix_rate": 3.25,
        "rent_growth": 3.5,
        "service_charge_growth": 3.0,
    },
}


# ============================================================
# RANDOM SCENARIO SECTION
# ============================================================

st.header("🎲 Market scenario")

st.markdown(
    """
Run the model using your own assumptions, select a market environment,
or roll the dice and stress-test the purchase against a random scenario.
"""
)

scenario_mode = st.radio(
    "How do you want to model the market?",
    [
        "Use my assumptions",
        "Choose a scenario",
        "Roll the dice",
    ],
    horizontal=True
)


if "random_market_scenario" not in st.session_state:
    st.session_state.random_market_scenario = "Steady market"


selected_scenario = None


if scenario_mode == "Choose a scenario":

    selected_scenario = st.selectbox(
        "Market scenario",
        list(MARKET_SCENARIOS.keys())
    )


elif scenario_mode == "Roll the dice":

    if st.button(
        "🎲 Roll the dice",
        type="primary"
    ):

        st.session_state.random_market_scenario = random.choice(
            list(MARKET_SCENARIOS.keys())
        )

    selected_scenario = (
        st.session_state.random_market_scenario
    )


if selected_scenario is not None:

    scenario = MARKET_SCENARIOS[
        selected_scenario
    ]

    st.subheader(
        f"Scenario: {selected_scenario}"
    )

    st.info(
        scenario["description"]
    )

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Rate after fixed period",
        f"{scenario['post_fix_rate']:.2f}%"
    )

    c2.metric(
        "Rent growth",
        f"{scenario['rent_growth']:.1f}%"
    )

    c3.metric(
        "Service-charge growth",
        f"{scenario['service_charge_growth']:.1f}%"
    )


    property_path_text = " → ".join(
        f"{x:+.1f}%"
        for x in scenario[
            "property_growth_path"
        ]
    )

    st.caption(
        "Property-growth path for the first five years: "
        f"{property_path_text}. "
        "The final listed rate is then used for later years."
    )


# ============================================================
# 1. PROPERTY AND MORTGAGE
# ============================================================

st.header("1. Property and mortgage")

col1, col2 = st.columns(2)


with col1:

    house_price = st.number_input(
        "Purchase price (£)",
        min_value=100_000,
        max_value=3_000_000,
        value=850_000,
        step=10_000
    )

    deposit = st.number_input(
        "Deposit (£)",
        min_value=0,
        max_value=int(house_price),
        value=min(
            150_000,
            int(house_price)
        ),
        step=10_000
    )

    mortgage_rate = st.number_input(
        "Initial mortgage rate (%)",
        min_value=0.0,
        max_value=15.0,
        value=4.25,
        step=0.05
    )

    mortgage_term_years = st.number_input(
        "Mortgage term (years)",
        min_value=1,
        max_value=40,
        value=30,
        step=1
    )


with col2:

    fixed_period_years = st.number_input(
        "Initial fixed / product period (years)",
        min_value=1,
        max_value=10,
        value=5,
        step=1
    )

    manual_post_fix_rate = st.number_input(
        "Assumed mortgage rate after fixed period (%)",
        min_value=0.0,
        max_value=15.0,
        value=4.50,
        step=0.05,
        disabled=selected_scenario is not None
    )

    remortgage_fee = st.number_input(
        "Cost each time you remortgage (£)",
        min_value=0,
        value=1_500,
        step=100
    )

    sale_year = st.slider(
        "How long will you own the property? (years)",
        1,
        40,
        7
    )


post_fix_rate = (
    MARKET_SCENARIOS[
        selected_scenario
    ]["post_fix_rate"]
    if selected_scenario is not None
    else manual_post_fix_rate
)


loan_amount = max(
    0.0,
    house_price - deposit
)

initial_monthly_payment = payment_for_balance(
    loan_amount,
    mortgage_rate,
    int(mortgage_term_years * 12)
)

ltv = (
    loan_amount / house_price
    if house_price
    else 0
)


m1, m2, m3 = st.columns(3)

m1.metric(
    "Mortgage",
    f"£{loan_amount:,.0f}"
)

m2.metric(
    "Initial monthly payment",
    f"£{initial_monthly_payment:,.0f}"
)

m3.metric(
    "Loan-to-value",
    f"{ltv * 100:.1f}%"
)


# ============================================================
# 2. RENTING AND ALTERNATIVE INVESTMENT
# ============================================================

st.header(
    "2. Renting and alternative investment"
)

col1, col2, col3 = st.columns(3)


with col1:

    rent_monthly = st.number_input(
        "Comparable monthly rent (£)",
        min_value=0,
        value=2_750,
        step=50
    )


with col2:

    manual_rent_growth = st.number_input(
        "Annual rent growth (%)",
        min_value=-5.0,
        max_value=15.0,
        value=3.0,
        step=0.25,
        disabled=selected_scenario is not None
    )


with col3:

    alt_investment_return = st.number_input(
        "Annual return on renter's investments (%)",
        min_value=-10.0,
        max_value=20.0,
        value=5.0,
        step=0.25
    )


rent_growth = (
    MARKET_SCENARIOS[
        selected_scenario
    ]["rent_growth"]
    if selected_scenario is not None
    else manual_rent_growth
)


st.caption(
    "The renter starts by investing all cash that the buyer spends upfront, "
    "then invests any monthly savings versus owning."
)


# ============================================================
# 3. PURCHASE, OWNERSHIP AND SALE COSTS
# ============================================================

st.header(
    "3. Purchase, ownership and sale costs"
)

col1, col2 = st.columns(2)


with col1:

    first_time_buyer = st.checkbox(
        "First-time buyer",
        value=False
    )

    additional_property = st.checkbox(
        "This will be an additional residential property",
        value=False
    )

    purchase_fees = st.number_input(
        "Purchase costs excluding SDLT (£)",
        min_value=0,
        value=5_000,
        step=500,
        help=(
            "For example solicitor, survey, "
            "mortgage/product and moving costs."
        )
    )

    renovation_costs = st.number_input(
        "Upfront renovation spend (£)",
        min_value=0,
        value=0,
        step=1_000
    )

    renovation_value_added = st.number_input(
        "Estimated value added by renovation (£)",
        min_value=0,
        value=0,
        step=1_000,
        help=(
            "The amount you think the works add "
            "to the market value of the property."
        )
    )


with col2:

    annual_maintenance_rate = st.number_input(
        "Annual maintenance (% of property value)",
        min_value=0.0,
        max_value=5.0,
        value=0.5,
        step=0.1
    )

    annual_service_charge = st.number_input(
        "Annual service charge (£)",
        min_value=0,
        value=0,
        step=250
    )

    manual_service_charge_growth = st.number_input(
        "Annual service-charge growth (%)",
        min_value=-5.0,
        max_value=15.0,
        value=3.0,
        step=0.25,
        disabled=selected_scenario is not None
    )

    annual_ground_rent = st.number_input(
        "Annual ground rent / estate charge (£)",
        min_value=0,
        value=0,
        step=50
    )

    major_works_cost = st.number_input(
        "One-off major works / structural cost (£)",
        min_value=0,
        value=0,
        step=1_000
    )

    major_works_year = st.number_input(
        "Year major works occur",
        min_value=1,
        max_value=40,
        value=min(
            3,
            sale_year
        ),
        step=1
    )


service_charge_growth = (
    MARKET_SCENARIOS[
        selected_scenario
    ]["service_charge_growth"]
    if selected_scenario is not None
    else manual_service_charge_growth
)


if (
    first_time_buyer
    and additional_property
):

    st.warning(
        "A purchase cannot normally be both a first-time "
        "purchase and an additional property. The calculator "
        "therefore applies the additional-property SDLT rates."
    )


stamp_duty = calculate_sdlt(
    house_price,
    first_time_buyer,
    additional_property
)


st.metric(
    "Estimated SDLT",
    f"£{stamp_duty:,.0f}"
)


# ============================================================
# 4. PROPERTY VALUE AND SELLING ASSUMPTIONS
# ============================================================

st.header(
    "4. Property value and selling assumptions"
)

col1, col2, col3 = st.columns(3)


with col1:

    manual_appreciation_rate = st.number_input(
        "Annual property appreciation (%)",
        min_value=-10.0,
        max_value=15.0,
        value=2.5,
        step=0.25,
        disabled=selected_scenario is not None
    )


with col2:

    estate_agent_fee_rate = st.number_input(
        "Estate-agent selling fee (% of sale price)",
        min_value=0.0,
        max_value=5.0,
        value=1.5,
        step=0.1
    )


with col3:

    fixed_sale_costs = st.number_input(
        "Other sale costs (£)",
        min_value=0,
        value=3_000,
        step=500
    )


# ============================================================
# PROPERTY GROWTH FUNCTION
# ============================================================

def get_property_growth_for_year(
    year_number: int,
    override_growth: float = None
) -> float:

    if override_growth is not None:
        return override_growth

    if selected_scenario is None:
        return manual_appreciation_rate

    path = MARKET_SCENARIOS[
        selected_scenario
    ]["property_growth_path"]

    index = min(
        year_number - 1,
        len(path) - 1
    )

    return path[index]


# ============================================================
# MODEL
# ============================================================

def simulate(
    holding_years: int,
    property_growth_override: float = None
):

    holding_months = int(
        holding_years * 12
    )

    term_months = int(
        mortgage_term_years * 12
    )

    product_months = max(
        1,
        int(fixed_period_years * 12)
    )


    # --------------------------------------------------------
    # INITIAL CASH
    # --------------------------------------------------------

    initial_cash_required = (
        deposit
        + stamp_duty
        + purchase_fees
        + renovation_costs
    )


    renter_portfolio = float(
        initial_cash_required
    )


    monthly_investment_return = (
        (1 + alt_investment_return / 100)
        ** (1 / 12)
        - 1
    )


    # --------------------------------------------------------
    # MORTGAGE
    # --------------------------------------------------------

    principal_remaining = float(
        loan_amount
    )

    current_mortgage_rate = float(
        mortgage_rate
    )

    remaining_term_months = term_months

    current_payment = payment_for_balance(
        principal_remaining,
        current_mortgage_rate,
        remaining_term_months
    )


    # --------------------------------------------------------
    # RENT AND OTHER COSTS
    # --------------------------------------------------------

    current_rent = float(
        rent_monthly
    )

    current_service_charge = float(
        annual_service_charge
    )


    # Start property value including any renovation uplift.
    current_property_value = float(
        house_price
        + renovation_value_added
    )


    # --------------------------------------------------------
    # TOTALS
    # --------------------------------------------------------

    total_rent_paid = 0.0
    total_interest_paid = 0.0
    total_principal_paid = 0.0

    total_maintenance_paid = 0.0
    total_service_charge_paid = 0.0
    total_ground_rent_paid = 0.0

    total_remortgage_fees = 0.0
    total_major_works = 0.0

    total_mortgage_payments = 0.0

    monthly_rows = []


    # --------------------------------------------------------
    # MONTHLY SIMULATION
    # --------------------------------------------------------

    for month in range(
        holding_months
    ):

        # Renter's existing portfolio compounds.
        renter_portfolio *= (
            1
            + monthly_investment_return
        )


        # ----------------------------------------------------
        # CURRENT YEAR AND PROPERTY GROWTH
        # ----------------------------------------------------

        current_year = (
            month // 12
        ) + 1

        annual_property_growth = (
            get_property_growth_for_year(
                current_year,
                property_growth_override
            )
        )

        monthly_property_growth = (
            (1 + annual_property_growth / 100)
            ** (1 / 12)
            - 1
        )

        current_property_value *= (
            1
            + monthly_property_growth
        )


        # ----------------------------------------------------
        # REMORTGAGE
        # ----------------------------------------------------

        remortgage_cost_this_month = 0.0

        if (
            month > 0
            and month % product_months == 0
            and principal_remaining > 0
            and remaining_term_months > 0
        ):

            current_mortgage_rate = float(
                post_fix_rate
            )

            current_payment = payment_for_balance(
                principal_remaining,
                current_mortgage_rate,
                remaining_term_months
            )

            remortgage_cost_this_month = float(
                remortgage_fee
            )

            total_remortgage_fees += (
                remortgage_cost_this_month
            )


        # ----------------------------------------------------
        # MORTGAGE PAYMENT
        # ----------------------------------------------------

        mortgage_payment_this_month = 0.0
        interest_this_month = 0.0
        principal_this_month = 0.0


        if (
            principal_remaining > 0
            and remaining_term_months > 0
        ):

            monthly_mortgage_rate = (
                current_mortgage_rate
                / 100
                / 12
            )

            interest_this_month = (
                principal_remaining
                * monthly_mortgage_rate
            )

            scheduled_principal = max(
                0.0,
                current_payment
                - interest_this_month
            )

            principal_this_month = min(
                principal_remaining,
                scheduled_principal
            )

            mortgage_payment_this_month = (
                interest_this_month
                + principal_this_month
            )

            principal_remaining -= (
                principal_this_month
            )

            remaining_term_months -= 1

            if principal_remaining < 0.01:
                principal_remaining = 0.0


        # ----------------------------------------------------
        # OWNERSHIP COSTS
        # ----------------------------------------------------

        maintenance_this_month = (
            current_property_value
            * annual_maintenance_rate
            / 100
            / 12
        )

        service_charge_this_month = (
            current_service_charge
            / 12
        )

        ground_rent_this_month = (
            annual_ground_rent
            / 12
        )


        major_works_this_month = 0.0

        if (
            major_works_cost > 0
            and month
            == int(
                (major_works_year - 1)
                * 12
            )
        ):

            major_works_this_month = float(
                major_works_cost
            )

            total_major_works += (
                major_works_this_month
            )


        buyer_cash_cost = (
            mortgage_payment_this_month
            + maintenance_this_month
            + service_charge_this_month
            + ground_rent_this_month
            + remortgage_cost_this_month
            + major_works_this_month
        )


        # ----------------------------------------------------
        # RENT VS BUY CASHFLOW DIFFERENCE
        # ----------------------------------------------------

        renter_portfolio += (
            buyer_cash_cost
            - current_rent
        )


        # ----------------------------------------------------
        # TOTALS
        # ----------------------------------------------------

        total_rent_paid += (
            current_rent
        )

        total_interest_paid += (
            interest_this_month
        )

        total_principal_paid += (
            principal_this_month
        )

        total_mortgage_payments += (
            mortgage_payment_this_month
        )

        total_maintenance_paid += (
            maintenance_this_month
        )

        total_service_charge_paid += (
            service_charge_this_month
        )

        total_ground_rent_paid += (
            ground_rent_this_month
        )


        # Current buyer equity before eventual selling costs.
        buyer_equity = (
            current_property_value
            - principal_remaining
        )


        monthly_rows.append(
            {
                "Month":
                    month + 1,

                "Property value":
                    current_property_value,

                "Mortgage balance":
                    principal_remaining,

                "Buyer equity":
                    buyer_equity,

                "Renter portfolio":
                    renter_portfolio,

                "Rent":
                    current_rent,

                "Buyer monthly cash cost":
                    buyer_cash_cost,

                "Annual property growth":
                    annual_property_growth,

                "Mortgage rate":
                    current_mortgage_rate,
            }
        )


        # ----------------------------------------------------
        # ANNUAL RENT / SERVICE CHARGE INFLATION
        # ----------------------------------------------------

        if (
            (month + 1) % 12 == 0
        ):

            current_rent *= (
                1
                + rent_growth / 100
            )

            current_service_charge *= (
                1
                + service_charge_growth / 100
            )


    # --------------------------------------------------------
    # SALE
    # --------------------------------------------------------

    sale_value = (
        current_property_value
    )

    estate_agent_fee = (
        sale_value
        * estate_agent_fee_rate
        / 100
    )

    total_sale_costs = (
        estate_agent_fee
        + fixed_sale_costs
    )


    buyer_net_worth = (
        sale_value
        - total_sale_costs
        - principal_remaining
    )


    renter_net_worth = (
        renter_portfolio
    )


    difference = (
        buyer_net_worth
        - renter_net_worth
    )


    return {

        "buyer_net_worth":
            buyer_net_worth,

        "renter_net_worth":
            renter_net_worth,

        "difference":
            difference,

        "sale_value":
            sale_value,

        "mortgage_balance":
            principal_remaining,

        "sale_costs":
            total_sale_costs,

        "initial_cash_required":
            initial_cash_required,

        "total_rent_paid":
            total_rent_paid,

        "total_interest_paid":
            total_interest_paid,

        "total_principal_paid":
            total_principal_paid,

        "total_mortgage_payments":
            total_mortgage_payments,

        "total_maintenance_paid":
            total_maintenance_paid,

        "total_service_charge_paid":
            total_service_charge_paid,

        "total_ground_rent_paid":
            total_ground_rent_paid,

        "total_remortgage_fees":
            total_remortgage_fees,

        "total_major_works":
            total_major_works,

        "monthly":
            pd.DataFrame(
                monthly_rows
            ),
    }


# ============================================================
# RUN MODEL
# ============================================================

result = simulate(
    sale_year
)


# ============================================================
# 5. RESULT
# ============================================================

st.header("5. Result")


if result["difference"] > 0:

    st.success(
        f"Buying leaves you "
        f"£{result['difference']:,.0f} "
        f"better off after "
        f"{sale_year} years."
    )


elif result["difference"] < 0:

    st.info(
        f"Renting leaves you "
        f"£{abs(result['difference']):,.0f} "
        f"better off after "
        f"{sale_year} years."
    )


else:

    st.info(
        f"Buying and renting are approximately "
        f"equal after {sale_year} years."
    )


c1, c2, c3 = st.columns(3)


c1.metric(
    "Buyer ending net worth",
    f"£{result['buyer_net_worth']:,.0f}"
)


c2.metric(
    "Renter ending portfolio",
    f"£{result['renter_net_worth']:,.0f}"
)


c3.metric(
    "Buy minus rent",
    f"£{result['difference']:,.0f}"
)


st.caption(
    "Buyer ending net worth is the equity released after selling the property, "
    "paying sale costs and clearing the outstanding mortgage. The renter's "
    "ending wealth is the investment portfolio built from the upfront cash "
    "they did not spend on buying and subsequent monthly savings."
)


# ============================================================
# WHAT HAPPENED
# ============================================================

st.subheader(
    "What happened over the period"
)


summary = pd.DataFrame(
    {

        "Item": [

            "Cash required upfront to buy",

            "Estimated sale value",

            "Mortgage remaining at sale",

            "Total mortgage payments",

            "of which interest",

            "of which principal",

            "Maintenance paid",

            "Service charges paid",

            "Ground rent / estate charges",

            "Remortgage fees",

            "Major works",

            "Selling costs",

            "Total rent paid",
        ],


        "Amount": [

            result[
                "initial_cash_required"
            ],

            result[
                "sale_value"
            ],

            result[
                "mortgage_balance"
            ],

            result[
                "total_mortgage_payments"
            ],

            result[
                "total_interest_paid"
            ],

            result[
                "total_principal_paid"
            ],

            result[
                "total_maintenance_paid"
            ],

            result[
                "total_service_charge_paid"
            ],

            result[
                "total_ground_rent_paid"
            ],

            result[
                "total_remortgage_fees"
            ],

            result[
                "total_major_works"
            ],

            result[
                "sale_costs"
            ],

            result[
                "total_rent_paid"
            ],
        ],
    }
)


summary["Amount"] = (
    summary["Amount"]
    .map(
        lambda x:
        f"£{x:,.0f}"
    )
)


st.dataframe(
    summary,
    use_container_width=True,
    hide_index=True
)


# ============================================================
# 6. BREAK-EVEN HOLDING PERIOD
# ============================================================

st.header(
    "6. Break-even holding period"
)


break_even_rows = []


for years in range(
    1,
    31
):

    year_result = simulate(
        years
    )

    break_even_rows.append(
        {

            "Years":
                years,

            "Buy minus rent (£)":
                year_result[
                    "difference"
                ],
        }
    )


break_even_df = pd.DataFrame(
    break_even_rows
)


st.line_chart(
    break_even_df.set_index(
        "Years"
    )
)


positive_years = (
    break_even_df.loc[
        break_even_df[
            "Buy minus rent (£)"
        ] >= 0,
        "Years"
    ]
)


if len(
    positive_years
) > 0:

    first_break_even = int(
        positive_years.iloc[0]
    )

    st.write(
        f"On these assumptions, buying first "
        f"overtakes renting at approximately "
        f"**year {first_break_even}**."
    )


else:

    st.write(
        "On these assumptions, buying does "
        "not overtake renting within 30 years."
    )


# ============================================================
# 7. PROPERTY GROWTH SENSITIVITY
# ============================================================

st.header(
    "7. Sensitivity to property-price growth"
)

st.caption(
    "This deliberately overrides the selected market scenario and asks: "
    "what happens if property prices instead grow at a constant rate?"
)


sensitivity_rates = np.arange(
    -2.0,
    6.01,
    0.5
)


sensitivity_rows = []


for growth in sensitivity_rates:

    sensitivity_result = simulate(
        sale_year,
        property_growth_override=float(
            growth
        )
    )

    sensitivity_rows.append(
        {

            "Annual property growth (%)":
                growth,

            "Buy minus rent (£)":
                sensitivity_result[
                    "difference"
                ],
        }
    )


sensitivity_df = pd.DataFrame(
    sensitivity_rows
)


st.line_chart(
    sensitivity_df.set_index(
        "Annual property growth (%)"
    )
)


closest_index = (
    sensitivity_df[
        "Buy minus rent (£)"
    ]
    .abs()
    .idxmin()
)


closest_growth = float(
    sensitivity_df.loc[
        closest_index,
        "Annual property growth (%)"
    ]
)


st.write(
    f"The closest point to break-even within the range shown is around "
    f"**{closest_growth:.1f}% annual property-price growth**."
)


# ============================================================
# 8. NET WORTH PATH
# ============================================================

st.header(
    "8. Wealth path"
)


chart_df = (
    result[
        "monthly"
    ]
    .copy()
)


chart_df["Year"] = (
    chart_df["Month"]
    / 12
)


wealth_chart = (
    chart_df
    .set_index(
        "Year"
    )
    [
        [
            "Buyer equity",
            "Renter portfolio",
        ]
    ]
)


st.line_chart(
    wealth_chart
)


# ============================================================
# 9. PROPERTY AND MORTGAGE PATH
# ============================================================

st.header(
    "9. Property and mortgage path"
)


property_chart = (
    chart_df
    .set_index(
        "Year"
    )
    [
        [
            "Property value",
            "Mortgage balance",
        ]
    ]
)


st.line_chart(
    property_chart
)


# ============================================================
# SCENARIO DETAILS
# ============================================================

if selected_scenario is not None:

    st.header(
        "10. Scenario path"
    )


    annual_data = (
        chart_df
        .copy()
    )

    annual_data["Year number"] = (
        np.ceil(
            annual_data["Year"]
        )
        .astype(int)
    )


    annual_data = (
        annual_data
        .groupby(
            "Year number"
        )
        .agg(
            {
                "Annual property growth":
                    "first",

                "Mortgage rate":
                    "last",
            }
        )
        .reset_index()
    )


    annual_data.columns = [
        "Year",
        "Property growth (%)",
        "Mortgage rate (%)",
    ]


    st.dataframe(
        annual_data,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# EXPLANATION
# ============================================================

with st.expander(
    "How this model works"
):

    st.markdown(
        """
### Buying

The buyer pays:

- the deposit
- SDLT
- purchase fees
- renovations
- monthly mortgage payments
- maintenance
- service charges
- ground rent or estate charges
- remortgage fees
- any major works

Mortgage principal is **not treated as money lost**. It reduces the outstanding
mortgage and therefore increases the buyer's equity.

At the end of the chosen holding period, the house is sold. Selling costs and the
remaining mortgage are deducted from the sale proceeds.


### Renting

The renter starts with the exact amount of cash that would have been required
upfront to purchase the property.

That money is invested.

Every month:

- if owning costs more than renting, the renter invests the difference
- if renting costs more than owning, the difference is withdrawn from the portfolio

The portfolio compounds at the selected alternative investment return.


### Market scenarios

When a predefined scenario is selected, the model changes:

- property-price growth
- the assumed mortgage rate after the fixed period
- rent growth
- service-charge growth

The crash scenario is modelled as an initial shock followed by recovery, rather
than assuming house prices decline indefinitely.

The property-growth sensitivity section separately tests constant annual growth
rates so you can see how dependent the result is on the property market.
"""
    )


# ============================================================
# FOOTER
# ============================================================

st.caption(
    "Educational model only. It simplifies taxes, investment returns, "
    "mortgage products, insurance, opportunity costs and individual "
    "circumstances. Check current tax rules and actual mortgage and "
    "transaction costs before making a financial decision."
)
