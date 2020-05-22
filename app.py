import os
import re
import requests
import pickle
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import plotly.colors as pc
import dash
import dash_table
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc

# ------ Model ------
# --- Data
# Data source
API_BASE = "https://data.ontario.ca/api/3/action/"
PACKAGE_IDS = {
    "status": "f4f86e54-872d-43f8-8a86-3892fd3cb5e6",  # Status of COVID-19 cases in Ontario
    "con_pos": "f4112442-bdc8-45d2-be3c-12efae72fb27",  # Confirmed positive cases of COVID-19 in Ontario
}


class Dataset:
    """
    A dataset from the Ontario Data Catalog. 
    Include attributes from start to finish: 
        From CKAN package ID
        To a cleaned DataFrame for plotting. 
    """

    def __init__(self, name, package_id):
        """
        Load a Dataset from a pickle, and update it if necessary.
        """
        self.name = name
        self.package_id = package_id
        self.resource_id = ""
        self.resource_name = ""
        self.url = ""
        self.last_modified = ""
        self.data = pd.DataFrame()
        self.refresh()

    def refresh(self):
        """
        Check to see if the resource has changed. 
        If it has, download and clean again.
        """
        # If there isn't a Dataset loaded
        # Load data from the cache, if it exists
        if self.data.empty:
            self.load_cache()

        # Check the resource for updates
        current_last_modified = self.last_modified
        resource_status = self.get_resource()

        # If the API call worked, and there is an update
        #   Download, clean and save data in the cache
        if resource_status == 200 and self.last_modified != current_last_modified:
            resource_data_status = self.get_resource_data()
            # If downloading worked, clean and save the data
            if resource_data_status == 200:
                self.clean_data()
                self.save_cache()

    def load_cache(self):
        """
        Load the cached Dataset, if it exists.
        """
        filename = f"{self.name}.pickle"
        if os.path.exists(filename):
            with open(filename, "rb") as f:
                self = pickle.load(f)

    def save_cache(self):
        """
        Save the Dataset in a cache.
        """
        filename = f"{self.name}.pickle"
        with open(filename, "wb") as f:
            pickle.dump(self, f)

    def get_resource(self):
        """
        Call the API to the get the current attributes of the CSV resource. 
        If the status is 200, update the attributes of the dataset with the new ones.
        If the status is anything else, don't update the attributes.

        Return the API status.
        """
        url = f"{API_BASE}package_show?id={self.package_id}"
        response = requests.get(url)

        if response.status_code == 200:
            resources = response.json()["result"]["resources"]
            resource = [r for r in resources if (r.get("format") == "CSV")][0]
            self.resource_id = resource.get("id")
            self.resource_name = resource.get("name")
            self.url = resource.get("url")
            self.last_modified = resource.get("last_modified")

        return response.status_code

    def get_resource_data(self):
        """
        Get tabular data from the resource.
        Wrapper for the more specific downloading functions.
        Note: if this doesn't work, consider switching to CSV downloads. 
        """
        if self.name == "status":
            status_code = self.get_resource_data_status()
        if self.name == "con_pos":
            status_code = self.get_resource_data_con_pos()
        return status_code

    # Downloading functions for each of the two datasets
    def get_resource_data_status(self):
        """ 
        Get the "Status of COVID-19 cases in Ontario" dataset

        Return the API status.
        """
        fields = [
            "Reported Date",
            "Confirmed Positive",
            "Resolved",
            "Deaths",
            "Total Cases",
            "Total tests completed in the last day",
            "Under Investigation",
            "Number of patients hospitalized with COVID-19",
            "Number of patients in ICU with COVID-19",
            "Number of patients in ICU on a ventilator with COVID-19",
        ]
        url = f"{API_BASE}datastore_search?resource_id={self.resource_id}&fields={','.join(fields)}&limit=32000"
        response = requests.get(url)

        if response.status_code == 200:
            records = response.json()["result"]["records"]
            self.data = pd.DataFrame(records)

        return response.status_code

    def get_resource_data_con_pos(self):
        """ 
        Get the "Confirmed positive cases of COVID-19 in Ontario" dataset
        Return the API status
        """
        fields = [
            "Accurate_Episode_Date",
            "Age_Group",
            "Client_Gender",
            "Case_AcquisitionInfo",
            "Outcome1",
            "Reporting_PHU_City",
        ]
        url = f"{API_BASE}datastore_search?resource_id={self.resource_id}&fields={','.join(fields)}&limit=32000"
        response = requests.get(url)

        if response.status_code == 200:
            records = response.json()["result"]["records"]
            self.data = pd.DataFrame(records)

        return response.status_code

    def clean_data(self):
        """
        Prepare data for plotting.
        Wrapper for the more specific cleaning functions.
        """
        # Handle the case where there's no data to clean
        df = self.data
        if df.empty:
            self.data = pd.DataFrame()

        # Pick a cleaning function specific to that dataset
        if self.name == "status":
            self.clean_data_status()
        if self.name == "con_pos":
            self.clean_data_con_pos()

    # Cleaning functions for each of the two datasets
    def clean_data_status(self):
        """ 
        Clean the "Status of COVID-19 cases in Ontario" dataset
        """
        df = self.data
        df["Reported Date"] = pd.to_datetime(df["Reported Date"]).dt.strftime(
            "%Y-%m-%d"
        )
        df = df.set_index("Reported Date").sort_index()
        df = df.fillna(0)
        df = df.astype(int)
        df = df.rename(
            columns={
                "Confirmed Positive": "Outstanding cases",
                "Resolved": "Resolved cases",
                "Total Cases": "Total cases",
                "Total tests completed in the last day": "Tests",
                "Number of patients hospitalized with COVID-19": "Hospital beds",
                "Number of patients in ICU with COVID-19": "ICU beds",
                "Number of patients in ICU on a ventilator with COVID-19": "Ventilator beds",
            }
        )
        self.data = df

    def clean_data_con_pos(self):
        """ 
        Clean the "Confirmed positive cases of COVID-19 in Ontario" dataset
        """
        df = self.data
        bad_date_mask = df["Accurate_Episode_Date"].str[0:4].astype(int) > int(
            pd.to_datetime("today").strftime("%Y")
        )
        df = df.loc[~bad_date_mask]
        df.loc[:, "Accurate_Episode_Date"] = pd.to_datetime(
            df.loc[:, "Accurate_Episode_Date"]
        )
        df = df.sort_values(by="Accurate_Episode_Date")
        df = df.rename(
            columns={
                "Accurate_Episode_Date": "Episode Date",
                "Age_Group": "Age",
                "Client_Gender": "Gender",
                "Case_AcquisitionInfo": "Acquisition",
                "Outcome1": "Outcome",
                "Reporting_PHU_City": "PHU City",
            }
        )
        self.data = df


