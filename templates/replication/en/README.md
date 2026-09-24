# Replication package — @@TITLE@@

This package alone reproduces every number, figure and table in the paper.

## Contents

    analysis/       the analysis (Quarto .qmd) and the helper octavo.R
    data/           data@@RAWNOTE@@
    data/HASHES.json  fingerprints (sha256) of the data that was used
    results/        the numbers the analysis produced (the ones in the text) and a record of the software
    figures/ tables/  the figures and tables the analysis produced
    octavo.config.py  settings
    literature.bib    bibliography

## Running it again

    quarto render analysis/*.qmd

or, with [octavo](https://github.com/yoshida-kd/octavo) installed,

    octavo analysis run --force
    octavo values --diff      # did the same numbers come out?

## Software

@@SESSION@@

## Data fingerprints

`data/HASHES.json` holds the sha256 of the data used at the time.
To check that your copy of the data is the same:

    octavo data status
