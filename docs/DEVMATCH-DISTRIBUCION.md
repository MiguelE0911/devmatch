# DEVMATCH - DISTRIBUCIÓN

Materia: Desarrollo de Software V
Ultima actualización: Septiembre 10, 2026 2:16 AM

# ORGANIZACIÓN Y DISTRIBUCIÓN DE TRABAJO – DEVMATCH

## Orden de implementación por ETAPAS para evaluación del profesor (Etapa por parcial)

| **ETAPA** | **DESCRIPCIÓN** |
| --- | --- |
| **Etapa 1: Infraestructura, Autenticación y Gestión Base (CR-01, CR-03, CR-10)** | Implementar la estructura base de la base de datos y configurar el entorno (Django, Tailwind CSS), diseñando y migrando el esquema completo del ORM desde el inicio (tablas presentes y pospuestas) para evitar migraciones destructivas a futuro. Sobre esta base, implementar el registro de usuarios, la validación estricta de Roles y permisos directamente en el servidor, y el formulario de Perfil técnico estructurado para garantizar que las habilidades se ingresen como datos estandarizados. Finalmente, desarrollar las vistas y modelos para la publicación de proyectos y configuración de vacantes, asegurando el manejo independiente de cupos, estados y tecnologías requeridas por rol. |
| **Etapa 2: Motor de Matchmaking y Flujo Transaccional (CR-04, CR-05, CR-07, CR-08, CR-09)** | Construir la capa lógica en Python que cruce las habilidades requeridas contra las del usuario, desarrollando la interfaz visual que desglose el porcentaje de compatibilidad y los factores técnicos considerados. Unificar el flujo de postulaciones con las operaciones atómicas de aceptación en la base de datos, controlando la concurrencia para evitar desbordamiento de cupos e implementando la advertencia por choques de disponibilidad. Programar la captura estática (Snapshot) del Match Score y guardarla en el registro de la postulación en el instante exacto en que el usuario aplica, mitigando recálculos costosos en el servidor. |
| **Etapa 3: Ciclo de Vida, Equipos, Auditoría y Reseñas (CR-02, CR-14, CR-17, CR-20)** | Habilitar la vista dinámica de roles cubiertos y vacantes pendientes conforme se acepten miembros, programando las reglas duras en el backend para bloquear transiciones de estado inválidas en los proyectos (Borrador, Publicado, Reclutando, Equipo completo, En desarrollo, Finalizado, Cancelado). En paralelo, activar el sistema de auditoría interna para registrar usuario, fecha y modificación en cada decisión crítica, y configurar las reglas de reseñas limitándolas exclusivamente a miembros de proyectos en estado Finalizado. |
| **Etapa 4: Integración Externa, Panel Administrativo y Servicios Complementarios (CR-11, CR-13, CR-18, CR-19)** | Desarrollar el consumo de la API de GitHub mediante la librería requests, implementando un manejo robusto de excepciones y tiempos de espera cortos para evitar que las caídas del servicio externo afecten el rendimiento de DevMatch. Consolidar en paralelo las herramientas de gestión operativas: habilitar la invitación proactiva a colaboradores, el panel de moderación para la gestión de reportes, y el dashboard administrativo con las métricas de éxito de la plataforma (cobertura de vacantes, tiempos, tasas de postulación y aceptación). |

## Orden de implementación por FASES para el equipo de desarrollo

