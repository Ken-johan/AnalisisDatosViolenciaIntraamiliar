"""Genera Data/dataset.pkl para que el tablero arranque rápido en Render.

Uso:
    python scripts/build_cache.py

El CSV comprimido tarda bastante en parsearse en una CPU pequeña; el pickle
guarda el DataFrame ya limpio, con claves y etiquetas precalculadas. Si el
archivo no existe (por ejemplo en local), la aplicación usa el CSV igual.
"""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import app  # noqa: E402  (necesita la raíz en sys.path)


def main():
    frame = app.read_dataset(app._data_path())
    frame.to_pickle(app.CACHE_DATA, protocol=5)
    print(
        f"Caché creada en {app.CACHE_DATA} "
        f"({app.CACHE_DATA.stat().st_size / 1e6:.1f} MB, {len(frame):,} filas)"
    )


if __name__ == "__main__":
    main()
