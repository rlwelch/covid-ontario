import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as ticker
import matplotlib.cm as cm
import matplotlib as mpl
import os.path

mpl.rc("font", family="Arial")

# Government of Ontario COVID data
# Base URL of the public facing website
BASE_URL = "https://data.ontario.ca/dataset"
# Names of datasets, which we can use to fetch CSVs
DATASETS = [
    "Status of COVID-19 cases in Ontario",
    "Confirmed positive cases of COVID-19 in Ontario",
]

# Folders to save test data and plots
FOLDER_TEST_DATA = "data"
FOLDER_IMAGES = "plots"


def get_website_url(dataset_name):
    """
    Return the URL of the public-facing website on COVID from the Government of Ontario.
    
    Parameter
    =========
    dataset_name: str
        The name of the dataset.
        
    Return
    ======
    str
        The URL of the public-facing website to scrape the CSV locations from.
    """
    url_title = dataset_name.lower().replace(" ", "-")
    url_website = "/".join([BASE_URL, url_title])
    return url_website


def get_data_urls(url_website):
    """
    Return the URLs of test data hosted by the Government of Ontario.
    
    Parameters
    ==========
    url_website: str
        The URL of the public-facing website on COVID from the Government of Ontario.
        
    Return
    ======
    url_test_data: list of str
        List of URLs for CSVs hosted on the site
    """
    response = requests.get(url_website, headers={"User-Agent": "Requests"})
    soup = BeautifulSoup(response.text, "html.parser")
    urls_html = soup.findAll(
        "a", class_="resource-url-analytics btn btn-primary dataset-download-link"
    )
    urls_data = [u["href"] for u in urls_html if "csv" in u["href"]]
    return urls_data


def fetch_test_data(urls_test_data):
    """
    Get and save today's Ontario COVID data. If it already exists, don't download again.
    
    Parameters
    ==========
    url_test_data: list of str
        URL to the CSV of today's COVID data.
    
    Return
    ======
    filepaths_test_data: list of str
        Local paths to the CSV files containing the COVID data.
    """
    date_iso = pd.to_datetime("now").strftime("%Y-%m-%d")
    date_folder = os.path.join(FOLDER_TEST_DATA, date_iso)
    if not os.path.exists(date_folder):
        os.mkdir(date_folder)

    filepaths_test_data = []
    for url in urls_test_data:
        basename_covid_data = os.path.basename(url)
        filename_covid_data = os.path.join(date_folder, basename_covid_data)

        if not os.path.exists(filename_covid_data):
            # print(f"File doesn't exist: {filename_covid_data}.\nDownloading from {url}.")
            http_response = requests.get(url)
            with open(filename_covid_data, "wb") as f:
                f.write(http_response.content)
        else:
            pass  # print(f"File already exists: {filename_covid_data}. Skipping download.")
        filepaths_test_data.append(filename_covid_data)

    return filepaths_test_data


def load_test_data(filename_test_data):
    """
    Load case data into memory.
    
    Parameters
    ==========
    filename_test_data: str
        Path to the CSV files containing the COVID data.
    
    Return
    ======
    tests: DataFrame
        The COVID data.
    """
    with open(filename_test_data, "rb") as f:
        tests = pd.read_csv(f)
    return tests


def clean_test_data(tests):
    """
    Clean the case data.
    
    Parameters
    ==========
    tests: DataFrame
        The COVID case count data.
        
    Return
    ======
    tests_cleaned: DataFrame
        The COVID case count data, cleaned.
    """
    df = tests.copy()
    df = df.set_index("Reported Date")
    df.index = pd.to_datetime(df.index)
    df = df.fillna(0)
    df = df.astype(int)
    tests_cleaned = df
    return tests_cleaned


