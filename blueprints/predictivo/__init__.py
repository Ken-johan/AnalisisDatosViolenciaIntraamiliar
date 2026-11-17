"""Predictivo blueprint – Nivel 3: ¿Qué podemos predecir/estimar?"""
from flask import Blueprint, render_template, request
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly
import json
from utils import get_dataset, load_config

predictivo_bp = Blueprint('predictivo', __name__, template_folder='../../templates')

# Métricas exactas reportadas en los notebooks de Johan Cortés & Martín Montaño
MODEL_METRICS = [
    {
        "name": "Modelo Base (Dummy)",
        "accuracy": 0.7567,
        "balanced_accuracy": 0.0385,
        "f1_macro": 0.0331,
        "precision_macro": 0.0291,
        "recall_macro": 0.0385,
    },
    {
        "name": "Regresión Logística",
        "accuracy": 0.1435,
        "balanced_accuracy": 0.3446,
        "f1_macro": 0.1042,
        "precision_macro": 0.1420,
        "recall_macro": 0.3446,
    },
    {
        "name": "Random Forest",
        "accuracy": 0.1122,
        "balanced_accuracy": 0.3428,
        "f1_macro": 0.0871,
        "precision_macro": 0.1180,
        "recall_macro": 0.3428,
    },
]

FEATURE_IMPORTANCES = [
    {"feature": "Año del hecho (Tendencia temporal)", "importance": 0.1042},
    {"feature": "Presunto agresor (Sin información / Desconocido)", "importance": 0.0302},
    {"feature": "Factor desencadenante: Intolerancia", "importance": 0.0236},
    {"feature": "Factor desencadenante: Intoxicación", "importance": 0.0213},
    {"feature": "Presunto agresor: Encargado de cuidado", "importance": 0.0206},
    {"feature": "Departamento: Bogotá, D.C.", "importance": 0.0203},
    {"feature": "Factor desencadenante: Consumo alcohol/SPA", "importance": 0.0189},
    {"feature": "Nivel de escolaridad de la víctima", "importance": 0.0177},
    {"feature": "Contexto: Lesiones no fatales", "importance": 0.0176},
    {"feature": "Factor desencadenante: Celos", "importance": 0.0150},
]


def _chart_json(fig):
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Inter, Segoe UI, sans-serif', size=11, color='#334155'),
        margin=dict(l=40, r=20, t=35, b=40),
    )
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


@predictivo_bp.route('/')
def predictivo_home():
    charts = {}

    # 1. Comparación Multimétrica de Modelos (Accuracy vs Balanced Accuracy vs F1-Macro)
    # Colores profesionales: Azul (#2563eb), Verde esmeralda (#059669), Púrpura (#7c3aed)
    fig = go.Figure()
    names = [m["name"] for m in MODEL_METRICS]
    accs = [m["accuracy"] * 100 for m in MODEL_METRICS]
    b_accs = [m["balanced_accuracy"] * 100 for m in MODEL_METRICS]
    f1s = [m["f1_macro"] * 100 for m in MODEL_METRICS]

    fig.add_trace(go.Bar(name='Exactitud (Accuracy)', x=names, y=accs, marker_color='#2563eb'))
    fig.add_trace(go.Bar(name='Exactitud Balanceada', x=names, y=b_accs, marker_color='#059669'))
    fig.add_trace(go.Bar(name='F1-Score Macro', x=names, y=f1s, marker_color='#7c3aed'))

    fig.update_layout(
        barmode='group',
        title='Comparación Multimétrica: Demostración de la Paradoja de Exactitud',
        yaxis=dict(title='Puntuación (%)', range=[0, 100]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    charts['models_comparison'] = _chart_json(fig)

    # 2. Importancia de Variables (Feature Importance - Random Forest)
    # Color cian oscuro / teal (#0891b2)
    df_imp = pd.DataFrame(FEATURE_IMPORTANCES).sort_values('importance', ascending=True)
    fig = px.bar(
        df_imp,
        x='importance',
        y='feature',
        orientation='h',
        color_discrete_sequence=['#0891b2'],
        labels={'importance': 'Puntaje de Importancia Relativa (Gini)', 'feature': 'Variable Predictora'}
    )
    fig.update_layout(title='Top 10 Variables con Mayor Poder Predictivo (Random Forest)')
    charts['feature_importance'] = _chart_json(fig)

    return render_template(
        'predictivo.html',
        model_metrics=MODEL_METRICS,
        charts=charts,
    )
