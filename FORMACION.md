# Plan de formación — medición de marketing

Itinerario para aprender las metodologías y librerías del catálogo, haciendo. Cada módulo
tiene lectura, un ejercicio con verdad conocida, y preguntas que hay que poder responder sin
mirar. Es un documento vivo: se reordena según lo que anotes en **Estado**.

**Cómo se adapta.** Al acabar un módulo, rellena su fila en Estado: fecha, qué te costó, qué
quieres profundizar o saltar. Al empezar cada sesión, Claude lee esta tabla y propone el
siguiente paso: profundizar donde costó, saltar lo que ya dominas, adelantar lo que pides.
Si un módulo genera una pregunta que no cabe aquí, va a `NOTES.md`; si genera un experimento,
a `experiments/`.

**Vídeo.** MMT no produce vídeo propio, pero `libs/videos.md` lista el ajeno que vale, con
duración y a qué módulo sirve. La serie oficial de Meridian cubre buena parte de los módulos 3,
4, 5 y 6 en cortos de 2 a 8 minutos. Es siempre opcional, y un vídeo que revele una avería va
después del drill.

Ritmo orientativo: un módulo por sesión de 2–3 h. Orden pensado para que cada módulo use lo
anterior; se puede alterar, pero el 0, el 1 y el 3 son la base de todo lo demás.

## Estado

| # | Módulo | Estado | Fecha | Qué me costó / qué quiero profundizar |
|---|---|---|---|---|
| 0 | Mapa del terreno | pendiente | | |
| 1 | Datos sintéticos y verdad conocida | pendiente | | |
| 2 | Encuestas de impacto | pendiente | | |
| 3 | MMM I: mecánica y PyMC-Marketing | pendiente | | |
| 4 | MMM II: Meridian, la misma tabla | pendiente | | |
| 5 | Experimentos geo e incrementalidad | pendiente | | |
| 6 | Calibración: experimento → prior → MMM | pendiente | | |
| 7 | Causalidad general y uplift | pendiente | | |
| 8 | Robyn: la escuela no bayesiana | pendiente | | |
| 9 | Conjoint y MaxDiff | pendiente | | |
| 10 | Medición unificada e IA aplicada | pendiente | | |

Estados: pendiente · en curso · hecho · saltado (con motivo).

## Módulos

### 0 · Mapa del terreno (1 h)
- **Leer:** `conceptos/mapa-del-terreno.md`, `libs/CATALOGO.md`.
- **Hacer:** para cada producto o cliente que tengas a mano escribe en una línea qué
  pregunta de medición tiene y qué familia la respondería. Guárdalo en `NOTES.md`.
- **Comprobar:** ¿Por qué son tres familias y no una? ¿Qué mide cada una que las otras no?
  ¿Por qué la atribución multi-touch se quedó atrás?

### 1 · Datos sintéticos y verdad conocida (2 h)
- **Leer:** docstrings de `generators/synthetic_mmm.py` y `generators/synthetic_brand_lift.py`.
- **Hacer:** genera `base` con otro seed y con `noise_sd_pct=0.15`; abre el `truth.json` y
  explica cada campo. Cambia el CV de gasto de search a 0,7 y guarda la verdad: la usarás en
  el módulo 3.
- **Comprobar:** ¿Qué es el ROI verdadero y por qué no es beta? ¿Por qué los datos reales
  no sirven para evaluar un modelo? ¿Qué hace "honesto pero fácil" a este generador (ver
  `libs/amss.md`)?

### 2 · Encuestas de impacto (2–3 h)
- **Leer:** `conceptos/encuestas-de-impacto.md`, `experiments/05-encuesta-brand-lift/RESULTADO.md`.
- **Hacer:** corre `run.py`. Luego cambia el generador para lift 0 pp en digitales y 15 en
  el resto, y observa si el ingenuo del RCT sigue acertando y si `balance` pasa a hacer
  falta. Anota el resultado en el RESULTADO como adenda.
- **Comprobar:** ¿Qué arregla reponderar y qué no? ¿Cuántas respuestas hacen falta para un
  lift de 2 pp con baseline 30 %? ¿Qué le preguntarías a un informe de brand lift de Meta?
- **Vídeo:** no hay nada decente; lo oficial de Google sobre brand lift es un tutorial de
  interfaz. Es un hueco declarado en `libs/videos.md`.

### 3 · MMM I: mecánica y PyMC-Marketing (3 h)
- **Leer:** sección MMM de `mapa-del-terreno.md`, `libs/pymc-marketing.md`,
  `experiments/01-pymc-vs-verdad/RESULTADO.md`.
- **Ver (opcional):** `Adstock and Hill` (5:51), que dibuja las dos curvas. Enlaces en
  `libs/videos.md`.
- **Hacer:** corre las tres variantes. Luego (a) quita el control `trend` y mira qué pasa con
  el baseline; (b) ajusta sobre el dataset con search CV 0,7 del módulo 1 y comprueba si su
  intervalo se estrecha. Eso es la lección entera de identificación.
- **Comprobar:** ¿Qué es adstock y qué es saturación, con un dibujo cada uno? ¿Por qué video
  se identifica y search no? ¿Por qué la verdad dentro del intervalo no basta para decidir?

### 4 · MMM II: Meridian (3 h)
- **Leer:** `libs/meridian.md`, `experiments/02-meridian-vs-verdad/RESULTADO.md`.
  Documentación oficial de Meridian: modelo y priors de ROI.
