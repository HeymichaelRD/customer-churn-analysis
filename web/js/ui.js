// =====================================================================
//  Componentes de la interfaz que comparten las páginas. Salen del
//  prototipo del diseño, y sus estilos están en css/base.css.
//  - h() e icon(): crean elementos HTML e íconos.
//  - mountRing(): el anillo con la probabilidad de abandono.
//  - setBadge(): la etiqueta "Riesgo alto", "Riesgo medio" o "Riesgo bajo".
//  - makeSeg(): el control segmentado, como en iOS.
//  - toast(): un mensaje flotante abajo, con un botón opcional ("Deshacer").
//  - bindTip(): el globo de ayuda que aparece al pasar por un gráfico.
//  - saveFile(): descarga un texto como archivo (por ejemplo, un CSV).
//
//  Uso en tu página:
//    import { mountRing, setBadge } from "./ui.js";
//    const ring = mountRing(document.getElementById("r-ring"), "probabilidad de abandono");
//    ring.set(result.probability, result.risk_level);
//    setBadge(document.getElementById("r-badge"), result.risk_level);
//  Si necesitas cambiar algo de este archivo, pídeselo a Michael.
// =====================================================================

import { RISK_LEVELS, formatPercent } from "./labels.js";

const SVG_NS = "http://www.w3.org/2000/svg";

// Archivo con los íconos. La ruta es relativa a la página: todas están en web/.
const ICONS_URL = "img/icons.svg";

/** El primer elemento que coincide con el selector CSS: $("#result") */
export const $ = (selector, root = document) => root.querySelector(selector);

/** Todos los elementos que coinciden, en una lista: $$(".chip") */
export const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

/** true si la persona pidió en su sistema que haya menos animaciones. */
export const prefersReducedMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;

/**
 * Crea un elemento HTML con sus atributos y su contenido.
 *   h("p", { class: "muted", text: "Hola" })                    → <p class="muted">Hola</p>
 *   h("button", { type: "button", onclick: probar }, "Probar")  → botón que llama a probar()
 * "text" pone el texto de forma segura: nunca se interpreta como HTML.
 */
export function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value == null || value === false) continue;
    if (key === "class") el.className = value;
    else if (key === "text") el.textContent = value;
    else if (key === "style") el.style.cssText = value;
    else if (key.startsWith("on") && typeof value === "function") el.addEventListener(key.slice(2), value);
    else el.setAttribute(key, value === true ? "" : value);
  }
  for (const child of children.flat()) {
    if (child != null && child !== false) el.append(child);
  }
  return el;
}

/** Un ícono de img/icons.svg: icon("check") */
export function icon(name, className = "ico") {
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("class", className);
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  const use = document.createElementNS(SVG_NS, "use");
  use.setAttribute("href", `${ICONS_URL}#i-${name}`);
  svg.append(use);
  return svg;
}

/**
 * Anima un número de "from" a "to" en "ms" milisegundos y llama a fn con cada valor.
 * Devuelve una función que detiene la animación.
 */
export function tween(from, to, ms, fn) {
  if (prefersReducedMotion || ms <= 0 || from === to) {
    fn(to);
    return () => {};
  }
  const start = performance.now();
  let frame;
  const step = (now) => {
    const progress = Math.min(1, (now - start) / ms);
    fn(from + (to - from) * (1 - Math.pow(1 - progress, 3))); // empieza rápido y frena al final
    if (progress < 1) frame = requestAnimationFrame(step);
  };
  frame = requestAnimationFrame(step);
  return () => cancelAnimationFrame(frame);
}

// --- Riesgo ------------------------------------------------------------

/** Ícono de cada nivel de riesgo. */
export const RISK_ICONS = { low: "check", medium: "alert", high: "warn" };

/** Pinta la etiqueta de riesgo en un elemento con class="badge": setBadge(el, "high") */
export function setBadge(el, level) {
  el.dataset.risk = level;
  el.replaceChildren(icon(RISK_ICONS[level]), document.createTextNode(RISK_LEVELS[level]));
}

// Medidas del anillo, dentro de un dibujo de 220 × 220
const RING_RADIUS = 96;
const RING_LENGTH = 2 * Math.PI * RING_RADIUS;

/**
 * Dibuja el anillo de probabilidad dentro de "box", un <div class="ring-box">.
 * Tiene marcas en 30% y 60%, donde cambia el nivel de riesgo.
 *   const ring = mountRing(box, "probabilidad de abandono");
 *   ring.set(0.79, "high");   // 79%, riesgo alto
 * Para cambiar el tamaño: <div class="ring-box" style="--ring: 150px">
 */
