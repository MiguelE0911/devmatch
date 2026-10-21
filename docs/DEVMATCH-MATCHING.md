# DevMatch — Motor de compatibilidad (Match Score)

Documenta la fórmula y los casos de prueba reproducibles que exige
`DEVMATCH-SOLICITUD.md §5.3`. Cubre CR-05 (Match Score explicable) y
CR-07 (snapshot al postular).

Código: `apps/matching/engine.py`, `apps/matching/constants.py`,
`apps/applications/services.py` (`crear_postulacion`).

---

## 1. Estrategia

El Match Score es una **suma ponderada de 5 factores**. Cada factor da un
puntaje de 0 a 100 y se multiplica por su peso:

```
score = Σ (score_factor × peso_factor)        redondeado a 2 decimales
```

Los pesos se leen de la fila activa de `configuracion_pesos_matching`
(`es_activo = true`, patrón singleton). Por ahora es la
**Ponderación estándar v1.0**, fija porque CR-06 (pesos ajustables por el
Creador) está pospuesto:

| Factor | Peso |
|---|---|
| habilidades | 0.35 |
| nivel | 0.15 |
| tecnologias | 0.30 |
| experiencia | 0.10 |
| disponibilidad | 0.10 |

Estos valores deben coincidir en **tres sitios**: el seed
(`apps/core/management/commands/seed_data.py`), `PESOS_DEFAULT` en
`apps/matching/constants.py` y `DEVMATCH-BD.md` (sección 5.3). Si el equipo
cambia la ponderación, se cambian los tres a la vez.

## 2. Fórmula de cada factor

| Factor | Cálculo | Casos especiales |
|---|---|---|
| `habilidades` | `(habilidades del perfil ∩ habilidades requeridas) / habilidades requeridas × 100` | Si la vacante no requiere ninguna: **100** |
| `tecnologias` | Igual que habilidades, con tecnologías | Si la vacante no requiere ninguna: **100** |
| `nivel` | principiante = **33.33**, intermedio = **66.67**, avanzado = **100** | — |
| `experiencia` | `min(años, 5) / 5 × 100` | 5 años o más = 100 |
| `disponibilidad` | `min(horas_semana, 40) / 40 × 100` | 40 horas o más = 100 |

Los topes (5 años, 40 horas) y la escala de nivel están en
`apps/matching/constants.py`.

## 3. Limitación conocida: nivel, experiencia y disponibilidad

La tabla `vacantes` **no tiene columnas de requisito** de nivel mínimo,
experiencia mínima ni disponibilidad requerida. Solo existen requisitos de
habilidades y tecnologías (`vacante_habilidades_requeridas`,
`vacante_tecnologias_requeridas`).

Por eso `habilidades` y `tecnologias` comparan el perfil contra la vacante,
pero `nivel`, `experiencia` y `disponibilidad` se calculan como una
**escala absoluta del perfil**, sin compararlo con la vacante. Es la única
aproximación viable con el esquema actual. Consecuencias:

- Un mismo perfil obtiene el mismo puntaje en esos tres factores en
  cualquier vacante.
- El score mínimo no es 0: un perfil principiante sin habilidades ni
  tecnologías coincidentes obtiene **5.0** (caso C), porque el nivel
  principiante aporta 33.33 × 0.15.
- Si en el futuro `vacantes` incorpora columnas de requisito, hay que
  reemplazar `_score_nivel`, `_score_experiencia` y `_score_disponibilidad`
  en `engine.py`. Las postulaciones ya creadas no cambian (ver sección 4).

## 4. Snapshot (CR-07 y CR-12)

Al postular, `crear_postulacion` guarda en la fila de `postulaciones`:

- `match_score`: el score total.
- `match_factores`: el desglose, con esta forma (contrato con `DEVMATCH-BD.md`
  sección 9 y con el dashboard visual):

