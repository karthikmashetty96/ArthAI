#!/bin/bash
# run.sh - Start the ArthAI Terminal application
cd "$(dirname "$0")"
venv/bin/python -m streamlit run app.py
