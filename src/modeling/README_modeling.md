# Entregables del equipo de Modelos

## Reproducir

Ejecutar primero `python src/modeling/compare_feature_reduction.py`, `python src/modeling/compare_final_classifiers.py` y `python src/modeling/compare_clustering.py`; luego ejecutar `notebooks/03_modeling_teudys.ipynb` con el entorno `.venv` y el CSV limpio en `data/processed/telco_churn_clean.csv`. `feature_selection_experiment.py` conserva el ensayo exploratorio inicial con el esquema de 19 variables. Ninguno modifica `data/raw/` ni `data/processed/`.

El notebook ejecuta la comparación supervisada, ajusta el umbral con validación, entrena K-Means (k=4), cruza segmentos con churn observado y guarda artefactos de modelos y salidas para dashboard.

## Reducción de variables supervisadas

La reducción final se compara de forma reproducible con:

```bash
python src/modeling/compare_feature_reduction.py
```

El punto de partida tiene 15 variables después de resumir seis servicios de internet en `SecuritySupportCount` y `StreamingServicesCount`. El script prueba eliminaciones individuales y combinadas con validación cruzada estratificada de cinco folds sobre el train. Elige el mayor recall entre las candidatas a no más de 0.005 del F1 máximo; prueba además si puede retirar otra variable sin salir de ese margen y subir el recall. El holdout final, semilla 47, queda reservado.

La candidata seleccionada tiene **12 variables derivadas**. Se quitaron `PhoneService`, `MultipleLines` y `TotalCharges`; el CSV limpio no se modifica.

| Variante Random Forest | Variables derivadas | F1 OOF | Recall OOF |
|---|---:|---:|---:|
| Mejor F1 de la búsqueda: sin `PhoneService` | 14 | 0.628 | 0.721 |
| Base actual | 15 | 0.625 | 0.738 |
| Seleccionada: sin teléfono ni `TotalCharges` | 12 | 0.625 | 0.761 |

La opción de 12 variables queda dentro del margen de 0.005 del mejor F1 y tiene mayor recall que la base, por lo que se prefiere aunque el F1 no sea el máximo de la búsqueda. El barrido no encontró una eliminación adicional que mantuviera ese margen y mejorara el recall.

La comparación repetida entre la base de 15 y la reducción elegida fue:

| Variante Random Forest | F1 medio (DE) | Recall medio (DE) | Precision media (DE) |
|---|---:|---:|---:|
| Base actual (15) | 0.629 (0.023) | 0.764 (0.019) | 0.535 (0.026) |
| Reducción elegida (12) | 0.626 (0.019) | 0.777 (0.037) | 0.524 (0.013) |

En el holdout reservado con umbral 0.460, la base obtuvo F1 0.605 y recall 0.749; la opción reducida obtuvo F1 0.606 y recall 0.759. La diferencia de F1 es mínima y el recall favorece la reducción.

Con las 12 variables, volvimos a comparar ambos clasificadores en cinco divisiones:

| Modelo | F1 medio (DE) | Recall medio (DE) | Precision media (DE) |
|---|---:|---:|---:|
| Regresión logística | 0.633 (0.017) | 0.739 (0.004) | 0.553 (0.027) |
| Random Forest | 0.626 (0.019) | 0.777 (0.037) | 0.524 (0.013) |

El F1 medio de Regresión Logística supera al de Random Forest por 0.007, más que la tolerancia de empate de 0.005. Por la regla acordada, seleccionamos **Regresión Logística**. En el holdout final reservado (semilla 47), con umbral 0.325, obtuvo precision 0.517, recall 0.735 y F1 0.607; su matriz de confusión es `[[778, 257], [99, 275]]`.

El entrenamiento parte de 16 columnas del CSV y agrupa seis indicadores de servicio en dos conteos, con lo que el clasificador usa 12 variables. El artefacto final de API recibe directamente esas **12 variables listas para el modelo**; el preprocesamiento estadístico (imputación, escalado y one-hot encoding) sigue dentro del artefacto. No recibe `customerID`, `Churn`, `PhoneService`, `MultipleLines`, `TotalCharges` ni los seis indicadores individuales de servicio.