| **FASE** | **DESCRIPCIÓN** |
| --- | --- |
| **FASE 1: Infraestructura y Estructura Relacional Base** | Configurar el entorno (Django, Tailwind CSS). Diseñar y migrar el esquema completo del ORM mapeando desde el inicio todas las tablas (presentes y propuestas) para evitar migraciones destructivas a futuro. |
| **FASE 2: Autenticación y Perfil Estructurado (CR-01, CR-10)** | Implementar el registro de usuarios, la validación estricta de Roles y permisos directamente en el servidor, y el formulario de Perfil técnico estructurado para garantizar que las habilidades se ingresen como datos estandarizados. |
| **FASE 3: CRUD de Proyectos y Estados de Vacantes (CR-03)** | Desarrollar las vistas y modelos para la publicación de proyectos y configuración de vacantes, asegurando el manejo independiente de cupos, estados y tecnologías requeridas por rol. |
| **FASE 4: Motor Transaccional de Postulación y Aceptación (CR-04, CR-08, CR-09)** | Unificar el flujo de postulaciones con las operaciones atómicas de aceptación en la base de datos. Controlar la concurrencia para evitar desbordamiento de cupos e implementar la advertencia por choques de disponibilidad. |
| **FASE 5: Algoritmo de Matchmaking y Explicabilidad (CR-05)** | Construir la capa lógica en Python que cruce las habilidades requeridas contra las del usuario. Desarrollar la interfaz visual que desglose el porcentaje de compatibilidad y los factores técnicos considerados. |
| **FASE 6: Congelamiento Histórico de Evaluaciones (CR-07)** | Programar la captura estática (Snapshot) del Match Score y guardarla en el registro de la postulación en el instante exacto en que el usuario aplica, mitigando recálculos costosos en el servidor. |
| **FASE 7: Composición de Equipos y Ciclo de Vida (CR-02, CR-14)** | Habilitar la vista dinámica de roles cubiertos y vacantes pendientes. Programar las reglas duras en el backend para bloquear transiciones de estado inválidas en los proyectos. |
| **FASE 8: Auditoría y Reseñas Verificadas (CR-17, CR-20)** | Activar el sistema de auditoría interna para registrar usuario, fecha y modificación en las decisiones críticas. Configurar las reglas de reseñas limitándolas exclusivamente a miembros de proyectos en estado Finalizado. |
| **FASE 9: Integración Externa con GitHub (CR-11)** | Desarrollar el consumo de la API mediante la librería requests. Implementar un manejo robusto de excepciones y tiempos de espera cortos para evitar que las caídas de GitHub afecten el rendimiento de DevMatch. |
| **FASE 10: Panel Administrativo, Métricas e Invitaciones (CR-13, CR-18, CR-19)** | Consolidar las herramientas de gestión operativas: habilitar la invitación proactiva a colaboradores, el panel de moderación para reportes y el dashboard de métricas de éxito (cobertura, tiempos, postulaciones). |

---

## Diferencia entre Etapa y Fase

Estos dos términos no son sinónimos ni una simple renombrada del mismo concepto:

- **FASE**: unidad de trabajo técnica e interna del equipo de desarrollo. Es una referencia de planificación para nosotros mismos, más corta y granular, que nos ayuda a ordenar en qué secuencia se construyen las piezas del sistema (ej. Fase 5: solo el algoritmo de matchmaking).
- **ETAPA**: ciclo de desarrollo completo que se entrega y evalúa formalmente con el profesor. Agrupa entre 2 y 3 fases relacionadas en un incremento funcional y demostrable del sistema (ej. la Etapa 2 agrupa las Fases 4, 5 y 6, porque juntas conforman el "flujo de matchmaking y postulación" completo, que es lo que tiene sentido mostrar como avance).

En la práctica: las FASES son la guía interna de "qué construir primero", las ETAPAS son los cortes de entrega. El repositorio y las ramas de git se organizan por ETAPA, no por fase, porque la fase es demasiado granular para justificar un ciclo de rama/PR/merge propio.

---

# DISTRIBUCIÓN DE EQUIPO

5 integrantes: 1 Integrador + Squad A (Datos y Lógica, 2 personas) + Squad B (Interfaz y Vistas, 2 personas).

### ROL DEL INTEGRADOR (todo terreno)

- Define la estructura base del repositorio y del proyecto Django (apps por dominio).
- Aprueba y ejecuta los merges hacia main en cada etapa.
- Genera los fixtures (datos de prueba) que Squad B necesita para maquetar sin depender del backend real.
- Ajusta nombres de campos, estructuras de datos y pequeños desajustes entre lo que entrega Squad A y lo que necesita Squad B, ANTES del merge (ver nota al final sobre el contrato de datos).
- Apoya puntualmente a cualquiera de los dos squads cuando haya cuello de botella o falta de tiempo.
- Actúa como sujeto de prueba UX: revisa flujos desde la perspectiva de un usuario nuevo, detecta detalles de usabilidad que los squads no alcanzan a notar por estar enfocados en su propia parte.
- Dueño de la app "core" (permisos base, mixins, templates compartidos).
- Dueño de los archivos compartidos de plantilla (`base.html`, `partials/`) — ver detalle en la sección de archivos compartidos más abajo.
- Crea y gestiona la infraestructura.