def build_datasets():
    """ Create and download all the datasets in PACKAGE_ID. """
    return {name: Dataset(name, package_id) for name, package_id in PACKAGE_IDS.items()}


def refresh_datasets(datasets):
    """ Refresh all the datasets. """
    for d in datasets.values():
        d.refresh()


def get_most_recent_update(datasets):
    """ Return the most recent update of the all the datasets. """
    last_updated = [d.last_modified for d in datasets.values()]
    most_recent_update = pd.to_datetime(last_updated).tz_localize(tz="UTC").max()
    return most_recent_update


# --- Text
TEXT_TITLE = "covid-ontario"
TEXT_TAGLINE = "Follow the rise and fall of COVID-19 in Ontario"

TEXT_BODY = "This is an independent project to visualize the "
TEXT_LINK_CATALOG = "Ontario Data Catalog's COVID-19 data"
URL_LINK_CATALOG = "https://data.ontario.ca/dataset?keywords_en=COVID-19"

TEXT_WARNING = "Please do your part to "
TEXT_LINK_WARNING = "stop the spread"
URL_LINK_WARNING = "https://covid-19.ontario.ca/index.html"

TEXT_MOST_RECENT_UPDATE = "Most recent data: "

TEXT_CON_POS_TABLE = "Confirmed positives"

