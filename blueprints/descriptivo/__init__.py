"""Descriptivo blueprint – Nivel 1: ¿Qué pasó?"""
from flask import Blueprint, render_template, request
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly
import json
from utils import get_dataset, load_config

descriptivo_bp = Blueprint('descriptivo', __name__, template_folder='../../templates')

# Paleta profesional multidimensional (NO monocromática naranja)
PALETTE_CATEGORICAL = ['#2563eb', '#0d9488', '#d97706', '#7c3aed', '#dc2626', '#0891b2', '#4f46e5', '#db2777']
PALETTE_GENDER = {'Mujer': '#db2777', 'Hombre': '#0284c7', 'Sin información': '#94a3b8'}


def _chart_json(fig):
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Inter, Segoe UI, sans-serif', size=11, color='#334155'),
        margin=dict(l=40, r=20, t=30, b=40),
    )
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


@descriptivo_bp.route('/')
def descriptivo_home():
    df = get_dataset()

    selected_year = request.args.get('year', 'all')
    selected_dept = request.args.get('department', 'all')

    filtered = df.copy()
    if selected_year != 'all':
        filtered = filtered[filtered['year'] == int(selected_year)]
    if selected_dept != 'all':
        filtered = filtered[filtered['department'] == selected_dept]

    total = len(filtered)
    women_count = (filtered['sex'].astype(str).str.lower() == 'mujer').sum() if total else 0
    women_share = round(women_count / total * 100, 1) if total else 0
    leading_scene = filtered['scene'].mode().iloc[0] if total else 'Sin datos'
    vivienda_count = (filtered['scene'].astype(str).str.lower().str.contains('vivienda', na=False)).sum()
    vivienda_share = round(vivienda_count / total * 100, 1) if total else 0

    # Crecimiento interanual
    annual = df.groupby('year').size()
    max_year = int(annual.index.max()) if len(annual) else 2024
    prev_year = max_year - 1
    cur_total = int(annual.get(max_year, 0))
    prev_total = int(annual.get(prev_year, 0))
    growth_rate = round((cur_total - prev_total) / prev_total * 100, 1) if prev_total else 0

    # Banderas rojas y KPIs desde config
    cfg = load_config()
    kpis = cfg.get('kpis', {})
    alerts = {
        'total_incidents': total > kpis.get('total_incidents', {}).get('threshold', 200000),
        'women_share': women_share > kpis.get('women_share', {}).get('threshold', 70.0),
        'growth_rate': growth_rate > kpis.get('growth_rate', {}).get('threshold', 10.0),
        'vivienda_share': vivienda_share > kpis.get('vivienda_share', {}).get('threshold', 75.0),
    }

    # Gráficos descriptivos con paleta profesional
    charts = {}

    # 1. Evolución anual (línea con área azul acero)
    annual_data = df.groupby('year').size().reset_index(name='count')
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=annual_data['year'], y=annual_data['count'],
        mode='lines+markers', name='Registros',
        line=dict(color='#2563eb', width=3),
        marker=dict(size=8, color='#1d4ed8'),
        fill='tozeroy', fillcolor='rgba(37, 99, 235, 0.08)',
    ))
    fig.update_layout(title='', xaxis_title='Año del hecho', yaxis_title='Cantidad de registros')
    charts['annual'] = _chart_json(fig)

    # 2. Distribución por sexo (Donut contrastado Rosa / Azul cielo)
    sex_data = filtered['sex'].value_counts().reset_index()
    sex_data.columns = ['sex', 'count']
    fig = px.pie(sex_data, values='count', names='sex',
                 color='sex',
                 color_discrete_map={'Mujer': '#db2777', 'Hombre': '#0284c7', 'Sin información': '#94a3b8'},
                 hole=0.45)
    charts['sex'] = _chart_json(fig)

    # 3. Escenarios más frecuentes (Barras horizontales Teal)
    scene_data = filtered['scene'].value_counts().head(8).reset_index()
    scene_data.columns = ['scene', 'count']
    fig = px.bar(scene_data, x='count', y='scene', orientation='h',
                 color_discrete_sequence=['#0d9488'])
    fig.update_layout(yaxis=dict(autorange='reversed'), xaxis_title='Registros', yaxis_title='')
    charts['scenes'] = _chart_json(fig)

    # 4. Departamentos (Barras horizontales Índigo)
    dept_data = filtered['department'].value_counts().head(10).reset_index()
    dept_data.columns = ['department', 'count']
    fig = px.bar(dept_data, x='count', y='department', orientation='h',
                 color_discrete_sequence=['#4f46e5'])
    fig.update_layout(yaxis=dict(autorange='reversed'), xaxis_title='Registros', yaxis_title='')
    charts['departments'] = _chart_json(fig)

    # 5. Factores desencadenantes (Barras Ámbar)
    trig_data = filtered['trigger'].value_counts().head(8).reset_index()
    trig_data.columns = ['trigger', 'count']
    fig = px.bar(trig_data, x='count', y='trigger', orientation='h',
                 color_discrete_sequence=['#d97706'])
    fig.update_layout(yaxis=dict(autorange='reversed'), xaxis_title='Registros', yaxis_title='')
    charts['triggers'] = _chart_json(fig)

    # 6. Días de la semana (Barras Púrpura)
    weekday_order = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
    wd_data = filtered['weekday'].value_counts().reindex(weekday_order).dropna().reset_index()
    wd_data.columns = ['weekday', 'count']
    fig = px.bar(wd_data, x='weekday', y='count', color_discrete_sequence=['#7c3aed'])
    fig.update_layout(xaxis_title='', yaxis_title='Registros')
    charts['weekdays'] = _chart_json(fig)

    # 7. Rango horario (Barras Esmeralda)
    if 'time_range' in filtered.columns:
        hour_data = filtered['time_range'].value_counts().head(8).reset_index()
        hour_data.columns = ['range', 'count']
        fig = px.bar(hour_data, x='range', y='count', color_discrete_sequence=['#059669'])
        fig.update_layout(xaxis_title='Franja horaria', yaxis_title='Registros')
        charts['hours'] = _chart_json(fig)

    years = sorted(df['year'].dropna().unique().astype(int))
    departments = sorted(df['department'].dropna().unique().astype(str))

    return render_template(
        'descriptivo.html',
        total=total,
        women_share=women_share,
        vivienda_share=vivienda_share,
        leading_scene=leading_scene,
        growth_rate=growth_rate,
        alerts=alerts,
        charts=charts,
        years=years,
        departments=departments,
        selected_year=selected_year,
        selected_department=selected_dept,
    )
