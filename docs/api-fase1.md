# API · Fase 1: cómo funciona `POST /predict`

Este documento explica el código de la Fase 1 de la API (PR #5) para quien lo revise o lo use desde la web. No hace falta leer el código para entenderlo.

**Responsable:** Christopher ([chpujols-DS07](https://github.com/chpujols-DS07)) · Persona API

---

## 1. La idea general

Cuando la página web pide una predicción, los datos del cliente pasan por tres piezas, cada una en su propio archivo:

```
La web envía los datos del cliente (POST /predict)
        │
        ▼
app.py ─────────── recibe la petición
        │
        ▼
schema.py ──────── ¿los datos cumplen el contrato?
        │                 │
        │ Sí              └── No → la API responde 400 con el error y el campo
        ▼
model_service.py ─ calcula la probabilidad y el nivel de riesgo
        │
        ▼
app.py ─────────── responde 200 con los 4 campos del contrato
```

| Archivo | Qué hace | Comparación |
|---|---|---|
| `src/api/app.py` | Recibe la petición y devuelve la respuesta | La puerta de entrada |
| `src/api/schema.py` | Revisa que los datos cumplan el contrato | El portero |
| `src/api/model_service.py` | Carga el modelo y calcula el riesgo | El médico |
| `tests/test_predict.py` | Verifica que todo lo anterior funcione | El inspector |

Cada archivo hace una sola cosa. Por eso, si cambia la validación, no hay que tocar el modelo, y viceversa.

---

## 2. Lo que recibe y lo que responde

Todo sigue el **contrato API → Web del README** ("Contratos entre equipos"). No se cambió ningún nombre ni formato.

**Ejemplo de respuesta correcta (200):**
```json
{ "churn": true, "probability": 0.63, "risk_level": "high",
  "segment": { "id": 2, "name": "Fibra en riesgo", "description": "…" },
  "model_version": "telco_churn_logistic" }
```

**Ejemplo de error (400):**
```json
{ "error": "El campo Contract tiene un valor no permitido", "field": "Contract" }
```

El campo `field` es el que usa `api.js`: llega como `error.field` y sirve para marcar en rojo la casilla del formulario que hay que corregir.

---

## 3. `schema.py`: las reglas de validación

Los datos pasan por cinco revisiones, en este orden. **En el primer problema se detiene** y responde ese error; no lista todos a la vez.

| # | Revisión | Ejemplo que se rechaza | Mensaje |
|---|---|---|---|
| 1 | ¿Llegó un objeto JSON? | Texto suelto, una lista o `null` | *Los datos del cliente deben enviarse como un objeto JSON* |
| 2 | ¿Están los 12 campos? | Falta `Contract` | *Falta el campo Contract* |
| 3 | ¿Sobra algún campo? | Se envía `customerID` | *El campo customerID no es parte del contrato* |
| 4 | ¿Cada valor es válido? | `"Contract": "Mensual"` | *El campo Contract tiene un valor no permitido* |
| 5 | ¿Los campos son coherentes entre sí? | Sin internet pero con `SecuritySupportCount: 1` | *Si InternetService es "No", SecuritySupportCount debe ser 0* |

### Reglas por campo

| Campo | Regla |
|---|---|
| Campos de texto | Solo los valores exactos del contrato, con mayúsculas incluidas: `"female"` se rechaza |
| `SeniorCitizen` | Solo el **número** `0` o `1`. Se rechazan `"1"` (texto) y `true` |
| `tenure` | Número **entero**, 0 o más. Se rechazan `1.5` y `-1` |
| `MonthlyCharges` | Número **mayor que 0**: un cliente activo siempre paga algo |
| `SecuritySupportCount` | Número **entero de 0 a 4**: cuántos de los 4 servicios de seguridad y soporte son `"Yes"` |
| `StreamingServicesCount` | Número **entero de 0 a 2**: cuántos de los 2 servicios de streaming son `"Yes"` |

### Casos especiales que se cuidan

- **`true` en lugar de `1`.** En Python, `True == 1`. Sin cuidado, un `true` enviado por error pasaría como un `1`. La validación compara el valor **y el tipo**.
- **`NaN` o `Infinity`.** El lector de JSON de Python los acepta aunque el estándar no los permita. Si llegaran al modelo, la predicción no tendría sentido. Se rechazan.
- **Números gigantes** como `10**400`. Python los lee como enteros, pero no caben en un número decimal y hacían fallar la API con un error 500. Ahora se rechazan con un 400, como cualquier dato inválido.

---

## 4. `model_service.py`: el modelo y el riesgo

### Qué modelo usa

```
¿El .env tiene MODEL_PATH y ese archivo existe?
   ├── Sí → usa ese modelo (el del equipo de Modelos)   ← con el .env de .env.example
   └── No → usa un modelo de prueba (o no arranca, si REQUIRE_MODEL=1)
```

- **El modelo real** es `models/telco_churn_logistic.joblib` (regresión logística con 12 campos). Se configura con `MODEL_PATH` en el `.env`; el umbral (`0.325`) sale de `models/churn_model_info.json`.
- **El modelo de prueba** es una regresión logística entrenada con `data/raw` y los mismos 12 campos. Existe para trabajar sin el modelo real. Sus resultados son de ejemplo, y por eso `model_version` responde `"demo"`.
- **Los modelos se cargan una sola vez, al arrancar la API**, y se reutilizan en todas las predicciones. Si falta un archivo o no coincide con el contrato, la API no arranca y el error dice cuál es.
- **El segmento** sale del K-Means de `models/telco_customer_segments.joblib`, con los nombres de `models/segments_info.json`. Al K-Means solo se le pasan las columnas de `"columns"` en ese JSON (`tenure`, `MonthlyCharges`, `Contract` e `InternetService`); si una no está en el contrato, la API no arranca.

### Requisitos del modelo real

- Debe ser un **`Pipeline` de scikit-learn que reciba los 12 campos del contrato** (`input_columns` en `churn_model_info.json`) y haga él mismo el escalado y el one-hot.
- Los dos conteos de servicios **no** los calcula el modelo: llegan ya calculados desde la página. Así, la API no necesita `src/modeling/feature_engineering.py` para predecir.
- Hay que cargarlo con la **misma versión de scikit-learn** con la que se entrenó (la de `requirements.txt`).

### Niveles de riesgo

| Probabilidad | `risk_level` |
|---|---|
| menos de 0.30 | `"low"` |
| de 0.30 a menos de 0.60 | `"medium"` |
| 0.60 o más | `"high"` |

- **`churn` es `true` desde 0.325** con el modelo real (el umbral de `models/churn_model_info.json`) y desde 0.50 con el de prueba. Un cliente con 0.55 tiene `churn: true` y riesgo `"medium"`: no es una contradicción, son dos preguntas distintas (*¿se va?* y *¿qué tan urgente es?*).
- **La probabilidad se redondea antes de calcular el nivel.** Si no, un 0.597 se mostraría como "0.60" pero con riesgo "medium".
- **Los cortes son provisionales.** Están como constantes al inicio del archivo para cambiarlos en un solo lugar cuando Modelos los defina.

---

## 5. Decisiones para revisar

Estas tres van **más allá de lo que dice el contrato**. Las tomé por las razones de abajo, pero se pueden cambiar si el equipo decide otra cosa.

| # | Decisión | Por qué | Si se prefiere lo contrario |
|---|---|---|---|
| 1 | **Se rechazan los campos que no están en el contrato** (por ejemplo, `customerID`) | Detecta errores de tipeo, como `contrato` en lugar de `Contract`, en vez de ignorarlos en silencio | La web debe enviar solo los 12 campos. Para ignorarlos, se borran 3 líneas en `validate_customer` |
| 2 | **Sin internet, los dos conteos deben ser 0** | Los servicios que se cuentan son de internet: en el dataset, sin internet todos dicen `"No internet service"`. El modelo nunca vio otra combinación | Se quita la regla en `_check_coherence` |
| 3 | **`churn: true` desde el umbral de Modelos** (0.325, en `models/churn_model_info.json`) | Modelos lo eligió por F1 y recall con validación cruzada. La API lo lee del JSON, así que no hay que cambiar código si lo ajustan | Modelos cambia `threshold` en el JSON |

---

## 6. Cómo probarlo

**Pruebas automáticas**, desde la raíz del repo, con el `.venv` activo:
```powershell
pytest
```
Deben pasar **59 pruebas**. Cubren las respuestas correctas, los datos inválidos (también los campos que ya no son parte del contrato, como `TotalCharges`), la regla de coherencia, `NaN`, números gigantes, cuerpos que no son JSON, el método GET y la carga de los modelos reales. Una de ellas predice los 7,043 clientes y compara con los resultados del equipo de Modelos.

**A mano**, con la API encendida (`flask --app src/api/app run`):
```powershell
Invoke-RestMethod http://127.0.0.1:5000/predict -Method Post -ContentType "application/json" -Body '{"gender":"Female","SeniorCitizen":0,"Partner":"Yes","Dependents":"No","tenure":1,"InternetService":"DSL","Contract":"Month-to-month","PaperlessBilling":"Yes","PaymentMethod":"Electronic check","MonthlyCharges":29.85,"SecuritySupportCount":1,"StreamingServicesCount":0}'
```

---

## 7. Para quien construya la página Predecir

- Envía **exactamente** los 12 campos del contrato, con los valores en inglés que define `labels.js`. Nada más: un campo extra se rechaza (decisión 1).
- Antes de enviar, calcula `SecuritySupportCount` (cuántos `"Yes"` hay entre `OnlineSecurity`, `OnlineBackup`, `DeviceProtection` y `TechSupport`) y `StreamingServicesCount` (cuántos hay entre `StreamingTV` y `StreamingMovies`). Los seis servicios no se envían.
- `SeniorCitizen` va como **número** (`0` o `1`), no como texto ni como `true`/`false`.
- `tenure` debe ser un **entero**.
- Sin internet, los dos conteos son `0`. Lo más fácil es que el formulario apague los seis servicios al elegir "Sin internet".
- Ante un 400, `error.field` dice qué casilla marcar y `error.message` ya viene en español, listo para mostrar.

---

## 8. Lo que falta (próximas fases)

| Fase | Pendiente | Depende de |
|---|---|---|
| 2 | `/samples`, `/recommendations`, `/insights` | Datos del equipo de Limpieza y EDA |
| 3 | Conectar el modelo real y `/model-info` | Listo: la regresión logística del equipo de Modelos, con 12 campos |
