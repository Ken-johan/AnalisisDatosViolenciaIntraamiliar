"""Prescriptivo blueprint"""
from flask import Blueprint, render_template, request
import pandas as pd, os, json, plotly.express as px, plotly
from utils import load_config

prescriptivo_bp = Blueprint('prescriptivo', __name__, template_folder='templates')

def compute_priorities(df, focus_year, previous_year):
    # Aggregate counts per department for two years
    cur = df[df['year'] == focus_year].groupby('department').size().rename('focus')
    prev = df[df['year'] == previous_year].groupby('department').size().rename('previous')
    merged = pd.concat([cur, prev], axis=1).fillna(0)
    merged['variation'] = ((merged['focus'] - merged['previous']) / merged['previous'].replace(0, 1) * 100).round(2)
    merged['participation'] = (merged['focus'] / merged['focus'].sum() * 100).round(2)
    merged = merged.reset_index().sort_values('focus', ascending=False)
    return merged.to_dict(orient='records')

@prescriptivo_bp.route('/')
def prescriptivo_home():
    cfg = load_config()
    data_path = os.path.join(os.path.dirname(__file__), '..', 'Data', 'dataset.pkl')
    df = pd.read_pickle(data_path)
    # default years
    focus_year = int(request.args.get('year', df['year'].max()))
    previous_year = focus_year - 1
    priorities = compute_priorities(df, focus_year, previous_year)
    return render_template('prescriptivo.html', priorities=priorities, focus_year=focus_year, previous_year=previous_year)
