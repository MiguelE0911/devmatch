**UNIVERSIDAD TECNOLÓGICA DE PANAMÁ**
**CENTRO REGIONAL DE CHIRIQUÍ**
**FACULTAD DE INGENIERÍA DE SISTEMAS COMPUTACIONALES**

---

# SOLICITUD FORMAL DE CAMBIO DE REQUERIMIENTOS

## Proyecto: DevMatch

*Plataforma de Formación y Gestión de Equipos de Software*

| | |
|---|---|
| **Asignatura** | Desarrollo de Software V |
| **Cliente / solicitante** | MSc. José Mendoza |
| **Equipo de desarrollo** | Syntax Error |
| **Documento** | Solicitud formal de cambio de requerimientos (RFC) |
| **Versión** | 1.0 - Final |
| **Fecha de emisión** | 4 de septiembre de 2026 |

> **Estado del documento: SOLICITUD EMITIDA POR EL CLIENTE.** Este documento complementa y modifica el alcance original de DevMatch. Los cambios deberán ser analizados e incorporados al proceso de planificación del equipo.

---

## ANOTACIONES DEL EQUIPO (actualizadas el 22 de octubre de 2026)

> El texto de este documento fue emitido por el cliente (MSc. José Mendoza, 4 de septiembre de 2026) y
> **se conserva íntegro**. Lo único que se agregó son las columnas y notas de estado que verifican,
> una por una, qué de cada requerimiento existe hoy en el código al cierre de la Etapa 2 y en el
> avance de la Etapa 3.
>
> Estas notas no reinterpretan la solicitud: solo contrastan la RFC contra
> `main` @ `cf30c60` (tag `v2.0-etapa-2`) y el estado actual de la rama `etapa-3-base`
> (CI y documentación de roles; sin cambios de dominio). Los entregables que la sección 8 exige
> (MoSCoW, matriz de impacto, dependencias, riesgos, plan) ya fueron producidos y entregados por
> el equipo; aquí solo se refleja el estado técnico.

**Leyenda de la columna "Estado en el código":**

| Marca | Significado |
|---|---|
| `LISTO` | Implementado y cubierto por tests automáticos |
| `LISTO (con limitación)` | Implementado y probado, con una deuda funcional documentada |
| `PARCIAL` | Una parte sustantiva existe y está probada; falta un flujo o una pantalla clave |
| `MODELO LISTO (falta servicio y UI)` | La tabla y las restricciones existen; falta el código que la use y su pantalla |
| `NO IMPLEMENTADO` | No existe implementación |
| `FUERA DE ALCANCE` | Descartado o pospuesto en el MoSCoW entregado; no se trabaja en ello |

La Etapa 1 dejó completa la **capa de datos** (20 tablas, 6 funciones y 19 triggers). La Etapa 2
construyó sobre ella el flujo principal: autenticación y perfil, feed, proyectos y vacantes,
Match Score explicable, snapshot de postulación, aceptación transaccional y control de carga.
La Etapa 3 debe cerrar la composición real del equipo, el alta de reseñas, el reporte de usuarios
y la auditoría de decisiones.

---

## 1. Antecedentes

La propuesta original de DevMatch plantea una plataforma web para conectar creadores de proyectos universitarios con estudiantes colaboradores. El sistema contempla publicación de proyectos y vacantes, postulación a roles y un algoritmo de matchmaking que calcula un porcentaje de compatibilidad técnica entre el perfil del estudiante y las oportunidades disponibles.

El alcance inicial también considera integración con GitHub para mostrar repositorios, vistas de proyectos y postulaciones, notificaciones básicas, filtros, reseñas, tutorial y mensajería. El cliente considera que esta base es adecuada, pero solicita ampliar el control del reclutamiento, la composición del equipo, la explicabilidad del Match Score, los estados, la disponibilidad, la validación de habilidades y la trazabilidad.

> **Decisión del cliente:** DevMatch ya no deberá limitarse a calcular un porcentaje y permitir postulaciones. La plataforma deberá administrar el proceso completo desde la publicación de una vacante hasta la aceptación del colaborador, la formación del equipo y el cierre verificable de la colaboración.

---

## 2. Propósito de la solicitud

El propósito de esta solicitud es comunicar formalmente las nuevas necesidades del cliente y establecer las condiciones mínimas que deberá satisfacer la siguiente versión de DevMatch.

