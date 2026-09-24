# DEVMATCH - ESP

Materia: Desarrollo de Software V
Ultima actualización: September 11, 2026 1:38 AM

# **Especificaciones Técnicas: Proyecto "DevMatch" V2.0**

## **1. Comprensión del Problema de Negocio**

**¿Qué problema desea resolver el sistema?**

La formación de equipos de software en el entorno universitario es empírica y desorganizada, lo que genera grupos con perfiles técnicos idénticos que carecen de competencias complementarias. No existe un punto de encuentro centralizado donde los estudiantes puedan exponer sus ideas y reclutar talento estudiantil (v1.0).

**¿Qué impacto tiene ese problema?**

Resulta en el abandono de proyectos por falta de roles clave, desequilibrio en la calidad del software (aplicaciones funcionales, pero sin diseño, o viceversa) y limita a los estudiantes sin experiencia a construir un portafolio sólido antes de graduarse (v1.0).

**¿Qué espera mejorar con el sistema?**

Automatizar la conexión entre creadores de proyectos y colaboradores mediante el cálculo de compatibilidad técnica, democratizando las oportunidades, validando de manera transparente las habilidades y fomentando un ecosistema donde estudiantes puedan liderar una idea o aportar a la de otro. La plataforma deberá administrar el proceso completo desde la publicación de una vacante hasta la aceptación del colaborador, la formación del equipo y el cierre verificable de la colaboración.

---

## **2. Identificación de los Stakeholders (Interesados)**

¿Quiénes participarán o serán afectados por el sistema?

- Usuarios Finales (Estudiantes): Perfil único y bidireccional. Un mismo usuario puede tener proyectos en curso como líder y, simultáneamente, pertenecer a otros equipos como colaborador.
- Administradores Principales: Personal técnico ilimitado. Tienen acceso absoluto e irrestricto a la configuración del sistema, bases de datos y control de usuarios y proyectos. Son los únicos con autoridad para otorgar, modificar o revocar los roles administrativos.
- Cliente Principal / Evaluador: El profesor de la asignatura (José Mendoza), quien aprobará los requisitos técnicos y evaluará la aplicación de los conocimientos del curso (v1.0).

---

## **3. Definición del Alcance del Proyecto**

Lo que el sistema HARÁ (Incluye):

- Administrar y validar acciones con base en tres roles definidos (Administrador, Creador, Colaborador) tanto en la interfaz como en el servidor.
- Gestión de estados y transiciones controladas para el ciclo de vida del proyecto (Borrador, Publicado, Reclutando, Equipo completo, En desarrollo, Finalizado y Cancelado).
- Gestión de vacantes con cupos específicos, tecnologías requeridas y cierre automático al cubrirse la necesidad.
- Manejo de estados formales de postulación conservando el historial (Pendiente, Preseleccionada, Aceptada, Rechazada y Retirada) e impidiendo postulaciones duplicadas.
- Motor de compatibilidad que genere un "Match Score explicable", desglosando al usuario qué factores influyeron en su porcentaje (habilidades, nivel, tecnologías, experiencia, disponibilidad).
- Guardado automático ("Snapshot") del Match Score y sus factores en el instante exacto de la postulación para proteger el registro histórico de futuros cambios en el perfil.
- Aceptación transaccional: el acto de aceptar a un colaborador ocupa la vacante, crea su membresía en el equipo y bloquea ingresos si se excede la capacidad del proyecto.
- Registro de disponibilidad y prevención de carga, advirtiendo o limitando asignaciones de colaboradores con proyectos activos incompatibles.
- Vista de composición del equipo para transparentar qué roles están cubiertos, cuáles faltan y la complementariedad del equipo.
- Invitación proactiva a colaboradores: permitir al Creador invitar directamente a un usuario a una vacante de su proyecto, quien podrá aceptar, rechazar o ignorar la invitación (CR-13).
- Extracción automática de repositorios conectando con la API de GitHub (v1.0).
- Vistas separadas para gestionar "Mis Proyectos" y "Mis Postulaciones" (v1.0).
- Trazabilidad y auditoría estricta de decisiones, guardando el usuario, fecha y hora al ocurrir cambios de estado, aceptaciones o rechazos.
- Sistema de reportes: permitir reportar proyectos, perfiles o conductas indebidas, gestionando cada reporte con un estado y una decisión desde el panel administrativo (CR-18).
- Procesamiento de imágenes (logotipos y prototipos) usando Pillow (v1.0) (Valor Agregado).
- Tableros estadísticos para la administración global de la plataforma, incluyendo indicadores de éxito como vacantes cubiertas, tiempo promedio de cobertura, tasa de postulación y aceptación, proyectos finalizados y Match Score promedio (CR-19) (v1.0) (Valor Agregado).
- Un panel de control centralizado para la auditoría de usuarios y estandarización de habilidades técnicas (v1.0) (Valor Agregado).

