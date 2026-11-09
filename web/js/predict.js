// =====================================================================
//  Página Predecir: el formulario del cliente y el resultado en vivo.
//  Cada vez que cambia un dato, la página le pregunta a la API
//  (POST /predict) y actualiza el resultado. Así también sirve de
//  simulador: cambia el contrato o la forma de pago y mira qué pasa.
//
//  Sale del prototipo del diseño. La diferencia: en el prototipo el modelo
//  corría en el navegador; aquí la probabilidad siempre la calcula la API.
//
//  Fase 2 (cuando existan en la API): clientes de ejemplo (GET /samples),
//  si el modelo acertó y las recomendaciones (POST /recommendations).
// =====================================================================

import { predict } from "./api.js";
import { FIELDS, FIELD_GROUPS, formatMoney, formatPercent, valueLabel } from "./labels.js";
import { $, h, icon, makeSeg, mountRing, prefersReducedMotion, setBadge } from "./ui.js";

// --- Datos fijos -------------------------------------------------------

// Los 19 campos que se envían a la API, en el orden del formulario.
const CUSTOMER_FIELDS = FIELD_GROUPS.flatMap((group) => group.fields);

// Servicios que solo existen si el cliente tiene internet.
const INTERNET_ADDONS = [
  "OnlineSecurity",
  "OnlineBackup",
  "DeviceProtection",
  "TechSupport",
  "StreamingTV",
  "StreamingMovies",
];

// Qué control usa cada campo en el formulario.
const CONTROL_TYPES = {
  gender: "segmented",
  SeniorCitizen: "switch",
  Partner: "switch",
  Dependents: "switch",
  PhoneService: "switch",
  MultipleLines: "switch",
  InternetService: "segmented",
  OnlineSecurity: "switch",
  OnlineBackup: "switch",
  DeviceProtection: "switch",
  TechSupport: "switch",
  StreamingTV: "switch",
  StreamingMovies: "switch",
  tenure: "slider",
  Contract: "segmented",
  PaperlessBilling: "switch",
  PaymentMethod: "select",
  MonthlyCharges: "slider",
  TotalCharges: "total",
};

// Mínimo, máximo y paso de los deslizadores: los rangos del dataset.
// En el campo de número se puede escribir un valor fuera del rango.
const SLIDERS = {
  tenure: { min: 0, max: 72, step: 1 },
  MonthlyCharges: { min: 18, max: 120, step: 0.05 },
};

// Cliente con el que empieza la página: uno real del dataset, de alto riesgo.
// En la Fase 2 los clientes de ejemplo llegarán de GET /samples.
const EXAMPLE = {
  id: "9305-CDSKC",
  label: "Cliente de ejemplo",
  customer: {
    gender: "Female",
    SeniorCitizen: 0,
    Partner: "No",
    Dependents: "No",
    PhoneService: "Yes",
    MultipleLines: "Yes",
    InternetService: "Fiber optic",
    OnlineSecurity: "No",
    OnlineBackup: "No",
    DeviceProtection: "Yes",
    TechSupport: "No",
    StreamingTV: "Yes",
    StreamingMovies: "Yes",
    tenure: 8,
    Contract: "Month-to-month",
    PaperlessBilling: "Yes",
    PaymentMethod: "Electronic check",
    MonthlyCharges: 99.65,
    TotalCharges: 820.5,
  },
};

// La API rechaza un cliente sin teléfono y sin internet (en el dataset no hay
// ninguno así). Por eso el formulario no deja quitar el último de los dos.
const NEEDS_A_SERVICE = "Necesita teléfono o internet";

/** Redondea a 2 decimales: round2(3.14159) → 3.14 */
const round2 = (value) => Math.round(value * 100) / 100;

// --- Estado de la página -----------------------------------------------

let customer = {}; // los 19 datos que se envían a la API
let baseline = null; // el cliente tal como se cargó y su probabilidad, para el "antes → ahora"
let totalIsAuto = false; // true: el cargo total se calcula solo (antigüedad × cargo mensual)
let fieldError = null; // { field, message }: el dato que rechazó la API, hasta la próxima respuesta buena
const controls = {}; // el control de cada campo, por ejemplo controls.tenure.set(12)

const form = $("#predict-form");
const result = $("#result");
const ring = mountRing($("#r-ring"), "probabilidad de abandono");

// --- Formulario ----------------------------------------------------------
// Cada campo es una fila con su nombre, una nota debajo (o el error que
// devuelva la API) y su control. controls[campo].set(valor) lo actualiza.