El equipo de desarrollo deberá revisar el impacto de estos cambios sobre los requisitos originales, proponer una nueva priorización MoSCoW, identificar dependencias y presentar al cliente un plan de implementación actualizado. La clasificación indicada en este documento representa el nivel de necesidad expresado por el cliente y no sustituye el análisis técnico que debe realizar el equipo.

---

## 3. Decisiones de alcance del cliente

- DevMatch deberá manejar al menos los roles Administrador, Creador y Colaborador, con acciones y restricciones diferenciadas.
- Los proyectos y vacantes deberán manejar estados y transiciones válidas; no se aceptará que cualquier acción pueda ejecutarse en cualquier momento.
- Cada postulación deberá tener un estado formal y conservar el Match Score calculado al momento de postularse.
- El Match Score deberá ser explicable: el usuario deberá poder conocer qué factores influyeron en su porcentaje de compatibilidad.
- La aceptación de un colaborador deberá ocupar una vacante, crear la membresía del equipo e impedir aceptaciones que excedan la capacidad definida.
- El sistema deberá considerar disponibilidad y carga del colaborador para evitar asignaciones incompatibles entre proyectos activos.
- Las reseñas, métricas y reputación deberán originarse en colaboraciones realmente aceptadas y finalizadas dentro de la plataforma.

---

## 4. Requerimientos de cambio solicitados

Los siguientes requerimientos se incorporan al alcance solicitado por el cliente. La columna "Nivel de necesidad" expresa la importancia del requerimiento para el cliente. El equipo deberá traducir esta necesidad a una nueva matriz MoSCoW y justificar cualquier propuesta de negociación.