Lo que el sistema NO HARÁ (No incluye):

- No gestionará transacciones financieras, estipendios ni modelos de contratación monetaria (v1.0).
- No integrará videollamadas, delegando esta necesidad a plataformas externas (Google Meet o Discord) (v1.0).
- No incluirá conexión con LinkedIn (v1.0).
- No será una aplicación móvil nativa; será estrictamente web responsiva (v1.0).
- No incluirá mensajería o chat interno entre miembros del equipo; esta comunicación se delega a herramientas externas en esta versión (Discord, WhatsApp, etc.) (CR-16).
- No recalculará el ranking de proyectos recomendados ante cambios de habilidades o disponibilidad del perfil, para evitar alterar las evaluaciones históricas ya registradas (CR-12).
- No gestionará hitos, fechas de entrega ni responsables de ejecución dentro de un proyecto, para evitar el desbordamiento del alcance (Scope Creep) y mantener a DevMatch como una plataforma de conexión y matchmaking, no de gestión de proyectos (CR-15).
- No permitirá al Creador ajustar o definir los pesos de los criterios de compatibilidad de una vacante en esta versión (CR-06).

---

## **4. Recopilación de Requerimientos Funcionales**

**¿Qué debe hacer el sistema?**

**Funcionalidades de Perfil y Compatibilidad:**

- Perfil técnico estructurado: El sistema debe registrar habilidades, nivel, tecnologías, intereses, experiencia y disponibilidad como datos estructurados y consultables para el algoritmo.
- Motor de Emparejamiento: Ejecutar un algoritmo que compare las habilidades requeridas vs. poseídas y retorne un Match Score (v1.0).
- Match Score Explicable: La plataforma debe mostrar no solo un porcentaje, sino un desglose de factores sobre el por qué un perfil obtiene dicha calificación.
- Snapshot de Postulación: El sistema debe "congelar" el Match Score y su desglose al momento de aplicar; modificaciones futuras en el perfil del usuario no deben alterar las evaluaciones históricas ya enviadas.
- Integración con GitHub: El sistema consumirá la API REST de GitHub para mostrar repositorios, manejando correctamente caídas del servicio externo para no congelar la navegación del usuario (v1.0) (Valor Agregado).
- Notificaciones Visuales: Mostrar alertas inmediatas en pantalla ante acciones exitosas o errores (intentos de aplicación duplicada) (v1.0) (Valor Agregado).

**Funcionalidades de Proyecto, Vacantes y Reclutamiento:**

- Gestión de Proyectos (CRUD): El sistema debe permitir a los usuarios crear, leer, actualizar y borrar (deshabilitar) sus propios proyectos y vacantes (v1.0).
- Control de transiciones de proyecto: El sistema debe validar que un proyecto no pase libremente a un estado inválido (ej. un proyecto Finalizado no podrá regresar a Reclutando ni abrir nuevas vacantes).
- Gestión de Estados de Vacante: La vacante se marcará como cubierta y no admitirá más integrantes al llenarse el cupo máximo definido.
- Validación de Disponibilidad: El sistema debe contrastar los compromisos adquiridos por el colaborador en otros proyectos activos antes de permitir su aceptación en uno nuevo, generando advertencias o bloqueos.
- Formación de Equipo: Visualizar los roles cubiertos y los pendientes a medida que los miembros son aceptados.
- Invitación a Colaboradores: El Creador podrá invitar directamente a un usuario a una vacante específica de su proyecto; el invitado podrá aceptar, rechazar o ignorar la invitación, sin afectar la integridad de la base de datos transaccional (CR-13) (Valor Agregado).
- Vistas de Gestión Personal (Mis Proyectos / Mis Postulaciones): Vistas especializadas para que cada rol rastree sus iniciativas o aplicaciones (v1.0) (Valor Agregado).
- Carga de Imágenes: Permitir cargar prototipos y logos, y procesarlos en el backend con Pillow (v1.0) (Valor Agregado).

