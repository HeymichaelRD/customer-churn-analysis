// =====================================================================
//  Código que comparten todas las páginas:
//  - el estado de la API en el encabezado (conectada / desconectada);
//  - el aviso de "modo demostración" mientras la API use el modelo
//    provisional en lugar del modelo real del equipo de Modelos.
//  Cada página lo carga con: <script type="module" src="js/common.js">
// =====================================================================

import { getHealth } from "./api.js";

function setApiStatus(state, text) {
  const status = document.getElementById("api-status");
  if (!status) return;
  status.dataset.state = state;
  status.querySelector(".status-text").textContent = text;
}

async function checkApi() {
  const demoBanner = document.getElementById("demo-banner");

  try {
    const health = await getHealth();
    const isDemo = health.model_version === "demo";
    setApiStatus("online", isDemo ? "API conectada · modelo demo" : "API conectada");
    if (demoBanner) demoBanner.hidden = !isDemo;
  } catch (error) {
    setApiStatus("offline", "API desconectada");
    console.warn(error.message);
  }
}

checkApi();