| ID | Cambio | Solicitud del cliente | Nivel de necesidad | Condición | Estado en el código (Etapa 2 cerrada / Etapa 3 en curso) |
|---|---|---|---|---|---|
| CR-01 | Roles y permisos | Implementar Administrador, Creador y Colaborador, con permisos diferenciados y validación tanto en interfaz como en servidor. | Crítico | No negociable | `LISTO` — mixins de rol y `creador_required` validan en servidor; 5 tests. Los roles son contextuales (Creador = dueño de un proyecto, Colaborador = se postuló), no un enum. |
| CR-02 | Ciclo de vida del proyecto | Manejar Borrador, Publicado, Reclutando, Equipo completo, En desarrollo, Finalizado y Cancelado con transiciones controladas. | Crítico | No negociable | `LISTO` — `TRANSICIONES_VALIDAS` en el servicio, replicado en el formulario y en un trigger de Postgres; 4 tests de transición. |
| CR-03 | Estados de vacantes | Cada vacante deberá manejar cupos, estado y tecnologías/habilidades requeridas; deberá cerrarse automáticamente al cubrirse. | Crítico | No negociable | `LISTO` — el trigger recalcula `cupos_ocupados` y mueve la vacante a `cubierta`; test que confirma que el campo es de solo lectura en el admin. |
| CR-04 | Estados de postulación | Manejar Pendiente, Preseleccionada, Aceptada, Rechazada y Retirada, conservando historial y evitando postulaciones duplicadas. | Crítico | No negociable | `PARCIAL` — los 5 estados, el índice único parcial `ux_postulacion_activa_unica`, el retiro y la pantalla "Mis Postulaciones" con sus 5 pestañas están implementados y probados. **Pendiente Etapa 3:** una postulación abierta de un proyecto cerrado se muestra como "rechazada" solo en la vista (`applications/views.py`); falta el cascade real en la base (servicio/trigger) y reparar las filas existentes. |
| CR-05 | Match Score explicable | Mostrar el porcentaje y un desglose de factores considerados, por ejemplo habilidades, nivel, tecnologías, experiencia y disponibilidad. | Crítico | No negociable | `LISTO` — `matching/engine.py` calcula habilidades, nivel, tecnologías, experiencia y disponibilidad con los pesos configurados. El score y sus factores se muestran en el feed, las vacantes, el detalle del proyecto y "Mis Postulaciones" mediante `_score_ring.html`, `_factor_bar.html` y paneles de explicabilidad. Cubierto por `test_engine.py`. |
| CR-06 | Pesos configurables | Permitir al Creador definir o seleccionar pesos para los criterios de compatibilidad de una vacante dentro de límites establecidos. | Alto | Negociable | `FUERA DE ALCANCE` — pospuesto en el MoSCoW. La tabla `configuracion_pesos_matching` existe con sus restricciones (los pesos suman 1.0, un solo perfil activo) y el motor la lee, pero no hay pantalla para que el Creador ajuste pesos; los valores por defecto viven en `matching/constants.py`. |
| CR-07 | Snapshot del Match Score | Guardar el Score y sus factores al postularse para que cambios posteriores del perfil no alteren la evaluación histórica. | Crítico | No negociable | `LISTO` — `crear_postulacion` calcula el score y congela `match_score`, `match_factores` y los pesos usados al momento de postular. Los tests confirman que el snapshot se persiste y no cambia aunque el perfil se modifique después. |
| CR-08 | Aceptación transaccional | Al aceptar una postulación, ocupar el cupo, crear la membresía del equipo y evitar aceptar más personas que las requeridas. | Crítico | No negociable | `LISTO` — `aceptar_postulacion` corre en una transacción con locks en postulación, vacante y perfil; valida cupo, membresía duplicada y carga, marca la postulación como aceptada y crea `EquipoMembresia`. Probado con aceptación concurrente sobre una vacante de un cupo (`test_concurrencia.py`) y con vacante llena. |
| CR-09 | Disponibilidad y carga | Registrar disponibilidad semanal y limitar o advertir nuevas aceptaciones cuando existan compromisos incompatibles. | Crítico | No negociable | `LISTO (con limitación)` — `calcular_carga` y `verificar_carga` comparan la disponibilidad declarada contra las membresías activas y bloquean la aceptación con `CargaIncompatible`. Limitación: cada membresía consume una constante `HORAS_POR_MEMBRESIA_ACTIVA`, no las horas estimadas de la vacante. |
| CR-10 | Perfil técnico estructurado | Registrar habilidades, nivel, tecnologías, intereses, experiencia y disponibilidad como datos estructurados utilizables por el algoritmo. | Crítico | No negociable | `LISTO` — catálogos de habilidades, tecnologías e intereses con tablas puente, más experiencia y disponibilidad. Consumibles en filtros y consultas. |
| CR-11 | Validación con GitHub | Usar GitHub para complementar evidencia técnica con repositorios, lenguajes y actividad disponible, manejando fallos del servicio externo. | Alto | Negociable | `FUERA DE ALCANCE` — etapa 4. Solo existe `Perfil.github_username` como dato declarado; no hay cliente de API ni verificación de repositorios. |
| CR-12 | Recalcular recomendaciones | Al modificar habilidades o disponibilidad, recalcular el ranking de proyectos recomendados sin modificar postulaciones históricas. | Alto | Negociable | `FUERA DE ALCANCE` — descartado en el MoSCoW. |
| CR-13 | Invitación a colaboradores | Permitir al Creador invitar a un usuario a una vacante; el invitado podrá aceptar, rechazar o ignorar la invitación. | Alto | Negociable | `MODELO LISTO (falta servicio y UI)` — `Invitacion` con los estados pendiente, aceptada, rechazada e ignorada, y su admin. No hay servicio, vistas, URLs ni pantalla para invitar o responder. |
| CR-14 | Composición del equipo | Mostrar roles cubiertos, roles faltantes y complementariedad básica de habilidades del equipo conforme se acepten miembros. | Crítico | No negociable | `NO IMPLEMENTADO` — la tarjeta `_equipo.html` está maquetada e incluida en el detalle del proyecto, pero muestra solo al creador y un texto que anuncia que los miembros llegarán en Etapa 3. Falta conectarla a `EquipoMembresia` y a las vacantes para calcular roles cubiertos, faltantes y complementariedad. |
| CR-15 | Hitos del proyecto | Permitir definir hitos básicos con fecha, estado y responsable para evidenciar que la colaboración pasó a una fase de ejecución. | Alto | Negociable | `FUERA DE ALCANCE` — descartado en el MoSCoW. |
| CR-16 | Mensajería del equipo | Habilitar mensajería únicamente entre miembros aceptados de un proyecto, conservando fecha, remitente y proyecto asociado. | Alto | Negociable | `FUERA DE ALCANCE` — descartado en el MoSCoW. La comunicación se delega a herramientas externas. |
| CR-17 | Reseñas verificadas | Solo participantes de un proyecto Finalizado podrán calificarse o dejar reseñas según las reglas definidas. | Crítico | No negociable | `PARCIAL` — la garantía está completa y probada en la base: el trigger rechaza la reseña si el proyecto no está Finalizado, si autor y destinatario no fueron miembros reales o si hay autorreseña. El perfil ya muestra reseñas recibidas, pero no existe formulario, vista ni servicio para crear una reseña. |
| CR-18 | Moderación y reportes | Permitir reportar proyectos, perfiles o conductas y gestionar el reporte desde un panel administrativo con estado y decisión. | Alto | Negociable | `PARCIAL` — `Reporte` con los estados pendiente, en_revision, resuelto y descartado, y `ReporteAdmin` para gestionarlo. Falta el flujo de usuario para reportar y automatizar `resuelto_por`/`resuelto_en` al resolver. |
| CR-19 | Indicadores de éxito | Mostrar métricas como vacantes cubiertas, tiempo promedio de cobertura, postulaciones, aceptación, proyectos finalizados y Match Score promedio. | Alto | Negociable | `NO IMPLEMENTADO` — etapa 4, sin app de dashboard. |
| CR-20 | Auditoría de decisiones | Registrar cambios críticos de estados, aceptación/rechazo de postulaciones, membresías y decisiones administrativas con usuario, fecha y hora. | Crítico | No negociable | `NO IMPLEMENTADO` — la tabla `auditoria_logs` existe y es inmutable por trigger, pero **nada escribe en ella**: no existe `audit/services.py` y quedan TODOs explícitos en `accounts/admin.py`, `applications/services.py` y `projects/views.py`. Es el requerimiento crítico con menos avance y el principal pendiente de Etapa 3. |