export function mountRing(box, caption = "") {
  const tick = (fraction) => {
    const angle = fraction * 2 * Math.PI;
    const point = (r) => `${(110 + r * Math.cos(angle)).toFixed(2)} ${(110 + r * Math.sin(angle)).toFixed(2)}`;
    return `<path class="ring-tick" d="M ${point(84)} L ${point(108)}"/>`;
  };
  const length = RING_LENGTH.toFixed(2);
  box.innerHTML =
    `<svg viewBox="0 0 220 220" aria-hidden="true">` +
    `<circle class="ring-track" cx="110" cy="110" r="${RING_RADIUS}" stroke-width="18"/>` +
    `<circle class="ring-bar" cx="110" cy="110" r="${RING_RADIUS}" stroke-width="18" ` +
    `stroke-dasharray="${length}" stroke-dashoffset="${length}"/>` +
    `${tick(0.3)}${tick(0.6)}</svg>`;

  const value = h("span", { class: "rv", text: "0" });
  box.append(
    h(
      "div",
      { class: "ring-center" },
      h("span", { class: "ring-value" }, value, h("sup", { text: "%" })),
      caption ? h("span", { class: "ring-cap", text: caption }) : null,
    ),
  );
  box.setAttribute("role", "img");

  const bar = box.querySelector(".ring-bar");
  let shown = 0;
  let stop = () => {};
  return {
    /** probability: de 0 a 1. level: "low", "medium" o "high". */
    set(probability, level) {
      box.dataset.risk = level;
      box.setAttribute("aria-label", `Probabilidad de abandono: ${formatPercent(probability, 0)}`);
      requestAnimationFrame(() => {
        bar.style.strokeDashoffset = (RING_LENGTH * (1 - Math.max(0.004, probability))).toFixed(2);
      });
      stop();
      stop = tween(shown, Math.round(probability * 100), 700, (v) => {
        shown = v;
        value.textContent = String(Math.round(v));
      });
    },
  };
}

// --- Controles -----------------------------------------------------------

/**
 * Control segmentado (como en iOS), hecho con botones de radio: funciona con el teclado.
 *   const contract = makeSeg({
 *     name: "contract",
 *     label: "Contrato",                    // o labelledBy: "id-del-título"
 *     options: FIELDS.Contract.options,     // [{ value, label }, ...]
 *     value: "Month-to-month",
 *     onChange: (value) => { ... },
 *   });
 *   row.append(contract.el);
 *   contract.set("Two year");               // marca otra opción, sin llamar a onChange
 *   contract.relabel(["Mes a mes", "1 año", "2 años"]);   // cambia los textos
 */
export function makeSeg({ name, options, value, label, labelledBy, onChange }) {
  const seg = h("div", {
    class: "seg",
    role: "radiogroup",
    "aria-label": label,
    "aria-labelledby": labelledBy,
    style: `--n: ${options.length}`,
  });
  seg.append(h("span", { class: "seg-thumb", "aria-hidden": "true" }));

  const inputs = options.map((option, i) => {
    const id = `${name}-${i}`;
    const input = h("input", { type: "radio", name, id, value: String(option.value) });
    input.addEventListener("change", () => {
      if (!input.checked) return;
      seg.style.setProperty("--i", i);
      onChange?.(option.value);
    });
    seg.append(input, h("label", { for: id, text: option.label }));
    return input;
  });

  const control = {
    el: seg,
    set(newValue) {
      const i = options.findIndex((option) => String(option.value) === String(newValue));
      if (i < 0) return;
      inputs[i].checked = true;
      seg.style.setProperty("--i", i);
    },
    relabel(labels) {
      seg.querySelectorAll("label").forEach((el, i) => {
        el.textContent = labels[i];
      });
    },
  };
  control.set(value);
  return control;
}

// --- Mensaje flotante ----------------------------------------------------

// Se crea una sola vez, al cargar la página, para que los lectores de
// pantalla lean cada mensaje nuevo.
const toastEl = h("div", { class: "toast", role: "status", "aria-live": "polite" });
document.body.append(toastEl);
let toastTimer;

/**
 * Muestra un mensaje flotante abajo de la pantalla durante unos segundos.
 *   toast("Listo: 7,043 clientes analizados.");
 *   toast("Contrato cambiado a un año.", { label: "Deshacer", fn: undo });
 */
export function toast(message, action) {
  toastEl.replaceChildren(h("span", { text: message }));
  if (action) {
    const onclick = () => {
      action.fn();
      toastEl.classList.remove("on");
    };
    toastEl.append(h("button", { type: "button", text: action.label, onclick }));
  }
  toastEl.classList.add("on");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toastEl.classList.remove("on"), action ? 6000 : 4200);
}

// --- Globo de ayuda de los gráficos ----------------------------------------

let tipEl = null; // se crea la primera vez que hace falta

function showTip(x, y, rows) {
  if (!tipEl) {
    tipEl = h("div", { class: "tooltip", role: "tooltip" });
    document.body.append(tipEl);
  }
  tipEl.replaceChildren(...rows);
  tipEl.classList.add("on");
  // Al lado del puntero, sin salirse de la pantalla
  const box = tipEl.getBoundingClientRect();
  const left = Math.min(window.innerWidth - box.width - 12, x + 14);
  const top = y + box.height + 20 > window.innerHeight ? y - box.height - 12 : y + 16;
  tipEl.style.left = `${Math.max(12, left)}px`;
  tipEl.style.top = `${Math.max(12, top)}px`;
}

/** Esconde el globo de ayuda. */
export function hideTip() {
  tipEl?.classList.remove("on");
}

/**
 * Muestra un globo de ayuda al pasar el puntero (o el foco del teclado) por "el".
 * "build" es una función que devuelve el contenido:
 *   bindTip(bar, () => [h("b", { text: "42.7%" }), h("span", { text: "Mes a mes" })]);
 */
export function bindTip(el, build) {
  el.addEventListener("pointermove", (event) => showTip(event.clientX, event.clientY, build()));
  el.addEventListener("pointerleave", hideTip);
  el.addEventListener("focus", () => {
    const box = el.getBoundingClientRect();
    showTip(box.left + box.width / 2, box.top + box.height / 2, build());
  });
  el.addEventListener("blur", hideTip);
}

// --- Archivos ------------------------------------------------------------

/** Descarga un texto como archivo: saveFile("resultados_churn.csv", csv) */
export function saveFile(name, text, type = "text/csv;charset=utf-8") {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const link = h("a", { href: url, download: name });
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
