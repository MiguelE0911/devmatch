# Guía de Puesta en Marcha Local — DevMatch

## 1. Descargar el Repositorio

Clona el repositorio de DevMatch en tu equipo:

```bash
git clone <URL_DEL_REPOSITORIO>
```

Entra a la carpeta del proyecto:

```bash
cd devmatch
```

Verifica que estás dentro del repositorio:

```bash
git status
```

Deberías ver información similar a:

```text
On branch main
Your branch is up to date with 'origin/main'.
```

### Obtener la rama de integración

Una vez clonado el repositorio, cambia a la rama de integración correspondiente a la etapa actual:

```bash
git checkout etapa-3-base
```

Actualiza la rama con los últimos cambios:

```bash
git pull origin etapa-3-base
```

A partir de este punto, puedes continuar con la configuración del entorno de desarrollo indicada en las siguientes secciones.

> **Importante:** no trabajes directamente sobre `etapa-3-base`. Cuando vayas a comenzar una tarea, crea tu propia rama siguiendo la convención establecida:
>
> ```bash
> git checkout -b etapa-3/<app>-<tarea>
> ```

---

## 2. Entorno de Desarrollo (Anaconda)

Activa el entorno virtual de Anaconda asignado al equipo:

```bash
conda activate dsw8408
```

Instala las dependencias base requeridas para el entorno:

```bash
pip install "Django>=5.2,<5.3"
pip install "dj-database-url>=3.1.2"
pip install "python-dotenv>=1.0,<2.0"
pip install "psycopg2-binary>=2.9,<3.0"
pip install "whitenoise>=6.7,<7.0"
pip install "Pillow>=10,<13"
pip install "boto3>=1.34,<2.0"
```

> Alternativa: `pip install -r requirements.txt` instala todo lo anterior de una vez (es la fuente de verdad de las versiones).

---

## 3. Variables de Entorno y Base de Datos

Crea tu archivo local copiando la plantilla:

```bash
cp .env.example .env
```

> **Windows:** si `cp` no funciona en tu terminal, puedes copiar `.env.example` manualmente y renombrar la copia como `.env`.

Pide las credenciales de acceso al Integrador y agrégalas a tu archivo `.env`.

DevMatch usa **tres roles de PostgreSQL distintos** en Neon:

- **`devmatch_app` (runtime):** lo usa `runserver` y la aplicación desplegada. Solo puede leer y escribir filas; no puede migrar, crear tablas, deshabilitar triggers ni borrar el historial.
- **`neondb_owner` (migraciones):** solo lo usa el Integrador para `migrate`. Nunca debe ir en la aplicación.
- **`devmatch_test` (tests):** solo crea la base `test_*` del runner de Django. No se usa en `runserver`.

Tu `.env` debe quedar así (el Integrador te pasa la URL de runtime):

```env
DATABASE_URL=postgresql://devmatch_app:password@ep-xxxx-pooler.neon.tech/devmatch_db?sslmode=require&channel_binding=require
```

Si tenías una `DATABASE_URL` con `neondb_owner`, fue rotada y ya no sirve. Reemplázala por la de `devmatch_app`.

Para correr tests locales contra Neon, el Integrador también te pasa `TEST_DATABASE_URL` (rol `devmatch_test`, con `CREATEDB`). No uses `devmatch_app` para tests: el runner de Django necesita crear una base `test_*`. Ver `docs/DEVMATCH-DISTRIBUCION.md`.

Si eres dueño de un `models.py`, puedes generar su migración con `python manage.py makemigrations <app>` y commitearla. **No ejecutes `migrate` contra Neon**: el Integrador aplica las migraciones después del merge. Ver la sección "Migraciones y roles de base de datos" en `docs/DEVMATCH-DISTRIBUCION.md`.

### Generar la llave secreta de Django

Genera tu propia llave secreta ejecutando:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

Copia el resultado en la variable correspondiente de tu `.env`:

```env
DJANGO_SECRET_KEY=tu_llave_secreta
```

> **Importante:** el archivo `.env` es local y no debe subirse al repositorio.

### Storage de imágenes (opcional)

Los logos y prototipos se procesan con Pillow (peso, formato real y redimensión) antes de guardarse. Por defecto el archivo se guarda en `media/` local, así que **tú lo ves pero tus compañeros no**: solo funciona para desarrollo individual.

Para que todo el equipo vea las imágenes subidas, pide al Integrador la credencial de **Neon Object Storage** y descomenta el bloque correspondiente en tu `.env` (ver `.env.example`):

```env
AWS_ACCESS_KEY_ID=nak_live_...
AWS_SECRET_ACCESS_KEY=nsk_live_...
AWS_ENDPOINT_URL_S3=https://<branch-id>.storage.c-2.us-east-2.aws.neon.tech
AWS_REGION=us-east-2
NEON_STORAGE_BUCKET=devmatch-media
```

Si esas 5 variables están completas, las imágenes se suben al bucket del equipo (URL https pública, visible en las páginas de proyecto). Si falta alguna, la app sigue funcionando con el guardado local. Nunca subas `.env` al repositorio.

---

## 4. Frontend (Tailwind CSS)

Instala las dependencias de Node:

```bash
npm install
```

Construye el CSS base por primera vez:

```bash
npm run build:css
```

Mientras trabajas en la interfaz, mantén el compilador de Tailwind en escucha:

```bash
npm run watch:css
```

> Puedes mantener este comando ejecutándose en una terminal mientras utilizas otra para levantar Django.

---

## 5. Levantar el Servidor

**No ejecutes `migrate`:** eso lo hace únicamente el Integrador con el rol de migraciones y `config.settings.migrate`. Tu `DATABASE_URL` es el rol de runtime y no tiene permisos para migrar.

Arranca la aplicación con:

```bash
python manage.py runserver
```

Si necesitas correr migraciones y eres el Integrador:

```powershell
$env:DJANGO_SETTINGS_MODULE="config.settings.migrate"
python manage.py migrate
```

```bash
DJANGO_SETTINGS_MODULE=config.settings.migrate python manage.py migrate
```

Abre en el navegador:

```text
http://127.0.0.1:8000/
```

Si las variables de entorno están configuradas correctamente y la conexión con Neon funciona, deberías ver la pantalla de confirmación de Django.

---

## 6. Flujo de Ramas (Git)

Posiciónate en la rama de integración actual y actualízala:

```bash
git checkout etapa-3-base
git pull origin etapa-3-base
```

Crea tu rama de tarea siguiendo estrictamente la convención:

```bash
git checkout -b etapa-3/<app>-<tarea>
```

Por ejemplo:

```bash
git checkout -b etapa-3/accounts-modelos
```

### Durante el desarrollo

Modifica únicamente los archivos asignados a tu rol.

Si necesitas alterar archivos compartidos, como `base.html`, `requirements.txt` o archivos de configuración comunes, **notifícalo previamente al equipo o coordínalo directamente con el Integrador**.

### Subir los cambios

Cuando termines tu tarea:

```bash
git add .
git commit -m "Descripción de los cambios"
git push origin etapa-3/<app>-<tarea>
```

Después, abre un **Pull Request (PR)** hacia:

```text
etapa-3-base
```

> La rama `main` está protegida y no se deben realizar pushes directos sobre ella.