# ------ View ------
# --- Data formatting
def format_date(unformatted_date):
    timezone_label = ""
    timezone_dest = "Canada/Eastern"
    date_format = "%B %-d, %-I:%M %p"

    localized_date = unformatted_date.tz_convert(timezone_dest)
    formatted_datetime = localized_date.strftime(date_format)
    return f"{formatted_datetime} {timezone_label}"


# --- Plotting!
START_DATE = "2020-03-15"

def date_agg(df, agg_col, date_col="Episode Date", cols_exclude=False):
    """ 
    Return a wide DataFrame where:
        Index is a datetime
        Columns are the counts of each value in the agg_col per day """
    if not cols_exclude:
        cols_exclude = []
    df_agg = (
        df.groupby([date_col, agg_col])[agg_col]
        .count()
        .unstack()
        .fillna(0)
        .drop(cols_exclude, axis=1)
    )
    return df_agg


def tidy(df):
    """ Switch from wide to long format """
    df_tidy = df.copy()
    df_tidy.columns.name = "Measure"
    df_tidy = df_tidy.stack()
    df_tidy.name = "Count"
    df_tidy = df_tidy.reset_index(level=1)
    return df_tidy

def filter_sort_measures(df, measures):
    """ Filter a tidy DataFrame to just the measures specified, 
    and sort by them in the order specified """
    df_filter_sort = df[df["Measure"].isin(measures)].copy()
    cat_dtype = pd.api.types.CategoricalDtype(categories=measures, ordered=True)
    df_filter_sort["Measure"] = df_filter_sort["Measure"].astype(cat_dtype)
    df_filter_sort = df_filter_sort.sort_values(by=["Measure"])
    return df_filter_sort

PLOT_LAYOUT = dict(
        barmode="stack",
        hovermode="x",
        xaxis={
            "title": "Date",
            "type": "date",
            "range": [pd.to_datetime(START_DATE), pd.to_datetime("today")],
            "tickformat": "%B %-d",
            "tickvals": [
                d
                for d in pd.date_range(pd.to_datetime(START_DATE), pd.to_datetime("today"))
                if (d.day in [1, 15])
            ],
            "showgrid": True,
            "gridcolor": "gainsboro",
        },
        yaxis={
            "title": "", 
            "showgrid": True, 
            "gridcolor": "gainsboro",
        },
        legend={
            "title_text": "",
            "xanchor": "center",
            "x": 0.5,
            "y": 1.1,
            "orientation": "h",
            "traceorder": "reversed",
        },
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin={"t": 0, "l": 0, "r": 0},
)

def plot_bar_timeseries(df, measures, colors):
    """ Make a pretty bar plot of a timeseries """
    # Make tidy, filtered and ordered for plotting with Plotly Express
    df_plot = filter_sort_measures(tidy(df), measures)
    # Map measures to colors
    measure_color_map = {m: c for m, c in zip(measures, colors)}

    fig = px.bar(
        df_plot,
        x=df_plot.index,
        y="Count",
        color="Measure",
        hover_name="Measure",
        color_discrete_map=measure_color_map,
    )

    fig.update_traces(hovertemplate="%{y}")
    fig.update_layout(PLOT_LAYOUT)
    
    return fig

