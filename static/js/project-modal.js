// Modal "Crear proyecto" por AJAX.
// Cualquier [data-crear-proyecto] (sidebar) pide el fragmento del modal con
// X-Requested-With y lo inyecta en un host propio al final del <body>, sin
// recargar. Se cierra con la X, "Cancelar", clic en el fondo o Escape. El
// envío va por fetch: si el server responde JSON {ok, redirect} se navega al
// proyecto creado; si responde 422 (HTML con errores) se reemplaza el modal.
// Sin JS, el enlace sigue siendo una página completa (Degradación elegante).
(function () {
    var host = null;

    function hostEl() {
        if (!host) {
            host = document.createElement("div");
            host.setAttribute("data-crear-host", "");
            document.body.appendChild(host);
        }
        return host;
    }

    function cerrar() {
        if (host) {
            host.innerHTML = "";
        }
    }

    function abrirDesde(url) {
        fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } })
            .then(function (respuesta) {
                // Sesión expirada / sin login: el server redirige; seguimos al
                // destino (login) en vez de inyectar esa página en el modal.
                if (respuesta.redirected) {
                    window.location.href = respuesta.url;
                    return null;
                }
                if (!respuesta.ok) {
                    throw new Error("No se pudo abrir el modal");
                }
                return respuesta.text();
            })
            .then(function (html) {
                if (html === null) {
                    return;
                }
                hostEl().innerHTML = html;
            })
            .catch(function () {
                // Red de seguridad: navegar a la página completa del modal.
                window.location.href = url;
            });
    }

    document.addEventListener("click", function (e) {
        var objetivo = e.target;
        if (!objetivo.closest) {
            return;
        }

        var disparador = objetivo.closest("[data-crear-proyecto]");
        if (disparador) {
            e.preventDefault();
            abrirDesde(disparador.href);
            return;
        }

        var cerrarBoton = objetivo.closest("[data-crear-close]");
        if (cerrarBoton && host && host.contains(cerrarBoton)) {
            e.preventDefault();
            cerrar();
            return;
        }

        var overlay = objetivo.closest("[data-crear-overlay]");
        if (overlay && objetivo === overlay) {
            cerrar();
        }
    });

    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape") {
            cerrar();
        }
    });

    document.addEventListener("submit", function (e) {
        var form = e.target;
        if (!form.matches || !form.matches("[data-crear-form]")) {
            return;
        }
        e.preventDefault();

        fetch(form.action, {
            method: "POST",
            body: new FormData(form),
            headers: { "X-Requested-With": "XMLHttpRequest" },
        })
            .then(function (respuesta) {
                if (respuesta.redirected) {
                    window.location.href = respuesta.url;
                    return;
                }
                var tipo = respuesta.headers.get("content-type") || "";
                if (respuesta.ok && tipo.indexOf("application/json") !== -1) {
                    return respuesta.json().then(function (data) {
                        window.location.href = data.redirect;
                    });
                }
                // 422: el fragmento vuelve con los errores de validación.
                return respuesta.text().then(function (html) {
                    hostEl().innerHTML = html;
                });
            })
            .catch(function () {
                // Red de seguridad: envío normal (no dispara el evento submit).
                form.submit();
            });
    });
})();
