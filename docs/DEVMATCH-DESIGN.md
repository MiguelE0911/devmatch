# DEVMATCH - DISEÑO FRONTEND

Materia: Desarrollo de Software V
Ultima actualización: September 20, 2026

# Modus operandi del frontend — DevMatch

> Documento de referencia para construir y expandir la interfaz de DevMatch **sin inventar nada que ya exista**.
> Lo lee cualquier persona del equipo (Squad B principalmente) y, si vas a pedirle a una IA que escriba código frontend, **pega este archivo completo como contexto** antes del prompt.
> Está escrito para ser reproducible solo desde los archivos del repositorio: cada color, clase, sombra y componente que se menciona existe hoy en el código real.

---

## 1. Propósito y cómo usar este documento

El frontend de DevMatch ya tiene una **base establecida**: diccionarios de color, fuentes, sombras y componentes reutilizables. El objetivo de la descentralización es que **cada ventana nueva referencie esa base en lugar de recrearla**.

Reglas de oro:

1. **No inventar colores, sombras ni fuentes.** Si necesitas algo visual, primero busca si ya existe en la Sección 3 (diccionarios) o en la Sección 5 (catálogo).
2. **No duplicar componentes.** Si necesitas algo que ya existe en `home.html` o en un include `_*.html`, lo reutilizas (o lo extraes siguiendo la convención de la Sección 8).
3. **Copiar el patrón de `home.html`.** Es la landing y el ejemplo canónico de todo el sistema visual. Cuando tengas dudas de "¿cómo se hace tal cosa?", mirá ahí primero.

**Archivo de referencia canónico:** `templates/core/home.html` (landing standalone). El `head`, el navbar y el script del menú ya fueron extraídos a archivos reutilizables (`core/_head.html`, `core/_landing_navbar.html`, `static/js/landing-menu.js`) y la landing los referencia con `{% include %}`. Leerlo es la mejor forma de verificar cómo se usan las clases de este documento.

---

## 2. Mapa de archivos del frontend

| Archivo | Rol | ¿Lo toca quien construye vistas? |
| --- | --- | --- |
| `tailwind.config.js` | Tokens de Tailwind: colores custom, sombras, `font-montserrat`. | ⚠️ **Sí, pero con aviso previo en el chat** (archivo compartido, ver Sección 10). |
| `static/src/theme.css` | **Diccionario de colores** (tokens `--dev-*` y `--color-*`, claro/oscuro). | Sí: es la fuente de verdad de la paleta. Se lee, no se reescribe sin aviso. |
| `static/src/input.css` | Entrada de build de Tailwind + estilos de selection/focus/caret/scrollbar. | No (capa base; cambios con aviso). |
| `static/dist/output.css` | CSS compilado (se sirve al navegador). **Nunca se edita a mano.** | No: se regenera con `npm run build:css`. |
| `templates/base.html` | Shell compartido de las páginas funcionales (nav/footer/alerts del shell). | No: propiedad del Integrador (solicitar cambios por chat/PR). |
| `templates/partials/navbar.html` | Navbar del **interior de la web** (shell, tonos slate). La landing tiene el suyo exclusivo. | No: propiedad del Integrador. |
| `templates/partials/footer.html` | **Footer GLOBAL** (violeta/paper, ex-landing). Aplica a todas las páginas del shell; la landing NO lo usa. | No: propiedad del Integrador. |
| `templates/partials/alerts.html` | Alertas genéricas del shell. | No: propiedad del Integrador. |
| `templates/core/home.html` | Landing standalone: arma su `<head>` y navbar con includes y compone las secciones. Ejemplo canónico. | Sí (es referencia + reutilizable por copy-paste de patrones). |
| `templates/core/_head.html` | `<head>` de páginas standalone: metas, `title`/`description` parametrizados, Google Fonts (Montserrat) y CSS. | Sí (usar en toda página standalone). |
| `templates/core/_landing_navbar.html` | Navbar píldora **EXCLUSIVO del landing** (no usar en la web). | Sí (solo en páginas de la landing). |
| `templates/core/_score_ring.html` | Componente donut de match score (se incluye con parámetros). | Sí. |
| `templates/core/_factor_bar.html` | Barra de factor (se incluye con parámetros). | Sí. |
| `static/js/landing-menu.js` | Script del menú móvil de la landing (vanilla). | Se referencia, no se edita desde las vistas. |
| `templates/core/health.html` | Health-check de la DB (extiende `base.html`). | Referencia de cómo se ve una vista "funcional" del shell. |