def plot_line_timeseries(df, measures, colors):
    """ Make a pretty line plot of a timeseries, including rolling averages """
    # Compute change metrics: difference per day, and rolling 7 day average of difference
    df_chg_dif = (df - df.shift(1)).fillna(0)
    df_chg_avg = df_chg_dif.rolling(7).mean()

    # Make tidy, filtered and ordered for plotting with Plotly Express
    df_chg_dif = filter_sort_measures(tidy(df_chg_dif), measures)
    df_chg_avg = filter_sort_measures(tidy(df_chg_avg), measures)

    # Map measures to colors
    measure_color_map = {m: c for m, c in zip(measures, colors)}

    # Add scatter points
    fig = px.scatter(
        df_chg_dif,
        x=df_chg_dif.index,
        y="Count",
        color="Measure",
        hover_name="Measure",
        color_discrete_map=measure_color_map,
    )
    fig.update_traces(
        opacity=0.5,
        marker={"size": 9}
    )

    # Add average lines
    for m in measures:
        df_plot = df_chg_avg[df_chg_avg["Measure"] == m]
        df_plot = df_plot.sort_index()
        fig.add_trace(
            go.Scatter(
                x=df_plot.index,
                y=df_plot["Count"],
                name=m,
                mode="lines",
                line={
                    "color": measure_color_map[m],
                    "width": 3
                }
            )
        )

    fig.update_layout(PLOT_LAYOUT)
    fig.update_traces(hovertemplate="%{y}")

    return fig 

# *** Overview
OVERVIEW_TITLE = "Deaths and outstanding cases"


def plot_overview(data_status):
    """ Return an Overview plot. """
    measures = ["Outstanding cases", "Deaths"]
    colors = ["steelblue", "darkgray"]
    return plot_bar_timeseries(data_status, measures, colors)

def plot_overview_change(data_status):
    """ Return the change in Overview plot. """
    measures = ["Outstanding cases", "Deaths"]
    colors = ["steelblue", "darkgray"]
    return plot_line_timeseries(data_status, measures, colors)


# *** Hospital
HOSPITAL_TITLE = "Hospital beds"


def plot_hospital(data_status):
    """ Return a Hospital plot. """
    measures = ["Hospital beds", "ICU beds", "Ventilator beds"]
    colors = ["sandybrown", "salmon", "indianred"]
    return plot_bar_timeseries(data_status, measures, colors)


# *** Tests
TESTS_TITLE = "Testing volume"


def plot_tests(data_status):
    """ Return a Tests plot. """
    measures = ["Tests"]
    colors = ["darkslateblue"]
    return plot_bar_timeseries(data_status, measures, colors)


# *** Episode dates
EPISODE_TITLE = "Case outcomes"
EPISODE_TEXT = "Episode date is the estimated date of disease onset."


def plot_episode(data_con_pos):
    """ Return an Episode plot. """
    outcomes = date_agg(data_con_pos, agg_col="Outcome", date_col="Episode Date")
    outcomes = outcomes.rename(
        columns={"Not Resolved": "Outstanding", "Fatal": "Deaths"}
    )

    measures = ["Resolved", "Deaths", "Outstanding"]
    colors = ["darkseagreen", "darkgray", "steelblue"]
    return plot_bar_timeseries(outcomes, measures, colors)


# *** Age
AGE_CASES_SUBTITLE = "Cases by age group"
AGE_DEATHS_SUBTITLE = "Deaths by age group"


def plot_age_cases(data_con_pos):
    """ Return an age cases plot. """
    age_cases = date_agg(
        data_con_pos,
        agg_col="Age",
        date_col="Episode Date",
        cols_exclude=["<20", "Unknown"],
    )
    color_map = px.colors.sequential.Rainbow[1:]
    return plot_bar_timeseries(age_cases, measures=age_cases.columns, colors=color_map)


def plot_age_deaths(data_con_pos):
    """ Return an age deaths plot. """
    data_con_pos_fatal = data_con_pos[data_con_pos["Outcome"] == "Fatal"]
    age_cases = date_agg(data_con_pos_fatal, agg_col="Age", date_col="Episode Date")
    color_map = px.colors.sequential.Rainbow[1:]
    return plot_bar_timeseries(age_cases, measures=age_cases.columns, colors=color_map)


# *** Acquisition method
ACQ_TITLE = "Cases by acquisition method"


