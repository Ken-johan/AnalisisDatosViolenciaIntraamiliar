"""Descriptivo blueprint"""
from flask import Blueprint, render_template, request
import pandas as pd, os
from utils import load_config

# Load dataset once per request (cached in memory could be added later)

descriptivo_bp = Blueprint('descriptivo', __name__, template_folder='templates')

@descriptivo_bp.route('/')
def descriptivo_home():
    # Load data
    data_path = os.path.join(os.path.dirname(__file__), '..', 'Data', 'dataset.pkl')
    df = pd.read_pickle(data_path)

    # Apply filters from query parameters (year, department)
    selected_year = request.args.get('year', 'all')
    selected_dept = request.args.get('department', 'all')
    if selected_year != 'all':
        df = df[df['year'] == int(selected_year)]
    if selected_dept != 'all':
        df = df[df['department'] == selected_dept]

    # Basic metrics
    total = len(df)
    women_share = (df['sex'] == 'mujer').mean() * 100 if len(df) else 0
    leading_scene = df['scene'].mode()[0] if len(df) else 'Sin datos'

    # Growth rate (inter‑annual) based on the most recent full year
    if 'year' in df.columns:
        current_year = df['year'].max()
        prev_year = current_year - 1
        total_current = len(df[df['year'] == current_year])
        total_prev = len(df[df['year'] == prev_year])
        growth_rate = ((total_current - total_prev) / total_prev * 100) if total_prev else 0
    else:
        growth_rate = 0

    # Load KPI thresholds
    cfg = load_config()
    alerts = {
        'total_incidents': total > cfg.get('kpis', {}).get('total_incidents', {}).get('threshold', 1e9),
        'women_share': women_share > cfg.get('kpis', {}).get('women_share', {}).get('threshold', 100),
        'growth_rate': growth_rate > cfg.get('kpis', {}).get('growth_rate', {}).get('threshold', 9999),
    }

    total = len(df)
    women_share = (df['sex'] == 'mujer').mean() * 100 if len(df) else 0
    leading_scene = df['scene'].mode()[0] if len(df) else 'Sin datos'

    # Load KPI thresholds
    cfg = load_config()
    alerts = {
        'total_incidents': total > cfg.get('kpis', {}).get('total_incidents', {}).get('threshold', 1e9),
        'women_share': women_share > cfg.get('kpis', {}).get('women_share', {}).get('threshold', 100),
    }

    # Years and departments for filter selectors (from original index logic)
    years = sorted(df['year'].unique()) if 'year' in df.columns else []
    departments = sorted(df['department'].unique()) if 'department' in df.columns else []
    selected_year_val = selected_year if selected_year != 'all' else 'all'
    selected_dept_val = selected_dept if selected_dept != 'all' else 'all'

    return render_template('descriptivo.html', total=total, women_share=women_share,
                           leading_scene=leading_scene, alerts=alerts,
                           years=years, departments=departments,
                           selected_year=selected_year_val, selected_department=selected_dept_val)