---

## 5. Reglas de negocio que deberán respetarse

### 5.1 Roles, proyectos y vacantes

- Todo usuario deberá tener un rol funcional y las operaciones sensibles deberán validarse en el servidor.
- Solo el Creador propietario o un Administrador podrá modificar un proyecto, según los permisos definidos.
- Un proyecto en Borrador no será visible para postulaciones; un proyecto Finalizado no podrá abrir nuevas vacantes.
- Una vacante deberá indicar rol, cantidad de cupos, tecnologías requeridas y estado.
- El número de miembros aceptados no podrá superar la capacidad total definida por las vacantes.

### 5.2 Postulaciones y aceptación

- Un Colaborador no podrá postularse dos veces a la misma vacante mientras exista una postulación activa.
- La aceptación de una postulación deberá realizarse de forma consistente con el cupo disponible.
- Al cubrirse el último cupo, la vacante deberá impedir nuevas aceptaciones y reflejar su nuevo estado.
- Retirar o rechazar una postulación deberá conservar el historial sin eliminar el registro.

### 5.3 Match Score y criterios de compatibilidad

- El Match Score deberá calcularse con criterios identificables y no como un número sin explicación.
- El sistema deberá conservar el Score y los factores utilizados al momento de cada postulación.
- Los cambios posteriores del perfil podrán afectar nuevas recomendaciones, pero no modificar evaluaciones históricas.
- Si se utilizan pesos configurables, la suma y los rangos permitidos deberán validarse.
- El equipo deberá documentar la fórmula o estrategia utilizada y proporcionar casos de prueba reproducibles.

### 5.4 Perfil, GitHub y evidencia técnica

- Las habilidades utilizadas para el matching deberán almacenarse de forma estructurada y no únicamente en texto libre.
- La información obtenida desde GitHub deberá distinguirse de la información declarada manualmente por el usuario.
- Una falla temporal de GitHub no deberá impedir que el usuario acceda al resto de DevMatch.
- Las credenciales o tokens de servicios externos no deberán exponerse en páginas, logs o repositorios públicos.

### 5.5 Disponibilidad y formación del equipo

- Cada Colaborador deberá poder registrar una disponibilidad mínima utilizable en la evaluación de compatibilidad.
- Antes de aceptar una postulación, el sistema deberá revisar la carga o compromisos definidos para el usuario.
- El equipo deberá mostrar qué roles están cubiertos y cuáles siguen vacantes.
- La complementariedad del equipo deberá derivarse de los perfiles y roles aceptados, no de un valor escrito manualmente.
- Un usuario retirado del equipo conservará su historial de participación y no deberá desaparecer de los registros anteriores.

### 5.6 Estados, cierre y reseñas

- Las transiciones de proyecto y postulación deberán respetar el estado actual y las reglas del proceso.
- Un proyecto solo podrá Finalizar cuando cumpla las condiciones mínimas definidas por el equipo y aprobadas por el cliente.
- Las reseñas deberán estar vinculadas a una membresía real en un proyecto Finalizado y no podrán duplicarse arbitrariamente.