def plot_acquisition(data_con_pos):
    """ Return an Acquisition plot. """
    acq = date_agg(data_con_pos, agg_col="Acquisition", date_col="Episode Date")
    acq_norm = 100 * acq.divide(acq.sum(axis=1), axis=0)
    acq_norm = acq_norm.rename(columns={"Travel-Related": "Travel"})

    measures = [
        "Travel",
        "Contact of a confirmed case",
        "Neither",
        "Information pending",
    ]
    colors = ["orangered", "hotpink", "darkturquoise", "lightgrey"]
    fig = plot_bar_timeseries(acq_norm, measures, colors)
    fig.update_layout(
        xaxis_title="Episode date",
        yaxis_title="Percent"
    )
    return fig


# --- Page layout
def build_layout(datasets):
    most_recently_updated = format_date(get_most_recent_update(datasets))
    data_status = datasets["status"].data
    data_con_pos = datasets["con_pos"].data

    # Layout itself
    layout = dbc.Container(
        [
            # Header
            html.H1(TEXT_TITLE),
            html.H4(TEXT_TAGLINE),
            html.Br(),
            # Intro paragraph
            html.Div(
                html.P(
                    [
                        TEXT_BODY,
                        html.A(TEXT_LINK_CATALOG, href=URL_LINK_CATALOG),
                        ".",
                        html.Br(),
                        TEXT_WARNING,
                        html.A(TEXT_LINK_WARNING, href=URL_LINK_WARNING),
                        ".",
                    ]
                ),
            ),
            # Last updated
            html.Div(html.P([TEXT_MOST_RECENT_UPDATE, most_recently_updated])),
            html.Br(),
            # *** Plots!
            # Overview
            html.Div(
                [
                    html.H2([OVERVIEW_TITLE]),
                    dcc.Graph(
                        figure=plot_overview(data_status),
                        config={"displayModeBar": False},
                    ),
                    dcc.Graph(
                        figure=plot_overview_change(data_status),
                        config={"displayModeBar": False},
                    ),
                ]
            ),
            html.Br(),
            # Hospital
            html.Div(
                [
                    html.H2([HOSPITAL_TITLE]),
                    dcc.Graph(
                        figure=plot_hospital(data_status),
                        config={"displayModeBar": False},
                    ),
                ]
            ),
            html.Br(),
            # Tests
            html.Div(
                [
                    html.H2([TESTS_TITLE]),
                    dcc.Graph(
                        figure=plot_tests(data_status), config={"displayModeBar": False}
                    ),
                ]
            ),
            html.Br(),
            # Outcomes by episode date
            html.Div(
                [
                    html.H2([EPISODE_TITLE]),
                    html.P([EPISODE_TEXT]),
                    dcc.Graph(
                        figure=plot_episode(data_con_pos),
                        config={"displayModeBar": False},
                    ),
                ]
            ),
            html.Br(),
            # Cases by age group
            html.Div(
                [
                    html.H2([AGE_CASES_SUBTITLE]),
                    dcc.Graph(
                        figure=plot_age_cases(data_con_pos),
                        config={"displayModeBar": False},
                    ),
                ]
            ),
            html.Br(),
            # Deaths by age group
            html.Div(
                [
                    html.H2([AGE_DEATHS_SUBTITLE]),
                    dcc.Graph(
                        figure=plot_age_deaths(data_con_pos),
                        config={"displayModeBar": False},
                    ),
                ]
            ),
            html.Br(),
            # Acquisition method
            html.Div(
                [
                    html.H2([ACQ_TITLE]),
                    dcc.Graph(
                        figure=plot_acquisition(data_con_pos),
                        config={"displayModeBar": False},
                    ),
                ]
            ),
            html.Br(),
        ],
        style=CONTAINER_STYLE,
    )
    return layout


STYLESHEET = [dbc.themes.FLATLY]
CONTAINER_STYLE = {"marginTop": 50}

# ------ Controller ---------
app = dash.Dash(__name__, external_stylesheets=STYLESHEET)
server = app.server

# App restart: load data, and if necessary refresh it
datasets = build_datasets()

# Page refresh: check for new data, download if it has changed
def serve_layout():
    refresh_datasets(datasets)
    layout = build_layout(datasets)
    return layout


app.layout = serve_layout

if __name__ == "__main__":
    app.run_server()