Los resultados de la búsqueda quedan en `data/output/feature_reduction_screening.csv`, `feature_reduction_path.csv`, `feature_reduction_repeated_holdout.csv` y `feature_reduction_holdout.json`. La comparación de clasificadores actualizada queda en `final_classifier_repeated_holdout.csv` y `final_classifier_holdout.json`.

## Segmentación no supervisada

`python src/modeling/compare_clustering.py` realiza dos comparaciones reproducibles con semilla 42 y `k=4` para evaluar las variables. Parte de `tenure`, `MonthlyCharges` y `Contract`; prueba 27 conjuntos: añadir cada predictor disponible de uno en uno, retirar cada variable base por turno, usar todas las predictoras y agregar `SecuritySupportCount`/`StreamingServicesCount` por separado y juntos, con y sin `InternetService`. Escala las variables numéricas y aplica one-hot encoding a las categóricas. Guarda los resultados en `data/output/clustering_feature_comparison.csv`. Las métricas de churn se calculan después de asignar los grupos y no intervienen en K-Means.

La búsqueda respaldó agregar `InternetService` a la base. El candidato elegido mantiene antigüedad, cargo mensual y contrato, y añade tipo de internet. La comparación muestra el intercambio entre métricas:

| Candidato con K-Means, k=4 | Silueta | Davies–Bouldin | Calinski–Harabasz | Cluster menor | Mayor churn de cluster | DE de churn entre clusters |
|---|---:|---:|---:|---:|---:|---:|
| Base: `tenure`, `MonthlyCharges`, `Contract` | 0.383 | 0.967 | 4,964.6 | 16.3% | 49.9% | 0.198 |
| Elegido: base + `InternetService` | 0.396 | 1.026 | 4,087.5 | 21.7% | 56.7% | 0.223 |
| Base + `TotalCharges` | 0.389 | 0.930 | 5,867.1 | 16.9% | 48.6% | 0.189 |
| Base sin `MonthlyCharges` | 0.586 | 0.657 | 10,463.4 | 15.5% | 43.4% | 0.183 |
| Base + ambos conteos de servicios | 0.306 | 1.207 | 3,675.1 | 16.7% | 48.9% | 0.216 |
| Selección actual + `SecuritySupportCount` | 0.363 | 1.087 | 3,855.7 | 21.3% | 56.6% | 0.224 |
| Selección actual + `StreamingServicesCount` | 0.312 | 1.206 | 3,418.6 | 15.5% | 51.7% | 0.208 |
| Selección actual + ambos conteos | 0.290 | 1.273 | 3,272.3 | 20.4% | 54.0% | 0.223 |

La desviación estándar de churn en la tabla se calcula entre los cuatro grupos después de asignarlos; no es una métrica usada para entrenar. No hay una opción que gane en todas las medidas. Quitar `MonthlyCharges` produce las mejores métricas internas, pero borra la dimensión de cargo mensual, útil para perfilar el valor de la cuenta, y separa menos las tasas de churn. Añadir `TotalCharges` mejora Davies–Bouldin y Calinski–Harabasz, pero incorpora una cantidad acumulada estrechamente ligada a antigüedad y cargo mensual. Los conteos de servicios no mejoran la solución elegida: agregarlos a la selección actual baja la silueta a 0.290; agregar solo `SecuritySupportCount` da 0.363, y solo `StreamingServicesCount`, 0.312. Esos conteos se diseñaron para resumir servicios para la clasificación supervisada, pero aquí no ayudan a separar mejor los clusters. `InternetService` aporta una dimensión de producto distinta y accionable; da grupos más equilibrados, la mayor silueta entre los candidatos que mantienen las tres variables base y mayor dispersión de churn posterior. Por estos motivos de interpretación y uso comercial seleccionamos **cuatro variables: `tenure`, `MonthlyCharges`, `Contract` e `InternetService`**. La salida completa permite revisar cada candidata.

Después se compara K-Means y Gaussian Mixture con esas cuatro variables para `k=2...8`. Los resultados quedan en `data/output/clustering_model_comparison.csv`. El script reporta inertia, silhouette (muestra fija de 2,000), Davies–Bouldin, Calinski–Harabasz y tamaños de clusters. AIC/BIC se reportan para Gaussian Mixture y solo comparan soluciones dentro de ese algoritmo.

