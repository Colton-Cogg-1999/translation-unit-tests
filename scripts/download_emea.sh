#!/usr/bin/env bash
# Download the OPUS EMEA English–Spanish parallel corpus (EU medicines documentation) into data/raw/EMEA.
# Corpus: J. Tiedemann, "Parallel Data, Tools and Interfaces in OPUS", LREC 2012. https://opus.nlpl.eu/EMEA
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p data/raw/EMEA
curl -sSL -o data/raw/EMEA.zip "https://object.pouta.csc.fi/OPUS-EMEA/v3/moses/en-es.txt.zip"
unzip -oq data/raw/EMEA.zip -d data/raw/EMEA && rm data/raw/EMEA.zip
wc -l data/raw/EMEA/EMEA.en-es.en
