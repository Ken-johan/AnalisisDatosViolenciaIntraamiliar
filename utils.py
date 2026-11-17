"""Utility functions and shared dataset helpers for the VIF Dashboard"""
from pathlib import Path
import os
import pandas as pd
import yaml
import json

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "Data"
CACHE_DATA = DATA_DIR / "dataset.pkl"
CSV_GZ_DATA = DATA_DIR / "Violencia_intrafamiliar._Colombia,_años_2015_a_2024._Cifras_definitivas_20261023.csv.gz"
CSV_DATA = DATA_DIR / "Violencia_intrafamiliar._Colombia,_años_2015_a_2024._Cifras_definitivas_20261023.csv"
CONFIG_FILE = ROOT / "config.yaml"

_CACHED_DF = None


def load_config():
    """Load configuration YAML for KPIs and alert thresholds."""
    if not CONFIG_FILE.exists():
        return {
            "kpis": {
                "total_incidents": {"threshold": 200000},
                "women_share": {"threshold": 70.0},
                "growth_rate": {"threshold": 10.0},
                "vivienda_share": {"threshold": 70.0},
            }
        }
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_dataset():
    """Safely load and return the preprocessed or raw dataframe with in-memory caching."""
    global _CACHED_DF
    if _CACHED_DF is not None:
        return _CACHED_DF

    if CACHE_DATA.is_file():
        _CACHED_DF = pd.read_pickle(CACHE_DATA)
        return _CACHED_DF

    if CSV_GZ_DATA.is_file():
        _CACHED_DF = pd.read_csv(CSV_GZ_DATA, low_memory=False)
        return _CACHED_DF

    if CSV_DATA.is_file():
        _CACHED_DF = pd.read_csv(CSV_DATA, low_memory=False)
        return _CACHED_DF

    raise FileNotFoundError(f"No se encontró archivo de datos en {DATA_DIR}")