Hay **dos patrones de página** conviviendo:

- **Standalone** (landing): `home.html` NO extiende `base.html`; trae su propio `<html>` y arma el `<head>` con `core/_head.html` (Montserrat + CSS), su navbar con `core/_landing_navbar.html` (exclusivo del landing) y sus secciones. Una página de marketing o que necesite el look completo de marca usa este patrón.
- **Shell** (funcionales): `health.html` extiende `base.html` (`{% extends "base.html" %}` + `{% block content %}`) y hereda el navbar del shell y el **footer global** (`partials/footer.html`). Las vistas de datos/forms de accounts/projects parten de acá.

**Navbar / footer por contexto:** el navbar del landing es **exclusivo de la landing** (`core/_landing_navbar.html`); dentro de la web se usa `partials/navbar.html`. El **footer global** (`partials/footer.html`) aplica a todas las páginas **excepto la landing**, que tendrá un footer exclusivo propio (pendiente de diseño).

---

## 3. Diccionarios (no inventar valores nuevos)

### 3.1 Colores — escala violeta de marca

Toda la paleta vive en `tailwind.config.js` (clases activas) y `static/src/theme.css` (tokens). Para **usar** en plantillas se anteponen las utilidades de Tailwind ya configuradas:

| Utilidad | Hex | Rol / dónde se usa |
| --- | --- | --- |
| `violet-700` | `#6D28D9` | **PRIMARY**. CTA principal, cards de la mecánica, titulares de sección, anillos del timeline, logo "MATCH". |
| `violet-800` | `#5B21C7` | Hover del primary, texto de énfasis en la tele de CTA final. |
| `violet-ray` | `#7C4FE0` | De degradado (hero, cards Creador/Colaborador). |
| `violet-deep` | `#5B21C7` | To de degradado de los cards saturados. |
| `violet-600` | `#7C3AED` | Enlaces del navbar de la landing. |
| `violet-500` | `#8B5CF6` | Badges y chips de estado, texto íntimo. |
| `violet-400` | `#A78BFA` | Logo "DEV", botón "Ingresar", banda de transición. |
| `violet-100` | `#EDE9FE` | Ring de cards claros, círculos de iconos, fondo del botón hamburguesa. |
| `violet-200` | `#DDD6FE` | Bordes horizontales de sección (`border-t border-violet-200`). |
| `violet-950` | `#2E1065` | Texto sobre violeta claro ("Ingresar"), sombra de CTA. |
| `violet-track` | `#A380D9` | Riel vacío de anillos/barras de progreso y línea del timeline. |
| `violet-fill-start` | `#C6B2E7` | Inicio del degradado de relleno de barras. |
| `violet-fill-end` | `#F4F8FA` | Fin del degradado de relleno (empata con el papel). |
| `paper` | `#F5F9FA` | **Ground global** y fondo de cards claros. |
| `ink` | `#3A455B` | **Texto de cuerpo** sobre papel (sustituye al negro). |

Transparencias permitidas (siempre sobre los de arriba): `white/90`, `white/85`, `white/70`, `violet-500/40` (chips), `violet-track/70` (línea del timeline), `paper/95` (navbar).

**Regla del diccionario:** si necesitás un color que no está en la tabla, **no lo inventes** — pedí confirmación del Integrador en el chat antes de agregarlo a `tailwind.config.js`.

### 3.2 Sombras (Halo Rule)

Definidas en `tailwind.config.js`. Solo estas 4, siempre con tinte violeta (nunca gris ni negro puro):

| Clase | Valor | Uso |
| --- | --- | --- |
| `shadow-hero` | `0 40px 80px -20px rgba(91,33,198,.55)` | Panel hero grande. |
| `shadow-navbar` | `0 18px 50px -20px rgba(91,33,198,.5)` | Barra píldora flotante. |
| `shadow-card` | `0 18px 45px -18px rgba(109,40,217,.35)` | Cards claros y anillos numerados. |
| `shadow-card-violet` | `0 35px 70px -22px rgba(32,10,70,.65)` | Cards violetas de la mecánica (la más profunda). |

### 3.3 Tipografía

