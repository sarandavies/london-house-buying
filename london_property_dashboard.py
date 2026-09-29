import streamlit as st
import numpy as np
import numpy_financial as npf
import pandas as pd
import json
from urllib.request import Request, urlopen
import plotly.express as px
import plotly.graph_objects as go


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
    """
    England / Northern Ireland residential SDLT rates
    applying from 1 April 2025.
    """

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
    """
    Apply first-time buyer relief where eligible.
    Otherwise use normal residential SDLT.
    """

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

    monthly_rate = (
        annual_rate_pct / 100 / 12
    )

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

    post_fix_rate = st.number_input(
        "Assumed mortgage rate after each product period (%)",
        min_value=0.0,
        max_value=15.0,
        value=4.50,
        step=0.05
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

    rent_growth = st.number_input(
        "Annual rent growth (%)",
        min_value=-5.0,
        max_value=15.0,
        value=3.0,
        step=0.25
    )


with col3:

    alt_investment_return = st.number_input(
        "Annual return on renter's investments (%)",
        min_value=-10.0,
        max_value=20.0,
        value=5.0,
        step=0.25
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
            "Use the amount you think the works add "
            "to the property's market value, rather "
            "than a percentage uplift."
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

    service_charge_growth = st.number_input(
        "Annual service-charge growth (%)",
        min_value=-5.0,
        max_value=15.0,
        value=3.0,
        step=0.25
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


if (
    first_time_buyer
    and additional_property
):
    st.warning(
        "A purchase cannot normally be both a first-time "
        "purchase and an additional property. The SDLT "
        "calculation therefore uses the additional-property rates."
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

st.caption(
    "This calculator models standard England / Northern Ireland "
    "residential SDLT and first-time-buyer relief. Check HMRC "
    "for unusual circumstances."
)


# ============================================================
# 4. PROPERTY VALUE AND SELLING ASSUMPTIONS
# ============================================================

st.header(
    "4. Property value and selling assumptions"
)

col1, col2, col3 = st.columns(3)


with col1:

    appreciation_rate = st.number_input(
        "Annual property appreciation (%)",
        min_value=-10.0,
        max_value=15.0,
        value=2.5,
        step=0.25
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
# MODEL
# ============================================================

def simulate(
    holding_years: int,
    property_growth_pct: float = None
):

    growth_pct = (
        appreciation_rate
        if property_growth_pct is None
        else property_growth_pct
    )

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


    # The renter invests the exact amount that the buyer
    # has to spend upfront.
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

    remaining_term_months = (
        term_months
    )

    current_payment = payment_for_balance(
        principal_remaining,
        current_mortgage_rate,
        remaining_term_months
    )


    # --------------------------------------------------------
    # RENT / SERVICE CHARGE
    # --------------------------------------------------------

    current_rent = float(
        rent_monthly
    )

    current_service_charge = float(
        annual_service_charge
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

        # Existing renter portfolio compounds.
        renter_portfolio *= (
            1
            + monthly_investment_return
        )


        # ----------------------------------------------------
        # REMORTGAGE
        # ----------------------------------------------------

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

            total_remortgage_fees += (
                remortgage_fee
            )

            # Buyer pays the remortgage fee.
            # Renter therefore gets to invest the
            # equivalent cash.
            renter_portfolio += (
                remortgage_fee
            )


        mortgage_payment_this_month = 0.0
        interest_this_month = 0.0
        principal_this_month = 0.0


        # ----------------------------------------------------
        # MORTGAGE PAYMENT
        # ----------------------------------------------------

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
        # PROPERTY VALUE
        # ----------------------------------------------------

        property_value_this_month = (
            house_price
            + renovation_value_added
        ) * (
            1
            + growth_pct / 100
        ) ** (
            (month + 1) / 12
        )


        # ----------------------------------------------------
        # OWNERSHIP COSTS
        # ----------------------------------------------------

        maintenance_this_month = (
            property_value_this_month
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
            + major_works_this_month
        )


        # ----------------------------------------------------
        # RENT VS BUY CASHFLOW DIFFERENCE
        # ----------------------------------------------------

        # If owning costs MORE than renting this month,
        # the renter invests the difference.
        #
        # If renting costs MORE than owning,
        # money is withdrawn from the renter's portfolio.

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


        monthly_rows.append(
            {
                "Month": month + 1,

                "Property value":
                    property_value_this_month,

                "Mortgage balance":
                    principal_remaining,

                "Renter portfolio":
                    renter_portfolio,

                "Rent":
                    current_rent,

                "Buyer monthly cash cost":
                    buyer_cash_cost,
            }
        )


        # ----------------------------------------------------
        # ANNUAL INFLATION
        # ----------------------------------------------------

        if (
            (month + 1)
            % 12
            == 0
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
        house_price
        + renovation_value_added
    ) * (
        1
        + growth_pct / 100
    ) ** holding_years


    estate_agent_fee = (
        sale_value
        * estate_agent_fee_rate
        / 100
    )

    total_sale_costs = (
        estate_agent_fee
        + fixed_sale_costs
    )


    # Buyer receives their equity after clearing the mortgage.
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

    verdict = (
        f"Buying leaves you "
        f"£{result['difference']:,.0f} "
        f"better off after "
        f"{sale_year} years"
    )

    st.success(verdict)


elif result["difference"] < 0:

    verdict = (
        f"Renting leaves you "
        f"£{abs(result['difference']):,.0f} "
        f"better off after "
        f"{sale_year} years"
    )

    st.info(verdict)


else:

    st.info(
        f"Buying and renting are approximately "
        f"equal after {sale_year} years"
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
    f"£{result['difference']:,.0f}",
    help=(
        "Positive means buying produces "
        "higher ending net worth; negative "
        "means renting does."
    )
)


st.caption(
    "Buyer ending net worth is sale proceeds after "
    "selling costs and repaying the outstanding mortgage. "
    "Renter ending net worth is the investment portfolio "
    "built from the buyer's upfront cash requirement and "
    "monthly cost differences."
)


# ============================================================
# BREAKDOWN
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

            "Ground rent / estate charges paid",

            "Remortgage fees paid",

            "Major works paid",

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
        f"overtakes renting at about "
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


sensitivity_rates = np.arange(
    -2.0,
    6.01,
    0.5
)


sensitivity_rows = []


for growth in sensitivity_rates:

    sensitivity_result = simulate(
        sale_year,
        property_growth_pct=float(
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


closest = sensitivity_df.iloc[
    (
        sensitivity_df[
            "Buy minus rent (£)"
        ]
        .abs()
    )
    .argsort()[:1]
]


closest_growth = float(
    closest[
        "Annual property growth (%)"
    ]
    .iloc[0]
)


st.write(
    f"Within the sensitivity range shown, "
    f"the closest point to break-even is "
    f"around **{closest_growth:.1f}% annual "
    f"property growth**."
)


# ============================================================
# 8. NET WORTH PATH
# ============================================================

st.header(
    "8. Net-worth path"
)


chart_df = (
    result[
        "monthly"
    ]
    .copy()
)


chart_df[
    "Year"
] = (
    chart_df[
        "Month"
    ]
    / 12
)


chart_df = (
    chart_df
    .set_index(
        "Year"
    )
    [
        [
            "Property value",
            "Mortgage balance",
            "Renter portfolio",
        ]
    ]
)


st.line_chart(
    chart_df
)


# ============================================================
# EXPLANATION
# ============================================================

with st.expander(
    "How this model works"
):

    st.markdown(
        """
- Both options start with the same financial resources.
- The buyer uses cash for the deposit, SDLT, purchase fees and renovations.
- The renter invests that same upfront amount instead.
- Each month, the renter's portfolio earns the selected investment return.
- If owning costs more than renting in a month, the renter invests the difference.
- If renting costs more, the difference is withdrawn from the renter's portfolio.
- Mortgage principal is not treated as an unrecoverable cost. It increases the buyer's equity by reducing the mortgage balance.
- At the end of the holding period, the buyer sells the property, pays selling costs and clears the remaining mortgage.
- The final comparison is buyer net sale equity versus renter investment portfolio.
"""
    )


# ============================================================
# 9. LONDON BOROUGH MARKET EXPLORER
# ============================================================

st.header("9. London borough house vs flat explorer")

st.markdown(
    """
Explore how **houses and flats have performed across London boroughs** using the
official UK House Price Index. Hover over the map for the headline numbers and
select a borough to inspect the full price path.

For the purposes of this view, **"houses" is an equal-weighted composite of the
detached, semi-detached and terraced UK HPI series**. That keeps the comparison
consistent across boroughs without pretending there is an official single
"house excluding flats" HPI series.
"""
)


UK_HPI_URL = (
    "https://publicdata.landregistry.gov.uk/market-trend-data/"
    "house-price-index-data/UK-HPI-full-file-2026-07.csv"
)

LONDON_BOROUGH_GEOJSON_URL = (
    "https://gis.london.gov.uk/arcgis/rest/services/apps/"
    "cultural_infrastructure_map_context_layers/MapServer/2/query"
    "?where=1%3D1&outFields=name%2Cgss_code&outSR=4326&f=geojson"
)


@st.cache_data(ttl=60 * 60 * 12, show_spinner=False)
def load_london_borough_market_data():
    """
    Download the official UK HPI full file and keep the 32 London boroughs.
    City of London is excluded because it is not a London borough and has a
    very small, atypical residential market.
    """

    hpi = pd.read_csv(UK_HPI_URL)

    hpi["Date"] = pd.to_datetime(
        hpi["Date"],
        dayfirst=True,
        errors="coerce"
    )

    london = hpi.loc[
        hpi["AreaCode"].astype(str).str.startswith("E090000")
    ].copy()

    london = london.loc[
        london["AreaCode"] != "E09000001"
    ].copy()

    house_index_cols = [
        "DetachedIndex",
        "SemiDetachedIndex",
        "TerracedIndex",
    ]

    house_price_cols = [
        "DetachedPrice",
        "SemiDetachedPrice",
        "TerracedPrice",
    ]

    london["HouseCompositeIndex"] = london[
        house_index_cols
    ].mean(axis=1, skipna=True)

    london["HouseCompositePrice"] = london[
        house_price_cols
    ].mean(axis=1, skipna=True)

    london = london.sort_values(
        ["AreaCode", "Date"]
    )

    req = Request(
        LONDON_BOROUGH_GEOJSON_URL,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    with urlopen(req, timeout=20) as response:
        borough_geojson = json.load(response)

    return london, borough_geojson


def build_borough_snapshot(
    london_df: pd.DataFrame,
    years_back: int,
):
    latest_date = london_df["Date"].max()

    target_start = (
        latest_date
        - pd.DateOffset(years=years_back)
    )

    rows = []

    for area_code, group in london_df.groupby(
        "AreaCode",
        sort=False
    ):
        group = (
            group
            .dropna(
                subset=[
                    "Date",
                    "HouseCompositeIndex",
                    "FlatIndex",
                ],
                how="any"
            )
            .sort_values("Date")
        )

        if group.empty:
            continue

        end_row = group.iloc[-1]

        start_pos = (
            group["Date"]
            .sub(target_start)
            .abs()
            .idxmin()
        )

        start_row = group.loc[
            start_pos
        ]

        house_change = (
            end_row["HouseCompositeIndex"]
            / start_row["HouseCompositeIndex"]
            - 1
        ) * 100

        flat_change = (
            end_row["FlatIndex"]
            / start_row["FlatIndex"]
            - 1
        ) * 100

        rows.append(
            {
                "AreaCode":
                    area_code,

                "Borough":
                    end_row["RegionName"],

                "StartDate":
                    start_row["Date"],

                "EndDate":
                    end_row["Date"],

                "HouseChange":
                    house_change,

                "FlatChange":
                    flat_change,

                "HouseMinusFlat":
                    house_change - flat_change,

                "HousePrice":
                    end_row["HouseCompositePrice"],

                "FlatPrice":
                    end_row["FlatPrice"],
            }
        )

    return pd.DataFrame(
        rows
    )


try:
    london_hpi, london_geojson = (
        load_london_borough_market_data()
    )

    latest_market_date = (
        london_hpi["Date"].max()
    )

    market_col1, market_col2, market_col3 = (
        st.columns(
            [1.0, 1.25, 1.25]
        )
    )

    with market_col1:
        lookback_years = st.slider(
            "Look-back period",
            min_value=5,
            max_value=20,
            value=10,
            step=1,
            key="borough_lookback_years",
        )

    with market_col2:
        map_metric_label = st.selectbox(
            "Colour the map by",
            [
                "House price growth",
                "Flat price growth",
                "House minus flat growth",
                "Latest flat price",
                "Latest house benchmark",
            ],
            index=2,
            key="borough_map_metric",
        )

    snapshot = build_borough_snapshot(
        london_hpi,
        lookback_years,
    )

    borough_names = sorted(
        snapshot["Borough"]
        .dropna()
        .unique()
        .tolist()
    )

    default_borough = (
        "Hackney"
        if "Hackney" in borough_names
        else borough_names[0]
    )

    with market_col3:
        chosen_borough = st.selectbox(
            "Detailed borough",
            borough_names,
            index=borough_names.index(
                default_borough
            ),
            key="borough_detail_selector",
        )

    metric_map = {
        "House price growth":
            (
                "HouseChange",
                f"{lookback_years}-year house growth (%)",
                "Blues",
            ),

        "Flat price growth":
            (
                "FlatChange",
                f"{lookback_years}-year flat growth (%)",
                "Oranges",
            ),

        "House minus flat growth":
            (
                "HouseMinusFlat",
                "House minus flat growth (percentage points)",
                "RdBu",
            ),

        "Latest flat price":
            (
                "FlatPrice",
                "Latest average flat price (£)",
                "Viridis",
            ),

        "Latest house benchmark":
            (
                "HousePrice",
                "Latest house benchmark (£)",
                "Viridis",
            ),
    }

    metric_col, metric_title, color_scale = (
        metric_map[
            map_metric_label
        ]
    )

    selected_row = snapshot.loc[
        snapshot["Borough"]
        == chosen_borough
    ].iloc[0]

    headline_1, headline_2, headline_3, headline_4 = (
        st.columns(4)
    )

    headline_1.metric(
        f"{lookback_years}y house growth",
        f"{selected_row['HouseChange']:+.1f}%"
    )

    headline_2.metric(
        f"{lookback_years}y flat growth",
        f"{selected_row['FlatChange']:+.1f}%"
    )

    headline_3.metric(
        "House vs flat gap",
        f"{selected_row['HouseMinusFlat']:+.1f} pp"
    )

    headline_4.metric(
        "Latest average flat price",
        (
            f"£{selected_row['FlatPrice']:,.0f}"
            if pd.notna(
                selected_row["FlatPrice"]
            )
            else "n/a"
        )
    )

    map_col, detail_col = st.columns(
        [1.18, 1.0]
    )

    with map_col:
        st.subheader(
            "Borough heat map"
        )

        map_df = snapshot.copy()

        map_df["HouseChangeText"] = (
            map_df["HouseChange"]
            .map(
                lambda x:
                f"{x:+.1f}%"
                if pd.notna(x)
                else "n/a"
            )
        )

        map_df["FlatChangeText"] = (
            map_df["FlatChange"]
            .map(
                lambda x:
                f"{x:+.1f}%"
                if pd.notna(x)
                else "n/a"
            )
        )

        map_df["GapText"] = (
            map_df["HouseMinusFlat"]
            .map(
                lambda x:
                f"{x:+.1f} pp"
                if pd.notna(x)
                else "n/a"
            )
        )

        map_df["HousePriceText"] = (
            map_df["HousePrice"]
            .map(
                lambda x:
                f"£{x:,.0f}"
                if pd.notna(x)
                else "n/a"
            )
        )

        map_df["FlatPriceText"] = (
            map_df["FlatPrice"]
            .map(
                lambda x:
                f"£{x:,.0f}"
                if pd.notna(x)
                else "n/a"
            )
        )

        map_fig = px.choropleth_mapbox(
            map_df,
            geojson=london_geojson,
            locations="AreaCode",
            featureidkey="properties.gss_code",
            color=metric_col,
            hover_name="Borough",
            custom_data=[
                "AreaCode",
                "HouseChangeText",
                "FlatChangeText",
                "GapText",
                "HousePriceText",
                "FlatPriceText",
            ],
            color_continuous_scale=color_scale,
            mapbox_style="carto-positron",
            center={
                "lat": 51.5074,
                "lon": -0.1278,
            },
            zoom=8.4,
            opacity=0.72,
            labels={
                metric_col:
                    metric_title,
            },
        )

        if (
            map_metric_label
            == "House minus flat growth"
        ):
            gap_max = max(
                1.0,
                float(
                    np.nanmax(
                        np.abs(
                            map_df[
                                "HouseMinusFlat"
                            ]
                        )
                    )
                )
            )

            map_fig.update_coloraxes(
                cmin=-gap_max,
                cmax=gap_max,
                cmid=0,
            )

        map_fig.update_traces(
            marker_line_width=0.7,
            marker_line_color="white",
            hovertemplate=(
                "<b>%{hovertext}</b><br>"
                "House growth: %{customdata[1]}<br>"
                "Flat growth: %{customdata[2]}<br>"
                "Gap: %{customdata[3]}<br>"
                "Latest house benchmark: %{customdata[4]}<br>"
                "Latest flat price: %{customdata[5]}"
                "<extra></extra>"
            )
        )

        map_fig.update_layout(
            margin=dict(
                l=0,
                r=0,
                t=10,
                b=0,
            ),
            height=600,
            coloraxis_colorbar=dict(
                title=metric_title,
            ),
        )

        map_event = st.plotly_chart(
            map_fig,
            use_container_width=True,
            key="borough_heatmap_chart",
            on_select="rerun",
            selection_mode="points",
        )

        clicked_code = None

        try:
            selected_points = (
                map_event.selection.points
            )

            if selected_points:
                point = selected_points[0]

                clicked_code = point.get(
                    "location"
                )

                if (
                    clicked_code is None
                    and point.get(
                        "customdata"
                    )
                ):
                    clicked_code = (
                        point[
                            "customdata"
                        ][0]
                    )

        except Exception:
            clicked_code = None

        if clicked_code:
            clicked_match = (
                snapshot.loc[
                    snapshot[
                        "AreaCode"
                    ]
                    == clicked_code,
                    "Borough"
                ]
            )

            if not clicked_match.empty:
                chosen_borough = (
                    clicked_match.iloc[0]
                )

        st.caption(
            "Hover for borough-level figures. Click a borough "
            "to drive the detail chart; you can also use the "
            "borough selector above."
        )

    with detail_col:
        st.subheader(
            f"{chosen_borough} over time"
        )

        borough_history = (
            london_hpi.loc[
                london_hpi[
                    "RegionName"
                ]
                == chosen_borough
            ]
            .dropna(
                subset=[
                    "Date",
                    "HouseCompositeIndex",
                    "FlatIndex",
                ]
            )
            .sort_values("Date")
            .copy()
        )

        detail_cutoff = (
            borough_history[
                "Date"
            ].max()
            - pd.DateOffset(
                years=lookback_years
            )
        )

        borough_history = (
            borough_history.loc[
                borough_history[
                    "Date"
                ]
                >= detail_cutoff
            ]
            .copy()
        )

        first_valid = (
            borough_history.iloc[0]
        )

        borough_history[
            "House — indexed to 100"
        ] = (
            borough_history[
                "HouseCompositeIndex"
            ]
            / first_valid[
                "HouseCompositeIndex"
            ]
            * 100
        )

        borough_history[
            "Flat — indexed to 100"
        ] = (
            borough_history[
                "FlatIndex"
            ]
            / first_valid[
                "FlatIndex"
            ]
            * 100
        )

        detail_fig = go.Figure()

        detail_fig.add_trace(
            go.Scatter(
                x=borough_history[
                    "Date"
                ],
                y=borough_history[
                    "House — indexed to 100"
                ],
                mode="lines",
                name="Houses",
                hovertemplate=(
                    "%{x|%b %Y}<br>"
                    "Houses: %{y:.1f}"
                    "<extra></extra>"
                ),
            )
        )

        detail_fig.add_trace(
            go.Scatter(
                x=borough_history[
                    "Date"
                ],
                y=borough_history[
                    "Flat — indexed to 100"
                ],
                mode="lines",
                name="Flats",
                hovertemplate=(
                    "%{x|%b %Y}<br>"
                    "Flats: %{y:.1f}"
                    "<extra></extra>"
                ),
            )
        )

        detail_fig.add_hline(
            y=100,
            line_dash="dot",
            line_width=1,
        )

        detail_fig.update_layout(
            height=430,
            margin=dict(
                l=10,
                r=10,
                t=10,
                b=10,
            ),
            yaxis_title=(
                "Price index "
                "(start of selected period = 100)"
            ),
            xaxis_title=None,
            legend_title=None,
            hovermode="x unified",
        )

        st.plotly_chart(
            detail_fig,
            use_container_width=True,
            key="borough_detail_chart",
        )

        detail_prices = (
            borough_history[
                [
                    "Date",
                    "HouseCompositePrice",
                    "FlatPrice",
                ]
            ]
            .rename(
                columns={
                    "HouseCompositePrice":
                        "House benchmark",
                    "FlatPrice":
                        "Flat",
                }
            )
            .set_index(
                "Date"
            )
        )

        st.caption(
            "The line chart rebases both property-type indices "
            "to 100 at the start of the selected period, so the "
            "relative performance is directly comparable."
        )

        with st.expander(
            "Show average-price path"
        ):
            st.line_chart(
                detail_prices
            )

    st.subheader(
        "House vs flat performance across boroughs"
    )

    scatter_fig = px.scatter(
        snapshot,
        x="FlatChange",
        y="HouseChange",
        hover_name="Borough",
        custom_data=[
            "HouseMinusFlat",
            "HousePrice",
            "FlatPrice",
        ],
        labels={
            "FlatChange":
                f"Flat growth over {lookback_years} years (%)",
            "HouseChange":
                f"House growth over {lookback_years} years (%)",
        },
    )

    low = float(
        np.nanmin(
            snapshot[
                [
                    "FlatChange",
                    "HouseChange",
                ]
            ].to_numpy()
        )
    )

    high = float(
        np.nanmax(
            snapshot[
                [
                    "FlatChange",
                    "HouseChange",
                ]
            ].to_numpy()
        )
    )

    padding = max(
        2.0,
        (high - low) * 0.08,
    )

    scatter_fig.add_shape(
        type="line",
        x0=low - padding,
        y0=low - padding,
        x1=high + padding,
        y1=high + padding,
        line=dict(
            dash="dash",
            width=1,
        ),
    )

    highlight = snapshot.loc[
        snapshot["Borough"]
        == chosen_borough
    ]

    scatter_fig.add_trace(
        go.Scatter(
            x=highlight[
                "FlatChange"
            ],
            y=highlight[
                "HouseChange"
            ],
            mode="markers+text",
            text=highlight[
                "Borough"
            ],
            textposition="top center",
            name="Selected borough",
            marker=dict(
                size=14,
                symbol="diamond",
            ),
            hovertemplate=(
                "<b>%{text}</b><br>"
                "Flat growth: %{x:+.1f}%<br>"
                "House growth: %{y:+.1f}%"
                "<extra></extra>"
            ),
        )
    )

    scatter_fig.update_traces(
        selector=dict(
            mode="markers"
        ),
        marker=dict(
            size=9,
            opacity=0.78,
        ),
    )

    scatter_fig.update_layout(
        height=500,
        margin=dict(
            l=10,
            r=10,
            t=10,
            b=10,
        ),
        showlegend=False,
    )

    st.plotly_chart(
        scatter_fig,
        use_container_width=True,
        key="borough_scatter_chart",
    )

    ranking = (
        snapshot[
            [
                "Borough",
                "HouseChange",
                "FlatChange",
                "HouseMinusFlat",
                "HousePrice",
                "FlatPrice",
            ]
        ]
        .sort_values(
            "HouseMinusFlat",
            ascending=False,
        )
        .copy()
    )

    ranking = ranking.rename(
        columns={
            "HouseChange":
                f"House growth {lookback_years}y (%)",
            "FlatChange":
                f"Flat growth {lookback_years}y (%)",
            "HouseMinusFlat":
                "House minus flat (pp)",
            "HousePrice":
                "Latest house benchmark (£)",
            "FlatPrice":
                "Latest flat price (£)",
        }
    )

    st.dataframe(
        ranking,
        use_container_width=True,
        hide_index=True,
        column_config={
            f"House growth {lookback_years}y (%)":
                st.column_config.NumberColumn(
                    format="%.1f%%"
                ),

            f"Flat growth {lookback_years}y (%)":
                st.column_config.NumberColumn(
                    format="%.1f%%"
                ),

            "House minus flat (pp)":
                st.column_config.NumberColumn(
                    format="%+.1f"
                ),

            "Latest house benchmark (£)":
                st.column_config.NumberColumn(
                    format="£%,.0f"
                ),

            "Latest flat price (£)":
                st.column_config.NumberColumn(
                    format="£%,.0f"
                ),
        },
    )

    st.caption(
        f"Source: HM Land Registry / ONS UK House Price Index. "
        f"Latest observation loaded: "
        f"{latest_market_date:%B %Y}. "
        "Recent UK HPI estimates are provisional and may be revised."
    )

except Exception as market_error:
    st.warning(
        "The London borough explorer could not load its external "
        "market data right now. The rest of the calculator is "
        "unaffected."
    )

    with st.expander(
        "Technical detail"
    ):
        st.code(
            str(
                market_error
            )
        )


# ============================================================
# FOOTER
# ============================================================

st.caption(
    "Educational model only. It simplifies taxes, investment "
    "returns, mortgage products, insurance, opportunity costs "
    "and individual circumstances. Check current HMRC rules "
    "and actual mortgage / transaction costs before making a "
    "financial decision."
)
