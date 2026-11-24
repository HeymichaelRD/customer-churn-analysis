# Limpieza de datos

Carpeta del equipo de Limpieza y EDA (rama `cleaning-eda`).

| Archivo | Qué hace |
|---|---|
| `clean_data.py` | Verifica la data original, la limpia y genera los archivos de `data/processed/` y `data/output/` |

## Cómo se ejecuta

Desde la raíz del repo, con el `.venv` activo:

```bash
python src/cleaning/clean_data.py
```

En la terminal se ve cada paso:

| Paso | Qué hace |
|---|---|
| 1 | Carga `data/raw/WA_Fn-UseC_-Telco-Customer-Churn.csv`, sin modificarlo |
| 2 | Verifica que es la data oficial: 7,043 filas, 21 columnas, valores permitidos y reglas de coherencia del contrato de la API. Si algo no cuadra, se detiene con un error |
| 3 | Convierte `TotalCharges` a número y llena con 0 los 11 vacíos (clientes con `tenure` 0) |
| 4 | Verifica el resultado: mismas filas y columnas, sin nulos y el resto de columnas sin cambios |
| 5 | Guarda `data/processed/telco_churn_clean.csv` |
| 6 | Guarda `data/output/telco_churn_dashboard.csv`, con `churn_flag` y `tenure_group`, y comprueba que el churn sea 26.5% |

## Más información

- Qué archivo de datos usar para cada cosa: [`data/README.md`](../../data/README.md)
- Criterios de cada decisión y pendientes del equipo: [`docs/plan-cleaning-eda.md`](../../docs/plan-cleaning-eda.md)
