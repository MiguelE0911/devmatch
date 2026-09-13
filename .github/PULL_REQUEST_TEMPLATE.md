## Descripción

<!-- ¿Qué hace este PR? Un par de líneas basta. -->

## Rama de tarea y archivos tocados

<!-- Rama: etapa-N/app-tarea -->
<!-- Lista los archivos que tocaste. Deben coincidir con los de tu rama de tarea
     según DISTRIBUCION.md. Si tocaste algo fuera de esa lista, explica por qué. -->

## Etapa / CR relacionados

<!-- ej. Etapa 1 — CR-01, CR-10 -->

## Definición de Terminado

- [ ] El proyecto corre sin errores localmente (`python manage.py runserver`)
- [ ] Si tocaste modelos: las migraciones están generadas y committeadas
- [ ] No dejaste código comentado ni prints de debug
- [ ] Solo actualizaste los archivos que te correspondían según tu rama de tarea

## ¿Tocaste un archivo compartido?

- [ ] No
- [ ] Sí, es `templates/base.html` o `templates/partials/` → coordinado con el Integrador
- [ ] Sí, es un archivo raíz compartido (`requirements.txt`, `.env.example`,
      `config/settings/base.py`, `package.json`, `tailwind.config.js`,
      `postcss.config.js`) → avisado en el chat del equipo antes de este PR

## Migraciones

- [ ] N/A — este PR no toca modelos
- [ ] Sí, y soy el dueño designado del `models.py` de esta app en esta etapa

## Rama destino

Confirmo que este PR apunta a `etapa-N` y **no** a `main`.
