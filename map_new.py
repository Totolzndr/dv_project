import streamlit as st
import pandas as pd
import plotly.express as px


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="COVID-19 in Europe",
    layout="wide"
)

st.title("COVID-19 in Europe")

st.markdown(
    """
    Explore how reported COVID-19 case rates evolved across Europe,
    both in calendar time and relative to major stay-at-home interventions.
    """
)


# ============================================================
# DATA SOURCES
# ============================================================

DATA_URL = (
    "https://catalog.ourworldindata.org/"
    "garden/covid/latest/compact/compact.csv"
)

OXCGRT_URL = (
    "https://raw.githubusercontent.com/OxCGRT/"
    "covid-policy-dataset/main/data/OxCGRT_compact_national_v1.csv"
)


# ============================================================
# LOAD OWID COVID DATA
# ============================================================

@st.cache_data
def load_covid_data():

    df = pd.read_csv(DATA_URL, low_memory=False)

    # Columns available in the OWID compact COVID dataset
    required_columns = [
        "code",
        "country",
        "date",
        "continent",
        "new_cases",
        "new_cases_smoothed",
        "new_cases_per_million",
        "new_cases_smoothed_per_million",
        "total_cases_per_million",
    ]

    missing_columns = [
        col for col in required_columns
        if col not in df.columns
    ]

    if missing_columns:

        st.error(
            "The OWID dataset is missing these expected columns: "
            + ", ".join(missing_columns)
        )

        st.write("Columns actually found:")
        st.write(df.columns.tolist())

        st.stop()

    df["date"] = pd.to_datetime(df["date"])

    # Keep actual countries with a valid 3-letter country code
    df = df[
        df["code"].notna()
        & df["code"].astype(str).str.len().eq(3)
    ].copy()

    # Convert cases per million to cases per 100,000
    df["new_cases_per_100k"] = (
        df["new_cases_per_million"] / 10
    )

    df["new_cases_smoothed_per_100k"] = (
        df["new_cases_smoothed_per_million"] / 10
    )

    df["total_cases_per_100k"] = (
        df["total_cases_per_million"] / 10
    )

    return df


# ============================================================
# LOAD OXCGRT POLICY DATA
# ============================================================

@st.cache_data
def load_policy_data():

    policy = pd.read_csv(OXCGRT_URL)

    policy["Date"] = pd.to_datetime(
        policy["Date"].astype(str),
        format="%Y%m%d",
        errors="coerce"
    )

    return policy


covid = load_covid_data()
policy = load_policy_data()


# ============================================================
# EUROPE FILTER
# ============================================================

europe = covid[
    covid["continent"] == "Europe"
].copy()


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.header("Controls")


# ------------------------------------------------------------
# COVID measure
# ------------------------------------------------------------

measure_options = {

    "7-day average new cases per 100k":
        "new_cases_smoothed_per_100k",

    "New cases per 100k":
        "new_cases_per_100k",

    "Cumulative cases per 100k":
        "total_cases_per_100k"
}


selected_measure_label = st.sidebar.selectbox(
    "COVID measure",
    list(measure_options.keys()),
    index=0
)

selected_measure = measure_options[selected_measure_label]


# ------------------------------------------------------------
# Relative timeline
# ------------------------------------------------------------

st.sidebar.subheader("Relative lockdown timeline")


relative_min = st.sidebar.slider(
    "Days before lockdown",
    min_value=-120,
    max_value=-1,
    value=-60
)


relative_max = st.sidebar.slider(
    "Days after lockdown",
    min_value=30,
    max_value=180,
    value=120
)


# ------------------------------------------------------------
# Relative timeline mode
# ------------------------------------------------------------

timeline_mode = st.sidebar.radio(
    "Relative timeline mode",
    [
        "Absolute cases per 100k",
        "Relative to Day 0"
    ],
    index=0
)


# ------------------------------------------------------------
# Fixed color scale
# ------------------------------------------------------------

st.sidebar.subheader("Color scale")


color_max = st.sidebar.selectbox(
    "Fixed maximum for absolute mode",
    [50, 100, 150, 200, 250, 300, 400, 500],
    index=4
)


if timeline_mode == "Absolute cases per 100k":

    st.sidebar.caption(
        f"The absolute color scale is fixed from 0 to "
        f"{color_max} cases per 100k for every animation frame."
    )