### 5.7 Notificaciones, moderación y auditoría

- Las decisiones relevantes de postulación deberán generar la notificación definida para los usuarios afectados.
- Los reportes administrativos deberán conservar motivo, estado, decisión y responsable de la resolución.
- Las acciones críticas deberán conservar trazabilidad suficiente para reconstruir quién hizo qué y cuándo.

> **Transición mínima esperada:** Borrador → Publicado → Reclutando → Equipo completo → En desarrollo → Finalizado. La ruta hacia Cancelado deberá definirse desde los estados permitidos. No se aceptarán transiciones arbitrarias ni acciones incompatibles con el estado actual.

---

## 6. Criterios de aceptación del cliente para los cambios no negociables

Los siguientes criterios serán utilizados por el cliente como base para validar la implementación. El equipo podrá ampliar estos criterios, pero no deberá reducirlos sin una negociación documentada.

| ID | Criterio de aceptación mínimo | Verificado hoy por |
|---|---|---|
| CR-01 | Un Colaborador no puede ejecutar operaciones exclusivas del Creador o Administrador; los permisos se validan aunque se intente acceder directamente a una URL. | `test_el_creador_autenticado_tiene_permiso`, `test_un_usuario_distinto_no_tiene_permiso`, `test_usuario_anonimo_no_tiene_permiso`, `test_sin_objeto_no_tiene_permiso` |
| CR-02 | Un proyecto recorre únicamente transiciones autorizadas. Un proyecto Finalizado no puede regresar libremente a Reclutando ni recibir nuevas postulaciones. | `test_transicion_valida_actualiza_el_estado`, `test_transicion_invalida_lanza_excepcion_y_no_guarda`, `test_estados_terminales_no_permiten_ninguna_transicion` |
| CR-03 | Una vacante con un único cupo pasa a cubierta al aceptar al colaborador correspondiente y no admite una segunda aceptación. | `test_aprobar_pasa_a_aceptada_y_ocupa_cupo`, `test_aprobar_sin_cupos_no_acepta`, `test_cupos_ocupados_es_readonly_en_vacante` y `test_dos_aceptaciones_simultaneas_en_vacante_de_un_cupo`. |
| CR-04 | El sistema rechaza una postulación duplicada y conserva los cambios de estado de una postulación existente. | `test_solo_una_postulacion_activa_por_vacante_y_postulante`, `test_puede_repentirse_despues_de_un_rechazo`, `test_retirar_la_postulacion_la_conserva_en_la_base` |
| CR-05 | El Match Score muestra porcentaje y factores que permiten explicar por qué un perfil obtiene mayor o menor compatibilidad. | `test_engine.py` (`test_match_perfecto_da_100`, `test_forma_del_json_coincide_con_devmatch_bd`) y pruebas de vistas que verifican el score y su desglose en feed, vacantes y postulaciones. |
| CR-07 | Si el usuario cambia posteriormente sus habilidades, la postulación conserva el Score y el desglose registrado al momento de aplicar. | `test_crea_postulacion_con_snapshot_completo`, `test_snapshot_no_cambia_si_el_perfil_cambia_despues`, `test_post_crea_postulacion_con_snapshot_del_motor` y `test_snapshot_de_factores_se_persiste_sin_sobrescribirse`. |
| CR-08 | Al aceptar una postulación se crea la membresía del equipo y se actualiza el cupo sin permitir exceder la capacidad. | `test_aceptar_desde_pendiente_crea_membresia_y_marca_aceptada`, `test_vacante_llena_lanza_excepcion_y_no_acepta`, `test_ya_miembro_del_proyecto_por_otra_vacante_no_se_puede_aceptar` y `test_dos_aceptaciones_simultaneas_en_vacante_de_un_cupo`. |
| CR-09 | Un usuario con compromisos incompatibles recibe una restricción o advertencia definida antes de ser aceptado en una nueva colaboración. | `test_carga_incompatible_bloquea_la_aceptacion_y_no_cambia_nada`, `test_limite_exacto_permite_la_aceptacion` y `test_verificar_carga_no_revienta_si_el_usuario_no_tiene_perfil`. La limitación es que las horas por membresía son una constante. |
| CR-10 | Habilidades, niveles y tecnologías se almacenan como datos consultables y pueden utilizarse en filtros y en el algoritmo. | `test_filtro_por_habilidad`, `test_filtro_por_varias_habilidades_es_and`, `test_filtro_por_tecnologia`, `test_filtro_por_nivel`, `test_filtro_por_experiencia_minima`, `test_filtros_se_combinan_con_and` |
| CR-14 | La vista del equipo refleja correctamente roles cubiertos, vacantes pendientes y perfiles de los miembros aceptados. | Nada todavía. La tarjeta existe pero solo muestra al creador; no consulta `EquipoMembresia` ni calcula roles cubiertos/faltantes. Es el pendiente crítico de Etapa 3. |
| CR-17 / CR-20 | Un usuario ajeno a un proyecto o con proyecto no Finalizado no puede crear una reseña verificada. Además, las decisiones críticas permiten identificar usuario, fecha, hora, registro afectado y acción realizada. | **CR-17:** la garantía de la base está completa y probada por `test_rechaza_autoresena`, `test_una_sola_resena_por_proyecto_autor_y_destinatario` y `test_no_se_puede_borrar_fisicamente_un_proyecto_con_resenas`; además, el perfil ya lista reseñas recibidas. Falta el alta de reseñas (formulario, vista y servicio). **CR-20:** no existe el servicio que escribe el registro; solo está verificado que `auditoria_logs` es inmutable (`test_auditoria_logs_bloquea_update_y_delete`), que no satisface el criterio de trazabilidad. |

