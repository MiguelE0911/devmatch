-- =====================================================================
-- DEVMATCH V2.0 — ESQUEMA COMPLETO DE BASE DE DATOS (PostgreSQL / Neon)
-- =====================================================================
-- Propósito: dejar mapeado desde el día 1 el modelo relacional completo
-- del proyecto (todas las etapas), para evitar migraciones destructivas
-- a futuro, tal como exige la Etapa 1 de la especificación técnica.
--
-- Cómo ejecutarlo en Neon:
--   psql "postgresql://usuario:password@ep-xxxx.neon.tech/devmatch?sslmode=require" -f devmatch_schema_v1.sql
--
-- Notas de diseño generales:
--   1. VARCHAR + CHECK en lugar de ENUM nativo de Postgres, por
--      compatibilidad directa con CharField(choices=...) de Django.
--   2. Claves primarias con BIGINT GENERATED ALWAYS AS IDENTITY,
--      equivalente al BigAutoField que Django usa por defecto (3.2+).
--   3. NINGÚN registro histórico se elimina físicamente jamás. Esto se
--      garantiza en DOS capas independientes:
--        a) Columnas es_activo (+ desactivado_en/desactivado_por_id)
--           para "ocultar sin borrar" en las tablas donde eliminar es
--           una acción disponible en la interfaz (proyectos, vacantes,
--           reseñas, etc).
--        b) Triggers BEFORE DELETE que RECHAZAN cualquier intento de
--           DELETE físico en tablas históricas, sin importar qué rol
--           de la aplicación lo intente (incluido un administrador).
--           La única forma real de borrar una fila es que alguien con
--           acceso directo a la base de datos deshabilite el trigger
--           a propósito (ALTER TABLE ... DISABLE TRIGGER ...), que es
--           exactamente el tipo de acción deliberada y fuera de la
--           aplicación que se busca exigir para un borrado real.
--      Las tablas de catálogo (habilidades, tecnologías, intereses) y
--      las tablas puente (usuarios_habilidades, etc.) NO llevan esta
--      segunda capa: seguir permitiendo DELETE ahí es intencional (ver
--      sección 11 para el detalle de qué se protege y por qué).
--   4. es_activo es SIEMPRE ortogonal a cualquier columna "estado" que
--      ya exista en la misma tabla: "estado" cuenta la verdad histórica
--      del ciclo de vida (ej. un proyecto Finalizado), mientras que
--      es_activo solo controla si el registro se sigue mostrando en la
--      interfaz. Ocultar un proyecto Finalizado no debe reescribir su
--      verdadero desenlace a "cancelado".
-- =====================================================================

BEGIN;

-- =====================================================================
-- SECCIÓN 1 — USUARIOS Y PERFIL TÉCNICO ESTRUCTURADO
-- App Django sugerida: accounts
-- =====================================================================