else:

    st.sidebar.caption(
        """
        In normalized mode, each country is compared with its own
        Day 0 value:

        **100% = same as Day 0**

        **50% = half of Day 0**

        **200% = twice Day 0**
        """
    )


# ============================================================
# OXCGRT C6M VARIABLES
# ============================================================

C6M = "C6M_Stay at home requirements"
C6M_FLAG = "C6M_Flag"


# ============================================================
# CHECK POLICY COLUMNS
# ============================================================

required_policy_columns = [
    "CountryCode",
    "CountryName",
    "Date",
    C6M,
    C6M_FLAG
]


missing_policy_columns = [
    col
    for col in required_policy_columns
    if col not in policy.columns
]


if missing_policy_columns:

    st.error(
        "The OxCGRT dataset is missing the following required columns: "
        + ", ".join(missing_policy_columns)
    )

    st.stop()


# ============================================================
# CREATE LOCKDOWN DEFINITIONS
# ============================================================

policy_c6 = policy[
    policy["CountryCode"].notna()
].copy()


policy_c6[C6M] = pd.to_numeric(
    policy_c6[C6M],
    errors="coerce"
)


policy_c6[C6M_FLAG] = pd.to_numeric(
    policy_c6[C6M_FLAG],
    errors="coerce"
)


# ------------------------------------------------------------
# Definition 1:
# Any major stay-at-home requirement
#
# C6M >= 2
# ------------------------------------------------------------

major_c6m = policy_c6[
    policy_c6[C6M] >= 2
].copy()


first_major_any = (
    major_c6m
    .sort_values(["CountryCode", "Date"])
    .groupby("CountryCode", as_index=False)
    .first()
)


first_major_any = first_major_any[
    [
        "CountryCode",
        "CountryName",
        "Date",
        C6M,
        C6M_FLAG
    ]
].rename(
    columns={
        "Date": "first_major_any_date",
        C6M: "major_any_level",
        C6M_FLAG: "major_any_flag"
    }
)


# ------------------------------------------------------------
# Definition 2:
# Major AND general
#
# C6M >= 2
# C6M_Flag == 1
# ------------------------------------------------------------

major_general_c6m = policy_c6[
    (policy_c6[C6M] >= 2)
    & (policy_c6[C6M_FLAG] == 1)
].copy()


first_major_general = (
    major_general_c6m
    .sort_values(["CountryCode", "Date"])
    .groupby("CountryCode", as_index=False)
    .first()
)


first_major_general = first_major_general[
    [
        "CountryCode",
        "CountryName",
        "Date",
        C6M,
        C6M_FLAG
    ]
].rename(
    columns={
        "Date": "first_major_general_date",
        C6M: "general_level",
        C6M_FLAG: "general_flag"
    }
)


# ------------------------------------------------------------
# Definition 3:
# Strict lockdown
#
# C6M == 3
# C6M_Flag == 1
# ------------------------------------------------------------

strict_c6m = policy_c6[
    (policy_c6[C6M] == 3)
    & (policy_c6[C6M_FLAG] == 1)
].copy()


first_strict = (
    strict_c6m
    .sort_values(["CountryCode", "Date"])
    .groupby("CountryCode", as_index=False)
    .first()
)


first_strict = first_strict[
    [
        "CountryCode",
        "CountryName",
        "Date",
        C6M,
        C6M_FLAG
    ]
].rename(
    columns={
        "Date": "first_strict_date",
        C6M: "strict_level",
        C6M_FLAG: "strict_flag"
    }
)


# ============================================================
# DIAGNOSTIC TABLE
# ============================================================

# European countries from OWID
europe_countries = (
    europe[
        ["code", "country"]
    ]
    .drop_duplicates()
    .rename(
        columns={
            "code": "CountryCode",
            "country": "OWID_country"
        }
    )
)


diagnostic = (
    europe_countries
    .merge(
        first_major_any,
        on="CountryCode",
        how="left"
    )
    .merge(
        first_major_general,
        on="CountryCode",
        how="left"
    )
    .merge(
        first_strict,
        on="CountryCode",
        how="left"
    )
)


# ------------------------------------------------------------
# Diagnostic status
# ------------------------------------------------------------

def lockdown_status(row):

    if pd.notna(row["first_major_general_date"]):

        return "General major lockdown found"

    elif pd.notna(row["first_major_any_date"]):

        return "Major lockdown found, but not general"

    else:

        return "No C6M >= 2 found"


diagnostic["status"] = diagnostic.apply(
    lockdown_status,
    axis=1
)


