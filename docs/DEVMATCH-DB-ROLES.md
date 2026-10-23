# Roles de base de datos de DevMatch

Referencia para el equipo. Complementa la sección 6.5 de `DEVMATCH-BD.md`.

> Este documento es público. **No contiene credenciales** y no debe contenerlas. El procedimiento
> operativo completo de creación, grants y rotación lo custodia el Integrador en el vault privado.
> Si necesitas una intervención sobre roles o permisos, pídesela al Integrador; no improvises
> SQL de propietario en Neon.

## Modelo

| Rol | Uso | Permisos |
| --- | --- | --- |
| `devmatch_app` | `runserver` y aplicación desplegada | DML sobre tablas de negocio; `SELECT` sobre infraestructura de Django y `django_migrations` |
| `neondb_owner` | Solo `migrate` y DDL | Dueño de las tablas, secuencias, funciones y esquema |
| `devmatch_test` | Solo tests locales contra Neon | `CREATEDB`; sin permisos sobre las tablas de `devmatch_db` |

El rol de runtime **no** puede:

- `CREATE TABLE`, `ALTER TABLE` ni `DROP TABLE`.
- `TRUNCATE`.
- `ALTER TABLE ... DISABLE TRIGGER`.
- Escribir en `django_migrations`.
- Crear roles o bases de datos.

Esa restricción es intencional: si la aplicación no puede desactivar triggers, el borrado lógico
y la auditoría quedan protegidos de verdad.

`devmatch_test` solo se usa para que Django cree `test_devmatch_db`. No debe usarse en
`runserver` ni en producción.

## Configuración de `.env`

```env
DATABASE_URL=postgresql://devmatch_app:...@ep-xxxx-pooler.../devmatch_db?sslmode=require&channel_binding=require
TEST_DATABASE_URL=postgresql://devmatch_test:...@ep-xxxx.../devmatch_db?sslmode=require&channel_binding=require
```

Solo el Integrador tiene además:

```env
MIGRATION_DATABASE_URL=postgresql://neondb_owner:...@ep-xxxx.../devmatch_db?sslmode=require&channel_binding=require
```

`DATABASE_URL` usa el host **pooler**. `MIGRATION_DATABASE_URL` y `TEST_DATABASE_URL` usan el
host **directo** (sin `-pooler`): las migraciones y la creación de bases de tests no son
compatibles con el pooling transaccional.

**Nunca compartas estas URLs por chat, PR, capturas o archivos dentro del repositorio.** El
`.env` es local y está ignorado por Git.

## Qué puede hacer cada integrante

Con `DATABASE_URL` (rol de runtime):

- Correr `python manage.py runserver`.
- Generar migraciones de su propia app con `python manage.py makemigrations <app>`.
- Verificar que no falten migraciones con `python manage.py makemigrations --check --dry-run`.
- Consultar el estado con comandos de solo lectura, si hace falta.

Lo que **no** debe hacer:

- Correr `python manage.py migrate` contra Neon.
- Usar `MIGRATION_DATABASE_URL` ni pedir la contraseña de `neondb_owner`.
- Editar migraciones ya aplicadas: los cambios van en una migración nueva.
- Desactivar triggers o modificar permisos/roles en Neon.
- Compartir credenciales o incluirlas en un PR.

El flujo completo de migraciones está en `DEVMATCH-DISTRIBUCION.md`, sección
**"Migraciones y roles de base de datos"**.

## Migraciones

Solo el Integrador:

```powershell
$env:DJANGO_SETTINGS_MODULE="config.settings.migrate"
python manage.py migrate
```

```bash
DJANGO_SETTINGS_MODULE=config.settings.migrate python manage.py migrate
```

Si se intenta con `DATABASE_URL` (runtime), PostgreSQL rechaza la operación. Eso es lo esperado.

## Tests contra Neon

```powershell
$env:DJANGO_SETTINGS_MODULE="config.settings.test"
python manage.py test apps --noinput --keepdb
```

```bash
DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test apps --noinput --keepdb
```

`devmatch_test` crea `test_devmatch_db` la primera vez. No dar permisos sobre las tablas de
producción a ese rol.

## Verificación segura

Estas consultas se pueden ejecutar como `devmatch_app`; no modifican nada:

```sql
SELECT current_user, rolsuper, rolcreaterole, rolcreatedb, rolbypassrls
FROM pg_roles WHERE rolname = current_user;

SELECT has_schema_privilege('public', 'CREATE'); -- false

SELECT
  has_table_privilege('proyectos', 'SELECT'),   -- true
  has_table_privilege('proyectos', 'INSERT'),   -- true
  has_table_privilege('proyectos', 'UPDATE'),   -- true
  has_table_privilege('proyectos', 'DELETE'),   -- true
  has_table_privilege('proyectos', 'TRUNCATE'), -- false
  has_table_privilege('proyectos', 'TRIGGER');  -- false

SELECT
  has_table_privilege('django_migrations', 'SELECT'), -- true
  has_table_privilege('django_migrations', 'INSERT'); -- false
```

Las pruebas negativas no se documentan aquí. Solo el Integrador las ejecuta, en una rama/staging
desechable y con respaldo.

## Rotación de credenciales

La rotación la hace el Integrador. Si una credencial circuló fuera del `.env` local o apareció en
un PR, un log o una captura, avisa de inmediato: hay que rotarla y verificar que la anterior ya
no conecta.