/** Nombre del campo con su nota debajo. */
function rowLabel(tag, attrs, def, note) {
  return h(tag, { class: "row-label", ...attrs }, h("span", { text: def.label }), note);
}

/** Interruptor: Sí o No (o 1 y 0 en SeniorCitizen). */
function buildSwitch(field, def, id, note) {
  const [on, off] = field === "SeniorCitizen" ? [1, 0] : ["Yes", "No"];
  const input = h("input", { type: "checkbox", class: "switch", id, role: "switch" });
  input.addEventListener("change", () => setField(field, input.checked ? on : off));
  const row = h("div", { class: "row", "data-field": field }, rowLabel("label", { for: id }, def, note), input);

  controls[field] = {
    row,
    inputs: [input],
    set(value) {
      // "Sin servicio telefónico" o "Sin servicio de internet": apagado y bloqueado.
      const special = value === "No phone service" || value === "No internet service";
      // Sin internet, el teléfono no se puede quitar.
      const locked = field === "PhoneService" && customer.InternetService === "No";
      input.checked = value === on;
      input.disabled = special || locked;
      row.classList.toggle("is-off", special);
      note.textContent = special ? valueLabel(field, value) : locked ? NEEDS_A_SERVICE : (def.hint ?? "");
    },
  };
  return row;
}

/** Control segmentado: una opción de varias (género, internet, contrato). */
function buildSegmented(field, def, id, note) {
  const labelId = `${id}-label`;
  const seg = makeSeg({
    name: id,
    options: def.options,
    value: def.options[0].value,
    labelledBy: labelId,
    onChange: (value) => setField(field, value),
  });
  // Sin teléfono, la opción "Sin internet" se bloquea.
  const noInternet = field === "InternetService" ? seg.el.querySelector('input[value="No"]') : null;
  const row = h(
    "div",
    { class: "row row-seg", "data-field": field },
    rowLabel("div", { id: labelId }, def, note),
    seg.el,
  );

  controls[field] = {
    row,
    inputs: [...seg.el.querySelectorAll("input")],
    set(value) {
      seg.set(value);
      const locked = noInternet !== null && customer.PhoneService === "No";
      if (noInternet) noInternet.disabled = locked;
      note.textContent = locked ? NEEDS_A_SERVICE : (def.hint ?? "");
    },
  };
  return row;
}

/** Lista desplegable (método de pago). */
function buildSelect(field, def, id, note) {
  const select = h(
    "select",
    { id },
    def.options.map((option) => h("option", { value: option.value, text: option.label })),
  );
  select.addEventListener("change", () => setField(field, select.value));
  const row = h(
    "div",
    { class: "row row-select", "data-field": field },
    rowLabel("label", { for: id }, def, note),
    h("span", { class: "select-wrap" }, select, icon("chevdown")),
  );

  controls[field] = {
    row,
    inputs: [select],
    set(value) {
      select.value = value;
      note.textContent = def.hint ?? "";
    },
  };
  return row;
}

/** Deslizador con un campo de número al lado (antigüedad y cargo mensual). */
function buildSlider(field, def, id, note) {
  const range = SLIDERS[field];
  const isInteger = def.type === "integer";
  const toValue = (number) => (isInteger ? Math.round(number) : round2(number));

  const slider = h("input", { type: "range", class: "range", id, min: range.min, max: range.max, step: range.step });
  const number = h("input", {
    type: "number",
    class: "field-num",
    id: `${id}-num`,
    min: def.min,
    step: isInteger ? 1 : 0.01,
    inputmode: isInteger ? "numeric" : "decimal",
    "aria-label": `${def.label} (${def.unit})`,
  });
  slider.addEventListener("input", () => setField(field, toValue(Number(slider.value))));
  number.addEventListener("input", () => {
    const value = Number(number.value);
    if (number.value !== "" && Number.isFinite(value) && value >= def.min) setField(field, toValue(value));
  });
  // Si quedó escrito un número que no vale, vuelve al último válido.
  number.addEventListener("blur", () => controls[field].set(customer[field]));

  const row = h(
    "div",
    { class: "row row-range", "data-field": field },
    rowLabel("label", { for: id }, def, note),
    h("span", { class: "num-wrap" }, isInteger ? null : def.unit, number, isInteger ? def.unit : null),
    slider,
  );

  controls[field] = {
    row,
    inputs: [slider, number],
    set(value) {
      slider.value = value;
      const clamped = Math.min(range.max, Math.max(range.min, value));
      slider.style.setProperty("--pct", `${((clamped - range.min) / (range.max - range.min)) * 100}%`);
      if (document.activeElement !== number) number.value = isInteger ? String(value) : value.toFixed(2);
      note.textContent = def.hint ?? "";
    },
  };
  return row;
}

