import streamlit as st
import pandas as pd
import plotly.express as px


# PAGE CONFIG

st.set_page_config(
    page_title="COVID-19 Europe",
    page_icon="🦠",
    layout="wide",
)


# DATA

# Current OWID COVID data source.
# OWID recommends its data catalog for current programmatic access.
DATA_URL = (
    "https://catalog.ourworldindata.org/"
    "garden/covid/latest/compact/compact.csv"
)


# Countries we want to show on the European map.
EUROPE_COUNTRIES = [
    "Albania",
    "Andorra",
    "Austria",
    "Belarus",
    "Belgium",
    "Bosnia and Herzegovina",
    "Bulgaria",
    "Croatia",
    "Cyprus",
    "Czechia",
    "Denmark",
    "Estonia",
    "Finland",
    "France",
    "Germany",
    "Greece",
    "Hungary",
    "Iceland",
    "Ireland",
    "Italy",
    "Kosovo",
    "Latvia",
    "Liechtenstein",
    "Lithuania",
    "Luxembourg",
    "Malta",
    "Moldova",
    "Monaco",
    "Montenegro",
    "Netherlands",
    "North Macedonia",
    "Norway",
    "Poland",
    "Portugal",
    "Romania",
    "Russia",
    "San Marino",
    "Serbia",
    "Slovakia",
    "Slovenia",
    "Spain",
    "Sweden",
    "Switzerland",
    "Turkey",
    "Ukraine",
    "United Kingdom",
    "Vatican",
]


@st.cache_data
def load_data():
    """
    Download the COVID dataset and keep only the columns we need.
    Streamlit caches this so we don't download the dataset every
    time the user changes a control.
    """

    df = pd.read_csv(DATA_URL)

    # Keep only columns needed by this app.
    columns = [
        "date",
        "country",
        "iso_code",
        "population",
        "total_cases",
        "new_cases",
        "new_cases_smoothed",
        "total_cases_per_million",
        "new_cases_per_million",
        "new_cases_smoothed_per_million",
    ]

    # Some datasets can change slightly over time.
    # Keep only columns that actually exist.
    columns = [c for c in columns if c in df.columns]

    df = df[columns].copy()

    # Convert date to datetime.
    df["date"] = pd.to_datetime(df["date"])

    # Only European countries.
    df = df[df["country"].isin(EUROPE_COUNTRIES)].copy()

    # Sort chronologically.
    df = df.sort_values(["country", "date"])

    return df


# LOAD DATA

try:
    df = load_data()

except Exception as e:
    st.error("Could not download the COVID dataset.")
    st.exception(e)
    st.stop()


# CALCULATE ADDITIONAL METRICS

# Make sure numeric columns are actually numeric.
numeric_columns = [
    "total_cases",
    "new_cases",
    "new_cases_smoothed",
    "population",
    "total_cases_per_million",
    "new_cases_per_million",
    "new_cases_smoothed_per_million",
]

for column in numeric_columns:
    if column in df.columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")


# Calculate cases per 100,000 people.
#
# OWID provides cases per million, so divide by 10.
if "new_cases_smoothed_per_million" in df.columns:
    df["new_cases_7day_per_100k"] = (
        df["new_cases_smoothed_per_million"] / 10
    )

if "new_cases_per_million" in df.columns:
    df["new_cases_per_100k"] = (
        df["new_cases_per_million"] / 10
    )

if "total_cases_per_million" in df.columns:
    df["total_cases_per_100k"] = (
        df["total_cases_per_million"] / 10
    )


# SIDEBAR

st.sidebar.title("Map controls")


# Measure

measure = st.sidebar.selectbox(
    "Measure",
    [
        "7-day average cases per 100k",
        "New cases per 100k",
        "Cumulative cases per 100k",
        "New cases",
        "Cumulative cases",
    ],
)


# Map the human-readable option to the dataframe column.
measure_columns = {
    "7-day average cases per 100k": "new_cases_7day_per_100k",
    "New cases per 100k": "new_cases_per_100k",
    "Cumulative cases per 100k": "total_cases_per_100k",
    "New cases": "new_cases",
    "Cumulative cases": "total_cases",
}

value_column = measure_columns[measure]


# Date range

min_date = df["date"].min().date()
max_date = df["date"].max().date()

st.sidebar.subheader("Date")

date_range = st.sidebar.slider(
    "Select date range",
    min_value=min_date,
    max_value=max_date,
    value=(min_date, max_date),
)


# Filter the data.
filtered_df = df[
    (df["date"].dt.date >= date_range[0])
    & (df["date"].dt.date <= date_range[1])
].copy()


# MAIN PAGE

st.title("🦠 COVID-19 in Europe")

st.markdown(
    """
Explore how reported COVID-19 cases changed across Europe over time.
Use the controls on the left and the play button on the map to animate
the pandemic through time.
"""
)


# MAP

# Remove rows without the selected metric.
map_df = filtered_df.dropna(
    subset=["country", value_column]
).copy()


# Plotly needs a value for every country/date combination that
# should appear in the animation.
#
# We use country names because Plotly has built-in country
# boundaries.
fig = px.choropleth(
    map_df,
    locations="country",
    locationmode="country names",

    # The variable controlling the country color.
    color=value_column,

    # This creates the time slider + play button.
    animation_frame="date",

    # Europe-only map.
    scope="europe",

    # Red intensity represents the number of cases.
    color_continuous_scale="Reds",

    # Hover information.
    hover_name="country",

    hover_data={
        value_column: ":,.1f",
        "country": False,
    },

    labels={
        value_column: measure,
        "date": "Date",
    },
)


# Map appearance

fig.update_layout(
    margin={
        "r": 0,
        "t": 20,
        "l": 0,
        "b": 0,
    },

    height=650,

    coloraxis_colorbar={
        "title": measure,
    },
)


# Make country borders visible.
fig.update_geos(
    showframe=False,
    showcountries=True,
    countrycolor="white",
)


# Display the map.
st.plotly_chart(
    fig,
    width="stretch",
)


# SELECTED DATE INFORMATION

st.subheader("About the data")

st.markdown(
    """
**Data source:** Our World in Data / World Health Organization.

The map shows reported confirmed COVID-19 cases. Reported cases
do not represent the true number of infections because testing
and reporting practices varied substantially between countries
and over time.
"""
)


# OPTIONAL TABLE

with st.expander("View the data"):

    # Get the most recent date currently represented.
    latest_date = filtered_df["date"].max()

    latest = filtered_df[
        filtered_df["date"] == latest_date
    ].copy()

    latest = latest[
        ["country", value_column]
    ].sort_values(
        value_column,
        ascending=False,
    )

    latest.columns = [
        "Country",
        measure,
    ]

    st.dataframe(
        latest,
        width="stretch",
        hide_index=True,
    )