---

## 7. Escenarios que el cliente utilizará para la demostración

La versión presentada deberá permitir demostrar, como mínimo, los siguientes escenarios de principio a fin:

**Escenario A - Match Score explicable**
Se crea una vacante con tecnologías y criterios definidos. Dos perfiles distintos se evalúan y el sistema muestra porcentajes diferentes junto con el desglose de los factores que originan cada resultado.

> Estado al cierre de la Etapa 2: `DEMOSTRABLE`. El motor calcula el score y la interfaz muestra el porcentaje con el desglose de factores (CR-05).

**Escenario B - Snapshot de postulación**
Un estudiante se postula y obtiene un Match Score. Luego modifica sus habilidades; las nuevas recomendaciones cambian, pero la postulación conserva el Score y los factores históricos.

> Estado al cierre de la Etapa 2: `DEMOSTRABLE`. `crear_postulacion` guarda el score y los factores; cambiar el perfil después no altera el snapshot (CR-07).

**Escenario C - Último cupo disponible**
Una vacante tiene un solo cupo y dos postulantes. Al aceptar al primero, se crea su membresía y la vacante queda cubierta; el sistema impide aceptar al segundo en ese mismo cupo.

> Estado al cierre de la Etapa 2: `DEMOSTRABLE`. `aceptar_postulacion` crea la membresía, ocupa el cupo y bloquea la segunda aceptación, incluso en concurrencia (CR-08).

**Escenario D - Disponibilidad incompatible**
Un colaborador ya aceptado en un proyecto intenta incorporarse a otro con una carga o disponibilidad incompatible. El sistema aplica la restricción o advertencia acordada.

> Estado al cierre de la Etapa 2: `DEMOSTRABLE con una limitación`. `verificar_carga` bloquea la aceptación si la disponibilidad no alcanza (CR-09); el cálculo usa una constante de horas por membresía, no las horas estimadas de la vacante.

**Escenario E - Formación y cierre del equipo**
El Creador cubre diferentes roles, visualiza cuáles faltan, completa el equipo, inicia el desarrollo y posteriormente Finaliza el proyecto siguiendo transiciones válidas.

> Estado al cierre de la Etapa 2: `PARCIAL`. El ciclo de vida con transiciones válidas está completo y probado (CR-02), pero sigue faltando la visualización de roles cubiertos y faltantes (CR-14, Etapa 3).

**Escenario F - Reseña y auditoría**
Un usuario sin participación intenta reseñar y es rechazado. Un miembro de un proyecto Finalizado puede hacerlo y las decisiones críticas del proceso quedan registradas con usuario, fecha y hora.

> Estado al cierre de la Etapa 2: `PARCIAL`. La regla de verificación de reseñas la garantiza la base de datos y el perfil ya las muestra (CR-17), pero faltan el formulario de alta y el servicio que escribe la auditoría (CR-20).