- **Ver (opcional):** de la serie oficial, `Intro to Priors` (2:17) y `Treatment Prior Types`
  (4:30). `Knots in Meridian` (5:25), solo después del drill de averías. Enlaces en
  `libs/videos.md`.
- **Hacer:** corre las tres variantes de `run.py` (venv `.venvs/meridian`, ~35 s cada una).
  Luego inventa un cuarto prior de ROI que te parezca defendible sin mirar la verdad, córrelo
  y compara search: eso es lo que hace un analista real cada vez que ajusta un Meridian.
- **Comprobar:** ¿En qué difieren los priors de Meridian (sobre ROI) y de PyMC-Marketing (sobre
  parámetros de curva)? ¿Cuál acerca más a la verdad y a qué coste? ¿Qué es un modelo geo y
  por qué Meridian lo prefiere?

### 5 · Experimentos geo e incrementalidad (3 h)
- **Leer:** `libs/meridian-geox.md`, `libs/geolift.md`, `libs/causalimpact.md`.
- **Ver (opcional):** `Geo Vs National Level Modeling` (4:47) de la serie oficial y
  `Conversion Lift` (4:52, solo los dos primeros tercios). Para ir en serio, la charla de ASOS
  sobre diseño geo (34:40), que es la más densa del catálogo. Enlaces en `libs/videos.md`.
- **Hacer:** extender el generador a panel geo (regiones con baseline distinto y un apagado
  en algunas). Correr CausalImpact (Python) sobre una intervención y GeoX sobre el panel.
  GeoLift requiere R (pendiente de instalar).
- **Comprobar:** ¿Qué es un control sintético? ¿Qué diferencia un geo-test de un holdout de
  usuarios? ¿Cuándo el pre-periodo es demasiado corto?

### 6 · Calibración: experimento → prior → MMM (3 h)
- **Leer:** "El bucle que de verdad funciona" en `mapa-del-terreno.md`; docs de lift-test
  calibration en PyMC-Marketing y de ROI priors en Meridian.
- **Ver (opcional):** `Calibrate Treatment Priors` (3:09), el bucle entero del curso en tres
  minutos, y la charla "Using Causal thinking to make MMM" (27:06), que calibra sobre datos
  simulados con verdad conocida igual que hacemos aquí. Enlaces en `libs/videos.md`.
- **Hacer:** `experiments/04-calibracion-experimento/`: inyectar el ROI verdadero de video
  como prior y medir cuánto se estrechan search y social. Repetir con un prior equivocado
  (2× la verdad) y ver cuánto daño hace.
- **Comprobar:** ¿Por qué el experimento identifica lo que el MMM no puede? ¿Qué pasa si el
  experimento midió otra cosa (ventas vs. consideración)? ¿Cuántos experimentos al año
  necesita un MMM de 6 canales?

### 7 · Causalidad general y uplift (3 h)
- **Leer:** `libs/causalpy.md`; notas por escribir de DoWhy, EconML, CausalML.
- **Ver (opcional):** `Controls, Mediators and Treatments` (7:09) explica el DAG, el confusor y
  el mediador mejor que ningún texto que tengamos. Enlace en `libs/videos.md`.
- **Hacer:** con el generador de brand lift observacional, estimar el efecto con CausalPy
  (regresión con covariables) y con DoWhy (grafo + refutación). Luego CausalML para uplift:
  ¿recupera que el lift es mayor en digitales?
- **Comprobar:** ¿Qué es un DAG y para qué sirve refutar? ¿Diferencia entre ATE, ATT y CATE?
  ¿Cuándo uplift modeling y cuándo lift medio?

### 8 · Robyn: la escuela no bayesiana (2–3 h, requiere R)
- **Leer:** `libs/robyn.md`.
- **Hacer:** `experiments/03-robyn-vs-verdad/` en R, mismos datos. Elegir un modelo del
  frente de Pareto y justificarlo.
- **Comprobar:** ¿Qué es Ridge y por qué Robyn lo usa? ¿Qué es un frente de Pareto de modelos
  y qué criterio eliges? ¿Qué le falta a Robyn que tienen los bayesianos?

### 9 · Conjoint y MaxDiff (2 h)
- **Leer:** nota por escribir de `xlogit`; concepto de elección discreta.
- **Hacer:** generador de un conjoint sintético (atributos con utilidades verdaderas) y
  recuperarlas con `xlogit`.
- **Comprobar:** ¿Qué pregunta responde un conjoint que no responde un brand lift? ¿Qué es la
  utilidad parcial? ¿Cuándo MaxDiff en vez de conjoint?

### 10 · Medición unificada e IA aplicada (3 h)
- **Leer:** todo lo anterior, de memoria.
- **Hacer:** un documento `conceptos/medicion-unificada.md` con cómo casan MMM, experimentos,
  encuestas y atribución para un caso de la cartera. Y el primer paso de IA aplicada: un
  script que lea el `summary.json` de un experimento MMM y escriba el diagnóstico en lenguaje
  llano (qué canal saturó, qué intervalo es demasiado ancho, qué experimento haría falta).
- **Comprobar:** ante un presupuesto de 100 k€ en 4 canales y un año, ¿qué medirías, con qué,
  en qué orden?

## Lo que va apareciendo

Anota aquí lo que quieras añadir al plan (una librería nueva, una metodología, una duda que
merece módulo). Claude lo integra en la siguiente revisión.

- (vacío)
