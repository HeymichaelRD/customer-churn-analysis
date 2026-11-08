// =====================================================================
//  Todas las llamadas a la API pasan por este archivo.
//  Así, si cambia una ruta o el formato de los errores, se corrige en un
//  solo lugar. El contrato está en el README ("Contratos entre equipos").
//
//  Uso en tu página:
//    import { predict, ApiError } from "./api.js";
//    try {
//      const result = await predict(customer);
//    } catch (error) {
//      // error.message ya viene en español, listo para mostrarlo.
//      // error.field indica el campo con problema (si la API lo dice).
//    }
// =====================================================================

import { API_BASE_URL, REQUEST_TIMEOUT_MS } from "./config.js";

/** Error de la API, con un mensaje en español listo para mostrar al usuario. */
export class ApiError extends Error {
  constructor(message, { status = 0, field = null } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status; // 0 = no se pudo conectar con la API
    this.field = field; // campo del formulario con el problema, o null
  }
}

/** Hace la petición, espera la respuesta y la convierte de JSON a objeto. */
async function request(path, { method = "GET", body, timeoutMs = REQUEST_TIMEOUT_MS } = {}) {
  const options = { method, signal: AbortSignal.timeout(timeoutMs) };

  if (body instanceof FormData) {
    options.body = body; // archivos: el navegador pone el Content-Type solo
  } else if (body !== undefined) {
    options.headers = { "Content-Type": "application/json" };
    options.body = JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, options);
  } catch (error) {
    const message =
      error.name === "TimeoutError"
        ? "La API tardó demasiado en responder. Inténtalo de nuevo."
        : "No se pudo conectar con la API. ¿Está encendida? (flask --app src/api/app run)";
    throw new ApiError(message);
  }

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(data?.error ?? `La API respondió con un error (${response.status}).`, {
      status: response.status,
      field: data?.field ?? null,
    });
  }
  return data;
}

// --- Fase 1 ------------------------------------------------------------

/** GET /health → { status, model_version } */
export const getHealth = () => request("/health", { timeoutMs: 5000 });

/** POST /predict → { churn, probability, risk_level, model_version } */
export const predict = (customer) => request("/predict", { method: "POST", body: customer });

// --- Fase 2 (todavía no existen en la API) -----------------------------

/** POST /recommendations → { probability, actions: [...] } */
export const getRecommendations = (customer) =>
  request("/recommendations", { method: "POST", body: customer });

/** GET /samples → clientes reales de ejemplo */
export const getSamples = () => request("/samples");

/** GET /samples/random → un cliente real al azar */
export const getRandomSample = () => request("/samples/random");

/** GET /insights → KPIs y churn por segmento */
export const getInsights = () => request("/insights");

// --- Fase 3 (todavía no existen en la API) -----------------------------

/** GET /model-info → algoritmo y métricas del modelo */
export const getModelInfo = () => request("/model-info");

/** POST /predict/batch → el archivo CSV va en el campo "file" */
export function predictBatch(file) {
  const formData = new FormData();
  formData.append("file", file);
  return request("/predict/batch", { method: "POST", body: formData, timeoutMs: 120000 });
}
