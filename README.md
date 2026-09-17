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
git checkout etapa-1-base
```

Actualiza la rama con los últimos cambios:

```bash
git pull origin etapa-1-base
```

A partir de este punto, puedes continuar con la configuración del entorno de desarrollo indicada en las siguientes secciones.

> **Importante:** no trabajes directamente sobre `etapa-1-base`. Cuando vayas a comenzar una tarea, crea tu propia rama siguiendo la convención establecida:
>
> ```bash
> git checkout -b etapa-1/<app>-<tarea>
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
```

---

## 3. Variables de Entorno y Base de Datos

Crea tu archivo local copiando la plantilla:

```bash
cp .env.example .env
```

> **Windows:** si `cp` no funciona en tu terminal, puedes copiar `.env.example` manualmente y renombrar la copia como `.env`.

Pide las credenciales de acceso al Integrador y agrégalas a tu archivo `.env`.

Al utilizar **Neon**, no necesitas crear una base de datos local ni configurar usuarios de PostgreSQL. La variable `DATABASE_URL` proporcionada por el Integrador conecta directamente con la base de datos compartida en la nube.

Ejemplo:

```env
DATABASE_URL=postgresql://usuario:password@ep-xxxx.neon.tech/db?sslmode=require&channel_binding=require
```

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

Por ahora, **no ejecutes migraciones** si estas todavía están siendo coordinadas por el equipo.

Arranca la aplicación con:

```bash
python manage.py runserver
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
git checkout etapa-1-base
git pull origin etapa-1-base
```

Crea tu rama de tarea siguiendo estrictamente la convención:

```bash
git checkout -b etapa-1/<app>-<tarea>
```

Por ejemplo:

```bash
git checkout -b etapa-1/accounts-modelos
```

### Durante el desarrollo

Modifica únicamente los archivos asignados a tu rol.

Si necesitas alterar archivos compartidos, como `base.html`, `requirements.txt` o archivos de configuración comunes, **notifícalo previamente al equipo o coordínalo directamente con el Integrador**.

### Subir los cambios

Cuando termines tu tarea:

```bash
git add .
git commit -m "Descripción de los cambios"
git push origin etapa-1/<app>-<tarea>
```

Después, abre un **Pull Request (PR)** hacia:

```text
etapa-1-base
```

> La rama `main` está protegida y no se deben realizar pushes directos sobre ella.