**Montserrat** es la única familia (Google Fonts, pesos 400/500/600/700/800 + itálica 400). Se declara con la clase `font-montserrat` (ya configurada) y **se carga mediante `core/_head.html`** en las páginas standalone que la usan (hoy: la landing). Las páginas del shell (`base.html`) mantienen su tipografía base; **no promover Montserrat a global** sin decisión explícita.

### 3.4 Tokens de `theme.css` (contexto)

`static/src/theme.css` es el **mapa completo de la paleta**: primitivas (`--dev-*`, tema-invariantes) y semánticas (`--color-*` claro/oscuro). Hoy las páginas usan las utilidades de la Sección 3.1 (las tokens semánticas ya mapeadas a clases como `bg-surface`, `text-ink` **aún no están activas en el build**; la migración es incremental y la coordina el Integrador). No uses utilidades tipo `bg-brand` suponiendo que existen — **verificá que esté en `tailwind.config.js`** antes de usarla.

---

## 4. Jerarquía tipográfica (recetas reales)

| Nivel | Clases usadas en la landing | Rol |
| --- | --- | --- |
| Display (H1) | `text-4xl sm:text-5xl lg:text-[3.4rem] font-extrabold leading-[1.08] tracking-tight text-white` | Hero, blanco sobre degradado violeta, máx. `max-w-[32rem]`. |
| Headline (H2) | `text-3xl` / `text-4xl font-extrabold tracking-tight text-violet-700` | Titulares de sección ("Cómo Funciona"). |
| Title (H3) | `text-xl`/`text-2xl font-extrabold leading-tight text-violet-700` | Títulos de paso, bloques y rótulos de cards. |
| Body | `leading-relaxed` con `text-ink` (o `text-white/85–90` sobre violeta) | Párrafos; ancho `max-w-prose`/`max-w-md`/`max-w-2xl`. |
| Label | `text-sm font-semibold` / badges `text-[11px] font-bold tracking-wide` | Metadatos, enlaces de nav, badges de estado. |

**Sin fuentes display alternativas** (nada de Arial/Segoe UI en rótulos de la landing) y **sin degradado de texto** (`text-transparent bg-clip-text` está descartado).

---

## 5. Catálogo de componentes

Todos los valores de clase están copiados del código real (`home.html` + includes). Usalos tal cual; si necesitás una variante, ajustá espacio/tamaño pero **preservá forma, sombra y reglas de contraste**.

### 5.1 Botones y CTAs

| Variante | Clases | Dónde |
| --- | --- | --- |
| **Primario** | `rounded-full bg-violet-700 px-7 py-3.5 text-sm font-bold text-white shadow-lg shadow-violet-950/30 transition-colors hover:bg-violet-800` | "Publicar un proyecto", "Crear mi cuenta" (en navbar usa `px-4 py-2.5` / `sm:px-5 sm:py-3`). |
| **Inverso** (sobre card violeta) | `rounded-full bg-white px-7 py-3.5 text-sm font-bold text-violet-700 shadow-sm transition-colors hover:bg-violet-100` | CTA final "Publicar un proyecto" sobre degradado `ray→deep`. |
| **Ghost on dark** | `rounded-full border border-white/60 bg-white/15 px-7 py-3.5 text-sm font-bold text-white backdrop-blur transition-colors hover:bg-white/25` | "Ver cómo funciona" del hero. |
| **Outline on light** | `rounded-full border-2 border-violet-700 px-7 py-3 text-sm font-bold text-violet-700 transition-colors hover:bg-violet-700 hover:text-white` | "Crear mi cuenta" sobre card claro. |
| **Ingresar** (navbar) | `rounded-full bg-violet-400 px-4 py-2.5 text-xs font-bold text-violet-950 shadow-sm transition-colors hover:bg-violet-300 sm:px-5 sm:py-3 sm:text-sm` | Login terciario; texto oscuro sobre violeta claro por contraste. |

### 5.2 Chips y badges

- **Tech chip** (dentro de cards violetas): `rounded-full border border-white/20 bg-violet-500/40 px-4 py-1.5 text-sm font-bold text-white`.
- **Status badge**: `rounded-full bg-violet-500 px-3 py-1 text-[11px] font-bold tracking-wide text-white` (ej. "Compatibilidad", "2/2 cupos", "Pendiente").

### 5.3 Cards y contenedores