En la corrida actual, K-Means `k=4` obtiene silueta 0.396, Davies–Bouldin 1.026 y Calinski–Harabasz 4,087.5; Gaussian Mixture `k=4` obtiene 0.369, 1.058 y 3,446.9. K-Means `k=8` mejora varias métricas internas (silueta 0.461; Davies–Bouldin 0.897; Calinski–Harabasz 4,826.1), pero su grupo más pequeño representa 8.3%, frente a 21.7% con `k=4`. La inercia se aplana gradualmente después de cuatro grupos. Conservamos **K-Means con `k=4`** por el tamaño y la facilidad operativa de cuatro segmentos; no afirmamos que sea la mejor solución según toda métrica matemática.

`Churn` no participa en el ajuste. Después de asignar los grupos, los perfiles medidos son:

| ID | Nombre | Perfil observado |
|---:|---|---|
| 0 | Conexión consolidada | Mediana de antigüedad 63 meses y cargo mensual $90.65; 59% fibra y 49% contrato de dos años; churn 11.9%. |
| 1 | DSL por fidelizar | 100% DSL; antigüedad mediana 14 meses; 74% mes a mes; churn 26.5%. |
| 2 | Fibra en riesgo | 100% fibra; antigüedad mediana 13 meses; 96% mes a mes y cargo mensual mediano $85.30; churn 56.7%. |
| 3 | Telefonía estable | 99.9% sin internet; cargo mensual mediano $20.15; churn 7.4%. |

Los nombres resumen patrones observados; no afirman causas. Las tasas se miden después del clustering. `segments_info.json` contiene descripciones, tamaños y tasas actuales; los IDs pueden cambiar al reentrenar.

## Lectura del riesgo y acciones sugeridas

El resumen cruza churn real, score OOF de Regresión Logística y segmento. El umbral aplicado es 0.325; los resultados describen estos 7,043 clientes.

| Segmento | Churn observado | Riesgo OOF medio | Marcados por el modelo | Parte de todos los churners |
|---|---:|---:|---:|---:|
| Conexión consolidada | 11.9% | 10.2% | 4.7% | 12.5% |
| DSL por fidelizar | 26.5% | 26.8% | 36.3% | 23.0% |
| Fibra en riesgo | 56.7% | 58.1% | 92.9% | 58.5% |
| Telefonía estable | 7.4% | 7.5% | 0.1% | 6.0% |

Acciones para probar con el equipo comercial:

- **Fibra en riesgo:** priorizar contacto temprano para revisar calidad, adecuación del plan y opciones de permanencia; ordenar contactos también con el score individual.
- **DSL por fidelizar:** reforzar onboarding y aclarar factura, pagos y uso; probar incentivos de bajo costo para quienes tengan riesgo alto.
- **Conexión consolidada:** proteger la relación con revisiones de valor y calidad; evitar descuentos generales.
- **Telefonía estable:** mantener atención regular y acciones de fidelidad de bajo costo.

Son hipótesis para validar: el dataset no incluye campañas, costos ni resultados de retención.

## Limitaciones

- El CSV es una fotografía histórica y no incluye fechas de eventos, historial de contactos ni resultados de campañas; no permite demostrar causas ni calcular retorno de inversión.
- Regresión Logística fue seleccionada con F1 medio 0.633 frente a 0.626 de Random Forest tras la reducción de variables. En el holdout final obtuvo F1 0.607; seguirá cometiendo errores y requiere monitoreo.
- El umbral 0.325 se ajustó para F1, no con costos reales de falsos positivos/falsos negativos o capacidad de agentes. En la salida OOF actual, 2,474 de 7,043 clientes quedan marcados como churn probable.
- `gender` y `SeniorCitizen` siguen entre las variables supervisadas; no se ha evaluado si los errores difieren entre grupos. El score no debe ser la única base para negar ofertas o servicios.
- Los clusters usan antigüedad, cargo mensual, contrato y tipo de internet. K-Means depende de escala, k y semilla; las métricas internas y nombres describen esta corrida, no garantizan grupos estables ni campañas eficaces.
- Agrupar los seis servicios reduce variables, pero elimina cuál complemento específico tiene cada cliente. Quitar `TotalCharges` reduce información acumulada de facturación, aunque en esta comparación su eliminación mantuvo F1 y aumentó recall. `MonthlyCharges` es un cargo, no una medida de consumo.

