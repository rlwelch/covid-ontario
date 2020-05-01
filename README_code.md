# covid-ontario
Follow the rise and fall of COVID-19 in Ontario.

## Overview
The current process to produce this site is:
* Run`covid_ontario/plot_on_gov_data.py`:
  * Download the most current data from the Ontario Government Open Data Catalog
  * Make plots using `matplotlib`
  * Save the plots as PNGs
* Commit and push the plots to GitHib
* Display the plots in `README.md`, hosted by GitHub Pages

## Setup
* Install requirements
```
python3 -m venv env
pip install -r requirements.txt
source env/bin/activate
```

## Running
In the `covid_ontario` directory:
```
python plot_on_gov_data.py
```
