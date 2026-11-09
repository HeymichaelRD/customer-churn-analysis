// =====================================================================
//  Código que comparten todas las páginas:
//  - el estado de la API en la barra de navegación (conectada o no);
//  - el aviso de "Modo demostración" mientras la API use el modelo
//    provisional en lugar del modelo real del equipo de Modelos;
//  - el botón para cambiar entre modo claro y modo oscuro.
//  Cada página lo carga con: <script type="module" src="js/common.js">
// =====================================================================

import { getHealth } from "./api.js";
import { icon } from "./ui.js";

// --- Guardar preferencias en el navegador ------------------------------
// localStorage guarda para siempre; sessionStorage, hasta cerrar el
// navegador. Los dos pueden fallar (por ejemplo, en una ventana privada):
// en ese caso, la página funciona igual, solo que no recuerda nada.

function readSetting(key, { session = false } = {}) {
  try {
    return (session ? sessionStorage : localStorage).getItem(key);
  } catch {
    return null;
  }
}

function saveSetting(key, value, { session = false } = {}) {
  try {
    (session ? sessionStorage : localStorage).setItem(key, value);
  } catch {
    // No se pudo guardar: no pasa nada.
  }
}

// --- Estado de la API ---------------------------------------------------

function setApiStatus(state, text, hint) {
  const status = document.getElementById("api-status");
  if (!status) return;
  status.dataset.state = state; // "checking", "online" u "offline"
  status.title = hint;
  status.querySelector(".status-text").textContent = text;
}

async function checkApi() {
  try {
    const health = await getHealth();
    setApiStatus("online", "API conectada", `La API está encendida. Modelo: ${health.model_version}.`);
    showDemoRibbon(health.model_version === "demo");
  } catch (error) {
    setApiStatus("offline", "API desconectada", "Enciéndela con: flask --app src/api/app run");
    console.warn(error.message);
  }
}

// --- Aviso de "Modo demostración" ---------------------------------------
// Si el usuario lo cierra, no vuelve a salir hasta que cierre el navegador.

const RIBBON_CLOSED = "demo-ribbon-closed";

function showDemoRibbon(isDemo) {
  const ribbon = document.getElementById("demo-ribbon");
  if (!ribbon) return;
  ribbon.hidden = !isDemo || readSetting(RIBBON_CLOSED, { session: true }) === "yes";
}

document.getElementById("demo-ribbon-close")?.addEventListener("click", () => {
  document.getElementById("demo-ribbon").hidden = true;
  saveSetting(RIBBON_CLOSED, "yes", { session: true });
});

// --- Modo claro u oscuro --------------------------------------------------
// js/theme.js aplica el tema guardado al cargar la página; aquí se cambia.

const root = document.documentElement;
const systemDark = matchMedia("(prefers-color-scheme: dark)");
const themeButton = document.getElementById("theme-btn");

/** true si la página se está viendo en modo oscuro. */
function isDark() {
  return root.dataset.theme ? root.dataset.theme === "dark" : systemDark.matches;
}

function paintThemeButton() {
  if (!themeButton) return;
  const dark = isDark();
  themeButton.replaceChildren(icon(dark ? "sun" : "moon"));
  themeButton.setAttribute("aria-label", dark ? "Cambiar a modo claro" : "Cambiar a modo oscuro");
}

themeButton?.addEventListener("click", () => {
  const theme = isDark() ? "light" : "dark";
  root.dataset.theme = theme;
  saveSetting("theme", theme);
  paintThemeButton();
});
systemDark.addEventListener("change", paintThemeButton);

paintThemeButton();
checkApi();
