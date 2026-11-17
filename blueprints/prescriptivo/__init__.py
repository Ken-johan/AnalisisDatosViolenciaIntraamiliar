"""Prescriptivo blueprint – Nivel 4: ¿Qué decisiones/acciones tomar?"""
from flask import Blueprint, render_template, request
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly
import json
from utils import get_dataset, load_config

prescriptivo_bp = Blueprint('prescriptivo', __name__, template_folder='../../templates')


def _chart_json(fig):
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Inter, Segoe UI, sans-serif', size=11, color='#334155'),
        margin=dict(l=40, r=20, t=35, b=40),
    )
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


def _compute_priorities(df, focus_year, previous_year):
    cur = df[df['year'] == focus_year].groupby('department', observed=False).size().rename('focus')
    prev = df[df['year'] == previous_year].groupby('department', observed=False).size().rename('previous')
    merged = pd.concat([cur, prev], axis=1).fillna(0)
    merged['variation'] = ((merged['focus'] - merged['previous']) / merged['previous'].replace(0, 1) * 100).round(1)
    total_focus = merged['focus'].sum()
    merged['share'] = (merged['focus'] / total_focus * 100).round(1) if total_focus else 0
    merged = merged.reset_index().sort_values('focus', ascending=False)

    # Regla de clasificación de atención institucional
    def assign_level(row):
        if row['focus'] >= 5000 and row['variation'] > 5:
            return 'Crítica (Alerta Roja)'
        elif row['focus'] >= 5000:
            return 'Prioritaria'
        elif row['variation'] > 10:
            return 'Monitoreo Activo'
        return 'Preventiva'

    merged['attention'] = merged.apply(assign_level, axis=1)
    return merged.head(10).to_dict(orient='records')


@prescriptivo_bp.route('/')
def prescriptivo_home():
    df = get_dataset()
    years = sorted(df['year'].dropna().unique().astype(int))
    focus_year = int(request.args.get('year', years[-1] if years else 2024))
    previous_year = focus_year - 1 if (focus_year - 1) in years else focus_year

    priorities = _compute_priorities(df, focus_year, previous_year)
    charts = {}

    # 1. Simulación Prescriptiva: Escenario Base vs Escenario Simulado con Intervención
    # Comparar volumen actual vs reducción simulada del 18% en los 5 departamentos prioritarios
    top_5 = priorities[:5]
    depts = [p['department'] for p in top_5]
    base_counts = [p['focus'] for p in top_5]
    simulated_counts = [int(p['focus'] * 0.82) for p in top_5]  # -18% con intervención en fin de semana

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name='Línea Base (Registros Observados)',
        x=depts,
        y=base_counts,
        marker_color='#64748b'  # Slate gris neutro
    ))
    fig.add_trace(go.Bar(
        name='Simulación Prescriptiva (-18% Casos con Intervención Focalizada)',
        x=depts,
        y=simulated_counts,
        marker_color='#059669'  # Verde éxito
    ))
    fig.update_layout(
        barmode='group',
        title=f'Simulación de Impacto: Reducción Estimada mediante Rutas Tempranas ({focus_year})',
        yaxis=dict(title='Cantidad de Registros'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    charts['simulation'] = _chart_json(fig)

    # 2. Distribución de Territorios por Nivel de Atención
    attention_counts = pd.Series([p['attention'] for p in priorities]).value_counts().reset_index()
    attention_counts.columns = ['level', 'count']
    fig = px.pie(
        attention_counts,
        names='level',
        values='count',
        color='level',
        color_discrete_map={
            'Crítica (Alerta Roja)': '#dc2626',
            'Prioritaria': '#d97706',
            'Monitoreo Activo': '#2563eb',
            'Preventiva': '#059669',
        },
        hole=0.4
    )
    fig.update_layout(title='Distribución de Territorios por Nivel de Atención')
    charts['attention_pie'] = _chart_json(fig)

    return render_template(
        'prescriptivo.html',
        priorities=priorities,
        focus_year=focus_year,
        previous_year=previous_year,
        charts=charts,
    )
