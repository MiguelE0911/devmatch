# DEVMATCH - ESTRUCTURA

Materia: Desarrollo de Software V
Última actualización: Octubre 22, 2026

Estado de referencia: **Etapa 2 cerrada** (`main` @ `cf30c60`, tag `v2.0-etapa-2`) y **Etapa 3 en curso**
(rama `etapa-3/ci-actions`: CI y documentación de roles, sin cambios de dominio).

---

# ESTRUCTURA REAL DEL REPOSITORIO

Esta es la estructura que existe hoy, no la estructura mínima de la Etapa 1. El repositorio tiene
9 apps, 20 modelos, 25 rutas HTTP propias, 43 plantillas, 32 archivos de tests y 483 métodos de prueba.

```
devmatch/
├── manage.py
├── requirements.txt
├── requirements-dev.txt          # Ruff, dependencias de desarrollo/CI
├── package.json                  # Tailwind: npm run build:css / watch:css
├── postcss.config.js
├── tailwind.config.js
├── README.md
├── PRODUCT.md
├── DESIGN.md
├── AGENTS.md                     # guía local de agentes (ignorada por git)
├── .env.example
├── .gitignore
├── .github/
│   ├── PULL_REQUEST_TEMPLATE.md  # checklist de PR, migraciones y credenciales
│   └── workflows/
│       └── ci.yml                # Ruff + Django checks + tests con Postgres 16 efímero
├── config/
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py               # settings compartidos, apps, middleware, templates, BD
│   │   ├── dev.py                # DEBUG local
│   │   ├── prod.py               # guards de producción; rechaza roles privilegiados
│   │   ├── test.py               # TEST_DATABASE_URL, hasher rápido, storage local
│   │   └── migrate.py            # MIGRATION_DATABASE_URL; solo el Integrador lo usa
│   ├── urls.py                   # admin, core, projects, accounts, applications y media
│   ├── wsgi.py
│   └── asgi.py
├── apps/
│   ├── core/                     # transversal: home, feed, permisos, middleware y triggers
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── mixins.py
│   │   ├── permissions.py
│   │   ├── middleware.py         # LoginRequired, límite de subidas, estado de cuenta
│   │   ├── templatetags/
│   │   │   └── core_extras.py    # active_link para el navbar
│   │   ├── management/
│   │   │   └── commands/
│   │   │       └── seed_data.py
│   │   ├── migrations/
│   │   │   └── 0001_triggers_postgres.py   # 6 funciones y 19 triggers (RunSQL)
│   │   └── tests/                # 7 archivos: home, feed, búsqueda, permisos, middleware,
│   │                             # seed y anti-drift de triggers
│   ├── accounts/                 # Usuario, Perfil, catálogos y auth/perfil
│   │   ├── models.py
│   │   ├── forms.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   ├── migrations/
│   │   │   ├── 0001_initial.py
│   │   │   └── 0002_alter_habilidad_options_alter_interes_options_and_more.py
│   │   └── tests/                # 5 archivos: modelos, forms, vistas y admin/bloqueo
│   ├── projects/                 # Proyecto, Vacante, media y gestión del creador
│   │   ├── models.py
│   │   ├── forms.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── services.py           # transiciones, vacantes, cierre de vacantes
│   │   ├── media_utils.py        # Pillow + Neon Object Storage / fallback local
│   │   ├── admin.py
│   │   ├── templates/
│   │   │   └── widgets/
│   │   │       └── chip_checkbox_select.html
│   │   ├── migrations/
│   │   │   ├── 0001_initial.py
│   │   │   ├── 0002_vacante.py
│   │   │   ├── 0003_proyectomedia.py
│   │   │   ├── 0004_vacantehabilidadrequerida_vacantetecnologiarequerida.py
│   │   │   └── 0005_vacante_chk_cupos_no_exceden.py
│   │   └── tests/                # 9 archivos + helpers.py: modelos, forms, servicios,
│   │                             # vistas, vacantes, postulaciones, uploads, media y admin
│   ├── applications/             # Postulación, snapshot y aceptación transaccional
│   │   ├── models.py
│   │   ├── services.py           # crear/aceptar/retirar, carga y snapshot
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   ├── migrations/
│   │   │   └── 0001_initial.py
│   │   └── tests/                # modelos, servicios, vistas y concurrencia
│   ├── matching/                 # Motor de Match Score
│   │   ├── models.py             # ConfiguracionPesosMatching
│   │   ├── engine.py             # cálculo y explicabilidad del score
│   │   ├── constants.py          # pesos por defecto
│   │   ├── admin.py
│   │   ├── migrations/
│   │   │   └── 0001_initial.py
│   │   └── tests/                # test_engine.py, test_models.py
│   ├── teams/                    # Invitación y membresía (sin vistas todavía)
│   │   ├── models.py
│   │   ├── admin.py
│   │   ├── migrations/
│   │   │   ├── 0001_initial.py
│   │   │   └── 0002_equipomembresia.py
│   │   └── tests/                # modelos de invitación y membresía
│   ├── audit/                    # AuditoriaLog inmutable (sin servicio de escritura aún)
│   │   ├── models.py
│   │   ├── admin.py
│   │   ├── migrations/
│   │   │   └── 0001_initial.py
│   │   └── tests/                # modelos y append-only
│   ├── reviews/                  # Reseña verificada por trigger (sin alta UI aún)
│   │   ├── models.py
│   │   ├── admin.py
│   │   ├── migrations/
│   │   │   └── 0001_initial.py
│   │   └── tests/                # modelos y reglas del trigger
│   └── moderation/               # Reporte y admin (sin flujo de usuario aún)
│       ├── models.py
│       ├── admin.py
│       ├── migrations/
│       │   └── 0001_initial.py
│       └── tests/                # modelos de reportes
├── templates/
│   ├── base.html
│   ├── partials/                 # Integrador-only
│   │   ├── topbar.html
│   │   ├── sidebar.html
│   │   ├── footer.html
│   │   └── alerts.html
│   ├── core/
│   │   ├── home.html             # landing pública
│   │   ├── feed.html             # feed autenticado con búsqueda y filtros
│   │   ├── _head.html
│   │   ├── _landing_navbar.html
│   │   ├── _landing_footer.html
│   │   ├── _project_card.html
│   │   ├── _filters_panel.html
│   │   ├── _pagination.html
│   │   ├── _score_ring.html
│   │   └── _factor_bar.html
│   ├── accounts/
│   │   ├── login.html
│   │   ├── register.html
│   │   ├── profile_detail.html
│   │   ├── profile_form.html
│   │   ├── _auth_base.html
│   │   ├── _auth_input.html
│   │   ├── _chip.html
│   │   ├── _profile_header.html
│   │   ├── _profile_biografia.html
│   │   ├── _profile_habilidades.html
│   │   ├── _profile_metrics.html
│   │   ├── _profile_proyectos.html
│   │   └── _profile_resenas.html
│   ├── projects/
│   │   ├── project_list.html
│   │   ├── project_create.html
│   │   ├── project_form.html
│   │   ├── project_detail.html
│   │   ├── vacancy_form.html
│   │   ├── gallery_form.html
│   │   ├── _proyecto_encabezado.html
│   │   ├── _proyecto_tabs.html
│   │   ├── _tab_descripcion.html
│   │   ├── _tab_vacantes.html
│   │   ├── _tab_galeria.html
│   │   ├── _requisitos.html
│   │   ├── _equipo.html          # maqueta: pendiente conectar a EquipoMembresia (CR-14)
│   │   └── _project_create_modal.html
│   └── applications/
│       └── application_list.html # "Mis Postulaciones" con 5 pestañas
├── static/
│   ├── src/
│   │   ├── input.css             # entrada de Tailwind
│   │   └── theme.css
│   ├── dist/
│   │   └── output.css            # ignorado por git; se genera con npm run build:css
│   ├── js/
│   │   ├── topbar-search.js
│   │   ├── project-modal.js
│   │   ├── menus.js
│   │   ├── landing-menu.js
│   │   └── feed-filters.js
│   └── img/
│       └── .gitkeep
├── media/                        # logos y prototipos (fallback local; con las 5 vars de
│                                 # Neon Object Storage, van al bucket del equipo)
└── docs/
    ├── devmatch_schema_v1.sql
    ├── DEVMATCH-BD.md
    ├── DEVMATCH-DB-ROLES.md
    ├── DEVMATCH-DESIGN.md
    ├── DEVMATCH-DISTRIBUCION.md
    ├── DEVMATCH-ESP-V2.md
    ├── DEVMATCH-ESTRUCTURA.md
    ├── DEVMATCH-MATCHING.md
    └── DEVMATCH-SOLICITUD.md
```

