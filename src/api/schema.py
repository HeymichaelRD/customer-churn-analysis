"""Validación de los datos de un cliente que llegan a POST /predict.

Aplica el contrato API → Web del README ("Contratos entre equipos"):
los 12 campos que usa el modelo de churn (models/churn_model_info.json,
"input_columns"), con sus nombres y valores originales en inglés, más las
reglas de coherencia entre campos.

Dos de los campos no están en el dataset: los calcula la página web antes
de enviar el cliente (ver src/modeling/README_modeling.md):
- SecuritySupportCount: cuántos "Yes" hay entre OnlineSecurity, OnlineBackup,
  DeviceProtection y TechSupport (0 a 4).
- StreamingServicesCount: cuántos "Yes" hay entre StreamingTV y StreamingMovies (0 a 2).

Si algo no cumple, se lanza ValidationError con un mensaje en español y el
nombre del campo, para que la página web pueda marcarlo en el formulario.
"""

import math

YES_NO = ["Yes", "No"]

# Los conteos de servicios: sin internet, no hay ninguno.
SERVICE_COUNTS = ["SecuritySupportCount", "StreamingServicesCount"]

# Los 12 campos, en el orden de "input_columns" de churn_model_info.json.
# - "choice": solo se acepta uno de los valores de la lista.
# - "integer" / "number": número; "min" es el mínimo permitido,
#   "exclusive_min" indica que el mínimo no está incluido (mayor que) y
#   "max" (opcional) es el máximo permitido.
FIELD_SPECS = {
    "gender": {"type": "choice", "values": ["Female", "Male"]},
    "SeniorCitizen": {"type": "choice", "values": [0, 1]},
    "Partner": {"type": "choice", "values": YES_NO},
    "Dependents": {"type": "choice", "values": YES_NO},
    "tenure": {"type": "integer", "min": 0},
    "InternetService": {"type": "choice", "values": ["DSL", "Fiber optic", "No"]},
    "Contract": {"type": "choice", "values": ["Month-to-month", "One year", "Two year"]},
    "PaperlessBilling": {"type": "choice", "values": YES_NO},
    "PaymentMethod": {
        "type": "choice",
        "values": [
            "Electronic check",
            "Mailed check",
            "Bank transfer (automatic)",
            "Credit card (automatic)",
        ],
    },
    "MonthlyCharges": {"type": "number", "min": 0, "exclusive_min": True},
    "SecuritySupportCount": {"type": "integer", "min": 0, "max": 4},
    "StreamingServicesCount": {"type": "integer", "min": 0, "max": 2},
}

FIELD_NAMES = list(FIELD_SPECS)


class ValidationError(Exception):
    """Datos que no cumplen el contrato. `field` es el campo con el problema, o None."""

    def __init__(self, message, field=None):
        super().__init__(message)
        self.message = message
        self.field = field


def _is_number(value):
    # En Python, True y False también son números (bool hereda de int): se excluyen.
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    # NaN e infinito llegan si alguien envía NaN o Infinity en el JSON: se excluyen.
    # Un entero gigante (por ejemplo 10**400) no cabe en un float: math.isfinite lanza
    # OverflowError. Se trata como número inválido para responder 400 y no 500.
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _check_field(name, value):
    spec = FIELD_SPECS[name]

    if spec["type"] == "choice":
        # Se compara también el tipo para que 1 y True, o "1" y 1, no se confundan.
        allowed = any(value == v and type(value) is type(v) for v in spec["values"])
        if not allowed:
            raise ValidationError(f"El campo {name} tiene un valor no permitido", name)
        return value

    if spec["type"] == "integer":
        if not _is_number(value) or value != int(value):
            raise ValidationError(f"El campo {name} debe ser un número entero", name)
        value = int(value)
    else:  # number
        if not _is_number(value):
            raise ValidationError(f"El campo {name} debe ser un número", name)
        value = float(value)

    minimum = spec["min"]
    if spec.get("exclusive_min") and value <= minimum:
        raise ValidationError(f"El campo {name} debe ser mayor que {minimum}", name)
    if value < minimum:
        raise ValidationError(f"El campo {name} debe ser {minimum} o más", name)
    if "max" in spec and value > spec["max"]:
        raise ValidationError(f"El campo {name} debe ser {spec['max']} o menos", name)
    return value


def _check_coherence(customer):
    # Los servicios que cuentan SecuritySupportCount y StreamingServicesCount son de internet:
    # sin internet, los dos conteos son 0 (en el dataset dicen "No internet service").
    if customer["InternetService"] == "No":
        for name in SERVICE_COUNTS:
            if customer[name] != 0:
                raise ValidationError(f'Si InternetService es "No", {name} debe ser 0', name)


def validate_customer(payload):
    """Revisa un cliente y lo devuelve listo para el modelo (los 12 campos, en orden).

    Lanza ValidationError en el primer problema que encuentra.
    """
    if not isinstance(payload, dict):
        raise ValidationError("Los datos del cliente deben enviarse como un objeto JSON")

    for name in FIELD_NAMES:
        if name not in payload:
            raise ValidationError(f"Falta el campo {name}", name)

    unknown = [key for key in payload if key not in FIELD_SPECS]
    if unknown:
        raise ValidationError(f"El campo {unknown[0]} no es parte del contrato", unknown[0])

    customer = {name: _check_field(name, payload[name]) for name in FIELD_NAMES}
    _check_coherence(customer)
    return customer