# ============================================================
# SHOW DIAGNOSTIC TABLE
# ============================================================

with st.expander(
    "🔎 Lockdown diagnostic: check the reference date for every country"
):

    st.markdown(
        """
        The relative timeline uses the **first major general
        stay-at-home intervention**:

        **C6M ≥ 2 AND C6M_Flag = 1**

        - C6M = 2: stay-at-home requirement with exceptions
        - C6M = 3: stay-at-home requirement with minimal exceptions
        - C6M_Flag = 1: general rather than targeted policy

        The table below lets us see exactly which date is being used
        for each country and why countries may be missing from the
        relative timeline.
        """
    )


    diagnostic_display = diagnostic.copy()


    diagnostic_display["first_major_any_date"] = (
        diagnostic_display["first_major_any_date"]
        .dt.strftime("%Y-%m-%d")
    )


    diagnostic_display["first_major_general_date"] = (
        diagnostic_display["first_major_general_date"]
        .dt.strftime("%Y-%m-%d")
    )


    diagnostic_display["first_strict_date"] = (
        diagnostic_display["first_strict_date"]
        .dt.strftime("%Y-%m-%d")
    )


    diagnostic_display = diagnostic_display[
        [
            "OWID_country",
            "CountryCode",
            "status",
            "first_major_any_date",
            "major_any_level",
            "major_any_flag",
            "first_major_general_date",
            "general_level",
            "general_flag",
            "first_strict_date",
            "strict_level"
        ]
    ].sort_values("OWID_country")


    diagnostic_display = diagnostic_display.rename(
        columns={
            "OWID_country": "Country",
            "CountryCode": "ISO",
            "status": "Status",
            "first_major_any_date": "First C6M ≥ 2",
            "major_any_level": "C6M level",
            "major_any_flag": "General flag",
            "first_major_general_date":
                "First C6M ≥ 2 + general",
            "general_level":
                "Selected C6M level",
            "general_flag":
                "Selected flag",
            "first_strict_date":
                "First C6M = 3 + general",
            "strict_level":
                "Strict level"
        }
    )


    st.dataframe(
        diagnostic_display,
        use_container_width=True,
        hide_index=True
    )


    # Summary statistics

    total_countries = len(diagnostic)


    general_count = diagnostic[
        diagnostic["first_major_general_date"].notna()
    ].shape[0]


    any_count = diagnostic[
        diagnostic["first_major_any_date"].notna()
    ].shape[0]


    missing_count = diagnostic[
        diagnostic["first_major_general_date"].isna()
    ].shape[0]


    col_a, col_b, col_c = st.columns(3)


    col_a.metric(
        "European countries",
        total_countries
    )


    col_b.metric(
        "General major lockdown found",
        general_count
    )


    col_c.metric(
        "Missing from relative timeline",
        missing_count
    )


    if missing_count > 0:

        missing_countries = diagnostic[
            diagnostic["first_major_general_date"].isna()
        ]["OWID_country"].tolist()


        st.warning(
            "Countries without a qualifying general C6M ≥ 2 intervention: "
            + ", ".join(missing_countries)
        )


# ============================================================
# CREATE COUNTRY LOCKDOWN DATE
# ============================================================

lockdown_dates = first_major_general[
    [
        "CountryCode",
        "first_major_general_date"
    ]
].copy()


lockdown_dates = lockdown_dates.rename(
    columns={
        "first_major_general_date":
            "first_major_lockdown"
    }
)


# ============================================================
# MERGE COVID DATA WITH LOCKDOWN DATE
# ============================================================

europe_relative = europe.merge(
    lockdown_dates,
    left_on="code",
    right_on="CountryCode",
    how="left"
)


# ============================================================
# CALCULATE RELATIVE DAY
# ============================================================

europe_relative["days_from_lockdown"] = (
    europe_relative["date"]
    - europe_relative["first_major_lockdown"]
).dt.days


# ============================================================
# CALCULATE DAY 0 BASELINE
# ============================================================

# Find each country's COVID value on its own Day 0.
day0_values = (
    europe_relative.loc[
        europe_relative["days_from_lockdown"].eq(0),
        [
            "code",
            selected_measure
        ]
    ]
    .drop_duplicates("code")
    .rename(
        columns={
            selected_measure: "day0_value"
        }
    )
)


# Remove an old baseline if Streamlit reruns this section
europe_relative = europe_relative.drop(
    columns=["day0_value"],
    errors="ignore"
)