## Archivos que produce

En el repositorio:

- `data/output/clustering_feature_comparison.csv`: evaluación con `k=4` de los 27 conjuntos candidatos, incluidas adiciones y retiros individuales, todas las predictoras y variantes con los dos conteos de servicios.
- `data/output/clustering_model_comparison.csv`: comparación de K-Means y Gaussian Mixture con las cuatro variables seleccionadas y `k=2...8`.
- `models/telco_churn_logistic.joblib`: pipeline final de Regresión Logística, reentrenado con todos los registros y preparado para recibir 12 variables derivadas.
- `models/churn_model_info.json`: clase positiva, columnas de entrada del artefacto, variante y umbral seleccionado (0.325 en esta corrida). La API debe usar ese umbral al convertir la probabilidad en `churn: true/false`.
- `models/telco_customer_segments.joblib`: pipeline K-Means (`k=4`) que recibe los campos originales y transforma `tenure`, `MonthlyCharges`, `Contract` e `InternetService`; devuelve un ID de 0 a 3.
- `models/segments_info.json`: k, columnas, nombres, descripciones, tamaños y tasa de churn de cada segmento.
- `data/output/telco_churn_model_output.csv`: `customerID`, `churn_probability`, `predicted_churn`, `segment`, `segment_name`.
- `data/output/telco_churn_dashboard_with_models.csv`: datos limpios más las cuatro columnas de salida anteriores.
- `data/output/telco_churn_segment_risk_summary.csv`: churn observado, riesgo OOF medio, proporción marcada por el modelo y concentración de churners por segmento.

Los scores exportados para la población histórica son OOF: cada cliente fue puntuado por un modelo que no entrenó con su fila. El artefacto de clasificación guardado se reentrena con todo el dataset para atender clientes nuevos; sus métricas de test son las reportadas en el notebook, no se calculan sobre el modelo reentrenado.

## Integración con API

Configurar `MODEL_PATH=models/telco_churn_logistic.joblib`. El modelo espera exactamente estos 12 campos: `gender`, `SeniorCitizen`, `Partner`, `Dependents`, `tenure`, `InternetService`, `Contract`, `PaperlessBilling`, `PaymentMethod`, `MonthlyCharges`, `SecuritySupportCount` y `StreamingServicesCount`. Antes del POST, la página debe calcular `SecuritySupportCount` como la cantidad de respuestas `Yes` entre `OnlineSecurity`, `OnlineBackup`, `DeviceProtection` y `TechSupport` (0–4), y `StreamingServicesCount` como la cantidad de respuestas `Yes` entre `StreamingTV` y `StreamingMovies` (0–2). Tanto `No` como `No internet service` cuentan como cero. El JSON no debe incluir `customerID`, `Churn`, `PhoneService`, `MultipleLines`, `TotalCharges` ni las seis columnas individuales de servicios. El artefacto ya no agrupa servicios dentro del Pipeline, por lo que API no necesita importar `src.modeling.feature_engineering` para inferencia. El umbral elegido por validación cruzada repetida es 0.325; actualmente `src/api/model_service.py` tiene un umbral provisional de 0.50, que API debe alinear con `models/churn_model_info.json` antes de usar el modelo real.

Ejemplo de cuerpo JSON (la página ya debe haber calculado los dos conteos):

```json
{
  "gender": "Female",
  "SeniorCitizen": 0,
  "Partner": "Yes",
  "Dependents": "No",
  "tenure": 12,
  "InternetService": "Fiber optic",
  "Contract": "Month-to-month",
  "PaperlessBilling": "Yes",
  "PaymentMethod": "Electronic check",
  "MonthlyCharges": 89.1,
  "SecuritySupportCount": 2,
  "StreamingServicesCount": 1
}
```

El pipeline de K-Means recibe un DataFrame con los campos originales; transforma `tenure`, `MonthlyCharges`, `Contract` e `InternetService`. Los IDs son arbitrarios y la correspondencia con `segments_info.json` debe regenerarse/revisarse al reentrenar. Gaussian Mixture quedó como modelo de comparación y no se usa para asignar segmentos en el artefacto final.
