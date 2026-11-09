// =====================================================================
//  Modo claro u oscuro, ANTES de pintar la página.
//  Este archivo se carga en el <head>, sin type="module" y antes que los
//  estilos. Así la página aparece desde el principio con el tema que
//  eligió el usuario, sin parpadear. El botón que cambia el tema está en
//  js/common.js.
// =====================================================================

try {
  const savedTheme = localStorage.getItem("theme");
  if (savedTheme === "light" || savedTheme === "dark") {
    document.documentElement.dataset.theme = savedTheme;
  }
} catch {
  // Si el navegador no deja guardar datos (por ejemplo, en una ventana
  // privada), se usa el tema del sistema.
}