# Merge Day 0 values back onto every observation
europe_relative = europe_relative.merge(
    day0_values,
    on="code",
    how="left"
)


# ============================================================
# NORMALIZE TO DAY 0
# ============================================================

# 100 = same value as Day 0
# 50  = half of Day 0
# 200 = twice Day 0
#
# If Day 0 is zero or missing, the normalized value becomes NaN.
europe_relative["relative_to_day0_pct"] = (
    europe_relative[selected_measure]
    .div(
        europe_relative["day0_value"]
        .where(europe_relative["day0_value"] > 0)
    )
    * 100
)


# ============================================================
# MAP 1 — ORIGINAL CALENDAR-TIME COVID MAP
# ============================================================

st.subheader("COVID-19 cases across Europe")


calendar_map = europe[
    [
        "country",
        "code",
        "date",
        selected_measure
    ]
].copy()


calendar_map = calendar_map.dropna(
    subset=[selected_measure]
)


calendar_map = calendar_map.rename(
    columns={
        "country": "location",
        "code": "iso_code",
        selected_measure: "value"
    }
)


fig_calendar = px.choropleth(
    calendar_map,
    locations="iso_code",
    color="value",
    hover_name="location",
    animation_frame="date",
    scope="europe",
    color_continuous_scale="Reds",
    range_color=(0, color_max),
    labels={
        "value": selected_measure_label
    }
)


fig_calendar.update_layout(
    margin=dict(l=0, r=0, t=40, b=0)
)


st.plotly_chart(
    fig_calendar,
    use_container_width=True
)


# ============================================================
# MAP 2 — LOCKDOWN-RELATIVE COVID MAP
# ============================================================

st.subheader(
    "COVID-19 cases relative to the first major general lockdown"
)


if timeline_mode == "Absolute cases per 100k":

    st.markdown(
        """
        **Absolute mode:** each country's actual reported case rate
        is shown in cases per 100,000 people.

        **Day 0** represents the country's first major general
        stay-at-home intervention recorded by OxCGRT.
        """
    )

else:

    st.markdown(
        """
        **Relative-to-Day-0 mode:** each country is normalized against
        its own COVID case value on Day 0.

        - **100%** = the country's Day 0 value
        - **50%** = half of its Day 0 value
        - **200%** = twice its Day 0 value

        This removes differences in absolute magnitude between countries
        and makes the **shape and relative change of the trajectories**
        easier to compare.

        This mode is particularly useful with the **7-day average new
        cases per 100k** measure.
        """
    )


# ------------------------------------------------------------
# Select time window
# ------------------------------------------------------------

relative_map = europe_relative[
    europe_relative["days_from_lockdown"].between(
        relative_min,
        relative_max
    )
].copy()


# ------------------------------------------------------------
# Choose displayed value
# ------------------------------------------------------------

if timeline_mode == "Relative to Day 0":

    relative_map["value"] = (
        relative_map["relative_to_day0_pct"]
    )

    relative_color_max = 200

    relative_color_scale = "RdBu_r"

    relative_color_midpoint = 100

    relative_label = (
        "Cases relative to Day 0 (%)"
    )

else:

    relative_map["value"] = (
        relative_map[selected_measure]
    )

    relative_color_max = color_max

    relative_color_scale = "Reds"

    relative_color_midpoint = None

    relative_label = selected_measure_label


# ------------------------------------------------------------
# Rename geographic columns
# ------------------------------------------------------------

relative_map = relative_map.rename(
    columns={
        "country": "location",
        "code": "iso_code"
    }
)


# ------------------------------------------------------------
# Remove missing values
# ------------------------------------------------------------

relative_map = relative_map.dropna(
    subset=[
        "days_from_lockdown",
        "value"
    ]
)


relative_map["days_from_lockdown"] = (
    relative_map["days_from_lockdown"]
    .astype(int)
)


# ============================================================
# RELATIVE CHOROPLETH
# ============================================================

fig_relative = px.choropleth(
    relative_map,
    locations="iso_code",
    color="value",
    hover_name="location",
    animation_frame="days_from_lockdown",
    scope="europe",
    color_continuous_scale=relative_color_scale,
    range_color=(0, relative_color_max),
    color_continuous_midpoint=relative_color_midpoint,
    labels={
        "value": relative_label,
        "days_from_lockdown":
            "Days relative to lockdown"
    },
    hover_data={
        "iso_code": False,
        "days_from_lockdown": True,
        "value": ":.1f"
    }
)