> **Resumen de los escenarios:** de los seis escenarios de demostración, al cierre de la Etapa 2
> se pueden recorrer de principio a fin **cuatro** (A, B, C y D, este último con la limitación de
> horas constantes). E y F quedan en estado parcial: E depende de CR-14 y F del alta de reseñas y
> del servicio de auditoría. La Etapa 2 completó CR-05, CR-07, CR-08 y CR-09; CR-14 sigue siendo
> el pendiente crítico de la Etapa 3, junto con CR-17 (alta), CR-20 y el cierre real de CR-04.

---

## 8. Respuesta y entregables solicitados al equipo de desarrollo

Como respuesta a esta solicitud, el equipo deberá entregar al cliente una propuesta actualizada que evidencie cómo gestionará el cambio de alcance. Se requieren los siguientes productos:

| Entregable | Descripción esperada |
|---|---|
| **MoSCoW actualizado** | Matriz completa que incorpore requisitos originales y nuevos. Debe mostrar Must Have, Should Have, Could Have y Won't Have for Now, con justificación de cada decisión. |
| **Matriz de impacto** | Identificación de módulos, entidades, relaciones, vistas, permisos, reglas y procesos que deben modificarse por cada cambio relevante. |
| **Dependencias** | Relación entre requisitos. Ejemplo: la aceptación depende de postulación y cupo; las reseñas dependen de membresía y proyecto Finalizado; el Score histórico depende del snapshot de evaluación. |
| **Modelo de datos actualizado** | Diagrama o representación equivalente que muestre usuarios/roles, proyectos, vacantes, habilidades, postulaciones, scores, membresías, disponibilidad, reseñas y auditoría. |
| **Criterios de aceptación** | Criterios verificables para los requisitos que el equipo se comprometa a implementar, incluyendo como mínimo los definidos por el cliente para los cambios no negociables. |
| **Riesgos y mitigación** | Al menos cinco riesgos técnicos, de algoritmo, concurrencia, integración externa, seguridad, datos, alcance o planificación, con una acción de mitigación para cada uno. |
| **Plan de trabajo actualizado** | Cronograma, backlog o plan de iteraciones que refleje el nuevo alcance, las dependencias y el orden propuesto de implementación. |
| **Demostración funcional** | Presentación de los escenarios de validación indicados en este documento y de las funcionalidades adicionales acordadas con el cliente. |

---

## 9. Condiciones de negociación del alcance

- Los cambios identificados como "No negociable" forman parte del alcance mínimo esperado por el cliente.
- Los cambios identificados como "Negociable" pueden ser reordenados, simplificados o pospuestos, siempre que el equipo presente una justificación técnica y una alternativa razonable.
- No se aceptará eliminar requisitos originales clasificados como esenciales sin aprobación explícita del cliente.
- La expresión "falta de tiempo" no será suficiente por sí sola para rechazar un requerimiento. El equipo deberá explicar impacto, esfuerzo, dependencia, riesgo y propuesta de tratamiento.
- Cuando dos requerimientos entren en conflicto, el equipo deberá documentar el conflicto y solicitar una decisión del cliente en lugar de asumir una solución.
- Toda simplificación acordada deberá conservar coherencia en los datos, permisos, estados, postulaciones, Match Score, membresías y experiencia de usuario.

---

## 10. Condición de aceptación de la respuesta del equipo

El cliente considerará satisfactoria la respuesta a esta solicitud cuando el equipo pueda explicar con claridad qué cambió respecto al alcance inicial, qué elementos se implementarán, qué elementos se negociarán o pospondrán, qué componentes técnicos se ven afectados y cómo se verificará cada funcionalidad acordada.

La finalidad de esta solicitud no es únicamente aumentar el número de pantallas del sistema. Los cambios deben reflejarse en reglas de negocio, estados, permisos, validaciones, relaciones de datos, algoritmo de compatibilidad, integración con GitHub, concurrencia y trazabilidad.

> **Resultado esperado por el cliente:** una nueva versión de DevMatch con un proceso de reclutamiento completo, Match Score explicable, formación de equipos consistente y mayor trazabilidad, acompañada de una gestión de requerimientos que permita justificar el alcance final del proyecto.

---

**Emitido por:**

**MSc. José Mendoza**
Cliente / Solicitante - Desarrollo de Software V

---

# ANEXO DEL EQUIPO — Estado al cierre de la Etapa 2 y avance de la Etapa 3

