import os
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

import pandas as pd
from flask import Flask, abort, jsonify, render_template, request


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "Data"
DEFAULT_DATA = (
    DATA_DIR
    / "Violencia_intrafamiliar._Colombia,_años_2015_a_2024._Cifras_definitivas_20261023.csv.gz"
)

COLUMN_MAP = {
    "ID": "record_id",
    "Año del hecho": "year",
    "Sexo de la victima": "sex",
    "Grupo de edad quinquenal": "age_group",
    "Ciclo Vital": "life_stage",
    "Mes del hecho": "month",
    "Dia del hecho": "weekday",
    "Rango de Hora del Hecho X 3 Horas": "time_range",
    "Departamento del hecho DANE": "department",
    "Municipio del hecho DANE": "municipality",
    "Escenario del Hecho": "scene",
    "Circunstancia del Hecho Detallada": "circumstance",
    "Contexto del Hecho": "context",
    "Presunto Agresor Detallado": "alleged_aggressor",
    "Factor Desencadenante de la Agresión": "trigger",
}

MODEL_METRICS = [
    {
        "name": "Modelo base",
        "accuracy": 0.7567,
        "balanced_accuracy": 0.0385,
        "f1_macro": 0.0331,
    },
    {
        "name": "Regresión logística",
        "accuracy": 0.1435,
        "balanced_accuracy": 0.3446,
        "f1_macro": 0.1042,
    },
    {
        "name": "Random Forest",
        "accuracy": 0.1122,
        "balanced_accuracy": 0.3428,
        "f1_macro": 0.0871,
    },
]

MONTH_ORDER = [
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
]

WEEKDAY_ORDER = [
    "Lunes",
    "Martes",
    "Miércoles",
    "Jueves",
    "Viernes",
    "Sábado",
    "Domingo",
]


def _data_path():
    configured_path = os.environ.get("DATA_PATH")
    if configured_path:
        path = Path(configured_path).expanduser()
        if not path.is_absolute():
            path = ROOT / path
        if not path.is_file():
            raise FileNotFoundError(f"El archivo configurado en DATA_PATH no existe: {path}")
        return path

    if DEFAULT_DATA.is_file():
        return DEFAULT_DATA

    candidates = sorted(DATA_DIR.glob("*.csv"))
    if candidates:
        return candidates[0]
    raise FileNotFoundError(
        "No se encontró el dataset. Añade el archivo comprimido a Data/ "
        "o configura DATA_PATH con una ruta accesible."
    )


@lru_cache(maxsize=1)
def load_data():
    path = _data_path()
    frame = pd.read_csv(
        path,
        usecols=list(COLUMN_MAP),
        dtype="string",
        encoding="utf-8-sig",
        compression="infer",
        keep_default_na=False,
    ).rename(columns=COLUMN_MAP)

    frame["year"] = pd.to_numeric(frame["year"], errors="coerce").astype("Int64")
    for column in frame.columns.difference(["year"]):
        frame[column] = frame[column].str.strip().replace("", "Sin información")

    if frame["year"].notna().sum() == 0:
        raise ValueError(f"No se encontraron años válidos en el dataset: {path}")
    return frame


@lru_cache(maxsize=8192)
def normalize_category(value):
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(text.casefold().split())


def category_counts(series, limit=10):
    labels = series.fillna("Sin información").astype(str).str.strip()
    labels = labels.replace("", "Sin información")
    keys = labels.map(normalize_category)
    display_names = labels.groupby(keys, sort=False).first()
    counts = keys.value_counts().head(limit)
    return pd.DataFrame(
        {
            "label": display_names.reindex(counts.index).to_numpy(),
            "count": counts.to_numpy(),
        }
    )


def _layout(data, height=340):
    return {
        "data": data,
        "layout": {
            "template": "plotly_white",
            "height": height,
            "margin": {"l": 12, "r": 12, "t": 30, "b": 20},
            "font": {"family": "Inter, Segoe UI, sans-serif", "color": "#3f4b60"},
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
            "hoverlabel": {"bgcolor": "#14243a", "font": {"color": "#ffffff"}},
        },
    }


