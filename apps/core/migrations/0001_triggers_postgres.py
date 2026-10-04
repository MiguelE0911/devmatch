"""Instala en PostgreSQL las 6 funciones y los 19 triggers de la Sección 11
de docs/devmatch_schema_v1.sql.

Motivo de existir: los triggers solo vivían en el .sql. La base de datos de
pruebas se construye solo con migraciones de Django, así que `manage.py test`
validaba un esquema sin ninguna de estas garantías: los tests afirmaban
cascadas que en producción abortan, y las transiciones de estado y las reseñas
no se validaban en absoluto.

Por qué en apps/core: el DDL es transversal (toca accounts, projects,
applications, teams, reviews, audit y moderation). Lo decide el Integrador
para no romper la regla de "solo el dueño de cada app corre makemigrations".

Idempotencia: esta migración se aplica sobre Neon, donde los triggers YA
existen (instalados a mano desde el .sql). `CREATE TRIGGER` no es idempotente
y fallaría, por eso cada uno va precedido de `DROP TRIGGER IF EXISTS`.
`CREATE OR REPLACE FUNCTION` sí es idempotente.

Orden: las dependencies apuntan a las 12 migraciones que crean las tablas, de
modo que en una base nueva los triggers se intenten crear después de que las
tablas existan. Sobre Neon no importan: esas migraciones van registradas como
aplicadas (--fake-initial) y esta es nueva, así que corre después.

Ninguna función usa SECURITY DEFINER a propósito: no hay escalada de
privilegios ni superficie de inyección de search_path. Si alguna vez se agrega,
debe fijar search_path con SET search_path = pg_catalog, public.
"""

from django.db import migrations

FUNCIONES_SQL = """
CREATE OR REPLACE FUNCTION fn_set_updated_at() RETURNS TRIGGER AS $$
BEGIN
    NEW.actualizado_en := now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

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
        RAISE EXCEPTION 'Transición de estado inválida en proyecto %: de % a %',
            NEW.id, OLD.estado, NEW.estado;
    END IF;

    IF NEW.estado = 'finalizado' THEN
        NEW.finalizado_en := now();
    ELSIF NEW.estado = 'cancelado' THEN
        NEW.cancelado_en := now();
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

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
        RAISE EXCEPTION 'Autor y destinatario deben haber sido miembros reales del proyecto %',
            NEW.proyecto_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_prevenir_borrado_fisico() RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION
        'Eliminación física no permitida en "%". Use la columna es_activo/estado correspondiente para ocultar el registro. Un borrado real solo es posible deshabilitando este trigger manualmente desde la base de datos.',
        TG_TABLE_NAME;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_inmutable_auditoria() RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'auditoria_logs es de solo-append: no se permite modificar ni eliminar registros existentes.';
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;
"""

TRIGGERS_SQL = """
DROP TRIGGER IF EXISTS trg_usuarios_updated_at ON usuarios;
CREATE TRIGGER trg_usuarios_updated_at BEFORE UPDATE ON usuarios
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

DROP TRIGGER IF EXISTS trg_perfiles_updated_at ON perfiles;
CREATE TRIGGER trg_perfiles_updated_at BEFORE UPDATE ON perfiles
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

DROP TRIGGER IF EXISTS trg_proyectos_updated_at ON proyectos;
CREATE TRIGGER trg_proyectos_updated_at BEFORE UPDATE ON proyectos
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

DROP TRIGGER IF EXISTS trg_vacantes_updated_at ON vacantes;
CREATE TRIGGER trg_vacantes_updated_at BEFORE UPDATE ON vacantes
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

DROP TRIGGER IF EXISTS trg_postulaciones_updated_at ON postulaciones;
CREATE TRIGGER trg_postulaciones_updated_at BEFORE UPDATE ON postulaciones
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

DROP TRIGGER IF EXISTS trg_membresia_actualiza_cupos ON equipos_membresias;
CREATE TRIGGER trg_membresia_actualiza_cupos
    AFTER INSERT OR UPDATE OF estado OR DELETE ON equipos_membresias
    FOR EACH ROW EXECUTE FUNCTION fn_actualizar_cupos_vacante();

DROP TRIGGER IF EXISTS trg_validar_transicion_proyecto ON proyectos;
CREATE TRIGGER trg_validar_transicion_proyecto
    BEFORE UPDATE OF estado ON proyectos
    FOR EACH ROW EXECUTE FUNCTION fn_validar_transicion_proyecto();

DROP TRIGGER IF EXISTS trg_validar_resena ON resenas;
CREATE TRIGGER trg_validar_resena
    BEFORE INSERT ON resenas
    FOR EACH ROW EXECUTE FUNCTION fn_validar_resena();

DROP TRIGGER IF EXISTS trg_bloquear_borrado_usuarios ON usuarios;
CREATE TRIGGER trg_bloquear_borrado_usuarios BEFORE DELETE ON usuarios
    FOR EACH ROW EXECUTE FUNCTION fn_prevenir_borrado_fisico();

DROP TRIGGER IF EXISTS trg_bloquear_borrado_perfiles ON perfiles;
CREATE TRIGGER trg_bloquear_borrado_perfiles BEFORE DELETE ON perfiles
    FOR EACH ROW EXECUTE FUNCTION fn_prevenir_borrado_fisico();

DROP TRIGGER IF EXISTS trg_bloquear_borrado_proyectos ON proyectos;
CREATE TRIGGER trg_bloquear_borrado_proyectos BEFORE DELETE ON proyectos
    FOR EACH ROW EXECUTE FUNCTION fn_prevenir_borrado_fisico();

DROP TRIGGER IF EXISTS trg_bloquear_borrado_proyecto_media ON proyecto_media;
CREATE TRIGGER trg_bloquear_borrado_proyecto_media BEFORE DELETE ON proyecto_media
    FOR EACH ROW EXECUTE FUNCTION fn_prevenir_borrado_fisico();

DROP TRIGGER IF EXISTS trg_bloquear_borrado_vacantes ON vacantes;
CREATE TRIGGER trg_bloquear_borrado_vacantes BEFORE DELETE ON vacantes
    FOR EACH ROW EXECUTE FUNCTION fn_prevenir_borrado_fisico();

DROP TRIGGER IF EXISTS trg_bloquear_borrado_postulaciones ON postulaciones;
CREATE TRIGGER trg_bloquear_borrado_postulaciones BEFORE DELETE ON postulaciones
    FOR EACH ROW EXECUTE FUNCTION fn_prevenir_borrado_fisico();

DROP TRIGGER IF EXISTS trg_bloquear_borrado_invitaciones ON invitaciones;
CREATE TRIGGER trg_bloquear_borrado_invitaciones BEFORE DELETE ON invitaciones
    FOR EACH ROW EXECUTE FUNCTION fn_prevenir_borrado_fisico();

DROP TRIGGER IF EXISTS trg_bloquear_borrado_membresias ON equipos_membresias;
CREATE TRIGGER trg_bloquear_borrado_membresias BEFORE DELETE ON equipos_membresias
    FOR EACH ROW EXECUTE FUNCTION fn_prevenir_borrado_fisico();

DROP TRIGGER IF EXISTS trg_bloquear_borrado_resenas ON resenas;
CREATE TRIGGER trg_bloquear_borrado_resenas BEFORE DELETE ON resenas
    FOR EACH ROW EXECUTE FUNCTION fn_prevenir_borrado_fisico();

DROP TRIGGER IF EXISTS trg_bloquear_borrado_reportes ON reportes;
CREATE TRIGGER trg_bloquear_borrado_reportes BEFORE DELETE ON reportes
    FOR EACH ROW EXECUTE FUNCTION fn_prevenir_borrado_fisico();

DROP TRIGGER IF EXISTS trg_inmutable_auditoria ON auditoria_logs;
CREATE TRIGGER trg_inmutable_auditoria
    BEFORE UPDATE OR DELETE ON auditoria_logs
    FOR EACH ROW EXECUTE FUNCTION fn_inmutable_auditoria();
"""