/** Cargo total: un número, con un botón para calcularlo a partir de los otros datos. */
function buildTotal(field, def, id, note) {
  const number = h("input", {
    type: "number",
    class: "field-num field-num-wide",
    id,
    min: def.min,
    step: 0.01,
    inputmode: "decimal",
  });
  const calculate = h("button", { type: "button", class: "text-btn", text: "Calcular" });
  number.addEventListener("input", () => {
    const value = Number(number.value);
    if (number.value !== "" && Number.isFinite(value) && value >= def.min) {
      totalIsAuto = false;
      setField(field, round2(value));
    }
  });
  number.addEventListener("blur", () => controls[field].set(customer[field]));
  calculate.addEventListener("click", () => {
    totalIsAuto = true;
    setField(field, round2(customer.tenure * customer.MonthlyCharges));
  });

  const row = h(
    "div",
    { class: "row", "data-field": field },
    rowLabel("label", { for: id }, def, note),
    h("span", { class: "row-tool" }, calculate, h("span", { class: "num-wrap" }, def.unit, number)),
  );

  controls[field] = {
    row,
    inputs: [number],
    set(value) {
      if (document.activeElement !== number) number.value = value.toFixed(2);
      note.textContent = totalIsAuto ? "Antigüedad × cargo mensual (aproximado)." : def.hint;
      calculate.hidden = totalIsAuto;
    },
  };
  return row;
}

const BUILDERS = {
  switch: buildSwitch,
  segmented: buildSegmented,
  select: buildSelect,
  slider: buildSlider,
  total: buildTotal,
};

function buildRow(field) {
  const note = h("small", { class: "row-note" });
  return BUILDERS[CONTROL_TYPES[field]](field, FIELDS[field], `f-${field}`, note);
}

// Los 3 grupos del formulario: perfil, servicios y cuenta
for (const group of FIELD_GROUPS) {
  const titleId = `g-${group.id}`;
  form.append(
    h(
      "div",
      { class: "group", role: "group", "aria-labelledby": titleId },
      h("p", { class: "group-title", id: titleId, text: group.label }),
      h("div", { class: "group-list" }, group.fields.map(buildRow)),
    ),
  );
}
form.addEventListener("submit", (event) => event.preventDefault());

/** Pone en cada control el valor que tiene el cliente. */
function writeAll() {
  for (const field of CUSTOMER_FIELDS) controls[field].set(customer[field]);
  // El mensaje de error de la API se queda hasta que llegue una respuesta buena.
  if (fieldError) paintFieldError();
}

/** Cambia un dato del cliente, aplica las reglas de coherencia y pide el resultado. */
function setField(field, value) {
  customer[field] = value;

  // Sin teléfono no hay líneas múltiples. Al volver a tenerlo, empiezan en "No".
  if (field === "PhoneService") {
    if (value === "No") customer.MultipleLines = "No phone service";
    else if (customer.MultipleLines === "No phone service") customer.MultipleLines = "No";
  }

  // Sin internet no hay servicios de internet. Al volver a tenerlo, empiezan en "No".
  if (field === "InternetService") {
    for (const addon of INTERNET_ADDONS) {
      if (value === "No") customer[addon] = "No internet service";
      else if (customer[addon] === "No internet service") customer[addon] = "No";
    }
  }

  if (totalIsAuto && (field === "tenure" || field === "MonthlyCharges")) {
    customer.TotalCharges = round2(customer.tenure * customer.MonthlyCharges);
  }

  writeAll();
  scheduleUpdate();
}

/** Carga un cliente en el formulario. `info` dice de dónde viene: { id, label }. */
function loadCustomer(data, info) {
  customer = Object.fromEntries(CUSTOMER_FIELDS.map((field) => [field, data[field]]));
  baseline = { customer: { ...customer }, probability: null, info };
  totalIsAuto = false;
  writeAll();
  updateResult();
}

/** true si los datos son los mismos del cliente que se cargó. */
function isUnchanged(data) {
  return CUSTOMER_FIELDS.every((field) => data[field] === baseline.customer[field]);
}

// --- Resultado en vivo -----------------------------------------------------

let waitTimer = null; // espera corta: así no se pregunta a la API por cada pixel del deslizador
let latest = null; // la petición más reciente; las anteriores se cancelan

function scheduleUpdate() {
  clearTimeout(waitTimer);
  waitTimer = setTimeout(updateResult, 150);
}

