// =====================================================================
//  Textos en español para los campos del dataset, y formato de números.
//  La API recibe y devuelve los valores ORIGINALES en inglés (ver el
//  contrato API → Web en el README); la página le muestra al usuario
//  estos textos. Si falta un texto, pídeselo a Michael.
//
//  Uso en tu página:
//    import { FIELDS, valueLabel, formatPercent } from "./labels.js";
//    valueLabel("Contract", "Month-to-month")  → "Mes a mes"
//    formatPercent(0.265)                       → "26.5%"
// =====================================================================

const YES_NO = [
  { value: "Yes", label: "Sí" },
  { value: "No", label: "No" },
];

// Servicios que solo existen si el cliente tiene internet.
const INTERNET_ADDON = [...YES_NO, { value: "No internet service", label: "Sin servicio de internet" }];

/**
 * Los 19 campos que recibe POST /predict.
 * - type "choice": se elige una opción; `value` es lo que se envía a la API.
 * - type "integer" / "number": se escribe un número; `min` es el mínimo permitido.
 */
export const FIELDS = {
  gender: {
    label: "Género",
    type: "choice",
    options: [
      { value: "Female", label: "Femenino" },
      { value: "Male", label: "Masculino" },
    ],
  },
  SeniorCitizen: {
    label: "Adulto mayor (65 años o más)",
    type: "choice",
    // Ojo: este campo se envía como número (1 o 0), no como texto.
    options: [
      { value: 1, label: "Sí" },
      { value: 0, label: "No" },
    ],
  },
  Partner: { label: "Tiene pareja", type: "choice", options: YES_NO },
  Dependents: { label: "Tiene dependientes", type: "choice", options: YES_NO },
  tenure: {
    label: "Antigüedad",
    type: "integer",
    min: 0,
    unit: "meses",
    hint: "Meses que lleva como cliente.",
  },
  PhoneService: { label: "Servicio telefónico", type: "choice", options: YES_NO },
  MultipleLines: {
    label: "Líneas múltiples",
    type: "choice",
    options: [...YES_NO, { value: "No phone service", label: "Sin servicio telefónico" }],
  },
  InternetService: {
    label: "Servicio de internet",
    type: "choice",
    options: [
      { value: "DSL", label: "DSL" },
      { value: "Fiber optic", label: "Fibra óptica" },
      { value: "No", label: "Sin internet" },
    ],
  },
  OnlineSecurity: { label: "Seguridad en línea", type: "choice", options: INTERNET_ADDON },
  OnlineBackup: { label: "Respaldo en línea", type: "choice", options: INTERNET_ADDON },
  DeviceProtection: { label: "Protección de dispositivos", type: "choice", options: INTERNET_ADDON },
  TechSupport: { label: "Soporte técnico", type: "choice", options: INTERNET_ADDON },
  StreamingTV: { label: "TV por streaming", type: "choice", options: INTERNET_ADDON },
  StreamingMovies: { label: "Películas por streaming", type: "choice", options: INTERNET_ADDON },
  Contract: {
    label: "Tipo de contrato",
    type: "choice",
    options: [
      { value: "Month-to-month", label: "Mes a mes" },
      { value: "One year", label: "Un año" },
      { value: "Two year", label: "Dos años" },
    ],
  },
  PaperlessBilling: { label: "Factura electrónica (sin papel)", type: "choice", options: YES_NO },
  PaymentMethod: {
    label: "Método de pago",
    type: "choice",
    options: [
      { value: "Electronic check", label: "Cheque electrónico" },
      { value: "Mailed check", label: "Cheque por correo" },
      { value: "Bank transfer (automatic)", label: "Transferencia bancaria (automática)" },
      { value: "Credit card (automatic)", label: "Tarjeta de crédito (automática)" },
    ],
  },
  MonthlyCharges: {
    label: "Cargo mensual",
    type: "number",
    min: 0.01,
    unit: "US$",
    hint: "Lo que paga cada mes.",
  },
  TotalCharges: {
    label: "Cargo total",
    type: "number",
    min: 0,
    unit: "US$",
    hint: "Todo lo facturado desde que es cliente.",
  },
};

/** Orden y grupos de los campos en el formulario. */
export const FIELD_GROUPS = [
  {
    id: "profile",
    label: "Perfil del cliente",
    fields: ["gender", "SeniorCitizen", "Partner", "Dependents"],
  },
  {
    id: "services",
    label: "Servicios contratados",
    fields: [
      "PhoneService",
      "MultipleLines",
      "InternetService",
      "OnlineSecurity",
      "OnlineBackup",
      "DeviceProtection",
      "TechSupport",
      "StreamingTV",
      "StreamingMovies",
    ],
  },
  {
    id: "account",
    label: "Cuenta y facturación",
    fields: ["tenure", "Contract", "PaperlessBilling", "PaymentMethod", "MonthlyCharges", "TotalCharges"],
  },
];

/** Textos de los niveles de riesgo que devuelve la API en "risk_level". */
export const RISK_LEVELS = {
  low: "Riesgo bajo",
  medium: "Riesgo medio",
  high: "Riesgo alto",
};

/** Nombre en español de un campo: fieldLabel("tenure") → "Antigüedad" */
export function fieldLabel(field) {
  return FIELDS[field]?.label ?? field;
}

/** Texto en español de un valor: valueLabel("Contract", "Two year") → "Dos años" */
export function valueLabel(field, value) {
  const option = FIELDS[field]?.options?.find((item) => String(item.value) === String(value));
  return option ? option.label : String(value);
}

// --- Formato de números (estilo de República Dominicana) ----------------
const LOCALE = "es-DO";
const percentFormat = new Intl.NumberFormat(LOCALE, { style: "percent", maximumFractionDigits: 1 });
const moneyFormat = new Intl.NumberFormat(LOCALE, { style: "currency", currency: "USD" });
const numberFormat = new Intl.NumberFormat(LOCALE);

/** formatPercent(0.265) → "26.5%" */
export const formatPercent = (value) => percentFormat.format(value);

/** formatMoney(139130.85) → "US$139,130.85" */
export const formatMoney = (value) => moneyFormat.format(value);

/** formatNumber(7043) → "7,043" */
export const formatNumber = (value) => numberFormat.format(value);
