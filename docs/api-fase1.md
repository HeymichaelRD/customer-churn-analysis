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
{ "churn": true, "probability": 0.64, "risk_level": "high", "model_version": "demo" }
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
| 2 | ¿Están los 19 campos? | Falta `Contract` | *Falta el campo Contract* |
| 3 | ¿Sobra algún campo? | Se envía `customerID` | *El campo customerID no es parte del contrato* |
| 4 | ¿Cada valor es válido? | `"Contract": "Mensual"` | *El campo Contract tiene un valor no permitido* |
| 5 | ¿Los campos son coherentes entre sí? | Sin teléfono pero con `MultipleLines: "No"` | *Si PhoneService es "No", MultipleLines debe ser "No phone service"* |

### Reglas por campo

| Campo | Regla |
|---|---|
| Campos de texto | Solo los valores exactos del contrato, con mayúsculas incluidas: `"female"` se rechaza |
| `SeniorCitizen` | Solo el **número** `0` o `1`. Se rechazan `"1"` (texto) y `true` |
| `tenure` | Número **entero**, 0 o más. Se rechazan `1.5` y `-1` |
| `MonthlyCharges` | Número **mayor que 0**: un cliente activo siempre paga algo |
| `TotalCharges` | Número, **0 o más**: un cliente recién llegado todavía no ha acumulado cargos |

### Casos especiales que se cuidan

- **`true` en lugar de `1`.** En Python, `True == 1`. Sin cuidado, un `true` enviado por error pasaría como un `1`. La validación compara el valor **y el tipo**.
- **`NaN` o `Infinity`.** El lector de JSON de Python los acepta aunque el estándar no los permita. Si llegaran al modelo, la predicción no tendría sentido. Se rechazan.

---

## 4. `model_service.py`: el modelo y el riesgo

### Qué modelo usa

```
¿El .env tiene MODEL_PATH y ese archivo existe?
   ├── Sí → usa ese modelo (el del equipo de Modelos)
   └── No → usa un modelo de prueba          ← la situación actual
```

- **El modelo de prueba** es una regresión logística entrenada con `data/raw`. Solo existe para que la web funcione mientras llega el modelo real. Sus resultados son de ejemplo, y por eso `model_version` responde `"demo"`.
- **El modelo se carga una sola vez**, en la primera predicción, y se reutiliza en las siguientes. La primera petición tarda unos segundos; las demás son inmediatas.

### Cómo conectar el modelo real

Cuando el equipo de Modelos entregue su archivo:
1. Ponerlo en la ruta de `MODEL_PATH` (hoy, `models/modelo.pkl`).
2. Reiniciar la API.

**No hay que cambiar código.** `model_version` pasa a mostrar el nombre del archivo.

**Requisito para que funcione:** el modelo debe ser un **`Pipeline` de scikit-learn que reciba las 19 columnas originales del contrato** y haga él mismo el preprocesamiento. El modelo de prueba ya está construido así. Si el modelo real esperara datos ya transformados, la API tendría que repetir esa limpieza, y cualquier diferencia entre ambas haría que prediga mal sin dar error.

### Niveles de riesgo

| Probabilidad | `risk_level` |
|---|---|
| menos de 0.30 | `"low"` |
| de 0.30 a menos de 0.60 | `"medium"` |
| 0.60 o más | `"high"` |

- **`churn` es `true` desde 0.50.** Un cliente con 0.55 tiene `churn: true` y riesgo `"medium"`: no es una contradicción, son dos preguntas distintas (*¿se va?* y *¿qué tan urgente es?*).
- **La probabilidad se redondea antes de calcular el nivel.** Si no, un 0.597 se mostraría como "0.60" pero con riesgo "medium".
- **Los cortes son provisionales.** Están como constantes al inicio del archivo para cambiarlos en un solo lugar cuando Modelos los defina.

---

## 5. Decisiones para revisar

Estas tres van **más allá de lo que dice el contrato**. Las tomé por las razones de abajo, pero se pueden cambiar si el equipo decide otra cosa.

| # | Decisión | Por qué | Si se prefiere lo contrario |
|---|---|---|---|
| 1 | **Se rechazan los campos que no están en el contrato** (por ejemplo, `customerID`) | Detecta errores de tipeo, como `contrato` en lugar de `Contract`, en vez de ignorarlos en silencio | La web debe enviar solo los 19 campos. Para ignorarlos, se borran 3 líneas en `validate_customer` |
| 2 | **Reglas de coherencia en los dos sentidos:** con teléfono, `MultipleLines` no puede ser `"No phone service"`; con internet, los servicios no pueden ser `"No internet service"` | El contrato pide un solo sentido, pero en los 7,043 clientes del dataset se cumplen los dos. El modelo nunca vio esas combinaciones | Se quitan las dos reglas inversas en `_check_coherence` |
| 3 | **`churn: true` desde 0.50** | Es el corte habitual mientras no se conozca el costo de cada error | Se cambia `CHURN_THRESHOLD` cuando Modelos lo defina |

---

## 6. Cómo probarlo

**Pruebas automáticas**, desde la raíz del repo, con el `.venv` activo:
```powershell
pytest
```
Deben pasar **28 pruebas**: las 3 que ya existían y 25 nuevas. Las nuevas cubren las respuestas correctas, los 14 tipos de error de la tabla de arriba, `NaN`, cuerpos que no son JSON y el método GET.

**A mano**, con la API encendida (`flask --app src/api/app run`):
```powershell
Invoke-RestMethod http://127.0.0.1:5000/predict -Method Post -ContentType "application/json" -Body '{"gender":"Female","SeniorCitizen":0,"Partner":"Yes","Dependents":"No","tenure":1,"PhoneService":"No","MultipleLines":"No phone service","InternetService":"DSL","OnlineSecurity":"No","OnlineBackup":"Yes","DeviceProtection":"No","TechSupport":"No","StreamingTV":"No","StreamingMovies":"No","Contract":"Month-to-month","PaperlessBilling":"Yes","PaymentMethod":"Electronic check","MonthlyCharges":29.85,"TotalCharges":29.85}'
```

---

## 7. Para quien construya la página Predecir

- Envía **exactamente** los 19 campos del contrato, con los valores en inglés que define `labels.js`. Nada más: un campo extra se rechaza (decisión 1).
- `SeniorCitizen` va como **número** (`0` o `1`), no como texto ni como `true`/`false`.
- `tenure` debe ser un **entero**.
- Si el cliente no tiene teléfono o internet, los campos que dependen de ellos deben llevar `"No phone service"` o `"No internet service"`. Lo más fácil es que el formulario los complete solo al elegir "No".
- Ante un 400, `error.field` dice qué casilla marcar y `error.message` ya viene en español, listo para mostrar.

---

## 8. Lo que falta (próximas fases)

| Fase | Pendiente | Depende de |
|---|---|---|
| 2 | `/samples`, `/recommendations`, `/insights` | Datos del equipo de Limpieza y EDA |
| 3 | Conectar el modelo real y `/model-info` | El modelo del equipo de Modelos, como `Pipeline` con las 19 columnas originales |