def get_and_load_data(dataset_name):
    """
    Convenience function: return the DataFrame of today's test data.
    
    Parameter
    =========
    dataset_name: str
        The name of the dataset.
        
    Return
    ======
    tests: DataFrame
        The COVID data.
    """
    url_website = get_website_url(dataset_name)
    url_dataset = get_data_urls(url_website)
    path_dataset = fetch_test_data(url_dataset)[0]
    covid_data = load_test_data(path_dataset)
    return covid_data


def add_date_annotations(ax, events, start_y=0.40, color="tomato"):
    """
    Mark dates with annotations on a timeline.
    Add vertical lines with labels to an axes with a datetime x-axis.
    
    Parameters:
    ===========
    ax: matplotlib axes
        The axes to add the lines to
    
    events: list of dict
        The dates and annotations to plot. Each list item must have keys:
            date: str, ISO-8601
                The date of the intervention
            label: str
                The text to print to describe the action
                
    Return:
    =======
    The axes with the lines added
    """
    y_pos_initial = start_y
    y_pos_pad = 0.05
    x_pos_pad = pd.Timedelta(days=0.5)

    for n, event in enumerate(events):
        x_pos = pd.to_datetime(event["date"])
        ax.axvline(x_pos, color=color, linewidth=3, alpha=0.75)

        plt.text(
            x_pos + x_pos_pad,
            y_pos_initial - n * y_pos_pad,
            event["label"],
            fontsize=12,
            color=color,
            transform=ax.get_xaxis_transform(),
        )
    return ax


def plot_timeline(
    time_series,
    start_date,
    colormap="rainbow",
    title_append="",
    days_warning=0,
    plot_change=True,
    title_total=False
):
    """
    Make a pretty plot of a timeseries.
    
    Parameters
    ==========
    time_series: DataFrame
        Table with a datetimeindex
        
    start_date: str, in ISO8601
        The date to start the timeline. 
        
    Return 
    ======
    fig: matplotlib.figure.Figure
        Contains two Axes: total per day, change per day.
    """
    cmap = plt.get_cmap(colormap)
    small_font = 10
    medium_font = 14
    large_font = 16

    fig, ax_output = plt.subplots(nrows=1 + plot_change, ncols=1)

    time_series.index = pd.to_datetime(time_series.index)
    ts = {"total": time_series}
    axes = {"total": ax_output}
    text = {"total": {"title": "Total per day", "ylabel": "# Cases", "xlabel": "Date"}}
    if plot_change:
        fig.set_size_inches(20, 14)
        ts["change"] = time_series - time_series.shift(1)
        axes["total"] = ax_output[0]
        axes["change"] = ax_output[1]
        text["change"] = {
            "title": "Change per day",
            "ylabel": "# Cases",
            "xlabel": "Date",
        }
    else: 
        fig.set_size_inches(20, 7)

    # Iterate over the two kinds of graph: total, and change
    for name, ax in axes.items():
        # Restrict range in x-axis
        # Be even more restrictive in the change plot
        x_data_min = pd.to_datetime(start_date)
        if name == "change":
            x_data_min = x_data_min + pd.DateOffset(1)

        df = ts[name]
        df_plot = df[df.index >= x_data_min]

        # If there's a warning that the data is incomplete
        if days_warning:
            # Add an annotation
            date_of_warning = df_plot.index.max() - pd.Timedelta(days=days_warning)
            date_warning = [
                {
                    "date": f"{date_of_warning.strftime('%Y-%m-%d')}",
                    "label": "Incomplete\ndata",
                }
            ]
            add_date_annotations(ax, date_warning, start_y=0.8, color="gray")
            # Restrict the data in the change plot to hide it
            if name == "change":
                x_data_max = date_of_warning
                df_plot = df[df.index <= x_data_max]

        colors = cmap(np.linspace(0, 1, len(df_plot.columns)))
        bar_below = pd.Series(data=0, index=df_plot.index)
        # Iterate over the columns selected
        for col, c in zip(df_plot, colors):
            if name == "total":
                ax.bar(
                    x=df_plot.index,
                    height=df_plot[col],
                    label=col,
                    color=c,
                    bottom=bar_below,
                )
                bar_below = bar_below + df_plot[col]

            if name == "change":
                ax.plot(
                    df_plot[col],
                    linewidth=0,
                    marker="o",
                    markersize="7",
                    alpha=0.75,
                    # label=col,
                    color=c,
                )
                ax.plot(
                    df_plot[col].rolling(7).mean(),
                    linewidth="3",
                    linestyle="-",
                    markersize="0",
                    alpha=1,
                    label=f"{col} average",
                    color=c,
                )
                ax.axhline(0, linewidth="2", color="grey")

        # Restrict the y-limits as well
        if name == "change":
            df_mean = df_plot.rolling(7).mean()
            ax.set_ylim([df_mean.min().min() - 5, df_mean.max().max() + 5])

        ax.set_xlim(
            [pd.to_datetime(start_date), ts[name].index.max() + pd.DateOffset(1)]
        )
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%B %-d"))
        ax.xaxis.grid(True, which="major")

        title_text = text[name]["title"]
        if not plot_change:
            title_text = ""
        if title_total and (name == "total"):
            title_text = title_total
        if title_append:
            title_text = f"{title_append}\n{title_text}"
        ax.set_title(title_text, fontsize=large_font)

        handles, labels = ax.get_legend_handles_labels()
        ax.legend(
            reversed(handles),
            reversed(labels),
            loc="upper left",
            fontsize=medium_font,
            fancybox=True,
        )

        ax.set_xlabel("Date", fontsize=medium_font)
        ax.tick_params(labelsize=medium_font)

    fig.autofmt_xdate()
    return fig


