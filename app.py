import os
import requests
import pickle
import pandas as pd
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
        self.get_resource()

        # If there is an update
        #   Download, clean and save data in the cache
        if self.last_modified != current_last_modified:
            self.get_resource_data()
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
        Get the attributes of the CSV resource associated with the to the package ID.
        """
        url = f"{API_BASE}package_show?id={self.package_id}"
        resources = requests.get(url).json()["result"]["resources"]
        resource = [r for r in resources if (r.get("format") == "CSV")][0]
        self.resource_id = resource.get("id")
        self.resource_name = resource.get("name")
        self.url = resource.get("url")
        self.last_modified = resource.get("last_modified")

    def get_resource_data(self):
        """
        Get tabular data from the resource.
        Wrapper for the more specific downloading functions.
        Note: if this doesn't work, consider switching to CSV downloads. 
        """
        if self.name == "status":
            self.get_resource_data_status()
        if self.name == "con_pos":
            self.get_resource_data_con_pos()

    # Downloading functions for each of the two datasets
    def get_resource_data_status(self):
        """ 
        Get the "Status of COVID-19 cases in Ontario" dataset
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
        records = requests.get(url).json()["result"]["records"]
        self.data = pd.DataFrame(records)

    def get_resource_data_con_pos(self):
        """ 
        Get the "Confirmed positive cases of COVID-19 in Ontario" dataset
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
        records = requests.get(url).json()["result"]["records"]
        self.data = pd.DataFrame(records)

    def clean_data(self):
        """
        Prepare data for plotting.
        Wrapper for the more specific cleaning functions.
        """
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
        df = df.set_index("Reported Date")
        df.index = pd.to_datetime(df.index)
        df = df.fillna(0)
        df = df.astype(int)
        df = df.rename(
            columns={
                "Confirmed Positive": "Outstanding cases",
                "Resolved": "Resolved cases",
                "Number of patients hospitalized with COVID-19": "Hospital beds",
                "Number of patients in ICU with COVID-19": "ICU beds",
                "Number of patients in ICU on a ventilator with COVID-19": "Ventilated beds",
            }
        )
        self.data = df

    def clean_data_con_pos(self):
        """ 
        Clean the "Confirmed positive cases of COVID-19 in Ontario" dataset
        """
        pass


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
TEXT_LINK_CATALOG = "Ontario Data Catalog"
URL_LINK_CATALOG = "https://data.ontario.ca/dataset?keywords_en=COVID-19"

TEXT_WARNING = "Please do your part to "
TEXT_LINK_WARNING = "stop the spread"
URL_LINK_WARNING = "https://covid-19.ontario.ca/index.html"

TEXT_MOST_RECENT_UPDATE = "Most recent update: "

TEXT_STATUS_TABLE = "Status of recent cases: "
TEXT_CON_POS_TABLE = "Confirmed positives: "

# ------ View ------
# --- Data formatting
def format_date(unformatted_date):
    timezone_label = "Eastern"
    timezone_dest = "Canada/Eastern"
    date_format = "%B %-d, %-I:%M %p"

    localized_date = unformatted_date.tz_convert(timezone_dest)
    formatted_datetime = localized_date.strftime(date_format)
    return f"{formatted_datetime} {timezone_label}"


# --- Page layout
def build_layout(datasets):
    most_recently_updated = format_date(get_most_recent_update(datasets))
    data_status = datasets["status"].data.tail(10)
    data_con_pos = datasets["con_pos"].data.tail(10)

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
            # Data table: status of recent cases
            html.Div(html.P(TEXT_STATUS_TABLE)),
            dash_table.DataTable(
                id="table_status",
                columns=[{"name": i, "id": i} for i in data_status.columns],
                data=data_status.to_dict("records"),
            ),
            html.Br(),
            # Data table: confirmed positive cases
            html.Div(html.P(TEXT_CON_POS_TABLE)),
            dash_table.DataTable(
                id="table_con_pos",
                columns=[{"name": i, "id": i} for i in data_con_pos.columns],
                data=data_con_pos.to_dict("records"),
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

# App restart: download data
datasets = build_datasets()

# Page refresh: check for new data, download if it has changed
def serve_layout():
    refresh_datasets(datasets)
    layout = build_layout(datasets)
    return layout


app.layout = serve_layout

if __name__ == "__main__":
    app.run_server(debug=True)