> **No existen todavía** `apps/dashboard` ni `apps/integrations/github`. Las apps `teams`, `audit`,
> `reviews` y `moderation` existen con modelo, admin, migración y tests, pero aún no tienen la capa
> de vistas/servicios de Etapa 3. La estructura mínima de Etapa 1 quedó superada por este árbol.

---

# NOTAS DE LA ESTRUCTURA ACTUAL

## Settings y roles de base de datos

`config/settings/base.py` contiene la configuración compartida. `dev.py` se usa para desarrollo
local, `prod.py` para producción y `test.py` para la suite contra PostgreSQL. `migrate.py` es
exclusivo para aplicar migraciones con el rol propietario (`MIGRATION_DATABASE_URL`).

El rol runtime (`devmatch_app`) nunca aplica migraciones ni desactiva triggers. El flujo completo
está documentado en [`DEVMATCH-DB-ROLES.md`](DEVMATCH-DB-ROLES.md) y en la sección de migraciones de
[`DEVMATCH-DISTRIBUCION.md`](DEVMATCH-DISTRIBUCION.md).

## Migraciones

| App | Migraciones actuales |
|---|---|
| `core` | `0001_triggers_postgres` (DDL de funciones y triggers) |
| `accounts` | `0001_initial`, `0002_alter_habilidad_options_...` |
| `projects` | `0001_initial` a `0005_vacante_chk_cupos_no_exceden` |
| `applications` | `0001_initial` |
| `matching` | `0001_initial` |
| `teams` | `0001_initial`, `0002_equipomembresia` |
| `audit`, `reviews`, `moderation` | `0001_initial` |

