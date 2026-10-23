## Descripción

<!-- ¿Qué hace este PR? Un par de líneas basta. -->

## Rama de tarea y archivos tocados

<!-- Rama: etapa-N/app-tarea -->
<!-- Lista los archivos que tocaste. Deben coincidir con los de tu rama de tarea
     según DEVMATCH-DISTRIBUCION.md. Si tocaste algo fuera de esa lista, explica por qué. -->

## Etapa / CR relacionados

<!-- ej. Etapa 3 — CR-14, CR-17 -->

## Definición de Terminado

- [ ] El proyecto corre sin errores localmente (`python manage.py runserver`)
- [ ] No dejaste código comentado ni prints de debug
- [ ] Solo actualizaste los archivos que te correspondían según tu rama de tarea
- [ ] Corrí los tests de mi app con `config.settings.test` y pasan

## ¿Tocaste un archivo compartido?

- [ ] No
- [ ] Sí, es `templates/base.html` o `templates/partials/` → coordinado con el Integrador
- [ ] Sí, es un archivo raíz compartido (`requirements.txt`, `.env.example`,
      `config/settings/base.py`, `package.json`, `tailwind.config.js`,
      `postcss.config.js`) → avisado en el chat del equipo antes de este PR

## Migraciones

- [ ] **N/A** — este PR no toca modelos ni migraciones.
- [ ] Soy la persona dueña del `models.py` de esta app en esta etapa.
- [ ] Generé la migración con `python manage.py makemigrations <app>` y la incluí en el PR.
- [ ] `python manage.py makemigrations --check --dry-run` no reporta cambios pendientes.
- [ ] No edité migraciones ya aplicadas; cualquier corrección va en una migración nueva.
- [ ] No ejecuté `migrate` contra Neon ni usé `MIGRATION_DATABASE_URL`.
- [ ] Entiendo que este PR **no aplica** la migración a Neon: el Integrador la aplicará
      después del merge con `config.settings.migrate` y `MIGRATION_DATABASE_URL`.
- [ ] Si la migración requiere datos, una maniobra especial o puede tardar, lo expliqué
      en la descripción y avisé al Integrador.

> No incluyas en el PR ni en capturas de pantalla `.env`, `MIGRATION_DATABASE_URL`,
> contraseñas de Neon ni credenciales de ningún rol.

## Rama destino

Confirmo que este PR apunta a `etapa-N-base` y **no** a `main`.
