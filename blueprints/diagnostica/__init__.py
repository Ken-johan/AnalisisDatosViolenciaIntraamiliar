"""Diagnóstica blueprint"""
from flask import Blueprint, render_template
import pandas as pd
import plotly.express as px
import plotly
import json, os
from utils import load_config

diagnostica_bp = Blueprint('diagnostica', __name__, template_folder='templates')

@diagnostica_bp.route('/')
def diagnostica_home():
    # Load cached dataset
    data_path = os.path.join(os.path.dirname(__file__), '..', 'Data', 'dataset.pkl')
    df = pd.read_pickle(data_path)
    # Correlation heatmap for numeric columns
    numeric = df.select_dtypes(include='number')
    corr = numeric.corr().fillna(0)
    fig = px.imshow(corr, text_auto=True, aspect='auto')
    chart_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return render_template('diagnostica.html', chart_json=chart_json)