def _bar_chart(counts, color="#4767e8", horizontal=False):
    if horizontal:
        chart = _layout(
            [
                {
                    "type": "bar",
                    "x": counts["count"].astype(int).tolist(),
                    "y": counts["label"].astype(str).tolist(),
                    "orientation": "h",
                    "marker": {"color": color},
                    "hovertemplate": "%{y}<br>%{x:,} registros<extra></extra>",
                }
            ]
        )
        chart["layout"]["yaxis"] = {"autorange": "reversed"}
        chart["layout"]["xaxis"] = {"title": None, "gridcolor": "#edf0f5"}
        return chart

    chart = _layout(
        [
            {
                "type": "bar",
                "x": counts["label"].astype(str).tolist(),
                "y": counts["count"].astype(int).tolist(),
                "marker": {"color": color},
                "hovertemplate": "%{x}<br>%{y:,} registros<extra></extra>",
            }
        ]
    )
    chart["layout"]["xaxis"] = {"title": None, "tickangle": -25}
    chart["layout"]["yaxis"] = {"title": None, "gridcolor": "#edf0f5"}
    return chart


def _annual_chart(frame, department=None):
    annual = frame.dropna(subset=["year"])
    if department:
        annual = annual[annual["department"] == department]
    counts = annual.groupby("year").size().sort_index()
    chart = _layout(
        [
            {
                "type": "scatter",
                "x": counts.index.astype(int).tolist(),
                "y": counts.astype(int).tolist(),
                "mode": "lines+markers",
                "line": {"color": "#4767e8", "width": 3},
                "marker": {"size": 8, "color": "#4767e8"},
                "fill": "tozeroy",
                "fillcolor": "rgba(71,103,232,0.10)",
                "hovertemplate": "%{x}: %{y:,} registros<extra></extra>",
            }
        ]
    )
    chart["layout"]["xaxis"] = {"title": None, "dtick": 1, "gridcolor": "#edf0f5"}
    chart["layout"]["yaxis"] = {"title": None, "gridcolor": "#edf0f5"}
    return chart


def _sex_chart(frame):
    counts = category_counts(frame["sex"], limit=8)
    return _layout(
        [
            {
                "type": "pie",
                "labels": counts["label"].astype(str).tolist(),
                "values": counts["count"].astype(int).tolist(),
                "hole": 0.66,
                "marker": {"colors": ["#4767e8", "#e98ca8", "#a9b5c8", "#d9deea"]},
                "textinfo": "percent",
                "hovertemplate": "%{label}<br>%{value:,} registros<extra></extra>",
            }
        ],
        height=310,
    )


def _age_sex_chart(frame):
    ages = category_counts(frame["age_group"], limit=10)
    age_keys = ages["label"].map(normalize_category).tolist()
    all_age_keys = frame["age_group"].map(normalize_category)
    all_sex_keys = frame["sex"].map(normalize_category)
    sex_labels = category_counts(frame["sex"], limit=8)["label"]
    traces = []

    for sex in sex_labels:
        sex_key = normalize_category(sex)
        values = [
            int(((all_age_keys == age) & (all_sex_keys == sex_key)).sum())
            for age in age_keys
        ]
        traces.append(
            {
                "type": "bar",
                "name": sex,
                "x": ages["label"].astype(str).tolist(),
                "y": values,
            }
        )

    chart = _layout(traces)
    chart["layout"]["barmode"] = "group"
    chart["layout"]["xaxis"] = {"title": None, "tickangle": -25}
    chart["layout"]["yaxis"] = {"title": None, "gridcolor": "#edf0f5"}
    return chart


def _ordered_counts(series, order):
    counts = category_counts(series, limit=len(order) + 2)
    positions = {normalize_category(label): index for index, label in enumerate(order)}
    counts["_position"] = counts["label"].map(
        lambda label: positions.get(normalize_category(label), len(positions))
    )
    return counts.sort_values("_position").drop(columns="_position")


