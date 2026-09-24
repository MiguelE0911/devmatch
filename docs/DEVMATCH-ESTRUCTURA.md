# DEVMATCH - ESTRUCTURA

Materia: Desarrollo de Software V
Ultima actualización: September 11, 2026

# ESTRUCTURA DE DIRECTORIOS (base completa de referencia para todo el proyecto)

```
devmatch/
├── manage.py
├── requirements.txt
├── package.json                  # Tailwind: npm run build:css / watch:css
├── postcss.config.js
├── tailwind.config.js
├── README.md
├── .env.example
├── .gitignore
├── config/
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── dev.py
│   │   └── prod.py
│   ├── urls.py                   # incluye apps.core y admin; media en DEBUG
│   ├── wsgi.py
│   └── asgi.py
├── apps/
│   ├── core/                    # [ETAPA 1 - real] mixins, permisos por rol, utilidades
│   │   ├── views.py             # home / health-check de conexión a DB
│   │   ├── urls.py              # ruta base "" → core:home
│   │   ├── mixins.py
│   │   ├── permissions.py
│   │   ├── templatetags/
│   │   │   └── core_extras.py   # simple_tag active_link para el navbar
│   │   ├── management/commands/ # comandos para fixtures/seed_data (seed_data.py)
│   │   └── tests/
│   ├── accounts/                # [ETAPA 1 - real] Usuario, Rol, Perfil técnico
│   │   ├── models.py
│   │   ├── forms.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   ├── migrations/
│   │   └── tests/
│   ├── projects/                # [ETAPA 1 - real] Proyecto, Vacante
│   │   ├── models.py
│   │   ├── forms.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── services.py          # transiciones de estado válidas (Etapa 3 lo completa)
│   │   ├── admin.py
│   │   ├── migrations/
│   │   └── tests/
│   ├── applications/            # [ESQUELETO] Postulación (+ campos snapshot)
│   │   ├── models.py
│   │   ├── services.py          # aceptación transaccional (Etapa 2)
│   │   ├── migrations/
│   │   └── tests/
│   ├── matching/                # [ESQUELETO] sin modelos, lógica pura Python
│   │   ├── engine.py            # algoritmo de compatibilidad (Etapa 2)
│   │   ├── constants.py         # pesos fijos por criterio (CR-06 pospuesto)
│   │   └── tests/
│   ├── teams/                   # [ESQUELETO] Membresía, Invitación
│   │   ├── models.py
│   │   ├── migrations/
│   │   └── tests/
│   ├── audit/                   # [ESQUELETO] AuditLog (GenericForeignKey)
│   │   ├── models.py
│   │   ├── services.py          # log_action(...) (Etapa 3)
│   │   ├── migrations/
│   │   └── tests/
│   ├── reviews/                 # [ESQUELETO] Reseña
│   │   ├── models.py
│   │   ├── migrations/
│   │   └── tests/
│   ├── moderation/               # [ESQUELETO] Reporte
│   │   ├── models.py
│   │   ├── migrations/
│   │   └── tests/
│   ├── integrations/
│   │   └── github/               # [ESQUELETO] cliente API GitHub (Etapa 4)
│   │       ├── client.py
│   │       └── tests/
│   └── dashboard/                # [ESQUELETO] métricas/agregaciones (Etapa 4)
│       ├── views.py
│       └── services.py
├── templates/
│   ├── base.html
│   ├── partials/ (navbar.html, footer.html, alerts.html)
│   ├── core/
│   │   └── home.html            # página de inicio / estado de la DB
│   ├── accounts/
│   ├── projects/
│   ├── applications/
│   ├── teams/
│   ├── reviews/
│   └── dashboard/
├── static/
│   ├── src/input.css            # entrada de Tailwind
│   ├── dist/output.css          # build de Tailwind
│   └── img/
└── media/                        # logos y prototipos subidos (Pillow)
```

> **Nota:** Estructura de referencia. Es probable que no se implemente completa desde la primera etapa; las apps marcadas como [ESQUELETO] se completan en su etapa correspondiente.
> 

---

## ESTRUCTURA DE DIRECTORIOS — SOLO ETAPA 1

Esta es la estructura mínima real que necesita existir en `main` para que ambos squads empiecen a trabajar.

