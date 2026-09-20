/* Menú móvil del landing page (navbar píldora exclusiva del landing).
   Se referencia con <script src="{% static 'js/landing-menu.js' %}"> al final del body.
   Vanilla JS — no usar librerías. */
(function () {
    var toggle = document.getElementById("menu-toggle");
    var menu = document.getElementById("mobile-menu");
    var iconOpen = document.getElementById("menu-icon-open");
    var iconClose = document.getElementById("menu-icon-close");
    if (!toggle || !menu) return;

    function setOpen(open) {
        menu.classList.toggle("hidden", !open);
        toggle.setAttribute("aria-expanded", open ? "true" : "false");
        iconOpen.classList.toggle("hidden", open);
        iconClose.classList.toggle("hidden", !open);
    }

    toggle.addEventListener("click", function () {
        setOpen(menu.classList.contains("hidden"));
    });

    menu.addEventListener("click", function (e) {
        if (e.target.closest("a")) setOpen(false);
    });

    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape") setOpen(false);
    });
})();