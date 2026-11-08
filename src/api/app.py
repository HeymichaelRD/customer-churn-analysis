"""API de predicción de churn (Flask).

Cómo ejecutarla (desde la raíz del repo, con el .venv activo):
    flask --app src/api/app run

El contrato con la página web (rutas, JSON de entrada y de salida) está en el
README, sección "Contratos entre equipos".
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

import model_service
from schema import ValidationError, validate_customer

# Direcciones desde donde la página web puede llamar a la API.
# Van las dos porque el navegador las trata como sitios distintos:
# si falta una, bloquea las llamadas con un error de CORS.
WEB_ORIGINS = ["http://localhost:8000", "http://127.0.0.1:8000"]

# Mensajes en español para los errores HTTP más comunes.
HTTP_ERROR_MESSAGES = {
    400: "La petición no es válida",
    404: "Esa ruta no existe en la API",
    405: "Esa ruta no acepta este método (GET/POST)",
    413: "El archivo es demasiado grande",
    500: "Error interno de la API",
}

app = Flask(__name__)
# Respuestas JSON legibles: con tildes y con los campos en el orden en que se escriben.
app.json.ensure_ascii = False
app.json.sort_keys = False
CORS(app, origins=WEB_ORIGINS)


@app.get("/health")
def health():
    """Indica si la API está encendida y qué modelo está usando."""
    # Mientras no llegue el modelo real del equipo de Modelos, la versión es "demo".
    return jsonify(status="ok", model_version=model_service.model_version())


@app.post("/predict")
def predict():
    """Riesgo de abandono de un cliente. El contrato está en el README."""
    # silent=True: si el cuerpo no es JSON válido, devuelve None en vez de lanzar un error genérico.
    payload = request.get_json(silent=True)
    customer = validate_customer(payload)
    return jsonify(model_service.predict_customer(customer))


@app.errorhandler(ValidationError)
def handle_validation_error(error):
    """Datos del cliente que no cumplen el contrato: 400 con el mensaje y el campo."""
    return jsonify(error=error.message, field=error.field), 400


@app.errorhandler(HTTPException)
def handle_http_error(error):
    """Devuelve los errores HTTP (404, 405, 500...) como JSON, como pide el contrato."""
    message = HTTP_ERROR_MESSAGES.get(error.code, "Error en la petición")
    return jsonify(error=message), error.code