```
devmatch/
├── manage.py
├── requirements.txt
├── package.json                  # Tailwind: npm run build:css / watch:css
├── postcss.config.js
├── tailwind.config.js
├── README.md
├── .env.example
├── .gitignore
├── config/
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── dev.py
│   │   └── prod.py
│   ├── urls.py                   # incluye apps.core y admin; media en DEBUG
│   ├── wsgi.py
│   └── asgi.py
├── apps/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── views.py             # home / health-check de conexión a DB
│   │   ├── urls.py              # ruta base "" → core:home
│   │   ├── mixins.py
│   │   ├── permissions.py
│   │   ├── templatetags/
│   │   │   ├── __init__.py
│   │   │   └── core_extras.py   # simple_tag active_link para el navbar
│   │   ├── management/
│   │   │   ├── __init__.py
│   │   │   └── commands/
│   │   │       ├── __init__.py
│   │   │       └── seed_data.py
│   │   └── tests/
│   │       ├── __init__.py
│   │       └── test_home_view.py
│   ├── accounts/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── forms.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   ├── migrations/
│   │   │   └── __init__.py
│   │   └── tests/
│   │       └── __init__.py
│   └── projects/
│       ├── __init__.py
│       ├── models.py
│       ├── forms.py
│       ├── views.py
│       ├── urls.py
│       ├── services.py
│       ├── admin.py
│       ├── migrations/
│       │   └── __init__.py
│       └── tests/
│           └── __init__.py
├── templates/
│   ├── base.html
│   ├── partials/
│   │   ├── navbar.html
│   │   ├── footer.html
│   │   └── alerts.html
│   ├── core/
│   │   └── home.html
│   ├── accounts/
│   │   ├── login.html
│   │   ├── register.html
│   │   └── profile_form.html
│   └── projects/
│       ├── project_list.html
│       ├── project_form.html
│       ├── project_detail.html
│       └── vacancy_form.html
├── static/
│   ├── src/
│   │   └── input.css
│   ├── dist/
│   │   └── output.css
│   └── img/
│       └── .gitkeep
└── media/
    └── .gitkeep
```

> **Nota:** dentro de `accounts/models.py` y `projects/models.py`, dejen los campos de relación (`ForeignKey`, `ManyToMany`) que ya se sabe que van a necesitar las etapas siguientes (ej. relación Usuario→Postulación, Proyecto→Vacante→Membresía), aunque el modelo del otro lado todavía no exista. Así cuando se cree la app `applications` en la Etapa 2, la conexión ya está prevista y no toca alterar una tabla que ya está en producción/demo.
> 

---

# PROPIEDAD DE ARCHIVOS COMPARTIDOS

Hay archivos que, por naturaleza, no pertenecen a una sola app ni a una sola persona, y que ambos squads probablemente necesiten tocar al mismo tiempo. Para evitar choques, quedan bajo una regla especial:

### a) Plantillas compartidas (`templates/base.html`, `templates/partials/`)

Propiedad exclusiva del **Integrador**, gestionadas dentro de `etapa-N/core-setup`. Ningún squad las edita directamente. Si Squad A o Squad B necesitan agregar un enlace al navbar, una nueva alerta genérica, o cualquier ajuste en el layout base, se lo solicitan al Integrador (por chat o incluyéndolo como comentario en su PR) y es el Integrador quien lo incorpora. Esto evita que dos personas editen el mismo `base.html` en ramas paralelas y generen conflictos en el archivo más "tocado" de todo el proyecto.

### b) Archivos raíz compartidos (`requirements.txt`, `.env.example`, `config/settings/base.py`, `package.json`, `tailwind.config.js`, `postcss.config.js`)

Estos sí pueden ser editados por cualquier persona cuando su tarea lo requiera (ej. agregar una nueva librería a `requirements.txt`), pero con una regla de coordinación simple: **antes de modificar uno de estos archivos, avisa en el chat del equipo qué vas a agregar.** No se necesita aprobación previa ni bloquear el trabajo — el aviso es solo para que el resto del equipo lo tenga en cuenta y, si llega a presentarse un conflicto al momento del merge, sea muy fácil de resolver porque ya se sabía qué cambio se venía y de parte de quién.