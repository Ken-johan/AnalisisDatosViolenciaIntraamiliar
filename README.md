# Análisis de violencia intrafamiliar en Colombia

Panel web en Flask para explorar los análisis descriptivo, predictivo y prescriptivo de registros de lesiones no fatales de violencia intrafamiliar en Colombia (2015–2024).

## Contenido

- `Data/AnalisisDescriptivo_*.ipynb`: calidad de datos, evolución, características de las víctimas, escenarios y distribución territorial.
- `Data/AnalisisPredictivo_*.ipynb`: clasificación del escenario registrado con regresión logística y Random Forest.
- `Data/AnalisisPrescriptivo_*.ipynb`: comparación territorial interanual, patrones y propuestas de seguimiento.
- `Data/*.csv.gz`: copia comprimida del dataset utilizada por la aplicación. El CSV original de 164 MB se excluye de Git; su copia comprimida ocupa cerca de 7 MB.
- `app.py`, `templates/` y `static/`: aplicación Flask y dashboard interactivo.

## Ejecutar localmente

En PowerShell, desde la raíz del proyecto:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Abre <http://127.0.0.1:5000>. Si el dataset está en otra ubicación, define `DATA_PATH` con la ruta al CSV o CSV comprimido antes de iniciar la aplicación.

## Publicar en Render

1. Sube el repositorio a GitHub e incluye `Data/*.csv.gz`. El CSV sin comprimir está ignorado para evitar el límite de tamaño de archivos de GitHub.
2. En Render, crea un **Blueprint** y selecciona el repositorio. Render leerá `render.yaml`, instalará `requirements.txt` e iniciará Gunicorn.
3. La ruta `/health` verifica que la aplicación encuentre el dataset.

## Lectura y límites de los resultados

- El dataset contiene 236.840 registros y 36 variables; la aplicación lee solo las columnas necesarias y agrupa etiquetas que difieren únicamente en mayúsculas o tildes.
- Las etiquetas pasan por un diccionario (`LABEL_DICTIONARY`): se ignoran mayúsculas, tildes, puntuación y espacios, se unifican sinónimos y se muestran nombres cortos con el texto completo en el hover. Por eso “Calle (Autopista,...)” y “Calle (autopista,...)” son una sola categoría, y “Alcoholismo/drogadicción” se suma a “Consumo de alcohol y/o SPA” (15,8% del total).
- La sección “Hallazgos y lectura de conjunto” calcula indicadores con los filtros activos y ofrece un diccionario de etiquetas desplegable para interpretar cada nombre corto.
- En las salidas de los notebooks, las mujeres representan el 59,4% de los registros; “Vivienda” es el escenario más frecuente (75,67%), Bogotá, D.C. concentra el 25,94% y “Intolerancia, machismo” aparece como factor desencadenante en el 70,84%. Son proporciones de registros, no medidas de riesgo.
- Los conteos son registros reportados, no tasas de incidencia ni estimaciones de prevalencia. Pueden existir subregistro y diferencias de cobertura entre periodos y territorios.
- Las métricas predictivas del dashboard se muestran tal como aparecen en el notebook: la categoría mayoritaria domina la exactitud del modelo base (75,67%), mientras que su F1 macro es 3,31%. La regresión logística alcanza F1 macro de 10,42%. El modelo clasifica el escenario de un registro observado; no estima riesgo futuro o individual y su rendimiento por clase es limitado.
- La priorización territorial compara conteos entre años y no ajusta por población, acceso a servicios o nivel de denuncia. Las variaciones no prueban causalidad.