DROP_TRIGGERS_SQL = """
DROP TRIGGER IF EXISTS trg_inmutable_auditoria ON auditoria_logs;
DROP TRIGGER IF EXISTS trg_bloquear_borrado_reportes ON reportes;
DROP TRIGGER IF EXISTS trg_bloquear_borrado_resenas ON resenas;
DROP TRIGGER IF EXISTS trg_bloquear_borrado_membresias ON equipos_membresias;
DROP TRIGGER IF EXISTS trg_bloquear_borrado_invitaciones ON invitaciones;
DROP TRIGGER IF EXISTS trg_bloquear_borrado_postulaciones ON postulaciones;
DROP TRIGGER IF EXISTS trg_bloquear_borrado_vacantes ON vacantes;
DROP TRIGGER IF EXISTS trg_bloquear_borrado_proyecto_media ON proyecto_media;
DROP TRIGGER IF EXISTS trg_bloquear_borrado_proyectos ON proyectos;
DROP TRIGGER IF EXISTS trg_bloquear_borrado_perfiles ON perfiles;
DROP TRIGGER IF EXISTS trg_bloquear_borrado_usuarios ON usuarios;
DROP TRIGGER IF EXISTS trg_validar_resena ON resenas;
DROP TRIGGER IF EXISTS trg_validar_transicion_proyecto ON proyectos;
DROP TRIGGER IF EXISTS trg_membresia_actualiza_cupos ON equipos_membresias;
DROP TRIGGER IF EXISTS trg_postulaciones_updated_at ON postulaciones;
DROP TRIGGER IF EXISTS trg_vacantes_updated_at ON vacantes;
DROP TRIGGER IF EXISTS trg_proyectos_updated_at ON proyectos;
DROP TRIGGER IF EXISTS trg_perfiles_updated_at ON perfiles;
DROP TRIGGER IF EXISTS trg_usuarios_updated_at ON usuarios;
"""

DROP_FUNCIONES_SQL = """
DROP FUNCTION IF EXISTS fn_inmutable_auditoria();
DROP FUNCTION IF EXISTS fn_prevenir_borrado_fisico();
DROP FUNCTION IF EXISTS fn_validar_resena();
DROP FUNCTION IF EXISTS fn_validar_transicion_proyecto();
DROP FUNCTION IF EXISTS fn_actualizar_cupos_vacante();
DROP FUNCTION IF EXISTS fn_set_updated_at();
"""


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
        ("applications", "0001_initial"),
        ("audit", "0001_initial"),
        ("matching", "0001_initial"),
        ("moderation", "0001_initial"),
        ("projects", "0001_initial"),
        ("projects", "0002_vacante"),
        ("projects", "0003_proyectomedia"),
        ("projects", "0004_vacantehabilidadrequerida_vacantetecnologiarequerida"),
        ("reviews", "0001_initial"),
        ("teams", "0001_initial"),
        ("teams", "0002_equipomembresia"),
    ]

    operations = [
        migrations.RunSQL(
            sql=FUNCIONES_SQL,
            reverse_sql=DROP_FUNCIONES_SQL,
        ),
        migrations.RunSQL(
            sql=TRIGGERS_SQL,
            reverse_sql=DROP_TRIGGERS_SQL,
        ),
    ]