- **Card oscura de la mecánica**: `rounded-[24px]` o `rounded-[28px] bg-violet-700 p-6 sm:p-7 shadow-card-violet ring-1 ring-white/20`.
- **Card clara**: `rounded-[24px] bg-paper p-6 shadow-card ring-1 ring-violet-100`.
- **Card saturada (degradado)**: `rounded-[28px] bg-gradient-to-br from-violet-ray to-violet-deep p-9 shadow-card-violet`.
- **Radios**: `28px` cards principales; `24px` cards de demostración; `rounded-full` píldoras/chips/badges/navbar; `56px` únicamente los labios del hero (`rounded-b-[56px]`) y su espejo (`rounded-t-[56px]`).

### 5.4 Componentes reutilizables (includes)

Ambos viven en `templates/core/` y **se incluyen con parámetros**; no copiar su HTML adentro de la página:

```django
{% include "core/_score_ring.html" with pct=94 size="h-32 w-32 shrink-0" %}
{% include "core/_factor_bar.html" with pct=92 %}
```

- `_score_ring.html`: donut SVG 120×120, pista `violet-track`, avance blanco, label central `{{ pct }}%`. El tamaño se pasa como clases (`h-32 w-32`, `h-28 w-28`).
- `_factor_bar.html`: pista `h-2 rounded-full bg-violet-track` + relleno `bg-gradient-to-r from-violet-fill-start to-violet-fill-end`, ancho inline `{{ pct }}%`.

### 5.5 Navbar de la landing (píldora flotante) — EXCLUSIVO del landing

Vive en `templates/core/_landing_navbar.html` (la landing lo incluye con `{% include %}`). **No se usa dentro de la web**: allá se usa `partials/navbar.html`. Características: `fixed inset-x-0 top-0 z-50 px-4 pt-4 …`, contenedor `max-w-[1248px]`, píldora `rounded-full bg-paper/95 shadow-navbar ring-1 ring-white/70 backdrop-blur`, logo `DEV<span v-400>MATCH<span v-700>`, enlaces `text-sm font-semibold text-violet-600 hover:text-violet-800`, CTAs a la derecha, botón hamburguesa `md:hidden`. El menú móvil es un dropdown `#mobile-menu` y su script vive en `static/js/landing-menu.js` (vanilla, alterna `.hidden` + `aria-expanded`, cierra con Esc). **No agregues librerías JS.**

### 5.6 Avatares iniciales

Círculos `h-11 w-11 rounded-full border-2 border-white bg-paper text-sm font-extrabold text-violet-700`, apilados con `-space-x-3`.

### 5.7 Footer GLOBAL (todas las páginas EXCEPTO la landing)

Vive en `templates/partials/footer.html` y lo hereda todo el shell (`base.html`): fondo `bg-paper`, borde `border-t border-violet-200`, contenedor `max-w-[1248px]`, logo DEV/MATCH (`text-violet-400` + `text-violet-700`) enlazado a `{% url 'core:home' %}` y crédito `text-ink/70 "Syntax Error - Etapa 1"`.
**La landing NO lo usa:** tendrá un footer exclusivo propio (pendiente de diseño); el lugar reservado está marcado con un comentario al final de `home.html`.

---

## 6. Layout y reglas de composición

- **Contenedor único:** `max-w-[1248px]` con `px-4 sm:px-6 lg:px-16`, centrado con `mx-auto`.
- **Ritmo vertical de secciones:** `py-20 lg:py-24` en escritorio, 64px en móvil (la landing usa `py-20` con `pt-24` donde hace falta aire).
- **Gajos:** `space-y-6` para listas, `gap-10`/`gap-12` entre bloques grandes.
- **Anclas:** las secciones con id usan `scroll-mt-24` para no quedar pegadas a la navbar flotante.
- **Esquinas espejo:** el hero cierra violeta con `rounded-b-[56px]`; la sección siguiente abre papel con `rounded-t-[56px]` + `-mt-14`, dejando asomar la banda violeta por las esquinas (patrón de `#como-funciona`).
- **Transición de sección violeta→papel:** banda `h-24 bg-gradient-to-b from-violet-700 via-violet-400 to-paper`.

---

## 7. Reglas no negociables

