import os
import requests
import pickle
import pandas as pd
import plotly.graph_objects as go
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

TEXT_STATUS_TABLE = "Status of recent cases"
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
def plot_bar_timeseries(df, measures, colors, start_date):
    """ Make a pretty bar plot of a timeseries """
    bars = [
        go.Bar(name=m, x=df.index, y=df[m], marker_color=c, hovertemplate="%{x}: %{y}")
        for c, m in zip(colors, measures)
    ]

    fig = go.Figure(
        data=bars,
        layout=go.Layout(
            barmode="stack",
            xaxis={
                "type": "date",
                "range":[pd.to_datetime(start_date), pd.to_datetime("today")],
                "tickformat": "%B %-d",
                "tickvals": [d for d in
                    pd.date_range(df.index.min(), df.index.max())
                    if (d.day in [1, 15])
                    ],
                "showgrid": True,
                "gridcolor": "gainsboro",
            },
            yaxis={
                "showgrid": True,
                "gridcolor": "gainsboro",
            },
             legend={
                "xanchor":"center",
                "x": 0.5,
                "y": 1.1,
                "orientation": "h",
                "traceorder": "reversed",
            },
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin={"t": 0, "l": 0, "r": 0},
        ),
    )
    return fig


# *** Overview
OVERVIEW_TITLE = "Overview"


def plot_overview(df):
    """ Return an Overview plot. """
    measures = ["Outstanding cases", "Deaths"]
    colors = ["steelblue", "darkgray"]
    start_date = "2020-03-08"
    return plot_bar_timeseries(df, measures, colors, start_date)

# *** Hospital
HOSPITAL_TITLE = "Hospital beds"

def plot_hospital(df):
    """ Return a Hospital plot. """
    measures = ["Hospital beds", "ICU beds", "Ventilator beds"]
    colors = ["sandybrown", "salmon", "indianred"]
    start_date = "2020-03-08"
    return plot_bar_timeseries(df, measures, colors, start_date)


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
                        config={'displayModeBar': False}
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
                        config={'displayModeBar': False}
                        ),
                ]
            ),
            html.Br(),
            # Data table: confirmed positive cases
            html.Div(html.H2(TEXT_CON_POS_TABLE)),
            dash_table.DataTable(
                id="table_con_pos",
                columns=[{"name": i, "id": i} for i in data_con_pos.columns],
                data=data_con_pos.tail(10).to_dict("records"),
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