### ETAPA 1 — Infraestructura, Autenticación y Gestión Base
**(CR-01, CR-03, CR-10) — Correspondiente a las Fases 1-3**

**Squad A (Datos y Lógica):**

- Diseña y migra el esquema completo del ORM, mapeando desde el inicio todas las tablas (presentes y pospuestas) para evitar migraciones destructivas.
- Implementa validación de roles y permisos a nivel servidor.
- Modela el Perfil técnico estructurado (habilidades, nivel, tecnologías, experiencia, disponibilidad).
- Modela Proyecto y Vacante (cupos, estados, tecnologías requeridas).

**Squad B (Interfaz y Vistas):**

- Maqueta Login y Registro.
- Maqueta el formulario visual del Perfil técnico estructurado en Tailwind.
- Maqueta las vistas de creación y publicación de Proyecto/Vacante.

**Integrador:**

- Configura repo, entorno Django + Tailwind, convención de ramas.
- Genera fixtures de usuarios y roles para que Squad B no dependa del modelo real terminado.
- Ajusta nombres/estructura de campos entre lo que define Squad A y lo que espera Squad B antes de fusionar a main.

### ETAPA 2 — Motor de Matchmaking y Flujo Transaccional
**(CR-04, CR-05, CR-07, CR-08, CR-09) — Correspondiente a las Fases 4-6**

**Squad A (Datos y Lógica):**

- Escribe el algoritmo de matching en Python puro.
- Implementa aceptación transaccional con control de concurrencia (evitar desbordamiento de cupos).
- Implementa la advertencia por choque de disponibilidad.
- Programa el snapshot del Match Score al momento de postular.

**Squad B (Interfaz y Vistas):**

- Maqueta el Dashboard visual del Match Score (barras de progreso, desglose de factores).
- Maqueta vistas de "Mis Proyectos" y "Mis Postulaciones".
- Diseña alertas visuales de éxito/error (ej. postulación duplicada).

**Integrador:**

- Genera fixtures de vacantes y postulaciones con distintos escenarios de score, para que Squad B pueda maquetar sin esperar el algoritmo terminado.
- Conecta la lógica real del algoritmo con las vistas del frontend y depura errores de integración.

### ETAPA 3 — Ciclo de Vida, Equipos, Auditoría y Reseñas
**(CR-02, CR-14, CR-17, CR-20) — Correspondiente a las Fases 7-8**

**Squad A (Datos y Lógica):**

- Programa las reglas duras de transición de estado del proyecto (Borrador, Publicado, Reclutando, Equipo completo, En desarrollo, Finalizado, Cancelado).
- Implementa el registro de auditoría interna (usuario, fecha, hora, acción, registro afectado).
- Implementa la regla de reseñas: solo miembros de proyectos Finalizados pueden crear reseñas.

**Squad B (Interfaz y Vistas):**

- Construye la vista dinámica de composición de equipo (roles cubiertos/pendientes).
- Maqueta la interfaz de reseñas.
- Maqueta la vista de historial de auditoría para administradores.

**Integrador:**

- Genera fixtures de equipos en distintos estados para validar que las reseñas y transiciones se comporten como se espera.
- Prueba de regresión: valida que las transiciones de estado no rompan datos ya existentes de etapas anteriores.

### ETAPA 4 — Integración Externa, Panel Administrativo y Servicios Complementarios
**(CR-11, CR-13, CR-18, CR-19) — Correspondiente a las Fases 9-10**

**Squad A (Datos y Lógica):**

- Desarrolla el cliente de la API de GitHub (manejo de excepciones, timeouts, caídas del servicio).
- Implementa la lógica de invitación proactiva a colaboradores.
- Implementa la lógica de reportes y moderación.
- Implementa las agregaciones ORM para las métricas del dashboard.

**Squad B (Interfaz y Vistas):**

- Construye el panel de moderación para administradores.
- Construye el dashboard de métricas con gráficos.
- Maqueta la UI de invitación a colaboradores.
- Implementa la exportación de reportes en CSV/PDF.

