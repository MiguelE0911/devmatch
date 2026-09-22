/* Panel de filtros del Home interno (feed). Contrato con core/_filters_panel.html:
   - 6 filas [data-filtro-toggle] con submenu [data-submenu] hermano.
   - Tipos: multiselect-search ([data-item-multi], [data-busqueda], [data-bandeja]),
     single-select-list ([data-item-single]) y stepper ([data-stepper-input],
     [data-stepper-up/down]).
   - El estado se guarda en inputs hidden del <form> (name habilidad/tecnologia/
     nivel/experiencia/estado_vacante/estado) y el formulario se auto-aplica
     (submit) al cambiar → el filtrado lo hace el servidor vía GET.
   - La topbar aporta [data-filters-toggle]; si no existe (páginas sin feed),
     el script se inhabilita solo. Vanilla JS — no usar librerías. */
(function () {
    var panel = document.querySelector("[data-panel-filtros]");
    var toggle = document.querySelector("[data-filters-toggle]");
    if (!panel || !toggle) return;

    var form = panel.querySelector("form");

    // ------------------------------------------------------------------ abrir/cerrar panel
    function posicionarPanel() {
        var rect = toggle.getBoundingClientRect();
        panel.style.top = rect.bottom + 10 + "px";
        panel.style.right = (window.innerWidth - rect.right) + "px";
    }

    function cerrarSubmenus() {
        panel.querySelectorAll("[data-submenu]").forEach(function (submenu) {
            submenu.classList.add("hidden");
        });
        panel.querySelectorAll("[data-chevron]").forEach(function (chevron) {
            chevron.classList.remove("rotate-180");
        });
    }

    function abrirPanel() {
        posicionarPanel();
        panel.classList.remove("hidden");
    }

    function cerrarPanel() {
        panel.classList.add("hidden");
        cerrarSubmenus();
    }

    function esAbierto() {
        return !panel.classList.contains("hidden");
    }

    toggle.addEventListener("click", function (e) {
        e.stopPropagation();
        if (esAbierto()) {
            cerrarPanel();
        } else {
            abrirPanel();
        }
    });

    document.addEventListener("click", function (e) {
        if (esAbierto() && !panel.contains(e.target) && !toggle.contains(e.target)) {
            cerrarPanel();
        }
    });

    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape") cerrarPanel();
    });

    // ------------------------------------------------------------------ submenús
    panel.querySelectorAll("[data-filtro-toggle]").forEach(function (boton) {
        var submenu = boton.parentElement.querySelector("[data-submenu]");
        if (!submenu) return;
        var chevron = boton.querySelector("[data-chevron]");

        boton.addEventListener("click", function (e) {
            e.stopPropagation();
            var abrir = submenu.classList.contains("hidden");
            cerrarSubmenus();
            if (abrir) {
                submenu.classList.remove("hidden");
                chevron.classList.add("rotate-180");
            }
        });
    });

    // ------------------------------------------------------------------ auto-aplicar
    function aplicar() {
        if (form) form.submit();
    }

    // ------------------------------------------------------------------ multiselect-search
    panel.querySelectorAll("[data-busqueda]").forEach(function (busqueda) {
        busqueda.addEventListener("input", function () {
            var texto = busqueda.value.toLowerCase();
            var submenu = busqueda.closest("[data-submenu]");
            if (!submenu) return;
            submenu.querySelectorAll("[data-item-multi]").forEach(function (opcion) {
                var coincide = opcion.dataset.nombre
                    .toLowerCase().indexOf(texto) !== -1;
                opcion.closest("li").style.display = coincide ? "" : "none";
            });
        });
    });

    function nombreParametroMulti(submenu) {
        var hidden = submenu.querySelector('input[type="hidden"]');
        return hidden ? hidden.name : "";
    }

    function opcionesMulti(submenu, nombre) {
        return Array.prototype.slice.call(
            submenu.querySelectorAll('input[type="hidden"][name="' + nombre + '"]')
        );
    }

    function idsMulti(submenu, nombre) {
        return opcionesMulti(submenu, nombre).map(function (input) {
            return input.value;
        });
    }

    function construirCheck() {
        var svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
        svg.setAttribute("xmlns", "http://www.w3.org/2000/svg");
        svg.setAttribute("viewBox", "0 0 24 24");
        svg.setAttribute("fill", "none");
        svg.setAttribute("stroke", "currentColor");
        svg.setAttribute("stroke-width", "2");
        svg.setAttribute("class", "h-4 w-4 text-violet-700");
        svg.innerHTML = '<path d="m5 13 4 4L19 7" stroke-linecap="round" stroke-linejoin="round"/>';
        return svg;
    }

    function construirQuitar() {
        var boton = document.createElement("button");
        boton.type = "button";
        boton.setAttribute("data-quitar", "");
        boton.className = "text-violet-400 transition-colors hover:text-violet-700";
        boton.innerHTML =
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-3 w-3">' +
            '<path d="M6 6l12 12M18 6 6 18" stroke-linecap="round" stroke-linejoin="round"/></svg>';
        return boton;
    }

    function rellenarBandeja(submenu, nombre) {
        var bandeja = submenu.querySelector("[data-bandeja]");
        if (!bandeja) return;
        bandeja.innerHTML = "";
        idsMulti(submenu, nombre).forEach(function (id) {
            var opcion = submenu.querySelector('[data-item-multi][value="' + id + '"]');
            if (!opcion) return;
            var chip = document.createElement("span");
            chip.className = "inline-flex items-center gap-1 rounded-full bg-violet-100 px-2 py-0.5 text-xs font-semibold text-violet-700";
            chip.appendChild(document.createTextNode(opcion.dataset.nombre));
            var quitar = construirQuitar();
            quitar.value = id;
            quitar.setAttribute("aria-label", "Quitar " + opcion.dataset.nombre);
            chip.appendChild(quitar);
            bandeja.appendChild(chip);
        });
    }

    function sincronizarItem(opcion, submenu, nombre) {
        var seleccion = idsMulti(submenu, nombre);
        var activa = seleccion.indexOf(opcion.value) !== -1;
        opcion.classList.toggle("font-bold", activa);
        opcion.classList.toggle("text-violet-700", activa);
        opcion.classList.toggle("text-slate-700", !activa);
        var check = opcion.querySelector("svg");
        if (activa && !check) {
            opcion.appendChild(construirCheck());
        } else if (!activa && check) {
            check.remove();
        }
    }

    function actualizarValorMulti(fila, submenu, nombre) {
        var valor = fila.querySelector("[data-filtro-valor]");
        var cantidad = idsMulti(submenu, nombre).length;
        valor.textContent = cantidad ? String(cantidad) : "—";
    }

    function sincronizarMulti(fila, submenu, nombre) {
        actualizarValorMulti(fila, submenu, nombre);
        submenu.querySelectorAll("[data-item-multi]").forEach(function (opcion) {
            sincronizarItem(opcion, submenu, nombre);
        });
        rellenarBandeja(submenu, nombre);
    }

    panel.querySelectorAll("[data-item-multi]").forEach(function (item) {
        item.addEventListener("click", function () {
            var submenu = item.closest("[data-submenu]");
            if (!submenu) return;
            var nombre = nombreParametroMulti(submenu);
            if (!nombre) return;
            var id = item.value;
            var seleccion = opcionesMulti(submenu, nombre);
            var activa = seleccion.some(function (input) {
                return input.value === id;
            });
            if (activa) {
                seleccion.forEach(function (input) {
                    if (input.value === id) input.remove();
                });
            } else {
                var nuevo = document.createElement("input");
                nuevo.type = "hidden";
                nuevo.name = nombre;
                nuevo.value = id;
                submenu.appendChild(nuevo);
            }
            var fila = submenu.parentElement;
            sincronizarMulti(fila, submenu, nombre);
            aplicar();
        });
    });

    panel.addEventListener("click", function (e) {
        var quitar = e.target.closest("[data-quitar]");
        if (!quitar) return;
        var submenu = quitar.closest("[data-submenu]");
        var nombre = nombreParametroMulti(submenu);
        opcionesMulti(submenu, nombre).forEach(function (input) {
            if (input.value === quitar.value) input.remove();
        });
        var fila = submenu.parentElement;
        sincronizarMulti(fila, submenu, nombre);
        // Reabre el submenú si se quitó desde la bandeja visible de otra fila.
        submenu.classList.remove("hidden");
        aplicar();
    });

    // ------------------------------------------------------------------ single-select-list
    panel.querySelectorAll("[data-item-single]").forEach(function (opcion) {
        opcion.addEventListener("click", function () {
            var submenu = opcion.closest("[data-submenu]");
            if (!submenu) return;
            var hidden = submenu.querySelector('input[type="hidden"]');
            if (!hidden) return;
            var valorSeleccionado = opcion.value;

            if (valorSeleccionado === hidden.value) {
                valorSeleccionado = ""; // deseleccionar → "Cualquiera"
            }
            hidden.value = valorSeleccionado;

            var etiqueta = "Cualquiera";
            submenu.querySelectorAll("[data-item-single]").forEach(function (otra) {
                var esActiva = otra.value === valorSeleccionado &&
                    !(valorSeleccionado === "" && otra.value !== "");
                if (valorSeleccionado === "") esActiva = otra.value === "";
                otra.classList.toggle("font-bold", esActiva);
                otra.classList.toggle("text-violet-700", esActiva);
                otra.classList.toggle("text-slate-700", !esActiva);
                if (esActiva && otra.value) etiqueta = otra.textContent.trim();
            });

            var valor = submenu.parentElement.querySelector("[data-filtro-valor]");
            if (valor) valor.textContent = etiqueta;
            aplicar();
        });
    });

    // ------------------------------------------------------------------ stepper (experiencia)
    panel.querySelectorAll("[data-stepper-input]").forEach(function (input) {
        var submenu = input.closest("[data-submenu]");
        if (!submenu) return;
        var hidden = submenu.querySelector("[data-experiencia-value]");
        var valor = submenu.parentElement.querySelector("[data-filtro-valor]");

        function anios() {
            var numero = Math.max(0, parseInt(input.value, 10) || 0);
            input.value = String(numero);
            if (hidden) hidden.value = numero ? String(numero) : "";
            if (valor) valor.textContent = numero ? (numero + " años") : "—";
            return numero;
        }

        var up = submenu.querySelector("[data-stepper-up]");
        var down = submenu.querySelector("[data-stepper-down]");
        if (up) {
            up.addEventListener("click", function (e) {
                e.stopPropagation();
                input.value = String((parseInt(input.value, 10) || 0) + 1);
                anios();
                aplicar();
            });
        }
        if (down) {
            down.addEventListener("click", function (e) {
                e.stopPropagation();
                input.value = String(Math.max(0, (parseInt(input.value, 10) || 0) - 1));
                anios();
                aplicar();
            });
        }
        input.addEventListener("change", function () {
            anios();
            aplicar();
        });
    });
})();