**Funcionalidades de Reseñas y Auditoría:**

- Reseñas Verificadas: El sistema validará que únicamente los miembros reales de un proyecto en estado "Finalizado" puedan crear reseñas para los participantes.
- Auditoría de Decisiones (Trazabilidad): Toda acción crítica (transición de estados, aceptación, membresías y rechazos) debe dejar un registro auditable identificando usuario, fecha, hora, acción y registro afectado.

**Funcionalidades del Panel de Administración:**

- Auditoría de Cuentas: Capacidad para bloquear o suspender usuarios, modificar roles y visualizar el historial de actividad (proyectos creados, postulaciones e infracciones) (v1.0) (Valor Agregado).
- Métricas y Analíticas (Dashboard): Visualización de KPIs de la plataforma (usuarios activos, proyectos publicados, tasa general de éxito), gráficos de tendencias sobre las tecnologías más demandadas, así como indicadores específicos de éxito: vacantes cubiertas, tiempo promedio de cobertura, tasa de postulación, tasa de aceptación, proyectos finalizados y Match Score promedio (CR-19) (v1.0) (Valor Agregado).
- Moderación de Contenido y Reportes: Capacidad para auditar, ocultar o eliminar proyectos que violen las normas de la comunidad (spam, contenido inapropiado o iniciativas no académicas). Incluye la gestión de reportes de proyectos, perfiles o conductas indebidas, cada uno con un estado y una decisión asignable desde el panel administrativo; no incluye mecanismo de apelación para el usuario reportado (CR-18) (v1.0).
- Exportación de Reportes: Opción para descargar reportes operativos globales en formato CSV o PDF (v1.0) (Valor Agregado).

---

## **5. Reglas de Negocio**

No negociables:

- Las validaciones de roles, permisos, transiciones de estados de proyectos y postulaciones deben ejecutarse obligatoriamente a nivel servidor.
- Un proyecto en estado "Borrador" no puede ser visible para recibir postulaciones.
- Un "Colaborador" no se puede postular a una vacante si ya posee una postulación activa en la misma.
- Las postulaciones rechazadas o retiradas deben conservar el historial, no deben ser eliminadas de la base de datos.
- Un usuario retirado de un equipo no desaparece de los registros anteriores, se conserva su historial.

Negociables:

- Pesos de compatibilidad ajustables (CR-06) – Pospuesto: El Creador no podrá modificar los pesos de los criterios del Match Score (habilidades, nivel, tecnologías, experiencia, disponibilidad) en esta versión; el algoritmo aplicará una ponderación estándar fija definida por el sistema para mantener estable la primera iteración del motor de matchmaking.
- Recálculo de ranking ante cambios de perfil (CR-12) – Descartado: Las modificaciones que un Colaborador realice a sus habilidades o disponibilidad no dispararán un recálculo del ranking de proyectos recomendados, y en ningún caso alterarán las postulaciones o evaluaciones históricas ya registradas.
- Hitos de ejecución del proyecto (CR-15) – Descartado: El sistema no gestionará hitos, fechas de entrega ni responsables una vez formado el equipo. Esto se descarta para evitar el Scope Creep y mantener a DevMatch como una plataforma de conexión y matchmaking, no como un gestor de proyectos.
- Mensajería interna entre miembros (CR-16) – Pospuesto: No se desarrollará un módulo de mensajería/chat dentro de la plataforma en esta versión; la comunicación entre los miembros aceptados de un equipo se delega a herramientas externas (Discord, WhatsApp, etc.).
- Invitación directa a colaboradores (CR-13) – Aceptado: El Creador podrá invitar proactivamente a un usuario específico a una vacante de su proyecto; el invitado podrá aceptar, rechazar o ignorar la invitación, sin comprometer la integridad de la base de datos transaccional.
- Reportes y moderación de conducta (CR-18) – Aceptado: Se habilita la opción de reportar proyectos, perfiles o conductas indebidas. Cada reporte contará con un estado y una decisión gestionables desde el panel administrativo; no incluye mecanismo de apelación para el usuario reportado.
- Indicadores de éxito de la plataforma (CR-19) – Aceptado: El Dashboard administrativo mostrará métricas de vacantes cubiertas, tiempo promedio de cobertura, tasa de postulación y aceptación, proyectos finalizados y Match Score promedio de la plataforma.

---

## **6. Identificación de Requerimientos No Funcionales**

