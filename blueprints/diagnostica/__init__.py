"""Diagnóstica blueprint – Nivel 2: ¿Por qué pasó?"""
from flask import Blueprint, render_template, request
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly
import json
from utils import get_dataset, load_config

diagnostica_bp = Blueprint('diagnostica', __name__, template_folder='../../templates')


def _chart_json(fig):
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Inter, Segoe UI, sans-serif', size=11, color='#334155'),
        margin=dict(l=40, r=20, t=35, b=40),
    )
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


@diagnostica_bp.route('/')
def diagnostica_home():
    df = get_dataset()
    charts = {}

    # 1. Diagnóstico Cruzado: Escenario x Sexo (Barras agrupadas Rosa / Azul)
    top_scenes = df['scene'].value_counts().head(5).index.tolist()
    df_scene_sex = df[df['scene'].isin(top_scenes)]
    cross_scene_sex = pd.crosstab(df_scene_sex['scene'], df_scene_sex['sex']).reset_index()
    fig = px.bar(
        cross_scene_sex,
        x='scene',
        y=[c for c in ['Mujer', 'Hombre'] if c in cross_scene_sex.columns],
        barmode='group',
        color_discrete_map={'Mujer': '#db2777', 'Hombre': '#0284c7'},
        labels={'value': 'Cantidad de Registros', 'scene': 'Escenario', 'variable': 'Sexo'}
    )
    fig.update_layout(title='Interacción Escenario del Hecho × Sexo de la Víctima')
    charts['scene_sex'] = _chart_json(fig)

    # 2. Diagnóstico Territorial: Heatmap Departamento x Año (Escala Blues)
    top_depts = df['department'].value_counts().head(8).index.tolist()
    df_dept_year = df[df['department'].isin(top_depts)]
    pivot_dept = pd.crosstab(df_dept_year['department'], df_dept_year['year'])
    fig = px.imshow(
        pivot_dept,
        color_continuous_scale='Blues',
        aspect='auto',
        labels=dict(color='Registros', x='Año', y='Departamento')
    )
    fig.update_layout(title='Matriz Térmica Territorial: Concentración Histórica (2015–2024)')
    charts['dept_heatmap'] = _chart_json(fig)

    # 3. Diagnóstico de Causas: Evolución de Factores Desencadenantes (Líneas Multicolores)
    top_triggers = df['trigger'].value_counts().head(4).index.tolist()
    df_trig = df[df['trigger'].isin(top_triggers)]
    trig_year = df_trig.groupby(['year', 'trigger'], observed=False).size().reset_index(name='count')
    fig = px.line(
        trig_year,
        x='year',
        y='count',
        color='trigger',
        color_discrete_sequence=['#2563eb', '#dc2626', '#d97706', '#7c3aed'],
        markers=True,
        labels={'count': 'Registros', 'year': 'Año', 'trigger': 'Factor'}
    )
    fig.update_layout(title='Dinámica Temporal de Factores Desencadenantes')
    charts['trigger_trend'] = _chart_json(fig)

    # 4. Diagnóstico de Temporalidad Crítica: Días x Franja Horaria
    if 'weekday' in df.columns and 'time_range' in df.columns:
        weekday_order = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        time_cross = pd.crosstab(df['weekday'], df['time_range']).reindex(weekday_order)
        fig = px.imshow(
            time_cross,
            color_continuous_scale='Tealgrn',
            aspect='auto',
            labels=dict(color='Registros', x='Franja Horaria', y='Día de la semana')
        )
        fig.update_layout(title='Matriz de Ocurrencia: Día de la Semana × Franja Horaria')
        charts['time_heatmap'] = _chart_json(fig)

    total = len(df)
    vivienda_pct = round((df['scene'].str.lower().str.contains('vivienda', na=False)).sum() / total * 100, 1)
    women_pct = round((df['sex'].str.lower() == 'mujer').sum() / total * 100, 1)

    return render_template(
        'diagnostica.html',
        charts=charts,
        vivienda_pct=vivienda_pct,
        women_pct=women_pct,
        total=total,
    )
