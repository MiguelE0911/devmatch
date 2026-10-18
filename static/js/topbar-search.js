/* Autocompletado de la barra de búsqueda del shell (topbar).
   Contrato con partials/topbar.html:
   - Form [data-busqueda] con [data-busqueda-url] (endpoint JSON, GET ?q=).
   - Input [data-busqueda-input] (name="q") y panel [data-busqueda-panel].
   - Plantillas [data-busqueda-template] (sugerencia) y
     [data-busqueda-vacio-template] (sin resultados), clonadas aquí.
   Comportamiento: clic en una sugerencia abre el detalle del proyecto.
   **Enter** NO abre ninguna sugerencia: envía el formulario a los resultados
   del feed (core:feed?q=…). Vanilla JS — no usar librerías. */
(function () {
    var form = document.querySelector("[data-busqueda]");
    if (!form) return;

    var input = form.querySelector("[data-busqueda-input]");
    var panel = form.querySelector("[data-busqueda-panel]");
    var plantilla = form.querySelector("[data-busqueda-template]");
    var plantillaVacio = form.querySelector("[data-busqueda-vacio-template]");
    var endpoint = form.dataset.busquedaUrl;
    if (!input || !panel || !plantilla || !endpoint) return;

    var MIN_CARACTERES = 2;
    var ESPERA_MS = 300;

    var temporizador = null;
    var controlador = null;

    function abrir() {
        panel.classList.remove("hidden");
    }

    function ocultar() {
        panel.classList.add("hidden");
    }

    // Destino del botón "Volver" del detalle: la página actual con sus filtros
    // (?pagina=… incluido). Se elimina un `next` previo para no anidarlo; el
    // backend lo revalida como URL interna.
    function origen() {
        var url = new URL(window.location.href);
        url.searchParams.delete("next");
        return url.pathname + (url.search || "");
    }

    function rellenar(item, proyecto) {
        item.href = proyecto.url + "?next=" + encodeURIComponent(origen());
        item.querySelector("[data-item-nombre]").textContent = proyecto.nombre;
        item.querySelector("[data-item-estado]").textContent = proyecto.estado;

        var img = item.querySelector("[data-item-img]");
        var iniciales = item.querySelector("[data-item-iniciales]");
        if (proyecto.logo) {
            img.src = proyecto.logo;
            img.alt = "Logo de " + proyecto.nombre;
            img.classList.remove("hidden");
            iniciales.classList.add("hidden");
            iniciales.textContent = "";
        } else {
            img.removeAttribute("src");
            img.classList.add("hidden");
            iniciales.classList.remove("hidden");
            iniciales.textContent = proyecto.iniciales;
        }
    }

    function render(resultados) {
        panel.innerHTML = "";

        if (!resultados.length) {
            if (plantillaVacio) {
                panel.appendChild(plantillaVacio.content.cloneNode(true));
            }
            abrir();
            return;
        }

        resultados.forEach(function (proyecto) {
            var item = plantilla.content
                .cloneNode(true)
                .querySelector("[data-busqueda-item]");
            rellenar(item, proyecto);
            panel.appendChild(item);
        });
        abrir();
    }

    function buscar(texto) {
        if (controlador) controlador.abort();
        controlador = new AbortController();

        fetch(endpoint + "?q=" + encodeURIComponent(texto), {
            signal: controlador.signal,
        })
            .then(function (respuesta) {
                if (!respuesta.ok) throw new Error("HTTP " + respuesta.status);
                return respuesta.json();
            })
            .then(function (datos) {
                render(datos.resultados || []);
            })
            .catch(function (error) {
                if (error.name !== "AbortError") ocultar();
            });
    }

    input.addEventListener("input", function () {
        var texto = input.value.trim();
        clearTimeout(temporizador);
        if (texto.length < MIN_CARACTERES) {
            ocultar();
            return;
        }
        temporizador = setTimeout(function () {
            buscar(texto);
        }, ESPERA_MS);
    });

    input.addEventListener("keydown", function (e) {
        if (e.key === "Escape") {
            ocultar();
        } else if (e.key === "Enter") {
            // Enter siempre lleva a los resultados del feed; nunca abre la
            // primera sugerencia.
            ocultar();
            form.submit();
        }
    });

    form.addEventListener("focusout", function (e) {
        if (!form.contains(e.relatedTarget)) {
            setTimeout(ocultar, 150);
        }
    });

    document.addEventListener("click", function (e) {
        if (!form.contains(e.target)) ocultar();
    });
})();
