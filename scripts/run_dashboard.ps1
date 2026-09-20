$ErrorActionPreference = "Stop"

Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
pip install -e .
streamlit run "src/leadgen/dashboard.py"
