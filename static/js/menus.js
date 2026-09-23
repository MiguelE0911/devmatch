// Menús desplegables del shell (patrón [data-menu]).
// Global y por delegación: abre/cierra CUALQUIER [data-menu-toggle] de la página
// (topbar, cabecera de proyecto, vacantes...) sin depender de un script local.
// Convive con los handlers inline de las páginas de proyecto: sus listeners
// hacen stopPropagation() antes de llegar a document, así que el toggle se
// procesa una sola vez y no hay doble bind.
(function () {
    function cerrarTodos() {
        document.querySelectorAll("[data-menu]").forEach(function (contenedor) {
            var toggle = contenedor.querySelector("[data-menu-toggle]");
            var panel = contenedor.querySelector("[data-menu-panel]");
            if (toggle && panel) {
                panel.classList.add("hidden");
                toggle.setAttribute("aria-expanded", "false");
            }
        });
    }

    document.addEventListener("click", function (e) {
        var palanca = e.target.closest ? e.target.closest("[data-menu-toggle]") : null;
        if (palanca) {
            var contenedor = palanca.closest("[data-menu]");
            var panel = contenedor.querySelector("[data-menu-panel]");
            if (panel.classList.contains("hidden")) {
                cerrarTodos();
                panel.classList.remove("hidden");
                palanca.setAttribute("aria-expanded", "true");
            } else {
                panel.classList.add("hidden");
                palanca.setAttribute("aria-expanded", "false");
            }
            return;
        }

        var item = e.target.closest ? e.target.closest("[data-menu] [role='menuitem']") : null;
        if (item || !e.target.closest("[data-menu]")) {
            cerrarTodos();
        }
    });

    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape") {
            cerrarTodos();
        }
    });
})();