import os
import re
import threading
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
# Caché generado en el build (scripts/build_cache.py). Evita parsear el CSV
# comprimido de 164 MB en la primera visita a Render.
CACHE_DATA = DATA_DIR / "dataset.pkl"

# Solo se leen las columnas que usa el tablero. Menos columnas = menos memoria
# y menos tiempo de arranque en planes gratuitos (Render: 512 MB, 0,1 CPU).
COLUMN_MAP = {
    "Año del hecho": "year",
    "Sexo de la victima": "sex",
    "Grupo de edad quinquenal": "age_group",
    "Mes del hecho": "month",
    "Dia del hecho": "weekday",
    "Rango de Hora del Hecho X 3 Horas": "time_range",
    "Departamento del hecho DANE": "department",
    "Escenario del Hecho": "scene",
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

# Diccionario de etiquetas: clave normalizada -> (etiqueta corta, etiqueta completa).
# Las gráficas usan la etiqueta corta y el texto completo aparece en el hover.
LABEL_DICTIONARY = {
    "sex": {
        "mujer": ("Mujer", "Mujer"),
        "hombre": ("Hombre", "Hombre"),
        "sin informacion": ("Sin información", "Sin información"),
    },
    "age_group": {
        "00 a 04": ("0–4", "(00 a 04)"),
        "05 a 09": ("5–9", "(05 a 09)"),
        "10 a 14": ("10–14", "(10 a 14)"),
        "15 a 17": ("15–17", "(15 a 17)"),
        "18 a 19": ("18–19", "(18 a 19)"),
        "20 a 24": ("20–24", "(20 a 24)"),
        "25 a 29": ("25–29", "(25 a 29)"),
        "30 a 34": ("30–34", "(30 a 34)"),
        "35 a 39": ("35–39", "(35 a 39)"),
        "40 a 44": ("40–44", "(40 a 44)"),
        "45 a 49": ("45–49", "(45 a 49)"),
        "50 a 54": ("50–54", "(50 a 54)"),
        "55 a 59": ("55–59", "(55 a 59)"),
        "60 a 64": ("60–64", "(60 a 64)"),
        "65 a 69": ("65–69", "(65 a 69)"),
        "70 a 74": ("70–74", "(70 a 74)"),
        "75 a 79": ("75–79", "(75 a 79)"),
        "80 y mas": ("80+", "(80 y más)"),
        "sin informacion": ("Sin información", "Sin información"),
    },
    "month": {
        "enero": ("Ene", "Enero"),
        "febrero": ("Feb", "Febrero"),
        "marzo": ("Mar", "Marzo"),
        "abril": ("Abr", "Abril"),
        "mayo": ("May", "Mayo"),
        "junio": ("Jun", "Junio"),
        "julio": ("Jul", "Julio"),
        "agosto": ("Ago", "Agosto"),
        "septiembre": ("Sep", "Septiembre"),
        "octubre": ("Oct", "Octubre"),
        "noviembre": ("Nov", "Noviembre"),
        "diciembre": ("Dic", "Diciembre"),
    },
    "weekday": {
        "lunes": ("Lun", "Lunes"),
        "martes": ("Mar", "Martes"),
        "miercoles": ("Mié", "Miércoles"),
        "jueves": ("Jue", "Jueves"),
        "viernes": ("Vie", "Viernes"),
        "sabado": ("Sáb", "Sábado"),
        "domingo": ("Dom", "Domingo"),
    },
    "time_range": {
        "00 00 a 02 59": ("00–03", "(00:00 a 02:59)"),
        "03 00 a 05 59": ("03–06", "(03:00 a 05:59)"),
        "06 00 a 08 59": ("06–09", "(06:00 a 08:59)"),
        "09 00 a 11 59": ("09–12", "(09:00 a 11:59)"),
        "12 00 a 14 59": ("12–15", "(12:00 a 14:59)"),
        "15 00 a 17 59": ("15–18", "(15:00 a 17:59)"),
        "18 00 a 20 59": ("18–21", "(18:00 a 20:59)"),
        "21 00 a 23 59": ("21–24", "(21:00 a 23:59)"),
        "sin informacion": ("Sin hora", "Sin información"),
    },
    "department": {
        "amazonas": ("Amazonas", "Amazonas"),
        "antioquia": ("Antioquia", "Antioquia"),
        "arauca": ("Arauca", "Arauca"),
        "atlantico": ("Atlántico", "Atlántico"),
        "bogota d c": ("Bogotá D.C.", "Bogotá, D.C."),
        "bolivar": ("Bolívar", "Bolívar"),
        "boyaca": ("Boyacá", "Boyacá"),
        "caldas": ("Caldas", "Caldas"),
        "caqueta": ("Caquetá", "Caquetá"),
        "casanare": ("Casanare", "Casanare"),
        "cauca": ("Cauca", "Cauca"),
        "cesar": ("Cesar", "Cesar"),
        "choco": ("Chocó", "Chocó"),
        "cordoba": ("Córdoba", "Córdoba"),
        "cundinamarca": ("Cundinamarca", "Cundinamarca"),
        "guainia": ("Guainía", "Guainía"),
        "guaviare": ("Guaviare", "Guaviare"),
        "huila": ("Huila", "Huila"),
        "la guajira": ("La Guajira", "La Guajira"),
        "magdalena": ("Magdalena", "Magdalena"),
        "meta": ("Meta", "Meta"),
        "narino": ("Nariño", "Nariño"),
        "norte de santander": ("Norte de Santander", "Norte de Santander"),
        "putumayo": ("Putumayo", "Putumayo"),
        "quindio": ("Quindío", "Quindío"),
        "risaralda": ("Risaralda", "Risaralda"),
        "santander": ("Santander", "Santander"),
        "sucre": ("Sucre", "Sucre"),
        "tolima": ("Tolima", "Tolima"),
        "valle del cauca": ("Valle del Cauca", "Valle del Cauca"),
        "vaupes": ("Vaupés", "Vaupés"),
        "vichada": ("Vichada", "Vichada"),
        "archipielago de san andres providencia y santa catalina": (
            "San Andrés y Providencia",
            "Archipiélago de San Andrés, Providencia y Santa Catalina",
        ),
        "sin informacion": ("Sin información", "Sin información"),
    },
    "scene": {
        "vivienda": ("Vivienda", "Vivienda"),
        "calle autopista avenida dentro de la ciudad": (
            "Calle / vía urbana",
            "Calle (autopista, avenida, dentro de la ciudad)",
        ),
        "via publica": ("Vía pública", "Vía pública"),
        "sin informacion": ("Sin información", "Sin información"),
        "lugares de hospedaje hoteles campamentos y otros tipos de hospedaje no permanente moteles etc": (
            "Hospedaje",
            "Lugares de hospedaje (hoteles, campamentos, moteles, etc.)",
        ),
        "establecimiento comercial": (
            "Comercio",
            "Establecimiento comercial (tienda, centro comercial, almacén, plaza de mercado)",
        ),
        "areas deportivas y o recreativas": ("Áreas deportivas", "Áreas deportivas y/o recreativas"),
        "lugares de esparcimiento con expendio de alcohol": (
            "Esparcimiento",
            "Lugares de esparcimiento con expendio de alcohol",
        ),
        "carretera fuera de la ciudad": ("Carretera", "Carretera (fuera de la ciudad)"),
        "centros educativos": ("Centros educativos", "Centros educativos"),
        "otros": ("Otros", "Otros"),
        "espacios terrestres al aire libre bosque potrero montana playa etc": (
            "Aire libre",
            "Espacios terrestres al aire libre (bosque, potrero, montaña, playa, etc.)",
        ),
        "centro de atencion medica hospital clinica consultorio etc": (
            "Centro médico",
            "Centro de atención médica (hospital, clínica, consultorio, etc.)",
        ),
        "zonas de actividades agropecuarias": ("Zonas agropecuarias", "Zonas de actividades agropecuarias"),
        "establecimientos de expendio de comidas restaurantes asaderos salsamentarias etc": (
            "Restaurantes",
            "Establecimientos de expendio de comidas (restaurantes, asaderos, etc.)",
        ),
        "oficinas y o edificios de oficinas": ("Oficinas", "Oficinas y/o edificios de oficinas"),
        "lugares de cuidado de personas hospicios orfelinatos hogares geriatricos etc": (
            "Cuidado de personas",
            "Lugares de cuidado de personas (hospicios, orfelinatos, hogares geriátricos, etc.)",
        ),
        "lugares de actividades culturales cines teatros museos bibliotecas etc": (
            "Lugares culturales",
            "Lugares de actividades culturales (cines, teatros, museos, bibliotecas, etc.)",
        ),
        "parqueaderos estacionamientos": ("Parqueaderos", "Parqueaderos, estacionamientos"),
        "centros de reclusion": ("Centros de reclusión", "Centros de reclusión"),
        "vehiculo particular": ("Vehículo particular", "Vehículo de servicio particular"),
        "establecimientos dedicados a la administracion publica cortes juzgados ministerios etc": (
            "Administración pública",
            "Establecimientos dedicados a la administración pública (cortes, juzgados, ministerios, etc.)",
        ),
        "establecimiento industrial fabrica planta y o obras en construccion": (
            "Industrial / obra",
            "Establecimiento industrial (fábrica, planta) y/o obras en construcción",
        ),
        "sitio de culto capilla iglesia templo etc": ("Sitio de culto", "Sitio de culto (capilla, iglesia, templo, etc.)"),
        "taller": ("Taller", "Taller"),
        "guarniciones militares y o de policia": ("Guarniciones", "Guarniciones militares y/o de policía"),
        "terminales de pasajeros": ("Terminales", "Terminales de pasajeros"),
        "terreno baldio": ("Terreno baldío", "Terreno baldío"),
        "espacios acuaticos al aire libre mar rio arroyo humedal lago etc": (
            "Espacios acuáticos",
            "Espacios acuáticos al aire libre (mar, río, arroyo, humedal, lago, etc.)",
        ),
        "estaciones de servicio bombas de gasolina": ("Estaciones de servicio", "Estaciones de servicio (bombas de gasolina)"),
        "vehiculo de transporte": ("Vehículo de transporte", "Vehículo de transporte"),
        "piscina y jacuzzi establecimientos turisticos recreativos deportivos": (
            "Piscina / turismo",
            "Piscina y jacuzzi (establecimientos turísticos, recreativos, deportivos)",
        ),
        "ambulancia transporte sanitario": ("Ambulancia", "Ambulancia - transporte sanitario"),
        "establecimientos financieros y relacionados bancos fiduciarias etc": (
            "Financiero",
            "Establecimientos financieros y relacionados (bancos, fiduciarias, etc.)",
        ),
        "transporte masivo": ("Transporte masivo", "Transporte masivo"),
        "piscina y jacuzzi vivienda": ("Piscina (vivienda)", "Piscina y jacuzzi (vivienda)"),
    },
    "trigger": {
        "intolerancia machismo": ("Intolerancia / machismo", "Intolerancia, machismo"),
        "consumo de alcohol y o sustancias psicoactivas": (
            "Alcohol / SPA",
            "Consumo de alcohol y/o sustancias psicoactivas; incluye alcoholismo y drogadicción",
        ),
        "sin informacion": ("Sin información", "Sin información"),
        "celos desconfianza infidelidad": ("Celos / infidelidad", "Celos, desconfianza, infidelidad"),
        "economicas": ("Económicas", "Económicas"),
        "otras": ("Otras", "Otras razones / otras"),
        "abandono": ("Abandono", "Abandono"),
        "enfermedad fisica o mental": ("Enfermedad", "Enfermedad física o mental"),
        "desamor": ("Desamor", "Desamor"),
    },
}

# Sinónimos que deben sumarse en una sola categoría antes de graficar.
CATEGORY_ALIASES = {
    "scene": {
        "establecimiento comercial tienda centro comercial almacen plaza de mercado": "establecimiento comercial",
        "establecimiento comercial tienda centro comercial almacen": "establecimiento comercial",
        "establecimiento comercial plaza de mercado galeria": "establecimiento comercial",
        "vehiculo servicio particular": "vehiculo particular",
        "vehiculo de servicio particular": "vehiculo particular",
    },
    "trigger": {
        "alcoholismo drogadiccion": "consumo de alcohol y o sustancias psicoactivas",
        "otras razones": "otras",
    },
}

LABEL_FIELD_NAMES = [
    ("department", "Departamento"),
    ("scene", "Escenario"),
    ("trigger", "Factor desencadenante"),
    ("age_group", "Grupo de edad"),
    ("time_range", "Rango horario"),
    ("month", "Mes"),
    ("weekday", "Día"),
    ("sex", "Sexo"),
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


_LOAD_LOCK = threading.Lock()


def read_dataset(path):
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
        frame[column] = (
            frame[column].str.strip().replace("", "Sin información").astype("category")
        )

    if frame["year"].notna().sum() == 0:
        raise ValueError(f"No se encontraron años válidos en el dataset: {path}")
    return prepare_frame(frame)


@lru_cache(maxsize=1)
def _load_data_cached():
    if CACHE_DATA.is_file() and not os.environ.get("DATA_PATH"):
        try:
            frame = pd.read_pickle(CACHE_DATA)
            if {"year", "department_label"}.issubset(frame.columns):
                return prepare_frame(frame)
        except Exception:
            # Si la caché no es compatible, se reconstruye desde el CSV.
            pass
    return read_dataset(_data_path())


def load_data():
    """Carga única y segura entre hilos (evita duplicar el DataFrame en memoria)."""
    with _LOAD_LOCK:
        return _load_data_cached()


@lru_cache(maxsize=8192)
def normalize_category(value):
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[^a-z0-9]+", " ", text.casefold())
    return " ".join(text.split())


def canonical_key(field, value):
    key = normalize_category(value)
    return CATEGORY_ALIASES.get(field, {}).get(key, key)


def _fallback_label(raw):
    text = " ".join(str(raw).split())
    short = re.sub(r"\s*\([^)]*\)", "", text).strip() or text
    if len(short) > 28:
        short = short[:27].rsplit(" ", 1)[0].rstrip(",;:") + "…"
    return short, text


def label_for(field, key, raw):
    entry = LABEL_DICTIONARY.get(field, {}).get(key)
    if entry:
        return entry
    return _fallback_label(raw)


@lru_cache(maxsize=8192)
def category_label(field, value):
    key = canonical_key(field, value)
    return label_for(field, key, value)


@lru_cache(maxsize=256)
def department_full(value):
    return category_label("department", value)[1]


def _canonical_series(frame, field):
    """Devuelve la clave canónica por fila sin recalcular en cada gráfico."""
    column = f"{field}_key"
    if column in frame.columns:
        return frame[column]
    values = frame[field].astype(object)
    mapping = {value: canonical_key(field, value) for value in pd.unique(values)}
    return values.map(mapping)


def _department_series(frame):
    if "department_label" in frame.columns:
        return frame["department_label"]
    values = frame["department"].astype(object)
    mapping = {value: department_full(value) for value in pd.unique(values)}
    return values.map(mapping)


def prepare_frame(frame):
    """Precalcula claves, etiquetas y diccionario una sola vez por dataset.

    El cálculo se hace sobre los valores únicos (no sobre las 236.840 filas),
    de modo que cada petición solo agrupa códigos ya preparados.
    """
    if frame.attrs.get("prepared"):
        return frame

    for field, _ in LABEL_FIELD_NAMES:
        if field not in frame.columns:
            continue
        values = frame[field].astype(object)
        mapping = {value: canonical_key(field, value) for value in pd.unique(values)}
        frame[f"{field}_key"] = values.map(mapping).astype("category")

    if "department" in frame.columns:
        departments = frame["department"].astype(object)
        mapping = {value: department_full(value) for value in pd.unique(departments)}
        frame["department_label"] = departments.map(mapping).astype("category")

    frame.attrs["prepared"] = True
    frame.attrs["dictionary"] = _dictionary_rows(frame)
    return frame


def category_counts(series, limit=10, field=None):
    field = field or series.name
    values = series
    if isinstance(values.dtype, pd.CategoricalDtype):
        unique = list(values.cat.categories)
    else:
        values = values.fillna("Sin información").astype(str)
        unique = list(pd.unique(values))

    mapping = {value: canonical_key(field, value) for value in unique}
    keys = values.map(mapping)

    counts = keys.value_counts()
    counts = counts[counts > 0].head(limit)
    if counts.empty:
        return pd.DataFrame(columns=["label", "full", "count"])

    raw_by_key = values.groupby(keys, observed=True).first()
    rows = []
    for key, count in counts.items():
        short, full = label_for(field, key, raw_by_key.get(key, key))
        rows.append({"label": short, "full": full, "count": int(count)})
    return pd.DataFrame(rows, columns=["label", "full", "count"])


def _pct(part, total):
    return (part / total * 100) if total else 0.0


def _pct_text(value, digits=1):
    return f"{float(value):.{digits}f}".replace(".", ",")


def _age_position(label):
    match = re.search(r"\((\d{2}) a (\d{2})\)", str(label))
    return int(match.group(1)) if match else 999



def _layout(data, height=340):
    return {
        "data": data,
        "layout": {
            "template": "plotly_white",
            "height": height,
            "margin": {"l": 10, "r": 16, "t": 30, "b": 20},
            "font": {"family": "Inter, Segoe UI, sans-serif", "color": "#3f4b60", "size": 11},
            "separators": ",.",
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
            "hoverlabel": {"bgcolor": "#14243a", "font": {"color": "#ffffff", "size": 11}},
        },
    }


def _bar_chart(counts, color="#4767e8", horizontal=False):
    full = counts["full"].astype(str).tolist()
    totals = counts["count"].astype(int).tolist()
    labels = counts["label"].astype(str).tolist()

    if horizontal:
        chart = _layout(
            [
                {
                    "type": "bar",
                    "x": totals,
                    "y": labels,
                    "customdata": full,
                    "orientation": "h",
                    "marker": {"color": color},
                    "text": [f"{value:,}".replace(",", ".") for value in totals],
                    "textposition": "auto",
                    "insidetextanchor": "end",
                    "textfont": {"size": 10},
                    "hovertemplate": "%{customdata}<br>%{x:,} registros<extra></extra>",
                }
            ]
        )
        chart["layout"]["yaxis"] = {
            "autorange": "reversed",
            "automargin": True,
            "tickfont": {"size": 11},
        }
        chart["layout"]["xaxis"] = {
            "title": None,
            "gridcolor": "#edf0f5",
            "automargin": True,
            "tickformat": ",d",
            "zeroline": False,
        }
        return chart

    chart = _layout(
        [
            {
                "type": "bar",
                "x": labels,
                "y": totals,
                "customdata": full,
                "marker": {"color": color},
                "hovertemplate": "%{customdata}<br>%{y:,} registros<extra></extra>",
            }
        ]
    )
    chart["layout"]["xaxis"] = {
        "title": None,
        "tickangle": 0,
        "automargin": True,
        "tickfont": {"size": 11},
    }
    chart["layout"]["yaxis"] = {
        "title": None,
        "gridcolor": "#edf0f5",
        "automargin": True,
        "tickformat": ",d",
        "zeroline": False,
    }
    return chart



def _annual_chart(frame, department=None):
    annual = frame.dropna(subset=["year"])
    if department:
        annual = annual[_department_series(annual) == department]
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
    chart["layout"]["xaxis"] = {
        "title": None,
        "dtick": 1,
        "gridcolor": "#edf0f5",
        "automargin": True,
    }
    chart["layout"]["yaxis"] = {
        "title": None,
        "gridcolor": "#edf0f5",
        "automargin": True,
        "tickformat": ",d",
        "zeroline": False,
    }
    return chart


def _sex_chart(frame):
    counts = category_counts(frame["sex"], limit=8)
    return _layout(
        [
            {
                "type": "pie",
                "labels": counts["label"].astype(str).tolist(),
                "values": counts["count"].astype(int).tolist(),
                "customdata": counts["full"].astype(str).tolist(),
                "hole": 0.66,
                "marker": {"colors": ["#4767e8", "#e98ca8", "#a9b5c8", "#d9deea"]},
                "textinfo": "percent",
                "textfont": {"size": 12},
                "hovertemplate": "%{customdata}<br>%{value:,} registros (%{percent})<extra></extra>",
            }
        ],
        height=310,
    )


def _age_sex_chart(frame):
    ages = category_counts(frame["age_group"], limit=10)
    ages["_position"] = ages["full"].map(_age_position)
    ages = ages.sort_values("_position").drop(columns="_position")
    age_keys = [canonical_key("age_group", full) for full in ages["full"]]
    age_full = ages["full"].astype(str).tolist()
    sex_counts = category_counts(frame["sex"], limit=8)
    sex_labels = sex_counts["label"].tolist()
    sex_keys = [canonical_key("sex", full) for full in sex_counts["full"]]

    table = pd.crosstab(
        _canonical_series(frame, "age_group"),
        _canonical_series(frame, "sex"),
    )
    palette = ["#4767e8", "#e98ca8", "#a9b5c8", "#d9deea"]
    traces = []

    for index, (sex, sex_key) in enumerate(zip(sex_labels, sex_keys)):
        values = [
            int(table.at[age, sex_key])
            if age in table.index and sex_key in table.columns
            else 0
            for age in age_keys
        ]
        traces.append(
            {
                "type": "bar",
                "name": sex,
                "x": ages["label"].astype(str).tolist(),
                "y": values,
                "customdata": age_full,
                "marker": {"color": palette[index % len(palette)]},
                "hovertemplate": "%{customdata}<br>%{fullData.name}: %{y:,}<extra></extra>",
            }
        )

    chart = _layout(traces)
    chart["layout"]["barmode"] = "stack"
    chart["layout"]["margin"]["t"] = 44
    chart["layout"]["legend"] = {
        "orientation": "h",
        "yanchor": "bottom",
        "y": 1.02,
        "x": 0,
        "font": {"size": 11},
    }
    chart["layout"]["xaxis"] = {
        "title": None,
        "tickangle": 0,
        "automargin": True,
        "tickfont": {"size": 11},
    }
    chart["layout"]["yaxis"] = {
        "title": None,
        "gridcolor": "#edf0f5",
        "automargin": True,
        "tickformat": ",d",
        "zeroline": False,
    }
    return chart


def _ordered_counts(frame, field, order):
    counts = category_counts(frame[field], limit=len(order) + 2, field=field)
    positions = {normalize_category(label): index for index, label in enumerate(order)}
    counts["_position"] = counts["full"].map(
        lambda label: positions.get(normalize_category(label), len(positions))
    )
    return counts.sort_values("_position").drop(columns="_position")


def _time_counts(frame, field="time_range"):
    counts = category_counts(frame[field], limit=20, field=field)

    def time_position(label):
        match = re.search(r"(\d{2}):(\d{2})", label)
        return int(match.group(1)) * 60 + int(match.group(2)) if match else 1440

    counts["_position"] = counts["full"].map(time_position)
    return counts.sort_values("_position").drop(columns="_position")



def _priority_table(frame, year):
    previous_year = year - 1
    labels = _department_series(frame)
    current = labels[frame["year"] == year].value_counts()
    previous = labels[frame["year"] == previous_year].value_counts()
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


def _dictionary_rows(frame):
    rows = []
    seen = set()
    for field, field_name in LABEL_FIELD_NAMES:
        values = frame[field].astype(object)
        for value in pd.unique(values):
            if pd.isna(value):
                continue
            key = canonical_key(field, value)
            short, full = label_for(field, key, value)
            if short == full:
                continue
            signature = (field_name, short, full)
            if signature in seen:
                continue
            seen.add(signature)
            rows.append({"field": field_name, "short": short, "full": full})
    return rows


def create_app():
    app = Flask(__name__)

    @app.template_filter("pct")
    def pct_filter(value, digits=1):
        return _pct_text(value, digits)

    @app.template_filter("signed_pct")
    def signed_pct_filter(value):
        return f"{float(value):+.1f}".replace(".", ",")

    @app.get("/")
    def index():
        frame = prepare_frame(load_data())
        years = sorted(int(year) for year in frame["year"].dropna().unique())
        departments = sorted(
            frame["department_label"].astype(str).unique(),
            key=str.casefold,
        )

        selected_year = request.args.get("year", "all")
        selected_department = request.args.get("department", "all")
        valid_years = {str(year) for year in years}
        if selected_year != "all" and selected_year not in valid_years:
            abort(400, description="El año seleccionado no está disponible.")
        if selected_department != "all" and selected_department not in departments:
            abort(400, description="El departamento seleccionado no está disponible.")

        selected = frame
        if selected_department != "all":
            selected = selected[selected["department_label"] == selected_department]
        if selected_year != "all":
            selected = selected[selected["year"] == int(selected_year)]

        year_frame = frame
        if selected_year != "all":
            year_frame = year_frame[year_frame["year"] == int(selected_year)]

        total = len(selected)

        scene_counts = category_counts(selected["scene"], limit=8, field="scene")
        sex_counts = category_counts(selected["sex"], limit=8, field="sex")
        trigger_counts = category_counts(selected["trigger"], limit=8, field="trigger")
        department_counts = category_counts(
            year_frame["department"], limit=10, field="department"
        )
        department_scope = category_counts(
            selected["department"], limit=10, field="department"
        )
        month_counts = _ordered_counts(selected, "month", MONTH_ORDER)
        weekday_counts = _ordered_counts(selected, "weekday", WEEKDAY_ORDER)
        hour_counts = _time_counts(selected)

        leading_scene = scene_counts.iloc[0]["label"] if not scene_counts.empty else "Sin datos"
        scene_share = _pct(int(scene_counts.iloc[0]["count"]), total) if not scene_counts.empty else 0.0
        women_count = int(sex_counts.loc[sex_counts["label"] == "Mujer", "count"].sum())
        women_share = _pct(women_count, total)
        top3_share = _pct(int(department_scope.head(3)["count"].sum()), total) if not department_scope.empty else 0.0
        top3_names = ", ".join(department_scope.head(3)["label"].tolist()) or "Los territorios disponibles"
        top_trigger = trigger_counts.iloc[0]["label"] if not trigger_counts.empty else "Sin datos"
        trigger_share = _pct(int(trigger_counts.iloc[0]["count"]), total) if not trigger_counts.empty else 0.0
        alcohol_count = int(trigger_counts.loc[trigger_counts["label"] == "Alcohol / SPA", "count"].sum())
        alcohol_share = _pct(alcohol_count, total)
        top_hour = (
            hour_counts.sort_values("count", ascending=False).iloc[0]
            if not hour_counts.empty
            else None
        )
        top_weekday = (
            weekday_counts.sort_values("count", ascending=False).iloc[0]
            if not weekday_counts.empty
            else None
        )
        top_month = (
            month_counts.sort_values("count", ascending=False).iloc[0]
            if not month_counts.empty
            else None
        )

        annual_frame = frame
        if selected_department != "all":
            annual_frame = annual_frame[
                annual_frame["department_label"] == selected_department
            ]
        annual_counts = annual_frame.dropna(subset=["year"]).groupby("year").size().sort_index()
        drop_2020 = None
        if 2019 in annual_counts.index and 2020 in annual_counts.index:
            previous_total = int(annual_counts.loc[2019])
            if previous_total:
                drop_2020 = (int(annual_counts.loc[2020]) - previous_total) / previous_total * 100

        logistic = next(
            (metric for metric in MODEL_METRICS if "log" in metric["name"].casefold()),
            MODEL_METRICS[0],
        )
        alcohol_count_text = f"{alcohol_count:,}".replace(",", ".")
        if selected_department == "all":
            territory_finding = {
                "tag": "TERRITORIO",
                "value": f"{_pct_text(top3_share)}%",
                "title": "se concentra en pocos territorios",
                "detail": f"{top3_names} reúnen la mayor parte de los registros.",
            }
        else:
            scope_label = f"en {selected_year}" if selected_year != "all" else "en el periodo"
            territory_finding = {
                "tag": "TERRITORIO",
                "value": f"{_pct_text(_pct(total, len(year_frame)))}%",
                "title": f"del total nacional {scope_label}",
                "detail": f"{selected_department} aporta {total:,}".replace(",", ".") + " registros en la selección.",
            }

        findings = [
            {
                "tag": "VIVIENDA",
                "value": f"{_pct_text(scene_share)}%",
                "title": "ocurre en la vivienda",
                "detail": f"“{leading_scene}” es el escenario más registrado en la selección actual.",
            },
            {
                "tag": "VÍCTIMAS",
                "value": f"{_pct_text(women_share)}%",
                "title": "de las víctimas son mujeres",
                "detail": "Participación femenina sobre los registros filtrados.",
            },
            territory_finding,
            {
                "tag": "FACTOR",
                "value": f"{_pct_text(trigger_share)}%",
                "title": f"se asocia a {top_trigger.lower()}",
                "detail": "Es el factor desencadenante más frecuente de la selección.",
            },
            {
                "tag": "CALIDAD",
                "value": f"{_pct_text(alcohol_share)}%",
                "title": "es la participación del alcohol/SPA",
                "detail": (
                    f"“Alcoholismo” y “Consumo de alcohol/SPA” suman {alcohol_count_text} "
                    "registros y juntos son el segundo factor."
                    if alcohol_count
                    else "No hay registros de alcohol/SPA en la selección actual."
                ),
            },
            {
                "tag": "MODELO",
                "value": f"{_pct_text(logistic['f1_macro'] * 100)}%",
                "title": "F1 macro del mejor modelo",
                "detail": "Clasifica el escenario de un registro observado; no estima riesgo individual.",
            },
        ]

        conclusion = (
            f"El patrón es consistente: {_pct_text(scene_share)}% de los registros ocurre en vivienda, "
            f"{_pct_text(women_share)}% corresponde a mujeres y {_pct_text(trigger_share)}% se asocia a "
            f"{top_trigger.lower()}."
        )
        if top_hour is not None:
            conclusion += (
                f" El rango {top_hour['label']} concentra "
                f"{_pct_text(_pct(int(top_hour['count']), total))}% de los registros."
            )
        if top_weekday is not None:
            conclusion += (
                f" El {top_weekday['full'].lower()} es el día con más registros "
                f"({_pct_text(_pct(int(top_weekday['count']), total))}%)"
            )
            if top_month is not None:
                conclusion += f" y {top_month['full'].lower()} el mes con más casos."
            else:
                conclusion += "."
        conclusion += (
            " Son señales descriptivas sobre registros reportados; no estiman riesgo individual ni prueban causalidad."
        )
        pandemic_note = None
        if drop_2020 is not None and drop_2020 < 0:
            pandemic_note = (
                f"Entre 2019 y 2020 los registros cayeron {_pct_text(abs(drop_2020))}%. La caída coincide con la pandemia, "
                "pero también con cambios en el acceso a servicios y en el reporte: no se puede atribuir solo a ella."
            )

        focus_year = int(selected_year) if selected_year != "all" else years[-1]
        priorities, previous_year = _priority_table(frame, focus_year)

        figures = {
            "annual": _annual_chart(frame, None if selected_department == "all" else selected_department),
            "sex": _sex_chart(selected),
            "scenes": _bar_chart(scene_counts, "#4767e8", True),
            "departments": _bar_chart(department_counts, "#58a69a", True),
            "triggers": _bar_chart(trigger_counts, "#e79a54", True),
            "age_sex": _age_sex_chart(selected),
            "months": _bar_chart(month_counts, "#58a69a"),
            "weekdays": _bar_chart(weekday_counts, "#765be7"),
            "hours": _bar_chart(hour_counts, "#e79a54"),
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
            findings=findings,
            conclusion=conclusion,
            pandemic_note=pandemic_note,
            dictionary=frame.attrs.get("dictionary") or _dictionary_rows(frame),
            figures=figures,
        )


    @app.get("/health")
    def health():
        try:
            path = _data_path()
        except FileNotFoundError as error:
            if CACHE_DATA.is_file():
                return jsonify(status="ok", dataset=CACHE_DATA.name)
            return jsonify(status="error", message=str(error)), 503
        return jsonify(status="ok", dataset=path.name)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