fig_relative.update_layout(
    margin=dict(l=0, r=0, t=40, b=0)
)


st.plotly_chart(
    fig_relative,
    use_container_width=True
)


# ============================================================
# NORMALIZATION EXPLANATION
# ============================================================

if timeline_mode == "Relative to Day 0":

    st.info(
        """
        **How to read this map:** every country is scaled relative to
        its own Day 0 value. Therefore, the map compares proportional
        changes rather than absolute case levels.

        For example, if Country A goes from 20 to 100 cases per 100k
        and Country B goes from 200 to 1,000 cases per 100k, both are
        shown as **500% of Day 0**.

        This makes trajectories comparable despite different baseline
        magnitudes, but it also means that the map no longer shows the
        absolute burden of COVID-19.
        """
    )


# ============================================================
# LOCKDOWN DATE TABLE
# ============================================================

st.subheader("Selected lockdown dates")


lockdown_table = diagnostic[
    [
        "OWID_country",
        "CountryCode",
        "first_major_general_date",
        "general_level",
        "general_flag",
        "status"
    ]
].copy()


lockdown_table = lockdown_table.rename(
    columns={
        "OWID_country": "Country",
        "CountryCode": "ISO",
        "first_major_general_date":
            "First major general lockdown",
        "general_level":
            "C6M level",
        "general_flag":
            "C6M general flag",
        "status":
            "Status"
    }
)


lockdown_table[
    "First major general lockdown"
] = pd.to_datetime(
    lockdown_table["First major general lockdown"]
).dt.strftime("%Y-%m-%d")


st.dataframe(
    lockdown_table.sort_values("Country"),
    use_container_width=True,
    hide_index=True
)


# ============================================================
# INTERPRETATION
# ============================================================

st.subheader("How to interpret the relative map")


if timeline_mode == "Absolute cases per 100k":

    st.markdown(
        """
        The **absolute mode** shows the actual reported COVID-19
        case rate in each country.

        The timeline is aligned around each country's first major
        general stay-at-home intervention, so:

        - **Day -30** = 30 days before the country's intervention
        - **Day 0** = first major general stay-at-home intervention
        - **Day +30** = 30 days after the intervention

        This mode preserves differences in the actual magnitude of
        COVID-19 cases between countries.
        """
    )

else:

    st.markdown(
        """
        The **relative-to-Day-0 mode** removes differences in baseline
        magnitude between countries.

        Each country's Day 0 value is treated as **100%**:

        - **50%** = half of Day 0
        - **100%** = same as Day 0
        - **200%** = twice Day 0

        This allows us to ask a different analytical question:

        > How did the trajectory of reported COVID-19 cases change
        > relative to each country's situation when the major
        > stay-at-home intervention began?

        This is useful because countries entered their interventions
        with very different levels of reported cases.

        However, normalization removes information about the absolute
        level of cases. Therefore, the **absolute and normalized maps
        should be interpreted together**.
        """
    )


st.markdown(
    """
    ### Important methodological point

    The relative map does **not** show the causal effect of lockdowns.

    Instead, it aligns countries according to the timing of their first
    major general stay-at-home intervention and compares their reported
    COVID-19 trajectories around that reference point.

    Countries may have introduced interventions at different stages of
    their outbreaks. In addition, reported cases are affected by testing,
    reporting delays, surveillance practices and other factors.

    Therefore, changes before and after Day 0 should be interpreted as
    **descriptive temporal patterns and associations**, not as evidence
    that the intervention itself caused the observed change.
    """
)


# ============================================================
# ABOUT
# ============================================================

with st.expander("About the data"):

    st.markdown(
        """
        **COVID-19 data:** Our World in Data

        **Government intervention data:** Oxford COVID-19 Government
        Response Tracker (OxCGRT)

        **Lockdown definition used here:**

        First date where:

        `C6M_Stay at home requirements >= 2`

        and

        `C6M_Flag == 1`

        This means the first recorded general stay-at-home requirement
        with a substantial restriction.

        **COVID measure:** 7-day average new confirmed cases per 100,000
        people by default.

        **Absolute relative timeline:** reports the actual case rate.

        **Relative-to-Day-0 timeline:** expresses each country's case
        rate as a percentage of its own Day 0 value.

        The relative timeline is intended for descriptive comparison,
        not causal inference.
        """
    )