# Replication package — @@TITLE@@

This package alone reproduces every number, figure and table in the paper.

## Contents

    analysis/       the analysis (Quarto .qmd) and the helper (octavo.R or octavo_helper.py)
    data/           data@@RAWNOTE@@
    data/HASHES.json  fingerprints (sha256) of the data that was used
    assets/values/  the numbers the analysis produced (the ones in the text) and a record of the software
    assets/figures/ assets/tables/  the figures and tables in the paper
    figures/        figures drawn by hand in Typst (<name>.typ), if any
    octavo.config.py  settings
    literature.bib    bibliography

## Running it again

    quarto render analysis/*.qmd

or, with [Octavo](https://github.com/yoshida-kd/octavo) installed,

    octavo analysis run --force
    octavo values --diff      # did the same numbers come out?

## Software

@@SESSION@@

## Data fingerprints

`data/HASHES.json` holds the sha256 of the data used at the time.
To check that your copy of the data is the same:

    octavo data status