**Integrador:**

- Aísla y prueba el consumo de la API de GitHub simulando caídas del servicio.
- Coordina la revisión final antes del cierre del proyecto.

### NOTA SOBRE EL "CONTRATO DE DATOS"

En lugar de exigir que ambos squads se pongan de acuerdo por adelantado en cada nombre de campo o forma de respuesta (algo difícil de anticipar hasta que ya se está programando), el Integrador asume ese ajuste de forma directa: revisa lo que entrega Squad A y lo que consume Squad B, corrige discrepancias, y solo entonces aprueba el merge a main. Esto evita bloquear a los squads con reuniones de alineación y concentra la responsabilidad de consistencia en un solo punto. Se evaluará en la primera etapa si este enfoque sigue siendo suficiente o si conviene formalizar algo más a partir de la Etapa 2, cuando el número de piezas conectadas crece.

---

# DESGLOSE DE RAMAS Y PROCEDIMIENTO GIT

### RAMAS PRINCIPALES

- `main` → siempre estable, solo recibe merge desde `etapa-N-base` cuando el integrador lo aprueba. Nadie hace push directo aquí.
- `etapa-N-base` → rama de integración de la etapa actual, nace de `main`. Aquí se juntan todas las tareas mientras se desarrolla.

### RAMAS DE TAREA — ETAPA 1

- `etapa-1/core-setup` → Integrador. Config del proyecto, Tailwind, app `core`, comando de fixtures/seed, `base.html`/`partials/`.
- `etapa-1/accounts-modelos` → Squad A - Persona 1. Archivos: `accounts/models.py`, `accounts/admin.py`, `accounts/migrations/`.
- `etapa-1/projects-modelos` → Squad A - Persona 2. Archivos: `projects/models.py`, `projects/services.py`, `projects/admin.py`, `projects/migrations/`.
- `etapa-1/accounts-vistas` → Squad B - Persona 1. Archivos: `accounts/forms.py`, `accounts/views.py`, `accounts/urls.py`, `templates/accounts/`.
- `etapa-1/projects-vistas` → Squad B - Persona 2. Archivos: `projects/forms.py`, `projects/views.py`, `projects/urls.py`, `templates/projects/`.

**REGLA DE ORO**: cada persona tiene su propia rama y su propio conjunto de archivos. Nadie más edita esos archivos mientras esa rama esté abierta. Si necesitas algo que está en el archivo de otra persona, avísale en el chat del equipo en vez de editarlo tú.

### PATRÓN GENERAL DE RAMAS (aplica a cualquier etapa futura)

El nombre de rama siempre sigue la misma fórmula, cambiando solo el número de etapa y el nombre de la app/tarea:

```
etapa-N/<app>-<tipo-de-tarea>
```

Ejemplo aplicado a la Etapa 2:

```
etapa-2/matching-engine         → algoritmo de compatibilidad (Squad A)
etapa-2/applications-modelos    → modelo Postulación + snapshot (Squad A)
etapa-2/applications-servicios  → aceptación transaccional (Squad A)
etapa-2/dashboard-vistas        → maquetado del Match Score (Squad B)
etapa-2/mis-proyectos-vistas    → vistas "Mis Proyectos"/"Mis Postulaciones" (Squad B)
```

Al iniciar cada nueva etapa, el Integrador crea `etapa-N-base` desde `main` y define junto con el equipo el listado de ramas de tarea de esa etapa, siguiendo este mismo patrón y repartiendo archivos igual que en la Etapa 1 (una persona = un conjunto de archivos claramente delimitado).

### PROCEDIMIENTO PASO A PASO (qué hacer cuando te asignan una tarea)

1. **Actualiza tu copia local de la rama de etapa antes de empezar.**

```
git checkout etapa-1-base
git pull origin etapa-1-base
```

1. **Crea tu rama de tarea a partir de la rama de etapa** (nunca desde `main` directamente, y nunca reutilices la rama de otra persona).

```
git checkout -b etapa-1/accounts-modelos
```

