# Datos del proyecto

Qué archivo usar según lo que necesites. Todos tienen los mismos 7,043 clientes.

| Carpeta | Archivo | Qué es | Quién lo usa |
|---|---|---|---|
| `raw/` | `WA_Fn-UseC_-Telco-Customer-Churn.csv` | Dataset original de Kaggle. **No se modifica nunca** | Solo el script de limpieza |
| `processed/` | `telco_churn_clean.csv` | Datos limpios: las mismas 21 columnas del original, con `TotalCharges` numérico | Modelos y API |
| `output/` | `telco_churn_dashboard.csv` | Datos limpios + 2 columnas extra para el dashboard | Power BI |

> Si vas a trabajar con los datos, **usa `processed/` u `output/`, no `raw/`**. La limpieza ya está hecha.

## Qué cambió en la limpieza

Solo `TotalCharges`. En el original venía como texto y tenía 11 valores en blanco. Ahora es numérico y esos 11 están en 0, porque son clientes con `tenure` 0, recién llegados, que todavía no han pagado nada. Las demás columnas quedan exactamente igual que en el original.

El detalle y el porqué de cada decisión están en [`docs/plan-cleaning-eda.md`](../docs/plan-cleaning-eda.md).

## Columnas derivadas en los archivos de salida

| Columna | Valores | Para qué |
|---|---|---|
| `churn_flag` | `1` si el cliente se fue, `0` si se quedó | Está en `output/telco_churn_dashboard.csv`. Sumarlo o promediarlo en Power BI para analizar churn; el promedio es la tasa de churn (26.5%). |
| `tenure_group` | `0-12 meses`, `13-24 meses`, `25-48 meses`, `49-72 meses` | Está en `output/telco_churn_dashboard.csv`; agrupa por antigüedad con los mismos rangos que el EDA y la web. |
| `churn_probability`, `predicted_churn`, `segment`, `segment_name` | Probabilidad y predicción del modelo; ID de segmento (0–3) y nombre descriptivo | Están en `output/telco_churn_model_output.csv` y en `output/telco_churn_dashboard_with_models.csv`. El equipo de Modelos los genera y los une por `customerID`; Power BI puede usar el archivo enriquecido. |

## Cómo se regeneran

Los dos archivos limpios los genera un solo script. Desde la raíz del repo, con el `.venv` activo:

```bash
python src/cleaning/clean_data.py
```

Solo el equipo de Limpieza y EDA sube versiones nuevas de `processed/` y `output/` (regla 7 de "Cómo colaborar" en el README).
