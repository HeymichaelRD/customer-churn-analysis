# Notebooks

Cada persona tiene sus propios notebooks y nunca edita el de otro (regla 4 de "Cómo colaborar" en el README). Nombre: `NN_tema_nombre.ipynb`.

| Notebook | Autor | Equipo | Qué contiene |
|---|---|---|---|
| `02_eda_bryan.ipynb` | Bryan Abreu | Limpieza y EDA | EDA completo: verificación de la data, calidad de datos, churn por variable, segmentos de alto riesgo, impacto en ingresos, hallazgos y notas de criterio |

> Cuando agregues un notebook, súmalo a esta tabla en el mismo Pull Request.

## Cómo abrirlos

- **Solo para verlos:** haz clic en el archivo aquí en GitHub. Se muestran con los gráficos, sin instalar nada.
- **Para correrlos:** ábrelos en VS Code y, en **Select Kernel**, elige el Python de `.venv`. Antes corre `python src/cleaning/clean_data.py`, porque el notebook comprueba que su limpieza es igual a la del script.

## Hallazgos principales del EDA

Resumen; el detalle está en el notebook y en [`docs/plan-cleaning-eda.md`](../docs/plan-cleaning-eda.md).

1. Se fue el 26.5% de los clientes: US$139,131 al mes, el 30.5% del ingreso.
2. Contrato mes a mes: 42.7% de bajas; un año: 11.3%; dos años: 2.8%.
3. Primer año: 47.4% de bajas, contra 9.5% con más de 4 años.
4. La fibra óptica (41.9%) y el cheque electrónico (45.3%) se relacionan con más bajas.
5. Entre clientes con internet, sin seguridad en línea o soporte técnico se van casi el triple (~42% contra ~15%).