1. **Dark-Card Rule:** todo card de "mecánica" es violeta profundo (`violet-700` o degradado `ray→deep`) con texto blanco; los cards claros llevan texto en tinta. Sobre violeta-400 o degradados lavanda, **texto oscuro** (`violet-800`/`ink`), nunca blanco.
2. **Rarity Rule:** el violeta intenso se concentra en paneles de mecánica y CTAs; el resto del lienzo es papel frío (≈70%).
3. **Halo Rule:** toda sombra es violeta difusa (`shadow-*` de la Sección 3.2); prohibido `rgba(0,0,0,…)` en grounds papel y sombras duras de offset.
4. **Contraste ≥ 4.5:1** en todo texto. Blanco solo sobre `violet-700` o más profundo; sobre `violet-400` → texto `violet-950`.
5. **Montserrat Scope Rule:** Montserrat solo donde está cargada (la landing); no promoverla a global.
6. **Sin fondo negro puro ni modo "coder dark"**: el dark mode (cuando exista) usa ground azul-gris `#141A2C` (ya definido en `theme.css`), acento siempre violeta.
7. **Iconos:** SVG inline (`stroke="currentColor" stroke-width="3" stroke-linecap="round"`), nunca glifos de sistema ni librerías de iconos.

---

## 8. Reglas de ingeniería de plantillas

- **Naming de includes:** archivos parciales reutilizables con prefijo `_` en la carpeta de su app (`templates/core/_score_ring.html`). Documentar el uso como comentario `{% comment %}…{% endcomment %}` arriba, con ejemplo de `{% include %}`.
- **Extracción:** si vas a reutilizar un fragmento de `home.html` en otra vista (navbar, footer, cards), **extráelo** a un `_nombre.html` y referencialo con `{% include %}` en lugar de copiar el HTML. Si el fragmento debería ser de todo el sitio (nav/footer global), lo solicita al Integrador para `templates/partials/` — no crees partials globales tuyos.
- **Bloques del shell** (`base.html`): `{% block title %}`, `{% block content %}`, `{% block extra_head %}`, `{% block extra_scripts %}`. Las vistas del shell usan `{% extends "base.html" %}`.
- **Scripts:** vanilla JS, sin librerías ni frameworks. Las páginas standalone referencian un archivo en `static/js/` con `<script src="{% static 'js/…js' %}" ></script>` al final del `<body>` (patrón: `landing-menu.js`); solo scripts muy cortos y de una sola página van inline. En páginas del shell, dentro de `{% block extra_scripts %}`.
- **Head de páginas standalone:** usar `{% include "core/_head.html" with title="…" description="…" %}` en vez de copiar las metas y los `<link>` de Montserrat/CSS.
- **Anclas de página:** los anclajes como `#como-funciona`, `#funciones`, `#roles` se resuelven como `href="#…"` y no cambian por ahora (las vistas de accounts/projects aún no existen).

---

## 9. Workflow de build

1. Los estilos se compilan desde `static/src/input.css` (+ `theme.css`) a `static/dist/output.css` con Tailwind.
2. `npm run build:css` → build único; `npm run watch:css` → rebuild automático.
3. **Quien edite clases/Tailwind debe regenerar el CSS y verificar** que las clases nuevas estén en `output.css`. Si una clase no tiene efecto, probablemente el build no se corrió.
4. Nunca editar `static/dist/output.css` a mano.

---

## 10. Ownership y coordinación

- `templates/base.html` y `templates/partials/` son **solo del Integrador**. Los pedidos van por chat o comentario de PR.
- `tailwind.config.js` (y cualquier archivo raíz) es **editable por el equipo pero exige aviso previo en el chat** antes de modificar.
- `theme.css` es la fuente de verdad de la paleta: agregar un color nuevo = avisar y actualizar el mapa comentado del archivo.
- Antes de crear "otra vez" algo que ya existe, revisar este documento y `home.html`. El objetivo es **extender la base, no replicarla**.

---

## 11. Anti-patrones (tabú)

- **No** inventar colores/sombras/fuentes fuera de las Secciones 3 y 5.
- **No** duplicar `_score_ring`/`_factor_bar` u otros componentes inline.
- **No** usar librerías JS, frameworks CSS ni iconos de sistema.
- **No** texto blanco sobre violeta-400/degradados claros (falla contraste).
- **No** sombras grises/negras duras, bordes gruesos, ni degradado de texto.
- **No** mezclar el patrón standalone con `partials/` del shell.
- **No** usar el navbar del landing (`core/_landing_navbar.html`) dentro de la web, ni el footer global (`partials/footer.html`) en la landing.
- **No** editar `base.html` / `partials/` ni `output.css`.