- **¿Cómo debe funcionar el sistema?**
- Usabilidad: La interfaz debe ser intuitiva, responsiva e incluir un tutorial dinámico opcional para presentar el flujo del sitio, construida integralmente con Tailwind CSS (v1.0).
- Seguridad y Jerarquía: Las contraseñas deben estar encriptadas y las rutas de administración protegidas. A nivel jerárquico, la capa de permisos del sistema debe bloquear automáticamente cualquier intento de acceder a creadores o colaboradores al panel administrativo.
- Rendimiento: Las consultas de compatibilidad y los filtros dinámicos deben estar optimizados. Las métricas en el Dashboard deben procesarse utilizando los métodos de agregación del ORM para no sobrecargar la memoria del servidor (v1.0).
- Disponibilidad y Tolerancia a Fallos: La integración con la API de GitHub debe manejar correctamente los límites de peticiones y las caídas del servicio externo sin congelar la navegación del usuario (v1.0).

---

## **7. Determinación de Restricciones**

- Tecnología Obligatoria: El proyecto debe construirse estrictamente bajo el stack del curso: Python, Django (ORM, vistas, modelos), PostgreSQL y Tailwind CSS (v1.0).
- Tiempo de Desarrollo: El ciclo de vida del proyecto está limitado al calendario académico del semestre (v1.0).
- Presupuesto Disponible: $0. El proyecto debe implementarse utilizando exclusivamente integraciones gratuitas (API de GitHub pública) y librerías de código abierto (v1.0).

---

## **8. Orden Propuesto de Implementación**

- **Fase 1:** **Infraestructura y Estructura Relacional Base**Configurar el entorno (Django, Tailwind CSS). Diseñar y migrar el esquema completo del ORM mapeando desde el inicio todas las tablas (presentes y propuestas) para evitar migraciones destructivas a futuro.
- **Fase 2: Autenticación y Perfil Estructurado (CR-01, CR-10)**Implementar el registro de usuarios, la validación estricta de Roles y permisos directamente en el servidor, y el formulario de Perfil técnico estructurado para garantizar que las habilidades se ingresen como datos estandarizados.
- **Fase 3: CRUD de Proyectos y Estados de Vacantes (CR-03)**Desarrollar las vistas y modelos para la publicación de proyectos y configuración de vacantes, asegurando el manejo independiente de cupos, estados y tecnologías requeridas por rol.
- **Fase 4: Motor Transaccional de Postulación y Aceptación (CR-04, CR-08, CR-09)**Unificar el flujo de postulaciones con las operaciones atómicas de aceptación en la base de datos. Controlar la concurrencia para evitar desbordamiento de cupos e implementar la advertencia por choques de disponibilidad.
- **Fase 5: Algoritmo de Matchmaking y Explicabilidad (CR-05)**Construir la capa lógica en Python que cruce las habilidades requeridas contra las del usuario. Desarrollar la interfaz visual que desglose el porcentaje de compatibilidad y los factores técnicos considerados.
- **Fase 6: Congelamiento Histórico de Evaluaciones (CR-07)**Programar la captura estática (Snapshot) del Match Score y guardarla en el registro de la postulación en el instante exacto en que el usuario aplica, mitigando recálculos costosos en el servidor.
- **Fase 7: Composición de Equipos y Ciclo de Vida (CR-02, CR-14)**Habilitar la vista dinámica de roles cubiertos y vacantes pendientes. Programar las reglas duras en el backend para bloquear transiciones de estado inválidas en los proyectos.
- **Fase 8: Auditoría y Reseñas Verificadas (CR-17, CR-20)**Activar el sistema de auditoría interna para registrar usuario, fecha y modificación en las decisiones críticas. Configurar las reglas de reseñas limitándolas exclusivamente a miembros de proyectos en estado Finalizado.
- **Fase 9: Integración Externa con GitHub (CR-11)**Desarrollar el consumo de la API mediante la librería requests. Implementar un manejo robusto de excepciones y tiempos de espera cortos para evitar que las caídas de GitHub afecten el rendimiento de DevMatch.
- **Fase 10: Panel Administrativo, Métricas e Invitaciones (CR-13, CR-18, CR-19)**Consolidar las herramientas de gestión operativas: habilitar la invitación proactiva a colaboradores, el panel de moderación para reportes y el dashboard de métricas de éxito (cobertura, tiempos, postulaciones).