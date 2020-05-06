import os
import requests
import pandas as pd
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc

# ------ Model ------
# --- Data
# Data source
API_BASE = "https://data.ontario.ca/api/3/action/"
PACKAGE_IDS = {
    "status": "f4f86e54-872d-43f8-8a86-3892fd3cb5e6",
    "con_pos": "f4112442-bdc8-45d2-be3c-12efae72fb27",
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
        self.last_modified = ""
        self.data = pd.DataFrame()

    def get_resource(self):
        """
        Get the attributes of the CSV resource associated with the to the package ID.
        """
        url = f"{API_BASE}package_show?id={self.package_id}"
        resources = requests.get(url).json()["result"]["resources"]
        resource = [r for r in resources if (r.get("format") == "CSV")][0]
        self.resource_id = resource.get("id")
        self.resource_name = resource.get("name")
        self.last_modified = resource.get("last_modified")

    def get_resource_data(self):
        """
        Get the tabular data from the resource.
        """
        url = f"{API_BASE}datastore_search?resource_id={self.resource_id}&limit=32000"
        records = requests.get(url).json()["result"]["records"]
        self.data = pd.DataFrame(records)


def build_datasets():
    """ Download and return every dataset in PACKAGE_ID. """
    datasets = {}
    for name, package_id in PACKAGE_IDS.items():
        d = Dataset(name, package_id)
        d.get_resource()
        d.get_resource_data()
        datasets[name] = d 
    return datasets

def most_recent_update(datasets):
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
    layout = dbc.Container(
    [
            # Header
            html.H1(TEXT_TITLE),
            html.H4(TEXT_TAGLINE),
            html.Br(),

            # Intro paragraph
            html.Div(
                html.P([
                TEXT_BODY, html.A(TEXT_LINK_CATALOG, href=URL_LINK_CATALOG), ".",
                html.Br(), 
                TEXT_WARNING, html.A(TEXT_LINK_WARNING, href=URL_LINK_WARNING), ".",
                ]),
                ),

            # Last updated
            html.Div(
                html.P([
                TEXT_MOST_RECENT_UPDATE, format_date(most_recent_update(datasets))
            ])
            )
        ], 
        style=CONTAINER_STYLE
    )
    return layout


STYLESHEET = [dbc.themes.FLATLY]
CONTAINER_STYLE = {"marginTop": 50}

# ------ Controller ---------
app = dash.Dash(__name__, external_stylesheets=STYLESHEET)
server = app.server

datasets = build_datasets()

app.layout = build_layout(datasets)

if __name__ == "__main__":
    app.run_server(debug=True)