CREATE TABLE usuarios (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email               VARCHAR(254) NOT NULL UNIQUE,
    username            VARCHAR(150) NOT NULL UNIQUE,
    password_hash       VARCHAR(128) NOT NULL,
    first_name          VARCHAR(150) NOT NULL DEFAULT '',
    last_name           VARCHAR(150) NOT NULL DEFAULT '',
    es_admin            BOOLEAN NOT NULL DEFAULT FALSE,
    es_activo           BOOLEAN NOT NULL DEFAULT TRUE,
    esta_bloqueado      BOOLEAN NOT NULL DEFAULT FALSE,
    motivo_bloqueo      TEXT,
    bloqueado_en        TIMESTAMPTZ,
    bloqueado_por_id    BIGINT REFERENCES usuarios(id) ON DELETE SET NULL,
    desactivado_en      TIMESTAMPTZ,
    desactivado_por_id  BIGINT REFERENCES usuarios(id) ON DELETE SET NULL,
    ultimo_login        TIMESTAMPTZ,
    creado_en           TIMESTAMPTZ NOT NULL DEFAULT now(),
    actualizado_en      TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON COLUMN usuarios.es_admin IS 'Único rol persistente sobre el usuario. Creador/Colaborador NO se guardan aquí: son contextuales según si el usuario tiene proyectos creados o membresías activas.';
COMMENT ON COLUMN usuarios.es_activo IS 'Cuenta oculta/deshabilitada por el propio usuario o por un admin. desactivado_por_id = NULL implica autoservicio; con valor implica acción administrativa.';
COMMENT ON COLUMN usuarios.esta_bloqueado IS 'Distinto de es_activo: bloqueo es una acción punitiva/administrativa (moderación), no una simple ocultación voluntaria.';
COMMENT ON TABLE usuarios IS 'Nunca se elimina un registro de esta tabla vía la aplicación (ver trigger trg_bloquear_borrado_usuarios en la Sección 11). Usar es_activo/esta_bloqueado.';

CREATE TABLE perfiles (
    id                              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    usuario_id                      BIGINT NOT NULL UNIQUE REFERENCES usuarios(id) ON DELETE CASCADE,
    nivel                           VARCHAR(20) NOT NULL DEFAULT 'principiante'
                                        CHECK (nivel IN ('principiante', 'intermedio', 'avanzado')),
    experiencia_anios               SMALLINT NOT NULL DEFAULT 0 CHECK (experiencia_anios >= 0),
    disponibilidad_horas_semana     SMALLINT NOT NULL DEFAULT 10 CHECK (disponibilidad_horas_semana >= 0),
    bio                             TEXT,
    github_username                 VARCHAR(100),
    avatar_url                      TEXT,
    creado_en                       TIMESTAMPTZ NOT NULL DEFAULT now(),
    actualizado_en                  TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON COLUMN perfiles.disponibilidad_horas_semana IS 'Valor numérico (no etiqueta) para poder calcular sobrecarga real comparando contra compromisos en proyectos activos.';
COMMENT ON TABLE perfiles IS 'No lleva es_activo propio: no existe una acción de "eliminar perfil" independiente de la cuenta de usuario en la especificación; sigue el ciclo de vida de usuarios.';

-- =====================================================================
-- SECCIÓN 2 — CATÁLOGOS ESTANDARIZADOS (habilidades, tecnologías, intereses)
-- App Django sugerida: accounts
-- =====================================================================

CREATE TABLE habilidades (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre              VARCHAR(100) NOT NULL UNIQUE,
    categoria           VARCHAR(50),
    es_activo           BOOLEAN NOT NULL DEFAULT TRUE,
    desactivado_en      TIMESTAMPTZ,
    desactivado_por_id  BIGINT REFERENCES usuarios(id) ON DELETE SET NULL,
    creado_en           TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE habilidades IS 'Catálogo estandarizado. Se desactiva (es_activo=false) para retirarla de uso sin romper referencias históricas en usuarios_habilidades. A diferencia de las tablas de historial, SÍ puede eliminarse físicamente si nunca fue usada (protegido solo por ON DELETE RESTRICT desde las tablas puente, sin trigger de bloqueo adicional) — por ejemplo, para corregir una entrada duplicada o mal escrita que nadie ha usado todavía.';

CREATE TABLE tecnologias (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre              VARCHAR(100) NOT NULL UNIQUE,
    categoria           VARCHAR(50),
    es_activo           BOOLEAN NOT NULL DEFAULT TRUE,
    desactivado_en      TIMESTAMPTZ,
    desactivado_por_id  BIGINT REFERENCES usuarios(id) ON DELETE SET NULL,
    creado_en           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE intereses (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre              VARCHAR(100) NOT NULL UNIQUE,
    es_activo           BOOLEAN NOT NULL DEFAULT TRUE,
    desactivado_en      TIMESTAMPTZ,
    desactivado_por_id  BIGINT REFERENCES usuarios(id) ON DELETE SET NULL,
    creado_en           TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =====================================================================
-- SECCIÓN 3 — RELACIONES USUARIO-CATÁLOGO
-- App Django sugerida: accounts
-- =====================================================================

CREATE TABLE usuarios_habilidades (
    usuario_id      BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    habilidad_id    BIGINT NOT NULL REFERENCES habilidades(id) ON DELETE RESTRICT,
    PRIMARY KEY (usuario_id, habilidad_id)
);

CREATE TABLE usuarios_tecnologias (
    usuario_id      BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    tecnologia_id   BIGINT NOT NULL REFERENCES tecnologias(id) ON DELETE RESTRICT,
    PRIMARY KEY (usuario_id, tecnologia_id)
);

CREATE TABLE usuarios_intereses (
    usuario_id      BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    interes_id      BIGINT NOT NULL REFERENCES intereses(id) ON DELETE RESTRICT,
    PRIMARY KEY (usuario_id, interes_id)
);
COMMENT ON TABLE usuarios_habilidades IS 'Tabla puente pura: agregar/quitar una habilidad del perfil es edición normal, no un evento de "historial" que deba preservarse línea por línea. Por eso no lleva es_activo ni bloqueo de DELETE.';

-- =====================================================================
-- SECCIÓN 4 — PROYECTOS Y VACANTES
-- App Django sugerida: projects
-- =====================================================================

CREATE TABLE proyectos (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    creador_id          BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE RESTRICT,
    nombre              VARCHAR(150) NOT NULL,
    descripcion         TEXT NOT NULL,
    estado              VARCHAR(20) NOT NULL DEFAULT 'borrador'
                            CHECK (estado IN ('borrador', 'publicado', 'reclutando', 'equipo_completo',
                                               'en_desarrollo', 'finalizado', 'cancelado')),
    es_activo           BOOLEAN NOT NULL DEFAULT TRUE,
    logo_url            TEXT,
    finalizado_en       TIMESTAMPTZ,
    cancelado_en        TIMESTAMPTZ,
    desactivado_en      TIMESTAMPTZ,
    desactivado_por_id  BIGINT REFERENCES usuarios(id) ON DELETE SET NULL,
    creado_en           TIMESTAMPTZ NOT NULL DEFAULT now(),
    actualizado_en      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_proyectos_creador ON proyectos (creador_id);
CREATE INDEX ix_proyectos_estado ON proyectos (estado);
CREATE INDEX ix_proyectos_activos ON proyectos (es_activo) WHERE es_activo = TRUE;
COMMENT ON COLUMN proyectos.es_activo IS 'Es lo que usa la acción "eliminar proyecto" de la interfaz: oculta el proyecto sin tocar su columna estado. Un proyecto puede estar estado=finalizado y es_activo=false a la vez (se completó con éxito, pero el creador lo archivó de su vista).';

CREATE TABLE proyecto_media (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    proyecto_id     BIGINT NOT NULL REFERENCES proyectos(id) ON DELETE CASCADE,
    tipo            VARCHAR(20) NOT NULL CHECK (tipo IN ('logo', 'prototipo')),
    archivo_url     TEXT NOT NULL,
    orden           SMALLINT NOT NULL DEFAULT 0,
    es_activo       BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_proyecto_media_proyecto ON proyecto_media (proyecto_id);

CREATE TABLE vacantes (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    proyecto_id         BIGINT NOT NULL REFERENCES proyectos(id) ON DELETE CASCADE,
    titulo              VARCHAR(150) NOT NULL,
    descripcion         TEXT NOT NULL,
    cupos_totales       SMALLINT NOT NULL CHECK (cupos_totales > 0),
    cupos_ocupados      SMALLINT NOT NULL DEFAULT 0 CHECK (cupos_ocupados >= 0),
    estado              VARCHAR(20) NOT NULL DEFAULT 'abierta'
                            CHECK (estado IN ('abierta', 'cubierta', 'cancelada')),
    es_activo           BOOLEAN NOT NULL DEFAULT TRUE,
    desactivado_en      TIMESTAMPTZ,
    desactivado_por_id  BIGINT REFERENCES usuarios(id) ON DELETE SET NULL,
    creado_en           TIMESTAMPTZ NOT NULL DEFAULT now(),
    actualizado_en      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_cupos_no_exceden CHECK (cupos_ocupados <= cupos_totales)
);
CREATE INDEX ix_vacantes_proyecto ON vacantes (proyecto_id);
CREATE INDEX ix_vacantes_estado ON vacantes (estado);
COMMENT ON COLUMN vacantes.cupos_ocupados IS 'Mantenido automáticamente por el trigger trg_membresia_actualiza_cupos. No modificar manualmente desde la aplicación.';
COMMENT ON COLUMN vacantes.es_activo IS 'Igual que en proyectos: ortogonal a estado. Una vacante cubierta puede ocultarse (es_activo=false) sin perder el hecho de que llegó a cubrirse.';

CREATE TABLE vacante_habilidades_requeridas (
    vacante_id      BIGINT NOT NULL REFERENCES vacantes(id) ON DELETE CASCADE,
    habilidad_id    BIGINT NOT NULL REFERENCES habilidades(id) ON DELETE RESTRICT,
    PRIMARY KEY (vacante_id, habilidad_id)
);

CREATE TABLE vacante_tecnologias_requeridas (
    vacante_id      BIGINT NOT NULL REFERENCES vacantes(id) ON DELETE CASCADE,
    tecnologia_id   BIGINT NOT NULL REFERENCES tecnologias(id) ON DELETE RESTRICT,
    PRIMARY KEY (vacante_id, tecnologia_id)
);

-- =====================================================================
-- SECCIÓN 5 — MOTOR DE MATCHMAKING (configuración de pesos)
-- App Django sugerida: matching / applications
-- =====================================================================

CREATE TABLE configuracion_pesos_matching (
    id                      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre                  VARCHAR(100) NOT NULL,
    peso_habilidades        NUMERIC(4,3) NOT NULL,
    peso_nivel              NUMERIC(4,3) NOT NULL,
    peso_tecnologias        NUMERIC(4,3) NOT NULL,
    peso_experiencia        NUMERIC(4,3) NOT NULL,
    peso_disponibilidad     NUMERIC(4,3) NOT NULL,
    vigente_desde           TIMESTAMPTZ NOT NULL DEFAULT now(),
    vigente_hasta           TIMESTAMPTZ,
    es_activo               BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT chk_pesos_suman_uno CHECK (
        ROUND(peso_habilidades + peso_nivel + peso_tecnologias + peso_experiencia + peso_disponibilidad, 3) = 1.000
    )
);
CREATE UNIQUE INDEX ux_un_solo_peso_activo ON configuracion_pesos_matching (es_activo) WHERE es_activo = TRUE;

COMMENT ON TABLE configuracion_pesos_matching IS
'CR-06 pospuso que el Creador ajuste los pesos por vacante; esta tabla ya está versionada y lista para esa función futura sin requerir cambios estructurales.';
COMMENT ON COLUMN configuracion_pesos_matching.es_activo IS
'Aquí es_activo significa "es el perfil de pesos vigente actualmente" (patrón singleton, solo puede haber uno) — un significado distinto al es_activo de "ocultar sin borrar" usado en el resto del esquema. No se elimina físicamente una fila de aquí una vez usada (ver ON DELETE RESTRICT desde postulaciones.pesos_usados_id): borrarla perdería la explicabilidad histórica de los Match Score que la usaron.';

-- =====================================================================
-- SECCIÓN 6 — POSTULACIONES (con snapshot congelado)
-- App Django sugerida: applications
-- =====================================================================

CREATE TABLE postulaciones (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    vacante_id          BIGINT NOT NULL REFERENCES vacantes(id) ON DELETE CASCADE,
    postulante_id       BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE RESTRICT,
    estado              VARCHAR(20) NOT NULL DEFAULT 'pendiente'
                            CHECK (estado IN ('pendiente', 'preseleccionada', 'aceptada', 'rechazada', 'retirada')),
    match_score         NUMERIC(5,2) NOT NULL CHECK (match_score >= 0 AND match_score <= 100),
    match_factores      JSONB NOT NULL,
    pesos_usados_id     BIGINT REFERENCES configuracion_pesos_matching(id) ON DELETE RESTRICT,
    decidido_por_id     BIGINT REFERENCES usuarios(id) ON DELETE SET NULL,
    motivo_decision     TEXT,
    postulado_en        TIMESTAMPTZ NOT NULL DEFAULT now(),
    decidido_en         TIMESTAMPTZ,
    actualizado_en      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_postulaciones_vacante ON postulaciones (vacante_id);
CREATE INDEX ix_postulaciones_postulante ON postulaciones (postulante_id);
CREATE INDEX ix_postulaciones_estado ON postulaciones (estado);
CREATE INDEX ix_postulaciones_match_factores ON postulaciones USING GIN (match_factores);

CREATE UNIQUE INDEX ux_postulacion_activa_unica
    ON postulaciones (vacante_id, postulante_id)
    WHERE estado IN ('pendiente', 'preseleccionada');

COMMENT ON COLUMN postulaciones.match_factores IS
'Snapshot congelado del desglose del Match Score en el instante exacto de la postulación. Nunca se recalcula ni se sobrescribe (CR-07, CR-12).';
COMMENT ON TABLE postulaciones IS
'No lleva es_activo: el estado "retirada" YA cumple la función de "ocultar sin borrar" que pide la regla de negocio — una postulación retirada conserva su historial completo, tal como exige la especificación, sin necesitar una columna adicional.';

-- =====================================================================
-- SECCIÓN 7 — INVITACIONES Y MEMBRESÍAS DE EQUIPO
-- App Django sugerida: teams
-- =====================================================================

CREATE TABLE invitaciones (
    id                      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    vacante_id              BIGINT NOT NULL REFERENCES vacantes(id) ON DELETE CASCADE,
    usuario_invitado_id     BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    invitado_por_id         BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE RESTRICT,
    estado                  VARCHAR(20) NOT NULL DEFAULT 'pendiente'
                                CHECK (estado IN ('pendiente', 'aceptada', 'rechazada', 'ignorada')),
    creado_en               TIMESTAMPTZ NOT NULL DEFAULT now(),
    respondido_en           TIMESTAMPTZ
);
CREATE INDEX ix_invitaciones_usuario_invitado ON invitaciones (usuario_invitado_id);

CREATE UNIQUE INDEX ux_invitacion_pendiente_unica
    ON invitaciones (vacante_id, usuario_invitado_id)
    WHERE estado = 'pendiente';
COMMENT ON TABLE invitaciones IS 'No lleva es_activo: sus estados terminales (aceptada/rechazada/ignorada) ya conservan el historial completo sin necesidad de ocultarlas.';

CREATE TABLE equipos_membresias (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    proyecto_id     BIGINT NOT NULL REFERENCES proyectos(id) ON DELETE CASCADE,
    vacante_id      BIGINT NOT NULL REFERENCES vacantes(id) ON DELETE CASCADE,
    usuario_id      BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE RESTRICT,
    postulacion_id  BIGINT REFERENCES postulaciones(id) ON DELETE SET NULL,
    invitacion_id   BIGINT REFERENCES invitaciones(id) ON DELETE SET NULL,
    estado          VARCHAR(20) NOT NULL DEFAULT 'activo' CHECK (estado IN ('activo', 'retirado')),
    ingreso_en      TIMESTAMPTZ NOT NULL DEFAULT now(),
    retiro_en       TIMESTAMPTZ,
    CONSTRAINT chk_origen_membresia CHECK (
        (postulacion_id IS NOT NULL AND invitacion_id IS NULL) OR
        (postulacion_id IS NULL AND invitacion_id IS NOT NULL)
    )
);
CREATE INDEX ix_membresias_usuario ON equipos_membresias (usuario_id);
CREATE INDEX ix_membresias_proyecto ON equipos_membresias (proyecto_id);

CREATE UNIQUE INDEX ux_membresia_activa_unica
    ON equipos_membresias (vacante_id, usuario_id)
    WHERE estado = 'activo';

COMMENT ON TABLE equipos_membresias IS
'Un usuario retirado nunca se elimina de esta tabla, solo cambia a estado=retirado (regla no negociable de conservar historial). estado ya cumple el rol de es_activo aquí.';

-- =====================================================================
-- SECCIÓN 8 — AUDITORÍA
-- App Django sugerida: audit
-- =====================================================================

CREATE TABLE auditoria_logs (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    usuario_id          BIGINT REFERENCES usuarios(id) ON DELETE SET NULL,
    accion              VARCHAR(100) NOT NULL,
    tabla_afectada      VARCHAR(100) NOT NULL,
    registro_id         BIGINT NOT NULL,
    detalle             JSONB,
    creado_en           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_auditoria_tabla_registro ON auditoria_logs (tabla_afectada, registro_id);
CREATE INDEX ix_auditoria_usuario ON auditoria_logs (usuario_id);

COMMENT ON TABLE auditoria_logs IS
'Registro de trazabilidad, escrito explícitamente desde audit/services.py en cada decisión crítica (incluyendo cada vez que algo se marca es_activo=false). Esta tabla es de solo-append: ni UPDATE ni DELETE están permitidos aquí, ni siquiera para un administrador (ver trigger trg_inmutable_auditoria en la Sección 11) — de lo contrario alguien podría reescribir la historia que se supone que audita.';

-- =====================================================================
-- SECCIÓN 9 — RESEÑAS VERIFICADAS
-- App Django sugerida: reviews
-- =====================================================================

CREATE TABLE resenas (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    proyecto_id         BIGINT NOT NULL REFERENCES proyectos(id) ON DELETE CASCADE,
    autor_id            BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE RESTRICT,
    destinatario_id     BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE RESTRICT,
    calificacion        SMALLINT NOT NULL CHECK (calificacion BETWEEN 1 AND 5),
    comentario          TEXT,
    es_activo           BOOLEAN NOT NULL DEFAULT TRUE,
    desactivado_en      TIMESTAMPTZ,
    desactivado_por_id  BIGINT REFERENCES usuarios(id) ON DELETE SET NULL,
    creado_en           TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_no_autoresena CHECK (autor_id <> destinatario_id),
    CONSTRAINT ux_resena_unica UNIQUE (proyecto_id, autor_id, destinatario_id)
);
CREATE INDEX ix_resenas_destinatario ON resenas (destinatario_id);
COMMENT ON COLUMN resenas.es_activo IS 'Permite a un admin ocultar una reseña reportada/ofensiva desde el panel de moderación sin borrar la evidencia.';

-- =====================================================================
-- SECCIÓN 10 — MODERACIÓN Y REPORTES
-- App Django sugerida: moderation
-- =====================================================================

CREATE TABLE reportes (
    id                      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    reportante_id           BIGINT REFERENCES usuarios(id) ON DELETE SET NULL,
    tipo_objetivo           VARCHAR(20) NOT NULL CHECK (tipo_objetivo IN ('proyecto', 'perfil', 'conducta')),
    proyecto_reportado_id   BIGINT REFERENCES proyectos(id) ON DELETE CASCADE,
    usuario_reportado_id    BIGINT REFERENCES usuarios(id) ON DELETE CASCADE,
    motivo                  VARCHAR(150) NOT NULL,
    descripcion             TEXT,
    estado                  VARCHAR(20) NOT NULL DEFAULT 'pendiente'
                                CHECK (estado IN ('pendiente', 'en_revision', 'resuelto', 'descartado')),
    decision                TEXT,
    resuelto_por_id         BIGINT REFERENCES usuarios(id) ON DELETE SET NULL,
    resuelto_en             TIMESTAMPTZ,
    creado_en               TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_objetivo_reporte CHECK (
        (tipo_objetivo = 'proyecto' AND proyecto_reportado_id IS NOT NULL AND usuario_reportado_id IS NULL) OR
        (tipo_objetivo IN ('perfil', 'conducta') AND usuario_reportado_id IS NOT NULL AND proyecto_reportado_id IS NULL)
    )
);
CREATE INDEX ix_reportes_estado ON reportes (estado);

COMMENT ON TABLE reportes IS
'No lleva es_activo: el estado "descartado" ya cumple esa función. Sí se incluye en el bloqueo de DELETE físico (Sección 11), porque un reporte resuelto es evidencia de una decisión de moderación que nunca debe poder borrarse.';

-- =====================================================================
-- SECCIÓN 11 — FUNCIONES Y TRIGGERS DE CONSISTENCIA
-- =====================================================================

-- 11.1 — Mantenimiento automático de actualizado_en
CREATE OR REPLACE FUNCTION fn_set_updated_at() RETURNS TRIGGER AS $$
BEGIN
    NEW.actualizado_en := now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_usuarios_updated_at BEFORE UPDATE ON usuarios
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_perfiles_updated_at BEFORE UPDATE ON perfiles
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_proyectos_updated_at BEFORE UPDATE ON proyectos
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_vacantes_updated_at BEFORE UPDATE ON vacantes
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_postulaciones_updated_at BEFORE UPDATE ON postulaciones
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

-- 11.2 — Cupos de vacante a prueba de condiciones de carrera
CREATE OR REPLACE FUNCTION fn_actualizar_cupos_vacante() RETURNS TRIGGER AS $$
DECLARE
    v_vacante_id    BIGINT := COALESCE(NEW.vacante_id, OLD.vacante_id);
    v_nuevo_conteo  SMALLINT;
BEGIN
    PERFORM 1 FROM vacantes WHERE id = v_vacante_id FOR UPDATE;

    SELECT COUNT(*) INTO v_nuevo_conteo
    FROM equipos_membresias
    WHERE vacante_id = v_vacante_id AND estado = 'activo';

    UPDATE vacantes
    SET cupos_ocupados = v_nuevo_conteo,
        estado = CASE
            WHEN v_nuevo_conteo >= cupos_totales AND estado <> 'cancelada' THEN 'cubierta'
            WHEN v_nuevo_conteo < cupos_totales AND estado = 'cubierta' THEN 'abierta'
            ELSE estado
        END,
        actualizado_en = now()
    WHERE id = v_vacante_id;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_membresia_actualiza_cupos
    AFTER INSERT OR UPDATE OF estado OR DELETE ON equipos_membresias
    FOR EACH ROW EXECUTE FUNCTION fn_actualizar_cupos_vacante();

-- 11.3 — Validación de transiciones de estado del proyecto
CREATE OR REPLACE FUNCTION fn_validar_transicion_proyecto() RETURNS TRIGGER AS $$
DECLARE
    v_transiciones_validas TEXT[];
BEGIN
    IF NEW.estado = OLD.estado THEN
        RETURN NEW;
    END IF;

    v_transiciones_validas := CASE OLD.estado
        WHEN 'borrador'        THEN ARRAY['publicado', 'cancelado']
        WHEN 'publicado'       THEN ARRAY['reclutando', 'cancelado']
        WHEN 'reclutando'      THEN ARRAY['equipo_completo', 'cancelado']
        WHEN 'equipo_completo' THEN ARRAY['en_desarrollo', 'reclutando', 'cancelado']
        WHEN 'en_desarrollo'   THEN ARRAY['finalizado', 'cancelado']
        WHEN 'finalizado'      THEN ARRAY[]::TEXT[]
        WHEN 'cancelado'       THEN ARRAY[]::TEXT[]
        ELSE ARRAY[]::TEXT[]
    END;

    IF NOT (NEW.estado = ANY(v_transiciones_validas)) THEN
        RAISE EXCEPTION 'Transición de estado inválida en proyecto %: de % a %', NEW.id, OLD.estado, NEW.estado;
    END IF;

    IF NEW.estado = 'finalizado' THEN
        NEW.finalizado_en := now();
    ELSIF NEW.estado = 'cancelado' THEN
        NEW.cancelado_en := now();
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validar_transicion_proyecto
    BEFORE UPDATE OF estado ON proyectos
    FOR EACH ROW EXECUTE FUNCTION fn_validar_transicion_proyecto();

-- 11.4 — Validación de reseñas verificadas
-- "Miembro real" incluye al Creador del proyecto (nunca pasa por
-- equipos_membresias, porque esa tabla solo registra ingresos vía
-- vacante) y a cualquier colaborador con membresía activa o retirada.
CREATE OR REPLACE FUNCTION fn_validar_resena() RETURNS TRIGGER AS $$
DECLARE
    v_estado_proyecto      VARCHAR(20);
    v_autor_es_miembro     BOOLEAN;
    v_destinatario_miembro BOOLEAN;
BEGIN
    SELECT estado INTO v_estado_proyecto FROM proyectos WHERE id = NEW.proyecto_id;

    IF v_estado_proyecto IS DISTINCT FROM 'finalizado' THEN
        RAISE EXCEPTION 'Solo se pueden crear reseñas en proyectos Finalizados (proyecto % está en estado %)',
            NEW.proyecto_id, v_estado_proyecto;
    END IF;

    SELECT EXISTS (
        SELECT 1 FROM equipos_membresias WHERE proyecto_id = NEW.proyecto_id AND usuario_id = NEW.autor_id
        UNION
        SELECT 1 FROM proyectos WHERE id = NEW.proyecto_id AND creador_id = NEW.autor_id
    ) INTO v_autor_es_miembro;

    SELECT EXISTS (
        SELECT 1 FROM equipos_membresias WHERE proyecto_id = NEW.proyecto_id AND usuario_id = NEW.destinatario_id
        UNION
        SELECT 1 FROM proyectos WHERE id = NEW.proyecto_id AND creador_id = NEW.destinatario_id
    ) INTO v_destinatario_miembro;

    IF NOT v_autor_es_miembro OR NOT v_destinatario_miembro THEN
        RAISE EXCEPTION 'Autor y destinatario deben haber sido miembros reales del proyecto %', NEW.proyecto_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validar_resena
    BEFORE INSERT ON resenas
    FOR EACH ROW EXECUTE FUNCTION fn_validar_resena();

-- 11.5 — Bloqueo de borrado físico en tablas de historial
-- Se aplica a: usuarios, perfiles, proyectos, proyecto_media, vacantes,
-- postulaciones, invitaciones, equipos_membresias, resenas, reportes.
--
-- NO se aplica a (a propósito):
--   - Catálogos (habilidades, tecnologias, intereses): pueden borrarse
--     físicamente cuando NO están en uso (protegidos solo por
--     ON DELETE RESTRICT desde las tablas puente).
--   - Tablas puente (usuarios_habilidades, vacante_tecnologias_requeridas,
--     etc.): agregar/quitar una asociación es edición normal, no un
--     evento de historial.
--   - configuracion_pesos_matching: ya protegida por ON DELETE RESTRICT
--     desde postulaciones.pesos_usados_id una vez que se usó alguna vez.
--
-- La única forma de revertir esto es deshabilitar manualmente el
-- trigger correspondiente desde una sesión con acceso directo a la
-- base de datos (fuera de la aplicación), tal como se pidió: ni
-- siquiera un administrador de la plataforma puede provocar un
-- DELETE real a través del sistema.
CREATE OR REPLACE FUNCTION fn_prevenir_borrado_fisico() RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION
        'Eliminación física no permitida en "%". Use la columna es_activo/estado correspondiente para ocultar el registro. Un borrado real solo es posible deshabilitando este trigger manualmente desde la base de datos.',
        TG_TABLE_NAME;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_bloquear_borrado_usuarios BEFORE DELETE ON usuarios
    FOR EACH ROW EXECUTE FUNCTION fn_prevenir_borrado_fisico();
CREATE TRIGGER trg_bloquear_borrado_perfiles BEFORE DELETE ON perfiles
    FOR EACH ROW EXECUTE FUNCTION fn_prevenir_borrado_fisico();
CREATE TRIGGER trg_bloquear_borrado_proyectos BEFORE DELETE ON proyectos
    FOR EACH ROW EXECUTE FUNCTION fn_prevenir_borrado_fisico();
CREATE TRIGGER trg_bloquear_borrado_proyecto_media BEFORE DELETE ON proyecto_media
    FOR EACH ROW EXECUTE FUNCTION fn_prevenir_borrado_fisico();
CREATE TRIGGER trg_bloquear_borrado_vacantes BEFORE DELETE ON vacantes
    FOR EACH ROW EXECUTE FUNCTION fn_prevenir_borrado_fisico();
CREATE TRIGGER trg_bloquear_borrado_postulaciones BEFORE DELETE ON postulaciones
    FOR EACH ROW EXECUTE FUNCTION fn_prevenir_borrado_fisico();
CREATE TRIGGER trg_bloquear_borrado_invitaciones BEFORE DELETE ON invitaciones
    FOR EACH ROW EXECUTE FUNCTION fn_prevenir_borrado_fisico();
CREATE TRIGGER trg_bloquear_borrado_membresias BEFORE DELETE ON equipos_membresias
    FOR EACH ROW EXECUTE FUNCTION fn_prevenir_borrado_fisico();
CREATE TRIGGER trg_bloquear_borrado_resenas BEFORE DELETE ON resenas
    FOR EACH ROW EXECUTE FUNCTION fn_prevenir_borrado_fisico();
CREATE TRIGGER trg_bloquear_borrado_reportes BEFORE DELETE ON reportes
    FOR EACH ROW EXECUTE FUNCTION fn_prevenir_borrado_fisico();

-- 11.6 — Inmutabilidad total de auditoria_logs (ni UPDATE ni DELETE)
-- Más estricto que el resto: un log de auditoría que se puede editar
-- ya no sirve como auditoría. Esta es la única tabla del esquema donde
-- se bloquea también el UPDATE, no solo el DELETE.
CREATE OR REPLACE FUNCTION fn_inmutable_auditoria() RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'auditoria_logs es de solo-append: no se permite modificar ni eliminar registros existentes.';
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_inmutable_auditoria
    BEFORE UPDATE OR DELETE ON auditoria_logs
    FOR EACH ROW EXECUTE FUNCTION fn_inmutable_auditoria();

-- =====================================================================
-- SECCIÓN 12 — DATOS SEMILLA DE CATÁLOGOS (ejemplo, ajustar libremente)
-- =====================================================================

INSERT INTO habilidades (nombre, categoria) VALUES
    ('Backend Development', 'Desarrollo'),
    ('Frontend Development', 'Desarrollo'),
    ('UI/UX Design', 'Diseño'),
    ('Database Design', 'Datos'),
    ('DevOps', 'Infraestructura'),
    ('QA / Testing', 'Calidad'),
    ('Project Management', 'Gestión'),
    ('Mobile Development', 'Desarrollo'),
    ('Data Science', 'Datos')
ON CONFLICT (nombre) DO NOTHING;

INSERT INTO tecnologias (nombre, categoria) VALUES
    ('Python', 'Lenguaje'),
    ('Django', 'Framework'),
    ('JavaScript', 'Lenguaje'),
    ('React', 'Framework'),
    ('Tailwind CSS', 'Framework'),
    ('PostgreSQL', 'Base de datos'),
    ('Docker', 'Infraestructura'),
    ('Git', 'Herramienta'),
    ('Figma', 'Herramienta')
ON CONFLICT (nombre) DO NOTHING;

COMMIT;