> Actualizado el 22 de octubre de 2026. No forma parte de la solicitud del cliente; es el contraste
> técnico contra `main` @ `cf30c60` (tag `v2.0-etapa-2`) y el estado actual de la rama
> `etapa-3/ci-actions` (CI y documentación de roles; sin cambios de dominio).

## Cómo leer el estado

La Etapa 1 construyó y verificó la **capa de datos**: 20 tablas, 6 funciones y 19 triggers de
Postgres que garantizan cupos, transiciones, reseñas verificadas, no-borrado e inmutabilidad de
la auditoría. La Etapa 2 construyó la **capa de comportamiento principal** sobre ese esquema:
autenticación y perfil, feed con filtros, proyectos y vacantes, Match Score explicable, snapshot
de postulación, aceptación transaccional y control de carga.

El repositorio tiene hoy 9 apps, 20 modelos, 25 rutas HTTP propias, 43 plantillas, 32 archivos de
tests y 483 métodos de prueba. La Etapa 3 está en curso: por ahora solo agrega CI y documentación
de roles, sin cambios de dominio.

| Marca | Cantidad | CR |
|---|---|---|
| `LISTO` | 7 | CR-01, CR-02, CR-03, CR-05, CR-07, CR-08, CR-10 |
| `LISTO (con limitación)` | 1 | CR-09 |
| `PARCIAL` | 3 | CR-04, CR-17, CR-18 |
| `MODELO LISTO (falta servicio y UI)` | 1 | CR-13 |
| `NO IMPLEMENTADO` | 3 | CR-14, CR-19, CR-20 |
| `FUERA DE ALCANCE` | 5 | CR-06, CR-11, CR-12, CR-15, CR-16 |

## Requisitos críticos

De los doce requerimientos marcados como **Crítico / No negociable**, ocho están implementados
(CR-09 con una limitación documentada), dos están parciales (CR-04 y CR-17) y dos siguen sin
implementación (CR-14 y CR-20).

| CR | Qué falta | Qué existe ya para construirlo |
|---|---|---|
| CR-04 Estados de postulación | El cascade real que cierra las postulaciones abiertas al finalizar o cancelar un proyecto, y la reparación de filas existentes | Los 5 estados, el índice único parcial, la vista que hoy simula el cierre y el servicio `cerrar_vacantes_abiertas` |
| CR-14 Composición del equipo | Consultar `EquipoMembresia`, calcular roles cubiertos/faltantes y complementariedad | La tarjeta `_equipo.html` ya maquetada en el detalle del proyecto |
| CR-17 Reseñas verificadas | Formulario, vista y servicio para crear reseñas | El trigger `fn_validar_resena` y el listado de reseñas recibidas en el perfil |
| CR-20 Auditoría de decisiones | El servicio que escribe usuario, fecha, acción y registro afectado | La tabla `auditoria_logs` y el trigger de inmutabilidad |

Ninguno requiere rediseñar la base de datos. Son servicios y vistas sobre un esquema que ya
soporta la operación.

## Trabajo restante de Etapa 3

Además de los cuatro CR anteriores, quedan flujos no críticos en distinto grado de avance:

| CR | Estado | Trabajo restante |
|---|---|---|
| CR-13 Invitaciones | Modelo y admin | Servicio y pantallas para invitar, aceptar, rechazar o ignorar |
| CR-18 Moderación | Modelo y admin | Flujo de usuario para reportar y resolución con responsable/fecha automáticos |
| CR-19 Indicadores | Sin implementación | App de dashboard y agregaciones de métricas |

## Nota sobre CR-20

Es el requerimiento crítico con menos avance, y la asimetría vale la pena explicitar: hoy está
garantizado que el log de auditoría **no se pueda reescribir**, pero no que se **escriba**. El
trigger `fn_inmutable_auditoria` bloquea modificaciones sobre `auditoria_logs`; eso es lo
contrario de lo que el criterio de aceptación CR-17 / CR-20 pide, que es que existan registros.
Sin el servicio que escribe, la trazabilidad no existe aunque la tabla esté lista.

## Nota sobre CR-04

La pantalla "Mis Postulaciones" presenta como rechazada una postulación abierta de un proyecto
cerrado, pero la fila sigue en estado pendiente o preseleccionada en la base. Si el proyecto se
reabre, la postulación reaparece como activa. La Etapa 3 debe mover el cierre a la capa de
servicio/trigger y corregir los datos existentes, no solo la presentación.
