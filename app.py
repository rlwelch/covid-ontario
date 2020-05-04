import os
import requests
import pandas as pd
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc

# --- Model: Requests and Pandas ---
# Data sources
API_BASE = "https://data.ontario.ca/api/3/action/"
PACKAGE_IDS = {
    "status": "f4f86e54-872d-43f8-8a86-3892fd3cb5e6",
    "con_pos": "f4112442-bdc8-45d2-be3c-12efae72fb27",
}
PACKAGE_LABELS = {
    "status": "Status of COVID-19 cases in Ontario",
    "con_pos": "Confirmed positive cases of COVID19 in Ontario",
}


def get_resource_id(package_name):
    """
    Return the resource ID and last modified date of the CSV resource belonging to a package name.
    """
    url = f"{API_BASE}package_show?id={PACKAGE_IDS[package_name]}"
    resources = requests.get(url).json()["result"]["resources"]
    resource = [
        r
        for r in resources
        if (r["format"] == "CSV") and (r["name"] == PACKAGE_LABELS[package_name])
    ][0]
    last_modified = resource.get("last_modified")
    id = resource.get("id")
    return id, last_modified


def get_resource_data(resource_id):
    """
    Return the contents of the resource in a Pandas DataFrame.
    """
    url = f"{API_BASE}datastore_search?resource_id={resource_id}&limit=32000"
    pass


def model():
    # Get the current ID of the resources, and how recently they were updated
    resource_ids = {}
    last_updated = {}
    for name, package_id in PACKAGE_IDS.items():
        resource_ids[name], last_updated[name] = get_resource_id(name)
    most_recent_update = (
        pd.to_datetime(list(last_updated.values())).tz_localize(tz="UTC").max()
    )

    return most_recent_update


# --- View: Plotly, configurations for Dash  ---
def format_date(unformatted_date):
    timezone_label = "Eastern"
    timezone_dest = "Canada/Eastern"
    date_format = "%B %-d, %-I:%M %p"

    localized_date = unformatted_date.tz_convert(timezone_dest)
    formatted_datetime = localized_date.strftime(date_format)
    return f"{formatted_datetime} ({timezone_label})"

STYLESHEET = [dbc.themes.FLATLY]

TEXT_TITLE = "covid-ontario"
TEXT_TAGLINE = "Follow the rise and fall of COVID-19 in Ontario."
TEXT_BODY = """This is an independent project to visualize the Ontario Government’s Data Catalog."""
TEXT_WARNING = """Please do your part to stop the spread."""
TEXT_MOST_RECENT_UPDATE = "Most recent update: {}"

# --- Controller: Dash ---
# Dash app configuration
def display_most_recent_update():
    most_recent_update = model()
    display_date = format_date(most_recent_update)
    return display_date

# Dash
app = dash.Dash(__name__, external_stylesheets=STYLESHEET)
server = app.server
app.layout = dbc.Container(
    [
        html.H2(TEXT_TITLE),
        html.H6(TEXT_TAGLINE),
        html.Div(
            html.P(
                [
                    TEXT_BODY,
                    html.Br(),
                    TEXT_WARNING,
                ]
            ),
        ),
        html.Div(
            TEXT_MOST_RECENT_UPDATE.format(display_most_recent_update()),
        )
    ],
    style={'marginTop': 50}
)

if __name__ == "__main__":
    app.run_server(debug=True)
