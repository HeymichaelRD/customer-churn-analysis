# Entregables del equipo de Modelos

## Reproducir

Ejecutar primero `python src/modeling/feature_selection_experiment.py`, `python src/modeling/compare_final_classifiers.py` y `python src/modeling/compare_clustering.py`; luego ejecutar `notebooks/03_modeling_teudys.ipynb` con el entorno `.venv` y el CSV limpio en `data/processed/telco_churn_clean.csv`. No modifica `data/raw/` ni `data/processed/`.

El notebook ejecuta la comparación supervisada, ajusta el umbral con validación, entrena K-Means (k=4), cruza segmentos con churn observado y guarda artefactos de modelos y salidas para dashboard.

## Reducción de variables supervisadas

La comparación reproducible de candidatas se ejecuta con:

```bash
python src/modeling/feature_selection_experiment.py
```

El script compara la base de 19 variables contra variantes que quitan `PhoneService` y `MultipleLines`, `gender` o `TotalCharges`; una variante combinada; la recodificación de categorías “No internet/phone service” a `No`; y dos variables agregadas que resumen los seis servicios de internet. Calcula probabilidades OOF con cinco folds sobre el 80% de entrenamiento, elige el umbral por F1 dentro de esas predicciones y ordena las candidatas por F1 y recall. La candidata se escoge solo con resultados OOF; después se informa su desempeño y el del modelo base en el 20% de test.

Resultados de esta corrida:

| Variante (Regresión Logística) | Variables | F1 OOF | Recall OOF | Precision OOF |
|---|---:|---:|---:|---:|
| Base completa | 19 | 0.637 | 0.740 | 0.560 |
| Sin `PhoneService` ni `MultipleLines` | 17 | 0.638 | 0.767 | 0.546 |
| Servicios agrupados en dos conteos | 15 | 0.636 | 0.779 | 0.537 |
| Compacta + servicios agrupados | 11 | 0.636 | 0.738 | 0.559 |

Entre candidatas a no más de 0.005 del mejor F1 OOF, se selecciona **Servicios agrupados en dos conteos** por tener mayor recall. En OOF, la base completa obtuvo F1 0.637 y recall 0.740; la variante agrupada obtuvo F1 0.636 y recall 0.779.

Con esa variante, la comparación de clasificadores en cinco divisiones estratificadas dio:

| Modelo | F1 medio (DE) | Recall medio (DE) | Precision media (DE) |
|---|---:|---:|---:|
| Random Forest | 0.629 (0.023) | 0.764 (0.019) | 0.535 (0.026) |
| Regresión logística | 0.628 (0.015) | 0.759 (0.029) | 0.538 (0.030) |

F1 y recall están casi empatados; siguiendo la regla acordada, se selecciona Random Forest por su recall medio ligeramente mayor. La diferencia queda dentro de la variación entre divisiones, por lo que no se presenta como una ventaja fuerte. En un holdout final que no participó en la selección (semilla 47), obtuvo precision 0.508, recall 0.749 y F1 0.605, con umbral 0.460 y matriz `[[764, 271], [94, 280]]`.

La decisión está implementada en `notebooks/03_modeling_teudys.ipynb` y `models/telco_churn_random_forest.joblib`. El pipeline recibe los 19 campos originales y genera internamente 15 variables: los seis servicios se resumen como `SecuritySupportCount` y `StreamingServicesCount`. La transformación está en `src/modeling/feature_engineering.py`; este módulo debe permanecer disponible en el entorno que cargue el artefacto con joblib. El CSV limpio sigue intacto.

Los resultados de comparación de variables quedan en `data/output/feature_selection_cv.csv` y `data/output/feature_selection_finalist_test.json`; la comparación repetida de modelos y el holdout final quedan en `data/output/final_classifier_repeated_holdout.csv` y `data/output/final_classifier_holdout.json`. El umbral registrado para esta corrida es 0.460. API debe usar ese valor al convertir probabilidad en `churn: true/false`.

## Segmentación no supervisada

`python src/modeling/compare_clustering.py` compara K-Means y Gaussian Mixture con `k=2...8`, usando `tenure`, `MonthlyCharges` y `Contract` en la misma matriz escalada/codificada. Guarda `data/output/clustering_model_comparison.csv`. Incluye inertia para dibujar el codo de K-Means; para comparar asignaciones usa silhouette (calculada con una muestra fija de 2,000), Davies–Bouldin, Calinski–Harabasz y tamaños de cluster. AIC/BIC se informan para Gaussian Mixture, pero solo comparan soluciones dentro de ese algoritmo.

En esta corrida se elige K-Means con `k=4`: el codo se aplana después de cuatro grupos; a `k=4` K-Means supera a Gaussian Mixture en silhouette (0.383 vs. 0.325), Davies–Bouldin (0.967 vs. 1.234) y Calinski–Harabasz (4,964.6 vs. 2,267.8). K-Means `k=8` tiene una silueta mayor (0.431), pero crea más grupos y su cluster más pequeño contiene 6.9% de los clientes. La selección de cuatro combina las métricas con una complejidad operativa menor.

Los nombres describen los perfiles medidos y no atribuyen causas:

| ID | Nombre | Perfil observado |
|---:|---|---|
| 0 | Relación estable | Mediana de antigüedad 54 meses; churn 4%; mayoría con contrato de dos años o sin internet. |
| 1 | Inicio por afianzar | Mediana 8 meses; cargo mensual mediano 25.55; 75% mes a mes; churn 25%. |
| 2 | Valor consolidado | Mediana 61 meses; cargo mensual mediano 94.25; 67% fibra; churn 14%. |
| 3 | Retención prioritaria | Mediana 13 meses; 93% mes a mes; 81% fibra; churn 50%. |

