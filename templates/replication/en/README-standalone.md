# Replication package — @@TITLE@@

This package alone reproduces the numbers, figures and tables in the paper. You need
[Quarto](https://quarto.org/) and the R or Python packages the analysis uses.

## Contents

    analysis/       the analysis (Quarto .qmd files)
    data/           the data@@RAWNOTE@@
    data/HASHES.json  fingerprints (sha256) of the data used
    assets/values/  the numbers in the paper, with a record of the environment that made them
    assets/figures/ assets/tables/  the paper's figures and tables
    literature.bib    the bibliography
    renv.lock requirements.txt  the package versions used (when the project has them)

## Setting up

@@SETUP@@

## Running it again

From this folder:

@@RUN@@

Paths in the code are relative to the folder holding the `.qmd`. To run chunks one at a time, make
`analysis/` the working directory.

Figures go to `assets/figures/` and tables to `assets/tables/` as CSV. Numbers appear in the HTML as
`name: value`, so you can compare them with the record in `assets/values/`.

## Environment

@@SESSION@@

## Data fingerprints

`data/HASHES.json` holds the sha256 of the data used.
