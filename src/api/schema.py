"""Validación de los datos de un cliente que llegan a POST /predict.

Aplica el contrato API → Web del README ("Contratos entre equipos"):
los 19 campos del dataset, con sus nombres y valores originales en inglés,
más las reglas de coherencia entre campos.

Si algo no cumple, se lanza ValidationError con un mensaje en español y el
nombre del campo, para que la página web pueda marcarlo en el formulario.
"""

import math

YES_NO = ["Yes", "No"]
INTERNET_ADDON = ["Yes", "No", "No internet service"]
INTERNET_ADDONS = [
    "OnlineSecurity",
    "OnlineBackup",
    "DeviceProtection",
    "TechSupport",
    "StreamingTV",
    "StreamingMovies",
]

# Los 19 campos, en el orden del dataset.
# - "choice": solo se acepta uno de los valores de la lista.
# - "integer" / "number": número; "min" es el mínimo permitido y
#   "exclusive_min" indica que el mínimo no está incluido (mayor que).
FIELD_SPECS = {
    "gender": {"type": "choice", "values": ["Female", "Male"]},
    "SeniorCitizen": {"type": "choice", "values": [0, 1]},
    "Partner": {"type": "choice", "values": YES_NO},
    "Dependents": {"type": "choice", "values": YES_NO},
    "tenure": {"type": "integer", "min": 0},
    "PhoneService": {"type": "choice", "values": YES_NO},
    "MultipleLines": {"type": "choice", "values": ["Yes", "No", "No phone service"]},
    "InternetService": {"type": "choice", "values": ["DSL", "Fiber optic", "No"]},
    **{name: {"type": "choice", "values": INTERNET_ADDON} for name in INTERNET_ADDONS},
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
    "TotalCharges": {"type": "number", "min": 0},
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
    # NaN e infinito llegan si alguien envía NaN o Infinity en el JSON: se excluyen.
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


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
    return value


def _check_coherence(customer):
    # Reglas del contrato: si no hay teléfono o internet, los servicios que dependen de ellos
    # deben decir "No phone service" o "No internet service".
    if customer["PhoneService"] == "No" and customer["MultipleLines"] != "No phone service":
        raise ValidationError(
            'Si PhoneService es "No", MultipleLines debe ser "No phone service"', "MultipleLines"
        )
    if customer["PhoneService"] == "Yes" and customer["MultipleLines"] == "No phone service":
        raise ValidationError(
            'Si PhoneService es "Yes", MultipleLines no puede ser "No phone service"', "MultipleLines"
        )
    for addon in INTERNET_ADDONS:
        if customer["InternetService"] == "No" and customer[addon] != "No internet service":
            raise ValidationError(
                f'Si InternetService es "No", {addon} debe ser "No internet service"', addon
            )
        if customer["InternetService"] != "No" and customer[addon] == "No internet service":
            raise ValidationError(
                f'Si el cliente tiene internet, {addon} no puede ser "No internet service"', addon
            )


def validate_customer(payload):
    """Revisa un cliente y lo devuelve listo para el modelo (los 19 campos, en orden).

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
