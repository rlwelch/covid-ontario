#!/bin/bash

source env/bin/activate
cd covid_ontario
python plot_on_gov_data.py
git add plots/*.png

TODAY=$(date +%Y-%m-%d)
git commit -m "Daily plot update: $(echo $TODAY)" 

git push