Solo el dueño del `models.py` genera migraciones de su app. Solo el Integrador las aplica a Neon
después del merge, usando `config.settings.migrate` y el endpoint directo (sin `-pooler`).

## Tailwind

`static/dist/output.css` está en `.gitignore` a propósito: es un artefacto construido, no fuente.
Cada persona lo genera en su máquina:

```bash
npm install
npm run build:css      # una vez, para tener el archivo
npm run watch:css      # y lo deja escuchando mientras trabaja
```

Si un PR no muestra estilos, casi siempre es porque no se corrió `npm run build:css`. No se
commitea el CSS minificado.

## `apps/core/migrations/`

`core` no tiene modelos propios, pero sí la migración transversal que instala los triggers. No se
agregan modelos a `core`: su función es transversal (salud, mixins, permisos, middleware y DDL de
las garantías de la base). Los modelos van en la app que les corresponde.

## CI

`.github/workflows/ci.yml` corre en cada PR y en pushes a `main`. Tiene dos jobs:

- **lint:** Ruff completo como reporte no bloqueante; solo fallan errores reales (`E9`, `F63`, `F7`, `F82`).
- **test:** levanta PostgreSQL 16 efímero, corre `manage.py check`, verifica que no falten migraciones
  y ejecuta la suite con `config.settings.test`. No toca Neon ni usa credenciales reales.

---

# PROPIEDAD DE ARCHIVOS COMPARTIDOS

Hay archivos que, por naturaleza, no pertenecen a una sola app ni a una sola persona, y que ambos
squads probablemente necesiten tocar al mismo tiempo. Para evitar choques, quedan bajo una regla
especial:

### a) Plantillas compartidas (`templates/base.html`, `templates/partials/`)

Propiedad exclusiva del **Integrador**, gestionadas dentro de `etapa-N/core-setup`. Ningún squad
las edita directamente. Si Squad A o Squad B necesitan agregar un enlace al navbar, una nueva
alerta genérica, o cualquier ajuste en el layout base, se lo solicitan al Integrador (por chat o
incluyéndolo como comentario en su PR) y es el Integrador quien lo incorpora. Esto evita que dos
personas editen el mismo `base.html` en ramas paralelas y generen conflictos en el archivo más
"tocado" de todo el proyecto.

### b) Archivos raíz compartidos (`requirements.txt`, `.env.example`, `config/settings/base.py`, `package.json`, `tailwind.config.js`, `postcss.config.js`)

Estos sí pueden ser editados por cualquier persona cuando su tarea lo requiera (ej. agregar una
nueva librería a `requirements.txt`), pero con una regla de coordinación simple: **antes de
modificar uno de estos archivos, avisa en el chat del equipo qué vas a agregar.** No se necesita
aprobación previa ni bloquear el trabajo — el aviso es solo para que el resto del equipo lo tenga
en cuenta y, si llega a presentarse un conflicto al momento del merge, sea muy fácil de resolver
porque ya se sabía qué cambio se venía y de parte de quién.

### c) CI y plantilla de PR (`.github/`)

Los cambios en `.github/workflows/ci.yml` o `.github/PULL_REQUEST_TEMPLATE.md` se coordinan con el
Integrador antes de abrir el PR. No se incluyen credenciales, rutas de Neon ni variables de entorno
reales en esos archivos.
