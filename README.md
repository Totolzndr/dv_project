python3 -m venv .venv

source .venv/bin/activate

python -m pip install --upgrade pip

python -m pip install streamlit pandas plotly

streamlit run map.py