def get_value_counts_timeseries(df, col_name):
    """Return a timeseries of how many counts there are of each value in col_name per day."""
    col_values = df[col_name].unique()
    # Create a new DataFrame to store counts per date
    bool_cols = pd.DataFrame(data=df["date"])
    # Add a new column for each value, showing whether the record matches that value
    for col in col_values:
        bool_cols[col] = df[col_name] == col
    # Aggregate over days to return a timeseries
    col_values_ts = bool_cols.groupby("date").sum()
    return col_values_ts


def mortality_groupby(outcomes, groupby_col_name, allowed_values=[]):
    """Show mortality disaggregated by the values in groupby_col_name."""
    df = outcomes[["Resolved", "Fatal"] + [groupby_col_name]]
    if allowed_values:
        df = df[df[groupby_col_name].isin(allowed_values)]

    df_sums = df.groupby(groupby_col_name).sum()
    df_sums["mortality"] = df_sums["Fatal"] / df_sums["Resolved"]
    df_sums["num_cases"] = (df_sums["Fatal"] + df_sums["Resolved"]).astype(int)
    return df_sums[["mortality", "num_cases"]]


def plot_mortality_groupby(mortality_groups, colormap="rainbow"):
    """Plot an hbar of mortalities grouped by category."""
    group_label = mortality_groups.index.name

    fig, ax = plt.subplots(figsize=(16, 8))

    cmap = plt.get_cmap(colormap)
    for i, mortality_group in enumerate(mortality_groups.index):
        mortality = mortality_groups.loc[mortality_group, "mortality"]
        plt.barh(y=mortality_group, width=mortality, color=cmap(mortality))
        ax.text(
            x=mortality + 0.0075, y=i - 0.05, s="{:.1%}".format(mortality), fontsize=16
        )

    ax.set_xlim([0, 1])
    ax.set_title(f"Mortality by {group_label}", fontsize=16)
    ax.set_xlabel("Mortality rate", fontsize=16)
    ax.set_ylabel(group_label.capitalize(), rotation=0, labelpad=40, fontsize=16)

    ax.xaxis.set_major_locator(ticker.MultipleLocator(0.1))
    ax.xaxis.set_major_formatter(ticker.PercentFormatter(1.0))
    ax.grid("on", which="major", axis="x", linestyle="--")
    ax.tick_params(axis="both", which="major", labelsize=16)
    return fig