def _time_counts(series):
    counts = category_counts(series, limit=20)

    def time_position(label):
        match = re.search(r"(\d{2}):(\d{2})", label)
        return int(match.group(1)) * 60 + int(match.group(2)) if match else 1440

    counts["_position"] = counts["label"].map(time_position)
    return counts.sort_values("_position").drop(columns="_position")


def _priority_table(frame, year):
    previous_year = year - 1
    current = frame[frame["year"] == year]["department"].value_counts()
    previous = frame[frame["year"] == previous_year]["department"].value_counts()
    total = int(current.sum())
    rows = []

    for department, count in current.head(10).items():
        previous_count = int(previous.get(department, 0))
        variation = (
            ((int(count) - previous_count) / previous_count * 100)
            if previous_count
            else None
        )
        share = int(count) / total * 100 if total else 0
        if share >= 5:
            attention = "Alto volumen"
        elif variation is not None and variation > 10:
            attention = "Crecimiento > 10%"
        else:
            attention = "Seguimiento"
        rows.append(
            {
                "department": department,
                "count": int(count),
                "previous_count": previous_count,
                "variation": variation,
                "share": share,
                "attention": attention,
            }
        )
    return rows, previous_year


def create_app():
    app = Flask(__name__)

    @app.get("/")
    def index():
        frame = load_data()
        years = sorted(int(year) for year in frame["year"].dropna().unique())
        departments = sorted(frame["department"].unique(), key=str.casefold)

        selected_year = request.args.get("year", "all")
        selected_department = request.args.get("department", "all")
        valid_years = {str(year) for year in years}
        if selected_year != "all" and selected_year not in valid_years:
            abort(400, description="El año seleccionado no está disponible.")
        if selected_department != "all" and selected_department not in departments:
            abort(400, description="El departamento seleccionado no está disponible.")

        selected = frame
        if selected_year != "all":
            selected = selected[selected["year"] == int(selected_year)]
        if selected_department != "all":
            selected = selected[selected["department"] == selected_department]

        year_frame = frame
        if selected_year != "all":
            year_frame = year_frame[year_frame["year"] == int(selected_year)]

        total = len(selected)
        sex_keys = selected["sex"].map(normalize_category)
        women_share = float((sex_keys == "mujer").mean() * 100) if total else 0
        top_scene = category_counts(selected["scene"], limit=1)
        leading_scene = top_scene.iloc[0]["label"] if not top_scene.empty else "Sin datos"
        focus_year = int(selected_year) if selected_year != "all" else years[-1]
        priorities, previous_year = _priority_table(frame, focus_year)

        figures = {
            "annual": _annual_chart(frame, None if selected_department == "all" else selected_department),
            "sex": _sex_chart(selected),
            "scenes": _bar_chart(category_counts(selected["scene"], 8), "#4767e8", True),
            "departments": _bar_chart(category_counts(year_frame["department"], 10), "#58a69a", True),
            "triggers": _bar_chart(category_counts(selected["trigger"], 8), "#e79a54", True),
            "age_sex": _age_sex_chart(selected),
            "months": _bar_chart(_ordered_counts(selected["month"], MONTH_ORDER), "#58a69a"),
            "weekdays": _bar_chart(_ordered_counts(selected["weekday"], WEEKDAY_ORDER), "#765be7"),
            "hours": _bar_chart(_time_counts(selected["time_range"]), "#e79a54"),
        }
        return render_template(
            "index.html",
            years=years,
            departments=departments,
            selected_year=selected_year,
            selected_department=selected_department,
            total=total,
            women_share=women_share,
            leading_scene=leading_scene,
            year_range=f"{years[0]}–{years[-1]}",
            focus_year=focus_year,
            previous_year=previous_year,
            priorities=priorities,
            model_metrics=MODEL_METRICS,
            figures=figures,
        )

    @app.get("/health")
    def health():
        try:
            path = _data_path()
        except FileNotFoundError as error:
            return jsonify(status="error", message=str(error)), 503
        return jsonify(status="ok", dataset=path.name)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
