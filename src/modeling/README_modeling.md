# Entregables del equipo de Modelos

## Reproducir

Ejecutar `notebooks/03_modeling_teudys.ipynb` con el entorno `.venv` y el CSV limpio en `data/processed/telco_churn_clean.csv`. El notebook también admite el CSV junto al directorio actual. No modifica `data/raw/` ni `data/processed/`.

El notebook ejecuta la comparación supervisada, ajusta umbral con CV dentro del train, entrena K-Means (k=8), cruza segmentos con churn observado y guarda artefactos de modelos y salidas de dashboard.

## Archivos que produce

En el repositorio:

- `models/telco_churn_logistic.joblib`: pipeline final de regresión logística, reentrenado con todos los registros limpios; API recibe los 19 campos originales.
- `models/churn_model_info.json`: clase positiva, columnas y umbral seleccionado (0.33). La API debe usar este umbral al convertir la probabilidad en `churn: true/false`.
- `models/telco_customer_segments.joblib`: pipeline K-Means que recibe los campos originales y devuelve un ID de 0 a 7.
- `models/segments_info.json`: k, columnas, nombres, descripciones, tamaños y tasa de churn de cada segmento.
- `data/output/telco_churn_model_output.csv`: `customerID`, `churn_probability`, `predicted_churn`, `segment`, `segment_name`.
- `data/output/telco_churn_dashboard_with_models.csv`: datos limpios más las cuatro columnas de salida anteriores.

Los scores exportados para la población histórica son OOF: cada cliente fue puntuado por un modelo que no entrenó con su fila. El artefacto de clasificación guardado se reentrena con todo el dataset para atender clientes nuevos; sus métricas de test son las reportadas en el notebook, no se calculan sobre el modelo reentrenado.

## Integración con API

Configurar `MODEL_PATH=models/telco_churn_logistic.joblib`. El modelo de churn espera las mismas columnas de `FIELD_NAMES` del API. El umbral elegido por validación cruzada es 0.33; actualmente `src/api/model_service.py` tiene un umbral provisional de 0.50, que API debe alinear con `models/churn_model_info.json` antes de usar el modelo real.

El pipeline de K-Means recibe un DataFrame con los campos originales; transforma solo `tenure`, `MonthlyCharges` y `Contract`. Los IDs son arbitrarios y la correspondencia con `segments_info.json` debe regenerarse/revisarse al reentrenar.