def main():
    if not os.path.exists(FOLDER_TEST_DATA):
        os.mkdir(FOLDER_TEST_DATA)
    if not os.path.exists(FOLDER_IMAGES):
        os.mkdir(FOLDER_IMAGES)

    # ----- First dataset: status summary of cases -----
    # Download and clean up
    dataset = "Status of COVID-19 cases in Ontario"
    case_status = get_and_load_data(dataset)
    tests = clean_test_data(case_status)

    # Plot: Overview
    cases = tests[["Confirmed Positive", "Resolved", "Deaths"]]
    cases = cases.rename(columns={
        "Confirmed Positive": "Outstanding cases",
        "Resolved": "Resolved cases"
    })
    fig = plot_timeline(
        cases,
        "2020-03-15",
        colormap="tab20c",
        title_append="",
        title_total="Running total"
    )
    plt.xlabel("Date")
    fig.savefig(os.path.join(FOLDER_IMAGES, "overview.png"), bbox_inches='tight')

    # Plot: Hospital beds
    healthcare_cols = {
        "Number of patients hospitalized with COVID-19": "Hospital beds",
        "Number of patients in ICU with COVID-19": "ICU beds",
        "Number of patients in ICU on a ventilator with COVID-19": "Ventilated beds",
    }
    healthcare = tests[healthcare_cols].rename(columns=healthcare_cols)
    fig = plot_timeline(
        healthcare,
        "2020-04-02",
        colormap="Paired",
        title_append="Hospital beds occupied by COVID patients per day",
        plot_change=False,
    )
    fig.savefig(os.path.join(FOLDER_IMAGES, "hospital.png"), bbox_inches='tight')

    # Plot: Testing volume
    case_cols = ["Total tests completed in the last day"]
    cases = tests[case_cols]
    fig = plot_timeline(
        cases,
        "2020-04-14",
        colormap="tab20b",
        title_append="COVID tests performed in the last day",
        plot_change=False,
    )
    ax = plt.gca()
    ax.legend().set_visible(False)
    plt.xlabel("Date")
    fig.savefig(os.path.join(FOLDER_IMAGES, "testing.png"), bbox_inches='tight')

    # ----- Second dataset: Confirmed positive COVID-19 cases-----
    # Download and clean up
    dataset = "Confirmed positive cases of COVID-19 in Ontario"
    pos_csv = get_and_load_data(dataset)
    outcomes = pos_csv.rename(
        columns={
            "Accurate_Episode_Date": "date",
            "Case_AcquisitionInfo": "acquisition",
            "Age_Group": "age",
            "Client_Gender": "gender",
            "Reporting_PHU_City": "city",
            "Outcome1": "outcome",
        }
    )
    outcomes["date"] = pd.to_datetime(outcomes["date"])
    outcomes["Fatal"] = outcomes["outcome"] == "Fatal"
    outcomes["Resolved"] = outcomes["outcome"] == "Resolved"

    # Plot: confirmed positive cases by episode date
    outcomes["Cases"] = "Cases"
    all_cases_ts = get_value_counts_timeseries(outcomes, "Cases")
    fig = plot_timeline(
        all_cases_ts,
        "2020-03-08",
        colormap="tab10",
        title_append="COVID cases by episode date",
        days_warning=7,
        plot_change=False,
    )
    plt.xlabel("Episode date")
    fig.savefig(os.path.join(FOLDER_IMAGES, "positive_cases.png"), bbox_inches='tight')

    # Plot: deaths by episode date
    mask_fatal = outcomes["outcome"] == "Fatal"
    outcomes["Deaths"] = ""
    outcomes.loc[mask_fatal, "Deaths"] = "Deaths"
    deaths_ts = get_value_counts_timeseries(outcomes, "Deaths")
    fig = plot_timeline(
        deaths_ts[["Deaths"]],
        "2020-03-08",
        colormap="RdBu",
        title_append="COVID deaths by episode date",
        days_warning=14,
        plot_change=False,
    )
    plt.xlabel("Episode date")
    fig.savefig(os.path.join(FOLDER_IMAGES, "deaths.png"), bbox_inches='tight')

    # Plot: cases by city
    # Get the top cities by case count
    num_cities = 9
    city_hotspots = outcomes["city"].value_counts().head(num_cities).index
    mask_not_hotspot = ~outcomes["city"].isin(city_hotspots)
    # Create a new column with just the top cities, and rename any other cities "other"
    outcomes["city_group"] = outcomes["city"]
    outcomes.loc[mask_not_hotspot, "city_group"] = "Other"
    city_ts = get_value_counts_timeseries(outcomes, "city_group")
    fig = plot_timeline(
        city_ts,
        start_date="2020-03-08",
        title_append="COVID cases by Public Health Unit",
        days_warning=7,
        plot_change=False,
    )
    plt.xlabel("Episode date")
    fig.savefig(os.path.join(FOLDER_IMAGES, "cases_city.png"), bbox_inches='tight')

    # Plot: deaths by city
    mask_fatal = outcomes["outcome"] == "Fatal"
    fatal_cases = outcomes[mask_fatal]
    # Use the same city groups as the plot above
    fatal_city_ts = get_value_counts_timeseries(fatal_cases, "city_group")
    fatal_city_ts = fatal_city_ts[city_ts.columns]
    fig = plot_timeline(
        fatal_city_ts,
        start_date="2020-03-08",
        title_append="COVID deaths by Public Health Unit",
        days_warning=14,
        plot_change=False,
    )
    plt.xlabel("Episode date")
    fig.savefig(os.path.join(FOLDER_IMAGES, "deaths_city.png"), bbox_inches='tight')

    # Plot: cases by age group
    age_ts = get_value_counts_timeseries(outcomes, "age")
    age_ts = age_ts[["20s", "30s", "40s", "50s", "60s", "70s", "80s", "90s"]]
    fig = plot_timeline(
        age_ts,
        start_date="2020-03-08",
        colormap="jet",
        title_append="COVID cases by age group",
        days_warning=7,
        plot_change=False,
    )
    plt.xlabel("Episode date")
    fig.savefig(os.path.join(FOLDER_IMAGES, "cases_age.png"), bbox_inches='tight')

    # Plot: deaths by age group
    mask_fatal = outcomes["outcome"] == "Fatal"
    fatal_cases = outcomes[mask_fatal]
    age_ts = get_value_counts_timeseries(fatal_cases, "age")
    if not "20s" in age_ts:
        age_ts["20s"] = 0
    age_ts = age_ts[["20s", "30s", "40s", "50s", "60s", "70s", "80s", "90s"]]
    fig = plot_timeline(
        age_ts,
        start_date="2020-03-08",
        colormap="jet",
        title_append="COVID deaths by age group",
        days_warning=14,
        plot_change=False,
    )
    plt.xlabel("Episode date")
    fig.savefig(os.path.join(FOLDER_IMAGES, "deaths_age.png"), bbox_inches='tight')

    # Plot: cases by acquisition method
    acquisition_ts = get_value_counts_timeseries(outcomes, "acquisition")
    fig = plot_timeline(
        acquisition_ts,
        start_date="2020-03-08",
        colormap="tab20",
        title_append="COVID cases by acquisition method",
        days_warning=7,
    )
    plt.xlabel("Episode date")
    fig.savefig(os.path.join(FOLDER_IMAGES, "cases_acquisition.png"), bbox_inches='tight')

    # Plot: mortality by age
    mortality_age = mortality_groupby(outcomes, "age")
    age_exclude = ["<20", "Unknown"]
    mortality_age = mortality_age[~mortality_age.index.isin(age_exclude)]
    fig = plot_mortality_groupby(mortality_age)
    plt.title("")
    fig.savefig(os.path.join(FOLDER_IMAGES, "mortality_age.png"), bbox_inches='tight')


if __name__ == "__main__":
    main()