```json
{
  "habilidades":    {"score": 50.0,  "peso": 0.35},
  "nivel":          {"score": 66.67, "peso": 0.15},
  "tecnologias":    {"score": 50.0,  "peso": 0.30},
  "experiencia":    {"score": 60.0,  "peso": 0.10},
  "disponibilidad": {"score": 50.0,  "peso": 0.10}
}
```

- `pesos_usados`: la fila de pesos que se usó, para poder explicar el
  cálculo después.

El snapshot **nunca se recalcula**. Cambiar el perfil después de postular no
modifica postulaciones existentes. Una fila de pesos que ya fue usada no
debe sobrescribirse: si cambia la ponderación, se crea una versión nueva y
se desactiva la anterior.

## 5. Casos de prueba reproducibles

Todos con la ponderación estándar v1.0. Los ids son ejemplos de elementos de
catálogo.

| Caso | Perfil | Vacante requiere | habilidades | nivel | tecnologias | experiencia | disponibilidad | **Score** |
|---|---|---|---|---|---|---|---|---|
| A. Perfil ideal | habilidades {1,2}, tecnologías {10}, avanzado, 5 años, 40 h | habilidades {1,2}, tecnologías {10} | 100 | 100 | 100 | 100 | 100 | **100.0** |
| B. Parcial | habilidades {1}, tecnologías {10}, intermedio, 3 años, 20 h | habilidades {1,2}, tecnologías {10,11} | 50 | 66.67 | 50 | 60 | 50 | **53.5** |
| C. Sin coincidencias | nada, principiante, 0 años, 0 h | habilidades {1}, tecnologías {10} | 0 | 33.33 | 0 | 0 | 0 | **5.0** |
| D. Vacante sin requisitos | nada, principiante, 0 años, 10 h | nada | 100 | 33.33 | 100 | 0 | 25 | **72.5** |
| E. Topes superados | habilidades {1}, tecnologías {10}, avanzado, 12 años, 60 h | habilidades {1}, tecnologías {10} | 100 | 100 | 100 | 100 | 100 | **100.0** |

Cálculo del caso B:
`50×0.35 + 66.67×0.15 + 50×0.30 + 60×0.10 + 50×0.10 = 17.5 + 10.0005 + 15 + 6 + 5 = 53.5`

Estos cinco casos están automatizados en
`apps/matching/tests/test_engine.py` (clase `CasosDocumentadosTests`):

```
python manage.py test apps.matching.tests.test_engine --noinput --keepdb
```

## 6. Qué valida `crear_postulacion`

`crear_postulacion` **sí comprueba** que la vacante admita postulaciones:

- Que esté **activa** y en estado **`abierta`**.
- Que su proyecto **no esté `finalizado` ni `cancelado`** (un proyecto cerrado
  ya no recluta; esta regla no tiene trigger que la aplique, así que el
  servicio es el punto donde se garantiza).

Los dos casos levantan `VacanteNoPostulable`.

Lo que **no** comprueba es que el proyecto sea *visible* (que no esté en
`borrador`): esa validación corresponde a las **vistas** (Squad B), según
`DEVMATCH-BD.md` §7 (un proyecto en `borrador` no debe recibir postulaciones:
"filtro en las vistas/queries") y §9 (el botón "Postularme" se deshabilita si
`vacantes.estado` no es `abierta`).

Lo que además garantiza el servicio:

- Calcula y congela el score y su desglose.
- Impide una segunda postulación activa a la misma vacante
  (`ux_postulacion_activa_unica` → `PostulacionDuplicadaError`).
- Permite volver a postular tras un rechazo o un retiro.
- Falla con `ConfiguracionPesosNoDisponibleError` si no hay pesos activos.

## 7. Verificar los pesos activos

```sql
SELECT nombre, peso_habilidades, peso_nivel, peso_tecnologias,
       peso_experiencia, peso_disponibilidad, es_activo
FROM configuracion_pesos_matching
WHERE es_activo = TRUE;
```

Esperado: `0.350, 0.150, 0.300, 0.100, 0.100`.