`Churn` no participa en los algoritmos de cluster; las tasas se calculan después de asignarlos. Los resultados actualizados por cliente incluyen `segment`, `segment_name` y la predicción supervisada.

## Lectura del riesgo y acciones sugeridas

El resumen cruza churn real, score OOF del Random Forest y cluster. El umbral aplicado es 0.460; los valores son descriptivos de estos 7,043 registros.

| Segmento | Churn observado | Riesgo OOF medio | Marcados por el modelo | Parte de todos los churners |
|---|---:|---:|---:|---:|
| Relación estable | 3.7% | 7.7% | 1.7% | 2.3% |
| Inicio por afianzar | 24.8% | 36.6% | 36.9% | 23.1% |
| Valor consolidado | 14.2% | 23.5% | 14.8% | 14.4% |
| Retención prioritaria | 49.9% | 63.5% | 76.4% | 60.2% |

Acciones para probar con el equipo comercial:

- **Retención prioritaria:** priorizar contacto temprano para revisar instalación, calidad del servicio y adecuación del plan. Probar opciones de permanencia si tienen valor para el cliente.
- **Inicio por afianzar:** reforzar onboarding y ayudar con dudas de factura, pagos y configuración; evaluar incentivos de bajo costo.
- **Valor consolidado:** hacer una revisión proactiva de calidad/valor y ofrecer beneficios a quienes además tengan un score individual alto.
- **Relación estable:** mantener atención regular y fidelidad de bajo costo; evitar descuentos generales.

El segmento no debe ser la única regla de contacto; también hay que priorizar por probabilidad individual. Son hipótesis para validar: el dataset no contiene campañas, costos o resultados de retención.

## Limitaciones

- El CSV es una fotografía histórica y no incluye fechas de eventos, historial de contactos ni resultados de campañas; no permite demostrar causas ni calcular retorno de inversión.
- Random Forest fue apenas superior en cinco divisiones repetidas (F1 medio 0.629 frente a 0.628 de logística); las diferencias están dentro de la variación observada. El holdout final obtuvo F1 0.605, por lo que el modelo seguirá cometiendo errores y requiere monitoreo.
- El umbral 0.460 se ajustó para F1/recall, no con costos reales de falsos positivos/falsos negativos o capacidad de agentes. En las salidas históricas 2,663 de 7,043 clientes quedaron marcados como churn probable.
- `gender` y `SeniorCitizen` siguen entre las variables supervisadas; no se ha evaluado si los errores difieren entre grupos. El score no debe ser la única base para negar ofertas o servicios.
- Los clusters usan solo antigüedad, cargo mensual y contrato. K-Means depende de escala, k y semilla; las métricas internas y nombres describen esta corrida, no garantizan grupos estables ni campañas eficaces.
- Agrupar los seis servicios reduce variables, pero elimina cuál complemento específico tiene cada cliente. `MonthlyCharges` es un cargo, no una medida de consumo.

## Archivos que produce

En el repositorio:

- `models/telco_churn_random_forest.joblib`: pipeline final de Random Forest, reentrenado con todos los registros limpios; API recibe los 19 campos originales.
- `models/churn_model_info.json`: clase positiva, columnas originales de entrada, variante, transformación y umbral seleccionado (0.460 en esta corrida). La API debe usar ese umbral al convertir la probabilidad en `churn: true/false`.
- `models/telco_customer_segments.joblib`: pipeline K-Means (`k=4`) que recibe los campos originales y devuelve un ID de 0 a 3.
- `models/segments_info.json`: k, columnas, nombres, descripciones, tamaños y tasa de churn de cada segmento.
- `data/output/telco_churn_model_output.csv`: `customerID`, `churn_probability`, `predicted_churn`, `segment`, `segment_name`.
- `data/output/telco_churn_dashboard_with_models.csv`: datos limpios más las cuatro columnas de salida anteriores.
- `data/output/telco_churn_segment_risk_summary.csv`: churn observado, riesgo OOF, tasa marcada por el modelo y concentración de churners por segmento.

Los scores exportados para la población histórica son OOF: cada cliente fue puntuado por un modelo que no entrenó con su fila. El artefacto de clasificación guardado se reentrena con todo el dataset para atender clientes nuevos; sus métricas de test son las reportadas en el notebook, no se calculan sobre el modelo reentrenado.

## Integración con API

Configurar `MODEL_PATH=models/telco_churn_random_forest.joblib`. El modelo de churn espera las mismas 19 columnas originales de `FIELD_NAMES` del API. El pipeline crea los dos conteos de servicios durante la predicción. El umbral elegido por validación cruzada repetida es 0.460; actualmente `src/api/model_service.py` tiene un umbral provisional de 0.50, que API debe alinear con `models/churn_model_info.json` antes de usar el modelo real. El entorno de API también debe poder importar `src.modeling.feature_engineering` al cargar el artefacto.

El pipeline de K-Means recibe un DataFrame con los campos originales; transforma solo `tenure`, `MonthlyCharges` y `Contract`. Los IDs son arbitrarios y la correspondencia con `segments_info.json` debe regenerarse/revisarse al reentrenar. Gaussian Mixture quedó como modelo de comparación y no se usa para asignar segmentos en el artefacto final.