1. **Trabaja solo dentro de los archivos que te corresponden** según la tabla de ramas de tarea. Si tu tarea requiere tocar un archivo fuera de tu lista, para y coordina con el dueño de ese archivo o con el integrador antes de editarlo. Si el archivo es uno de los compartidos (ver sección "Propiedad de archivos compartidos"), sigue esa regla específica.
2. **Haz commits pequeños y frecuentes**, no uno gigante al final.

```
git add apps/accounts/models.py
git commit -m "accounts: agrega modelo Usuario con roles"
```

1. **Migraciones — regla especial:** solo la persona dueña del `models.py` de esa app corre `makemigrations` para esa app en esa etapa. Si dos personas generan migraciones de la misma app al mismo tiempo, se generan archivos duplicados y eso rompe todo. Ejemplo: solo Persona A1 corre `makemigrations accounts`.

```
python manage.py makemigrations accounts
git add apps/accounts/migrations/
git commit -m "accounts: migración inicial de Usuario y Perfil"
```

1. **Sube tu rama al repositorio remoto** (no a la rama de etapa directamente, a tu propia rama de tarea).

```
git push origin etapa-1/accounts-modelos
```

1. **Antes de abrir el PR, verifica la Definición de Terminado** (ver sección siguiente).
2. **Abre un Pull Request de tu rama hacia la rama de etapa** (no hacia `main`). En la descripción del PR indica brevemente qué hiciste y qué archivos tocaste.
3. **El integrador revisa y fusiona el PR.** Solo el integrador (o quien él delegue puntualmente) hace merge hacia la rama de etapa. Esto evita que dos personas fusionen al mismo tiempo y generen conflictos por sorpresa.
4. **Si git te muestra un conflicto al hacer push o al abrir el PR:** NO intentes resolverlo solo si no te sientes seguro. Detente, avisa al integrador de inmediato y espera indicaciones. Es preferible perder cinco minutos preguntando que forzar un push (`-force`) y borrar el trabajo de otro.
5. **Al terminar toda la etapa**, el integrador fusiona `etapa-N-base` → `main`, etiqueta el commit (ej. `v1.0-etapa1`) y abre `etapa-(N+1)-base` desde `main` para reiniciar el ciclo con las nuevas ramas de tarea.

### DEFINICIÓN DE "TERMINADO" — checklist antes de abrir tu PR

Antes de subir tu rama y abrir el Pull Request, verifica estos puntos. Esto evita que el Integrador tenga que rebotar PRs a medio hacer y ahorra tiempo a todo el equipo:

```
□ El proyecto corre sin errores localmente (python manage.py runserver)
□ Si tocaste modelos: las migraciones están generadas y committeadas
□ No dejaste código comentado o prints de debug
□ Actualizaste solo los archivos que te correspondían según tu rama de tarea
```

### PROTECCIÓN DE RAMAS EN GITHUB (configuración técnica, no solo acuerdo verbal)

Para que la regla de "nadie hace push directo a `main` ni a `etapa-N-base`" no dependa de que cada persona la recuerde, se configura como restricción real del repositorio:

1. Entrar a **Settings → Branches** del repositorio en GitHub.
2. Agregar una **Branch protection rule** para `main`.
3. Activar **"Require a pull request before merging"**.
4. Repetir el mismo proceso para `etapa-1-base` (y para cada `etapa-N-base` que se cree más adelante).

Con esto, aunque alguien intente hacer push directo a esas ramas por error, GitHub lo va a rechazar automáticamente — el error se vuelve imposible en vez de solo "no recomendado".

### RESUMEN DE LO QUE NUNCA DEBEN HACER

- No editar `main` ni la rama de etapa (`etapa-N-base`) directamente.
- No compartir una misma rama de tarea entre dos personas.
- No correr `makemigrations` sobre una app que no es la tuya en esa etapa.
- No editar `base.html` o `partials/` directamente — coordinar con el Integrador.
- No modificar `requirements.txt`, `.env.example` o `config/settings/base.py` sin avisar antes en el chat del equipo.
- No hacer `push --force` sin avisarle antes al integrador.
- No dejar una rama de tarea abierta por mucho tiempo sin subir avances — dado el ritmo de trabajo del equipo, no hay un límite estricto de días, pero entre más vieja quede sin actualizarse respecto a la rama de etapa, más probable es el conflicto al momento de fusionar.