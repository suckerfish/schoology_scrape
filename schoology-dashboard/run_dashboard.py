#!/usr/bin/env python3
"""
Schoology Dashboard Launch Script
Independent Streamlit dashboard for grade visualization
"""
import subprocess
import sys

if __name__ == "__main__":
    # Run the Streamlit app
    subprocess.run([sys.executable, "-m", "streamlit", "run", "streamlit_viewer.py"])