async function updateResult() {
  latest?.abort();
  const request = new AbortController();
  latest = request;
  const sent = { ...customer };
  try {
    const answer = await predict(sent, { signal: request.signal });
    if (request === latest) showResult(sent, answer);
  } catch (error) {
    // Si ya hay una petición más nueva, esta respuesta no importa.
    if (request === latest) showError(sent, error);
  }
}

function showResult(sent, answer) {
  const { churn, probability, risk_level: level } = answer;
  const unchanged = isUnchanged(sent);
  if (unchanged && baseline.probability === null) baseline.probability = probability;

  clearErrors();
  ring.set(probability, level);
  const badge = $("#r-badge");
  setBadge(badge, level);
  badge.hidden = false;
  $("#r-verdict").replaceChildren(
    "El modelo predice que el cliente ",
    h("b", { text: churn ? "se va" : "se queda" }),
    ".",
  );

  // "Antes → ahora": cuando se cambió algún dato del cliente que se cargó
  const delta = $("#r-delta");
  delta.hidden = unchanged || baseline.probability === null;
  if (!delta.hidden) {
    delta.replaceChildren(
      `Antes ${formatPercent(baseline.probability, 0)} → ahora `,
      h("b", { text: formatPercent(probability, 0) }),
    );
  }
  $("#r-who").textContent = unchanged ? baseline.info.label : "Simulación";
  $("#r-id").textContent = unchanged ? baseline.info.id : `a partir de ${baseline.info.id}`;

  // Ingreso en riesgo: lo que paga cada mes × la probabilidad de que se vaya
  const monthly = sent.MonthlyCharges * probability;
  $("#r-month").replaceChildren(formatMoney(monthly), " ", h("small", { text: "/mes" }));
  $("#r-year").textContent = formatMoney(monthly * 12, 0);

  showPayload(sent, `Respuesta 200\n${JSON.stringify(answer, null, 2)}`);

  $("#mini-value").textContent = formatPercent(probability, 0);
  const miniBadge = $("#mini-badge");
  setBadge(miniBadge, level);
  miniBadge.hidden = false;
}

function showError(sent, error) {
  result.classList.add("is-stale");
  const live = $("#r-live");
  live.classList.add("is-off");
  live.textContent = error.status === 0 ? "Sin conexión" : "Con error";
  $("#r-error-text").textContent = error.message;
  // Si la API rechazó un dato, se corrige el dato; intentar de nuevo no sirve.
  $("#r-retry").hidden = error.status === 400;
  $("#r-error").hidden = false;
  clearFieldError();
  if (controls[error.field]) {
    fieldError = { field: error.field, message: error.message };
    paintFieldError();
  }

  const answerText = error.status
    ? `Respuesta ${error.status}\n${JSON.stringify({ error: error.message, field: error.field }, null, 2)}`
    : "Sin respuesta: la API no contestó.";
  showPayload(sent, answerText);
}

/** Marca en rojo el campo que rechazó la API y muestra el mensaje debajo. */
function paintFieldError() {
  const control = controls[fieldError.field];
  control.row.classList.add("has-error");
  control.inputs.forEach((input) => input.setAttribute("aria-invalid", "true"));
  control.row.querySelector(".row-note").textContent = fieldError.message;
}

/** Quita la marca del campo con error y le devuelve su nota normal. */
function clearFieldError() {
  if (!fieldError) return;
  const { field } = fieldError;
  fieldError = null;
  controls[field].row.classList.remove("has-error");
  controls[field].inputs.forEach((input) => input.removeAttribute("aria-invalid"));
  controls[field].set(customer[field]);
}

function clearErrors() {
  result.classList.remove("is-stale");
  const live = $("#r-live");
  live.classList.remove("is-off");
  live.textContent = "En vivo";
  $("#r-error").hidden = true;
  clearFieldError();
}

/** "Ver la petición a la API": lo que se envió y lo que respondió. */
function showPayload(sent, answerText) {
  $("#r-payload").textContent = `POST /predict\n${JSON.stringify(sent, null, 2)}\n\n${answerText}`;
}

$("#r-retry").addEventListener("click", updateResult);

// --- Barra flotante en el celular, cuando el resultado no se ve -------------

const mini = $("#mini-result");
mini.classList.add("on");
new IntersectionObserver(([entry]) => mini.classList.toggle("is-away", entry.isIntersecting), {
  threshold: 0.15,
}).observe(result);
$("#mini-go").addEventListener("click", () => {
  result.scrollIntoView({ behavior: prefersReducedMotion ? "auto" : "smooth", block: "start" });
});

// --- Al abrir la página ---------------------------------------------------------

loadCustomer(EXAMPLE.customer, { id: EXAMPLE.id, label: EXAMPLE.label });
