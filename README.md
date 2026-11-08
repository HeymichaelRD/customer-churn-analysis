<div align="center">

# 📉 Customer Churn Analysis

**Predicción de abandono de clientes: de los datos crudos a una aplicación web**

Proyecto final · Técnico en Ciencia de Datos · Talendig

![Python](https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white)
![pandas](https://img.shields.io/badge/pandas-3.1-150458?logo=pandas&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-1.9-F7931E?logo=scikitlearn&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.1-000000?logo=flask&logoColor=white)
![Jupyter](https://img.shields.io/badge/Jupyter-Notebooks-F37626?logo=jupyter&logoColor=white)
![Power BI](https://img.shields.io/badge/Power%20BI-Dashboard-F2C811)
![Estado](https://img.shields.io/badge/Estado-En%20desarrollo-yellow)

</div>

---

## 📑 Contenido

- [Sobre el proyecto](#-sobre-el-proyecto)
- [Flujo del proyecto](#-flujo-del-proyecto)
- [Equipos](#-equipos)
- [Estructura de carpetas](#-estructura-de-carpetas)
- [Instalación](#-instalación)
- [Cómo ejecutar](#-cómo-ejecutar)
- [Cómo colaborar](#-cómo-colaborar)
- [Convenciones](#-convenciones)
- [Contratos entre equipos](#-contratos-entre-equipos)
- [Problemas comunes](#-problemas-comunes)
- [Integrantes](#-integrantes)

---

## 📌 Sobre el proyecto

El **churn** es el porcentaje de clientes que dejan de usar un servicio. Retener un cliente cuesta mucho menos que conseguir uno nuevo, así que saber **quién está en riesgo de irse** permite actuar a tiempo.

En este proyecto vamos a:

1. **Limpiar** el dataset de clientes.
2. **Explorar** los datos (EDA) para entender qué factores se relacionan con el abandono.
3. **Entrenar modelos de Machine Learning** que predigan si un cliente se va a ir.
4. **Exponer el modelo en una API** hecha con Flask.
5. **Construir una página web** donde se pueda consultar la predicción.
6. **Crear un dashboard en Power BI** con los hallazgos.
7. **Automatizar tareas con RPA** en Python.

### 🗂️ Dataset

Usamos **[Telco Customer Churn](https://www.kaggle.com/datasets/blastchar/telco-customer-churn)** (Kaggle), datos de ejemplo de IBM de una empresa ficticia de telecomunicaciones.

| | |
|---|---|
| **Clientes (filas)** | 7,043 |
| **Columnas** | 21 |
| **Variable objetivo** | `Churn`: si el cliente se fue en el último mes (`Yes` / `No`) |
| **Archivo** | `data/raw/WA_Fn-UseC_-Telco-Customer-Churn.csv` |

Cada cliente tiene información de:

- 📞 **Servicios contratados:** teléfono, líneas múltiples, internet, seguridad en línea, respaldo, protección de dispositivos, soporte técnico y streaming.
- 💳 **Cuenta:** antigüedad (`tenure`), tipo de contrato, facturación electrónica, método de pago, cargo mensual y cargo total.
- 👤 **Datos demográficos:** género, si es adulto mayor, si tiene pareja y si tiene dependientes.

---

## 🔄 Flujo del proyecto

```mermaid
flowchart LR
    RAW[("data/raw<br/>Dataset original")] --> CLEAN["🧹 Limpieza<br/>src/cleaning"]
    CLEAN --> PROC[("data/processed<br/>Datos limpios")]
    PROC --> EDA["🔍 EDA<br/>notebooks"]
    PROC --> ML["🤖 Modelos ML<br/>src/modeling"]
    ML --> MODEL[("models/<br/>Modelo entrenado")]
    MODEL --> API
    subgraph TEAM_API_WEB["Equipo API y Web"]
        API["🔌 API Flask<br/>src/api"] --> WEB["🌐 Página web<br/>web"]
    end
    PROC --> OUT[("data/output<br/>Datos para el dashboard")]
    ML --> OUT
    OUT --> BI["📊 Power BI<br/>dashboard"]
    RPA["⚙️ RPA<br/>src/rpa"]
```

> [!NOTE]
> La tarea que va a automatizar el equipo de RPA está por definir. Cuando se decida, se conecta en este diagrama.

---

## 👥 Equipos

Cada equipo trabaja **en su carpeta** y **en su rama**. Así nadie pisa el trabajo de otro.

| Equipo | Carpeta | Rama | Entrega |
|---|---|---|---|
| 🧹 Limpieza y 🔍 EDA | `src/cleaning/` y `notebooks/` | `cleaning-eda` | Datos limpios en `data/processed/` y notebooks con el análisis y los hallazgos |
| 🤖 Modelos de ML | `src/modeling/` | `modeling` | Modelo entrenado en `models/` |
| 🔌 API y 🌐 Web | `src/api/` y `web/` | `api-web` | API en Flask que devuelve predicciones y página en HTML/CSS/JS que la consume |
| 📊 Dashboard | `dashboard/` | `dashboard` | Archivo `.pbix` de Power BI |
| ⚙️ RPA | `src/rpa/` | `rpa` | Bot de automatización en Python |

---

## 📁 Estructura de carpetas

```
customer-churn-analysis/
├── README.md           ← este archivo
├── requirements.txt    ← librerías de Python con versiones fijas
├── .env.example        ← plantilla de variables de entorno
├── data/
│   ├── raw/            ← dataset original (no se modifica nunca)
│   ├── processed/      ← datos limpios
│   └── output/         ← datos para Power BI y resultados
├── notebooks/          ← EDA y experimentos (cada persona los suyos)
├── src/
│   ├── cleaning/       ← scripts de limpieza
│   ├── modeling/       ← código para entrenar y evaluar modelos
│   ├── api/            ← API en Flask
│   └── rpa/            ← automatización en Python
├── models/             ← modelos ya entrenados (.pkl / .joblib)
├── dashboard/          ← archivo .pbix de Power BI
├── web/                ← página web (HTML, CSS, JS)
├── assets/             ← imágenes y documentos del proyecto
└── tests/              ← pruebas automáticas
```

> [!TIP]
> `src/modeling/` tiene el **código** que entrena el modelo. `models/` guarda el **modelo ya entrenado**. No los confundas.

---

## 🚀 Instalación

### 1. Instala las herramientas (una sola vez)

| Herramienta | Para qué sirve | Descarga |
|---|---|---|
| **Python 3.14** | Correr el código del proyecto | [python.org/downloads](https://www.python.org/downloads/) |
| **Git** | Control de versiones | [git-scm.com](https://git-scm.com/downloads) |
| **GitHub Desktop** | Usar Git con botones, sin terminal | [desktop.github.com](https://desktop.github.com/) |
| **VS Code** | Editor de código y notebooks | [code.visualstudio.com](https://code.visualstudio.com/) |
| **Power BI Desktop** | Solo el equipo de dashboard | Microsoft Store |

> [!IMPORTANT]
> Al instalar Python en Windows, marca la casilla **"Add python.exe to PATH"** en la primera pantalla del instalador.

### 2. Descarga (clona) el proyecto

1. Abre **GitHub Desktop** e inicia sesión con tu cuenta de GitHub.
2. Ve a **File → Clone repository → URL**.
3. Pega la dirección del repo: `https://github.com/HeymichaelRD/customer-churn-analysis`
4. Elige en qué carpeta de tu computadora guardarlo y haz clic en **Clone**.
5. Haz clic en **Open in Visual Studio Code**.

### 3. Crea tu ambiente virtual e instala las librerías

En VS Code abre una terminal (**Terminal → New Terminal**) y ejecuta los comandos según tu sistema:

<details open>
<summary><b>🪟 Windows (PowerShell)</b></summary>

```powershell
# Crear el ambiente virtual (solo la primera vez)
py -3.14 -m venv .venv

# Activarlo (cada vez que abras una terminal nueva)
.venv\Scripts\Activate.ps1

# Instalar las librerías
pip install -r requirements.txt

# Crear tu archivo de configuración
copy .env.example .env
```

</details>

<details>
<summary><b>🍎 Mac / 🐧 Linux</b></summary>

```bash
# Crear el ambiente virtual (solo la primera vez)
python3.14 -m venv .venv

# Activarlo (cada vez que abras una terminal nueva)
source .venv/bin/activate

# Instalar las librerías
pip install -r requirements.txt

# Crear tu archivo de configuración
cp .env.example .env
```

</details>

✅ Sabrás que el ambiente está activo porque la terminal muestra **`(.venv)`** al principio de la línea.

> [!TIP]
> Si alguien agrega una librería nueva a `requirements.txt`, vuelve a correr `pip install -r requirements.txt` después de descargar los cambios.

---

## 💻 Cómo ejecutar

> Activa siempre el ambiente virtual antes de correr cualquier cosa.

**Notebooks (EDA y experimentos)**

Abre el `.ipynb` en VS Code y, arriba a la derecha, en **Select Kernel**, elige el Python de **`.venv`**.
También puedes usar Jupyter en el navegador:

```bash
jupyter notebook
```

**API (Flask)**

```bash
flask --app src/api/app run
```

La API queda disponible en `http://localhost:5000`. Para comprobar que está encendida, abre `http://localhost:5000/health` en el navegador: debe responder `{"status": "ok", ...}`.

**Página web**

Con la API corriendo, abre otra terminal:

```bash
python -m http.server 8000 --directory web
```

Luego abre `http://localhost:8000` en el navegador. Arriba a la derecha verás si la página está conectada con la API (punto verde) o no (punto rojo).

**Pruebas**

```bash
pytest
```

---

## 🤝 Cómo colaborar

### Reglas de oro

1. 🚫 **Nunca trabajes directo en `main`.** Trabaja siempre en la rama de tu equipo.
2. ⬇️ **Antes de empezar, descarga los últimos cambios** (*Fetch origin* → *Pull origin*).
3. 📂 **Trabaja solo en la carpeta de tu equipo.** Si necesitas algo de otra carpeta, habla con ese equipo.
4. 📓 **Cada persona tiene sus propios notebooks.** Nunca edites el notebook de otra persona.
5. 💾 **Haz commits pequeños y seguido**, con un mensaje que explique qué hiciste.
6. 🔐 **Nunca subas contraseñas.** Van en tu `.env`, que no se sube.
7. 📦 **Solo el responsable sube** los datos oficiales (`data/processed/`, `data/output/`), el modelo (`models/`) y el `.pbix`. Para tus pruebas usa una carpeta `tmp/`, que Git ignora.

### Paso a paso con GitHub Desktop

```mermaid
flowchart LR
    A["1. Pull origin<br/>bajar cambios"] --> B["2. Cambiar a<br/>la rama del equipo"]
    B --> C["3. Trabajar<br/>en VS Code"]
    C --> D["4. Commit<br/>guardar cambios"]
    D --> E["5. Push origin<br/>subir cambios"]
    E --> F["6. Pull Request<br/>pedir revisión"]
    F --> G["7. Revisión<br/>y merge a main"]
```

1. **Bajar cambios:** clic en **Fetch origin** y luego en **Pull origin**.
2. **Cambiar de rama:** en **Current branch**, elige la rama de tu equipo (por ejemplo `cleaning-eda`).
3. **Actualizar tu rama con `main`:** menú **Branch → Update from main**. Así tienes lo último que aprobaron los otros equipos.
4. **Trabajar:** haz tus cambios en VS Code.
5. **Commit:** en GitHub Desktop revisa los archivos de la izquierda (desmarca los que no quieras subir), escribe un resumen abajo y clic en **Commit to `<tu-rama>`**.
6. **Subir:** clic en **Push origin**.
7. **Pull Request:** clic en **Preview Pull Request** (o **Create Pull Request**, según tu versión). Se abre GitHub en el navegador: describe qué hiciste y clic en **Create pull request**.
8. **Revisión:** Michael (mantenedor del repo) revisa y, si todo está bien, lo une a `main` (*merge*).

### Mensajes de commit

Escribe en español, en presente, empezando con el área:

```
cleaning: elimina clientes duplicados
eda: agrega gráfico de churn por tipo de contrato
api: crea endpoint /predict
```

<details>
<summary><b>📖 Glosario de Git para principiantes</b></summary>

| Término | Qué significa |
|---|---|
| **Repositorio (repo)** | La carpeta del proyecto con todo su historial de cambios. |
| **Clonar** | Descargar el repo de GitHub a tu computadora. |
| **Commit** | Una "foto" de tus cambios, con un mensaje que explica qué hiciste. |
| **Rama (branch)** | Una copia paralela del proyecto donde puedes trabajar sin afectar `main`. |
| **`main`** | La rama principal, con la versión aprobada del proyecto. |
| **Push** | Subir tus commits a GitHub. |
| **Pull** | Bajar a tu computadora los cambios que otros subieron. |
| **Pull Request (PR)** | Una solicitud para unir tu rama a `main`, que otra persona revisa. |
| **Mantenedor (maintainer)** | La persona que revisa los Pull Requests y los une a `main`. |
| **Merge** | Unir los cambios de una rama con otra. |
| **Conflicto** | Cuando dos personas cambiaron la misma parte de un archivo y Git no sabe cuál dejar. |

</details>

---

## 📏 Convenciones

- **Idioma:** el código (variables, funciones, archivos) va en **inglés**, igual que las columnas del dataset. Los comentarios, notebooks y documentación van en **español**.

  ```python
  # Convertimos el cargo total a número; los valores en blanco quedan como NaN
  raw_df["TotalCharges"] = pd.to_numeric(raw_df["TotalCharges"], errors="coerce")
  ```

- **Nombres de archivos y carpetas:** sin tildes, sin ñ y sin espacios. Usa guion bajo: `clean_data.py`, no `clean data.py`.
- **Notebooks:** `NN_tema_nombre.ipynb`. Por ejemplo: `01_cleaning_juan.ipynb`, `02_eda_maria.ipynb`.
- **Datos originales:** lo que está en `data/raw/` **no se modifica nunca**. La limpieza genera archivos nuevos en `data/processed/`.
- **Librerías nuevas:** se agregan a `requirements.txt` con su versión fija (`nombre==X.Y.Z`).

---

## 📜 Contratos entre equipos

Lo que cada equipo **entrega** al siguiente. Con esto definido, todos pueden trabajar en paralelo sin esperarse.

| Entrega | De → Para | Archivo / endpoint | Estado |
|---|---|---|---|
| Datos limpios | Limpieza y EDA → Modelos | `data/processed/________.csv` | ⏳ Por definir |
| Modelo entrenado | Modelos → API | `models/________.pkl` | ⏳ Por definir |
| Datos para el dashboard | Limpieza y EDA, Modelos → Power BI | `data/output/________.csv` | ⏳ Por definir |
| Predicción | API → Web | `GET /health` y `POST /predict` | 📝 Borrador v1 (abajo) |

<details>
<summary><b>📝 Contrato API → Web (borrador v1)</b></summary>

**Conexión:** la API corre en `http://localhost:5000` y habla en JSON. Solo acepta llamadas de la página web (`http://localhost:8000` o `http://127.0.0.1:8000`).

#### `GET /health`: ¿está encendida la API?

```json
{ "status": "ok", "model_version": "demo" }
```

`model_version` es `"demo"` mientras la API use un modelo provisional. Cuando llegue el modelo real del equipo de Modelos, dirá su versión.

#### `POST /predict`: riesgo de abandono de un cliente

**Petición:** los 19 campos del dataset, con los **mismos nombres y valores** (en inglés y con las mismas mayúsculas). `customerID` no se envía.

| Campo | Tipo | Valores permitidos |
|---|---|---|
| `gender` | texto | `"Female"`, `"Male"` |
| `SeniorCitizen` | entero | `0` (no), `1` (sí) |
| `Partner`, `Dependents`, `PhoneService`, `PaperlessBilling` | texto | `"Yes"`, `"No"` |
| `tenure` | entero | `0` o más (meses como cliente) |
| `MultipleLines` | texto | `"Yes"`, `"No"`, `"No phone service"` |
| `InternetService` | texto | `"DSL"`, `"Fiber optic"`, `"No"` |
| `OnlineSecurity`, `OnlineBackup`, `DeviceProtection`, `TechSupport`, `StreamingTV`, `StreamingMovies` | texto | `"Yes"`, `"No"`, `"No internet service"` |
| `Contract` | texto | `"Month-to-month"`, `"One year"`, `"Two year"` |
| `PaymentMethod` | texto | `"Electronic check"`, `"Mailed check"`, `"Bank transfer (automatic)"`, `"Credit card (automatic)"` |
| `MonthlyCharges` | número | mayor que `0` |
| `TotalCharges` | número | `0` o más (con `tenure` 0, se envía `0`) |

**Reglas de coherencia** (si no se cumplen, la API responde `400`):

- Si `PhoneService` es `"No"`, `MultipleLines` debe ser `"No phone service"`.
- Si `InternetService` es `"No"`, los 6 servicios de internet deben ser `"No internet service"`.

Ejemplo (el primer cliente del dataset):

```json
{
  "gender": "Female",
  "SeniorCitizen": 0,
  "Partner": "Yes",
  "Dependents": "No",
  "tenure": 1,
  "PhoneService": "No",
  "MultipleLines": "No phone service",
  "InternetService": "DSL",
  "OnlineSecurity": "No",
  "OnlineBackup": "Yes",
  "DeviceProtection": "No",
  "TechSupport": "No",
  "StreamingTV": "No",
  "StreamingMovies": "No",
  "Contract": "Month-to-month",
  "PaperlessBilling": "Yes",
  "PaymentMethod": "Electronic check",
  "MonthlyCharges": 29.85,
  "TotalCharges": 29.85
}
```

**Respuesta** (`200`; los valores son ilustrativos):

```json
{
  "churn": true,
  "probability": 0.78,
  "risk_level": "high",
  "model_version": "demo"
}
```

| Campo | Significado |
|---|---|
| `churn` | `true` si el modelo predice que el cliente **abandona** |
| `probability` | Probabilidad de abandono, de `0` a `1`, con 2 decimales |
| `risk_level` | `"low"` (menos de 0.30), `"medium"` (de 0.30 a menos de 0.60) o `"high"` (0.60 o más). Umbrales provisionales |
| `model_version` | `"demo"` o la versión del modelo real |

#### Errores

| Código | Cuándo | Respuesta |
|---|---|---|
| `400` | Falta un campo, el tipo o el valor no es válido, o se rompe una regla de coherencia | `{"error": "El campo Contract tiene un valor no permitido", "field": "Contract"}` |
| `404` | La ruta no existe | `{"error": "Esa ruta no existe en la API"}` |
| `500` | Falla la API o el modelo | `{"error": "Error interno de la API"}` |

Los mensajes van en español porque la página se los muestra al usuario. `field` sirve para marcar en rojo el campo del formulario.

**Por confirmar con otros equipos:**

1. **Modelos:** qué columnas usa el modelo. Si son menos de 19, se recorta este contrato.
2. **Limpieza y EDA:** cómo tratan `TotalCharges` vacío (los 11 clientes con `tenure` 0).
3. **Modelos:** a partir de qué probabilidad `churn` es `true` (por defecto, `0.5`).

Las demás rutas de la API (recomendaciones, clientes de ejemplo, hallazgos, información del modelo y predicción por lotes) se documentan aquí cuando se construyan.

</details>

---

## 🧯 Problemas comunes

<details>
<summary><b>"python" o "py" no se reconoce como comando</b></summary>

Python no quedó en el PATH. Reinstala Python y marca **"Add python.exe to PATH"** en la primera pantalla.

</details>

<details>
<summary><b>PowerShell dice "la ejecución de scripts está deshabilitada"</b></summary>

Ejecuta esto una sola vez y vuelve a activar el ambiente:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

</details>

<details>
<summary><b>El notebook dice <code>ModuleNotFoundError: No module named 'pandas'</code></b></summary>

El notebook está usando otro Python. Arriba a la derecha, en **Select Kernel**, elige el de **`.venv`**. Si sigue fallando, activa el ambiente y corre `pip install -r requirements.txt`.

</details>

<details>
<summary><b>GitHub Desktop muestra un conflicto</b></summary>

No borres nada ni fuerces nada. Avísale a Michael en el grupo y lo resuelven juntos.

</details>

<details>
<summary><b>Subí un archivo por error</b></summary>

Avísale a Michael. Si fue una contraseña, cámbiala de inmediato: aunque se borre después, queda en el historial.

</details>

---

## 🎓 Integrantes

> [!NOTE]
> Cada equipo agrega sus nombres aquí en su **primer Pull Request**. Es una buena forma de practicar el flujo.

| Equipo | Integrantes |
|---|---|
| 🛠️ Mantenedor del repo | Michael ([HeymichaelRD](https://github.com/HeymichaelRD)) |
| 🧹 Limpieza y 🔍 EDA | _(por completar)_ |
| 🤖 Modelos de ML | _(por completar)_ |
| 🔌 API y 🌐 Web | Michael ([HeymichaelRD](https://github.com/HeymichaelRD)), _(por completar)_ |
| 📊 Dashboard | _(por completar)_ |
| ⚙️ RPA | _(por completar)_ |

---

<div align="center">

Proyecto final del **Técnico en Ciencia de Datos** · Talendig · 2026

</div>
