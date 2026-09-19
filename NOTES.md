# NOTES — MMT (Marketing Measurement Toolkit)

Estado vivo del proyecto. Lo cerrado va arriba, lo pendiente abajo.

## 2026-09-18 (tarde) — Revisar vídeo de verdad: leer la transcripción, no la ficha

Segunda pasada sobre `libs/videos.md`, esta vez leyendo el contenido. El método quedó escrito en
el propio fichero y tiene tres pasos: ficha comprobada contra YouTube, **transcripción
descargada y leída**, y veredicto explícito de método contra producto.

**Por qué hace falta el segundo paso.** El tutorial oficial de Brand Lift de Google parecía el
vídeo que le faltaba al módulo 2: canal oficial, cuatro minutos, vocabulario correcto. Leída la
transcripción, es "ve a Objetivos, Medición y pulsa el botón más". Ni una palabra de la
metodología de la encuesta. Desde la ficha era indistinguible de una clase; desde el texto, no.
Se pueden contar términos de método por cada mil palabras y el contraste es brutal: 75 en
`Treatment Prior Types`, 0 en el recorrido por el informe de Brand Report.

**Lo que confirma las averías.** Dos vídeos oficiales describen exactamente dos defectos que
escribimos mirando los datos:

- `Knots in Meridian` dice qué pasa cuando hay un solo nudo, que es la avería 1 de la lección 04.
- `Controls, Mediators and Treatments` llama **mediador** a una variable entre el anuncio y la
  venta, pone como ejemplo las visitas a la web y explica que fijarla impide que el anuncio se
  lleve mérito. Es palabra por palabra nuestra avería 2 de la lección 03, que mete `sessions`
  como control. Nuestra medición decía "los cuatro canales se van a cero a la vez"; ahora
  tenemos además el nombre y la razón.

Que el equipo de la librería dedique un vídeo a cada uno confirma que los defectos elegidos son
los que importan.

**Un hueco propio, encontrado viendo un vídeo.** Meridian tiene **tres** tipos de prior de
tratamiento y el experimento 02 prueba dos. Falta **mROI**, el retorno de la siguiente unidad de
gasto, que es el que su documentación asocia a decidir presupuesto. Anotado en `libs/meridian.md`.

**Dónde discrepamos de la fuente oficial, y se dice.** `Intro to Priors` vende el prior como
virtud: estabiliza, aporta contexto, da confianza. Cierto y a medias. La lección 04 enseña el
otro lado, que cuando los datos no identifican un canal el prior no ayuda a la estimación, **es**
la estimación. El catálogo lo advierte en vez de dejar que el vídeo hable solo.

**Lo mejor no es oficial.** Para incrementalidad, lo de Google son tutoriales de interfaz salvo
`Conversion Lift`, cuyos dos primeros tercios sí valen. Lo bueno son charlas de conferencia: la
de ASOS sobre diseño geo es la más densa de todo el catálogo y enseña la hipótesis **SUTVA**
(la interferencia entre personas que se conocen), un concepto que este repo no nombraba en
ningún sitio. Y una charla de PyData de un principal data scientist de PyMC Labs **se fabrica un
dataset simulado con contribuciones conocidas** para demostrar su argumento: es exactamente el
método de este repo, hecho por alguien de fuera.

**Rechazados con motivo**, todos en el fichero: tres playlists antiguas del canal de Google
Analytics que documentan productos muertos (Attribution 360, Google Surveys, Measure Matters de
2018), dos tutoriales de interfaz y un anuncio de Performance Max disfrazado de tutorial de
experimentos.

**Corregido lo que dije por la mañana:** escribí que no había nada de calidad sobre
PyMC-Marketing. Lo hay, en formato charla, no en serie.

## 2026-09-18 — Catálogo de vídeo: la serie oficial de Meridian encaja lección por lección

`libs/videos.md`, con 18 vídeos verificados uno a uno (título, canal, duración y fecha
comprobados contra YouTube, no copiados de una búsqueda: dos de las búsquedas devolvían como
"oficiales" vídeos de canales personales).

**El hallazgo:** Google Analytics mantiene una playlist de 13 cortos sobre Meridian, uno por
concepto, de 2 a 8 minutos, publicados el 2026-03-31. No es material de marketing: es el equipo
de la librería explicando priors, nudos, adstock y controles por separado. Y encaja con lo que
ya teníamos escrito con una precisión incómoda:

| Vídeo oficial | Cae justo en |
|---|---|
| Intro to Priors (2:17) | §1 de la lección 04, que trata exactamente de eso |
| Treatment Prior Types (4:30) | las tres variantes del experimento 02 |
| Knots in Meridian (5:25) | la **avería 1** de la lección 04 (`knots=1`) |
| Controls, Mediators and Treatments (7:09) | las **averías 1 y 2** de la lección 03 |
| Geo Vs National Level Modeling (4:47) | la pregunta P3 de Comprobar de la 04 |

Que dos vídeos oficiales coincidan con averías que escribimos mirando los datos dice que los
defectos elegidos son los que el propio Google considera dignos de un vídeo. Eso vale como
validación externa del drill.

**La decisión editorial que importa:** un vídeo que explica una avería va **después** del
drill, nunca antes. Si el alumno ve "Knots in Meridian" antes de diagnosticar, el ejercicio
deja de medir nada. Está escrito en `libs/videos.md`, en el contrato y en las dos lecciones.

**Se cierra un hueco de FEAT-005.** `perfil.py` respondía "No hay vídeos versionados" a quien
declaraba preferir vídeo. Era cierto y ahora no lo es: ese texto apuntaba a una carencia que
ya tiene lista. Actualizado el `_presentation` y su test.

Lo que **no** hay, y se dice en el fichero: nada oficial en serie sobre PyMC-Marketing, nada
decente sobre encuestas de impacto ni sobre conjoint. Lo que sale buscando son piezas
comerciales de proveedores de paneles.

## 2026-09-18 — Lección 04 (Meridian): el prior a la vista, y cuatro averías que lo demuestran

`lecciones/04-mmm-meridian/` sobre el experimento 02, con el patrón de la 03: `LECCION.md`,
siete ejercicios calculados desde los `summary.json` guardados (y uno desde el ajuste del propio
alumno), cuatro averías medidas, notebook Colab regenerado. El `run.py` del experimento 02 gana
la variante `roi-custom` (`--roi-median`, `--roi-sigma`) para el "cuarto prior" que pedía el
módulo 4 de `FORMACION.md`; el prior se escribe en el paso 1, antes de ver ninguna tabla, y se
corre en el paso 5.

Lo que enseñan las averías, medidas el 2026-09-18 con google-meridian 2.0.0 (2 cadenas,
300/300/500), que no estaba escrito en ningún sitio:

- **El prior de ROI tapa el error de unidades.** El gasto de display dividido por mil salía en
  PyMC-Marketing (lección 03) como un ROI de 5000, imposible de no ver. En Meridian el prior no
  deja que el ROI se vaya a miles, así que el modelo paga la escala en la contribución: display
  queda con ROI 1,3 (pegado al prior) y **0,00 % del KPI**. El error de datos se convierte en
  "display no funciona", que es la conclusión más cara posible.
- **Un solo nudo en el baseline rompe el reparto y mejora la cuota de baseline** (0,81 → 0,76,
  verdad 0,75). Video pierde la verdad por primera vez y social se dobla. Mismo patrón que quitar
  el control de tendencia en PyMC: la métrica global mejora mientras la de decisión empeora.
- **Un prior estrecho no informa, sustituye.** LogNormal(log 0,8, 0,15) deja los cuatro canales
  en 0,8–0,9, video incluido, con cero divergencias.
- **Sin adstock (`max_lag=0`) se descartó como avería**: hunde video igual que el cruce de
  tablas roto, y en la tabla no se distinguen. El contrato pide que la señal se vea; con dos
  defectos con la misma firma, el drill sería una moneda al aire.

Los avisos S102 de `ruff` en `tests/test_build_notebooks.py` (el `exec` del test del token) son
previos a esta rama; no se tocan.

## 2026-09-18 — FEAT-003 mergeada, E2E condicionado a abrir el repo

La PR #17 llegó al gate con el notebook piloto roto: 7 de sus 10 celdas de código no eran Python
válido, porque el generador convertía todo fence en celda sin distinguir un comando de shell de
una fórmula. Arreglado y mergeado (`a8d4909`); ahora compilan las 13. El detalle que más enseña:
`ruff check lecciones/` *parecía* pasar porque ruff se saltaba las celdas que no podía parsear.
El bug tapaba su propio detector.

Y al preparar el E2E salió el segundo hueco: el notebook clona el repo sin credenciales, y el repo
es privado. En Colab falla en la primera celda. La decisión fue no autenticar el clonado —sería
meter la fricción que la FEAT quiere quitar— sino esperar a que el repo se abra. **Cerrado el
2026-09-20 al publicar el repo:** la celda clona sin credenciales y FEAT-003 deja de estar
bloqueada. Dos veces seguidas el E2E habría cazado en treinta segundos
lo que ningún test unitario vio; la lección es hacerlo *antes* de dar la implementación por buena,
no después.

## 2026-09-11 — Panel geo con experimento: el primer generador de la nueva primera línea

`generators/synthetic_geo_mmm.py` (FEAT-004). Emite un panel de N regiones en el esquema
canónico de FEAT-001 —pasa el validador en modo completo, con `kpi` y `control_*`— más un
`truth.json` con la población por región, el ROI verdadero por canal y, cuando hay experimento,
el **lift incremental verdadero**.

**La decisión que da valor al fichero: el lift se deriva, no se declara.** Cada ejecución simula
dos ramas sobre las mismas tiradas aleatorias —la contrafactual, donde nadie tocó el plan de
medios, y la observada, donde las regiones tratadas recibieron el experimento— y resta una de
otra sobre las tratadas y la ventana. Las dos comparten el mismo ruido, así que lo único que
puede mover el KPI entre ellas es el gasto. Eso es lo que convierte la resta en un lift limpio, y
es el número contra el que se puntúa a GeoX, GeoLift, CausalImpact y CausalPy.

**Se fusionan dos pendientes en uno.** "Extender el generador a geo" y "extender el generador a
intervenciones puntuales" eran el mismo objeto: series tratadas, series de control y una ventana.
CausalImpact y CausalPy consumen este panel mirando una región tratada contra el resto.

Los tres diseños que nombra Meridian GeoX, verificados con `--weeks 104 --geos 20 --seed 42
--treated 5 --test-start 80 --test-weeks 12`:

| diseño | qué hace | lift verdadero |
|---|---|---|
| `go-dark` | apaga todos los canales en las tratadas | −408 865 (−23,4 %) |
| `holdback --holdback-channel video` | apaga solo un canal | −84 474 (−4,8 %) |
| `heavy-up --effect-size 1.0` | dobla el gasto | +132 915 (+7,6 %) |
| `go-dark --effect-size 0` | placebo A/A, no toca nada | 0 exacto |

Dos cosas que saltan de esa tabla y que valen como lección:

1. **Doblar el gasto solo suma un 7,6 %.** Eso es la saturación Hill hecha número: la segunda
   mitad del presupuesto compra mucho menos que la primera. Cuesta más explicarlo con palabras
   que enseñarlo con estas dos filas.
2. **Un go-dark completo da −23 %, que cualquier método detecta.** El experimento honesto es el
   de `--effect-size 0.3` (−4,2 %), o un holdback de un canal. Un panel donde el efecto se ve a
   simple vista no prueba nada sobre el método; conviene que la lección empiece por el fácil y
   acabe por el que está en el límite del ruido.

**El ROI medio no es una propiedad fija de un canal, y el generador lo dejó claro a base de
sorprender.** Al revisar la PR salió que `true_roi` cambiaba según el diseño: con un go-dark de
19 de 20 regiones, social pasaba de 5,35 a 6,41. No es un fallo de cálculo. El ROI medio es
contribución partido por gasto, así que un canal que gasta menos baja por su curva de saturación
y devuelve más por euro. La cifra observada describe bien el panel escrito —y es la que un modelo
ajustado sobre ese CSV debe recuperar—, pero se lee como si fuera el parámetro del canal, y no lo
es. Ahora el `truth.json` lleva las dos: `true_roi` (el panel tal como está) y
`true_roi_without_experiment` (el mismo panel sin test, invariante al diseño), con un campo
`roi_basis` que explica la diferencia. Los parámetros fijos de verdad siguen en `channels`.

Vale como lección por sí solo: si alguien reporta "el ROI de este canal es 5,3", la pregunta
correcta es *a qué nivel de gasto*.

El placebo (`--effect-size 0`) importa más de lo que parece: deja el plan de medios intacto y el
lift en cero exacto, así que sirve para medir cuántas veces un método encuentra un efecto que no
existe. Es la mitad de la lección que casi nadie enseña.

**El adstock sigue pagando después de cerrar la ventana**, y eso es otra trampa que el
generador deja a la vista: el eco posterior vale un 7,3 % del efecto medido en un go-dark y
hasta un 28 % en un holdback de `video`, que es el canal de decay largo. GeoLift y GeoX puntúan
lo que pasa dentro de la ventana, así que esa es la cifra principal; pero alguien que mida
"incrementalidad total" se desviará ese tanto y culpará al método. El `truth.json` lleva las dos,
con `carryover_share_of_effect` entre medias.

**Limitación heredada a propósito:** el KPI sale del mismo mecanismo adstock + Hill que el MMM
asume, así que un modelo probado aquí se examina en un mundo construido con sus propias reglas
—"honesto pero fácil", en palabras de `libs/amss.md`—. Resolverlo es el trabajo de AMSS; mezclarlo
con esta FEAT habría dejado el panel sin hacer mientras tanto. Está escrito en el docstring del
generador, que es donde alguien lo va a leer.

Lo que desbloquea: Meridian GeoX y GeoLift (el duelo que pedía `geolift.md`), CausalImpact y
CausalPy, y los módulos 5 y 7 de `FORMACION.md`. Siguiente paso natural:
`experiments/06-geo-vs-verdad/`, con GeoX y GeoLift sobre el mismo panel.

## 2026-09-11 — Tres pilares, y los generadores como cuello de botella

Decisión de Jesús, cerrando la tensión de identidad que quedó abierta al revisar el estado del
proyecto: **mmt es banco de pruebas, curso agent-native y lugar de referencia, las tres cosas a
la vez**. No es un curso con utilidades ni una herramienta con curso. La entrada del 2026-09-05
decía "recurso educativo público" y se queda corta: la referencia es un pilar por derecho
propio, porque alguien puede venir a consultar qué asume Meridian o dónde miente la MTA sin
cursar nada.

Segunda parte de la decisión: **mientras Jesús construya el repo no van a llegar datos reales
suyos**, así que la obligación es que lo sintético baste para aprender y practicar. Eso sube el
listón de `generators/`: un generador ya no entra por terminar sin error, entra cuando el
fenómeno que enseña se ve en los datos y se puede romper a propósito para que haya algo que
diagnosticar.

**Lo que esto cambia en el orden de trabajo.** Los tres pilares comparten cuello de botella y
es el mismo: los generadores. Hoy faltan tres y cada uno bloquea a los tres pilares a la vez.

| Generador que falta | Bloquea como banco de pruebas | Bloquea como curso | Bloquea como referencia |
|---|---|---|---|
| Panel geo | Meridian GeoX, GeoLift | módulo 5 | 4 filas del catálogo sin probar |
| Intervención puntual | CausalImpact, CausalPy | módulos 5 y 7 | 2 filas sin probar |
| `synthetic_ga4.py` | atribución, agregación | módulo 10 | la familia MTA entera |

Ninguna de las tres familias del catálogo que dependen de ellos se ha podido tocar todavía. Es
decir: el catálogo dice 21 herramientas, pero el banco de pruebas solo alcanza a las que corren
sobre una serie temporal nacional. Mientras eso siga así, "lugar de referencia" es una promesa,
no un hecho.

Consecuencia práctica para la priorización: los generadores dejan de estar en la lista de
"pendiente / abierto" y pasan a ser trabajo de primera línea, por delante de más skills de
ingesta. Las skills de `skills/` quedan justificadas como **referencia ejecutable** —enseñan
qué forma tiene de verdad un export de plataforma y qué hace un validador serio— no como
tubería de datos para la cartera.

## 2026-09-11 — Importadores de exports de plataforma

FEAT-002 añade cinco skills: `import-google-mmm`, `import-meta-mmm`, `import-tiktok-mmm`,
`import-amazon-mmm` y la paraguas `mmm-import`. Leen el CSV tal como lo entrega la plataforma
y escriben la mitad de medios del esquema canónico de FEAT-001 (`date, geo, channel, spend,
impressions, clicks`), validada con `mmm-data-validate --media-only`. Solo CSV: un `.xlsx` sale
con código 2 y el consejo de reexportar.

Lo que se aprendió al investigar los formatos, que es el hallazgo de verdad: **solo Google
documenta sus columnas**. Meta publica las 14 de la API de Insights pero nada sobre lo que
escribe la UI de Ads Reporting; TikTok y Amazon no publican ninguna. Así que el diseño es un
contrato de cabecera por plataforma en JSON con un flag `confirmed`, y los tres importadores
sin contrato fallan a propósito con "sin cabecera confirmada" en vez de fingir que funcionan.
Cerrar cada uno cuesta una fila de cabecera de un export real, nada más; los pasos están en su
`SKILL.md`.

Ninguno convierte moneda ni granularidad en silencio: monedas mezcladas, anclas semanales
mezcladas (lunes y domingo a la vez) o granularidades mezcladas dentro de un fichero paran con
código 2 y explican cómo volver a pedir el export. La paraguas sí re-muestrea diario a semanal
cuando el ancla ya está presente en la carpeta, descarta las semanas parciales de los extremos
sin imputarlas y lo anota en el informe. Tampoco deduplica: dos ficheros que describan el mismo
`(date, geo, channel)` los rechaza el validador, porque sumarlos o descartar uno sería una
decisión de modelado que no le toca a la herramienta.

Los fixtures son sintéticos de punta a punta, derivados de `generators/synthetic_mmm.py` (sin
tocarlo) más un supuesto explícito de CPM/CTR que vive en `skills/_lib/fixtures_common.py`.
Nada de exports reales recortados, aquí ni nunca.

## 2026-09-07 — Base MMM-ready para trabajar con datos locales

FEAT-001 incorpora tres skills locales: el esquema canónico largo con sus conversores, el
validador y el diagnóstico. Los datos de un profesional se quedan fuera del repositorio; las
skills rechazan rutas versionables salvo `--allow-tracked` explícito. El generador MMM puede
emitir ahora el mismo formato canónico con `--canonical`, manteniendo sin cambios su CSV ancho y
su ground truth anteriores. PyMC-Marketing multi-geo sigue fuera de alcance; el conversor lo
remite explícitamente a Meridian o a una entrega futura.

## 2026-09-06 — Máquina de práctica: el curso deja de evaluarse a ojo

Decisión previa de Jesús: ante la pregunta de si faltaban librerías, la respuesta fue que el
hueco no era de catálogo (21 herramientas, 1 lección) sino de práctica verificable. Se congela
la ampliación del catálogo y se construyen tres piezas, ya en `main`:

- **`lecciones/practica.py`** — arnés de ejercicios. Solo biblioteca estándar, corre en
  cualquier venv. Regla de diseño que importa: **el valor esperado se calcula desde los
  ficheros** (`truth.json`, `summary.json` del experimento), nunca se escribe en el ejercicio.
  Si una versión nueva mueve los números, el ejercicio se mueve con ellos. Un fallo devuelve
  pista, nunca la respuesta.
- **`lecciones/03-*/ejercicios.py`** — seis ejercicios para la lección 03. Cinco se verifican
  contra datos; el sexto es conceptual. El e5 lee la salida que produce el propio alumno en el
  paso 4 y falla con aviso si no existe.
- **`lecciones/03-*/averia.py`** — cuatro modelos rotos a propósito. Verificadas las cuatro
  señales el 2026-09-06 (PyMC-Marketing 1.1.0, 500 draws, 2 cadenas), contra el ajuste sano
  `logistic-default`:

  | avería | qué se rompe | cómo se ve |
  |---|---|---|
  | 1 | control de tendencia ausente | search 4,6 → 9,6; baseline 0,78 → 0,70 |
  | 2 | fuga del KPI en un control | los 4 canales a ~0; baseline 0,995 |
  | 3 | gasto de display ÷1000 | ROI de display 5190 |
  | 4 | serie de video barajada | video 4,4 → 0,13, intervalo pegado a cero |

  **Las cuatro dan cero divergencias.** Ninguna hace protestar al muestreo, que es justo lo
  que las hace buen ejercicio.

Hallazgo bonito de la avería 1: al quitar el control de tendencia, la cuota de baseline se
*acerca* a la verdad (0,70 frente a 0,78 del ajuste sano, verdad 0,75) mientras el reparto por
canal empeora. Un resumen global puede mejorar mientras se estropea el número con el que
decides. Está escrito en la revelación del drill.

También: registro automático en `.progreso/predicciones.md`, una fila por respuesta, y
`practica.py --calibracion` da el acierto **a la primera**, que es la métrica que mide el curso.
El contrato de lección recoge las tres piezas y prohíbe explícitamente al agente revelar una
respuesta esperada.

Pendiente de esta línea: el **modo caso**, donde el agente hace de director de marketing y
discute el resultado. Es lo único que un libro no puede hacer y quedó fuera de este bloque.

## 2026-09-05 — `setup.sh`: el entorno entero en un comando

`./setup.sh` (raíz) monta el `.venv` base con `uv sync` (ahora con `uv.lock` versionado), los
venvs `pymc`, `meridian` y `surveys` con exactamente lo que usan las lecciones, y con `--r` la
cadena de paquetes de R de la entrada de abajo (Boom 0.9.15 → BoomSpikeSlab 1.2.6 → bsts 0.9.10
fijados desde el archivo de CRAN, augsynth y GeoLift de GitHub, Robyn de GitHub). `--check` solo
verifica y devuelve 1 si falta algo; `--robyn` crea el venv opcional de robynpy (0.3.6, 780 MB,
carga). Idempotente: sobre el entorno ya montado corre en 14 s y no toca nada.

Hallazgo al probarlo: el `.venv` base no tenía matplotlib aunque está en `pyproject.toml`;
`uv sync` lo arregló. Sin `--check` nadie lo habría visto hasta la primera gráfica de una lección.

No instala R (eso es `apt`, sin sudo desde el script) ni configura Nevergrad para Robyn vía
`reticulate`: sigue pendiente. Tampoco causalpy, tfcausalimpact ni meridian-geox: entran cuando
una lección los use.

## 2026-09-05 — Pivote: el repo es un curso, el agente es el tutor

Jesús no invierte en marketing: mmt no se aplica a la cartera. Lo que quiere es aprender y que el
repo sirva para que cualquiera aprenda **y practique** medición de marketing dentro de un agente
de código (Claude Code, Codex, Antigravity). Decisiones:

- La unidad es la **lección**, no el experimento. Contrato en `lecciones/CONTRATO.md`: cuatro
  partes (Explicar, Practicar, Comprobar, Registrar) y un protocolo de tutor que cualquier
  agente sigue leyendo `AGENTS.md`. Los adaptadores por plataforma son finos
  (`.claude/commands/leccion.md`).
- Piloto: `lecciones/03-mmm-pymc-marketing/`, construida sobre el experimento 01. La prueba
  Jesús como alumno en Claude Code antes de escribir la segunda.
- Idioma español. Apertura del repo cuando haya tres lecciones completas, con licencia
  decidida antes (MIT código, CC-BY textos, pendiente de confirmar).
- El ejercicio "una línea por proyecto de la cartera" del módulo 0 se retira.
- ~~Pendiente: `setup.sh` reproducible~~ hecho el mismo día, ver la entrada de arriba. Sigue
  pendiente reordenar `FORMACION.md` con experimentos y encuestas antes que MMM.

## 2026-09-05 — Experimento 02: Meridian contra la verdad

`experiments/02-meridian-vs-verdad/`: Meridian 2.0.0, mismos datos que el 01, tres priors
(ROI por defecto, ROI centrado en el generador, contribución). Conclusión en su `RESULTADO.md`:
el prior de ROI decide los canales que los datos no identifican; search se va a 1,76 (verdad
5,36, fuera del intervalo) con el prior por defecto y vuelve a 3,4 con el prior centrado. Video
sale 5,3–5,9 haga lo que haga el prior (verdad 4,53). Muestreo 33–39 s en CPU. Con esto el
módulo 4 de `FORMACION.md` ya tiene experimento.

## 2026-09-05 — R cerrado: Robyn, GeoLift, CausalImpact cargan

R 4.3.3 en la máquina de pruebas con los tres paquetes que faltaban. `requireNamespace` TRUE para Robyn
3.12.1, GeoLift 2.7.5, augsynth 0.2.0, CausalImpact 1.4.1, MarketMatching y bsts 0.9.10.

Lo que costó (dos pasadas fallidas antes de la buena):

1. `augsynth` no está en CRAN, va por GitHub (`ebenmichael/augsynth`).
2. `Boom`, `BoomSpikeSlab`, `bsts` están **archivados** en CRAN. `remotes::install_version`
   sin número de versión coge la **más antigua** del archivo (Boom 0.9, 2013), que no compila
   con el Boost de 2026. Hay que fijar: Boom 0.9.15, BoomSpikeSlab 1.2.6, bsts 0.9.10.
3. Boom compila con un solo hilo por defecto; `MAKEFLAGS=-j12` lo deja en minutos (no medido).

Pasada que funcionó, entera:

```r
lib <- "~/R/library"; repos <- "https://cloud.r-project.org"
remotes::install_github("ebenmichael/augsynth", lib = lib, upgrade = "never")
remotes::install_version("Boom", version = "0.9.15", lib = lib, repos = repos, upgrade = "never")
remotes::install_version("BoomSpikeSlab", version = "1.2.6", lib = lib, repos = repos, upgrade = "never")
remotes::install_version("bsts", version = "0.9.10", lib = lib, repos = repos, upgrade = "never")
install.packages(c("CausalImpact", "MarketMatching"), lib = lib, repos = repos)
remotes::install_github("facebookincubator/GeoLift", lib = lib, upgrade = "never")
```

(con `MAKEFLAGS=-j12 Rscript ...`). Pendiente en Robyn: Nevergrad vía `reticulate`, no
configurado. Meridian: instalado en `.venvs/meridian`, versión **2.0.0** (la nota decía 1.8.0
el día 4; ahora muestrea con JAX). Experimento 02 hecho, ver entrada anterior.

## 2026-09-04 — Ámbito ampliado: guías de uso + encuestas

Jesús: el proyecto tiene que enseñar **cómo usar** cada librería (y las relevantes que
falten) y cubrir **encuestas de impacto** y otras metodologías. Decisión: entran con la misma
regla, generador sintético con verdad conocida o no entran. Familias nuevas: encuestas
(brand lift, pre/post, autodeclarada), uplift modeling, conjoint/MaxDiff, medición unificada.
Primera en entrar: encuestas.

## 2026-09-04 — Experimento 05: brand lift contra la verdad

`experiments/05-encuesta-brand-lift/RESULTADO.md` y `conceptos/encuestas-de-impacto.md`.

- **Aleatorizado: el estimador ingenuo acierta** (7,22 vs 7,21 pp). **Observacional: lo infla
  un 60 %** (12,4 vs 7,8), y con 2000 respuestas sale significativo el 100 % de las veces
  cubriendo la verdad el 38 %.
- **`balance` (Meta) corrige la no respuesta, no la exposición.** Reponderar a población deja
  el sesgo observacional intacto; el ajuste por regresión lo quita (7,3) porque aquí todas las
  covariables están medidas.
- Generador nuevo: `generators/synthetic_brand_lift.py` (RCT u observacional, no respuesta
  dependiente de covariables y de la exposición, lift por segmento). Venv `.venvs/surveys`.

## 2026-09-04 — Experimento 01: PyMC-Marketing contra la verdad

`experiments/01-pymc-vs-verdad/RESULTADO.md`. Tres variantes de saturación sobre `base.csv`.

- **Solo se recupera bien el canal con gasto variable** (video, flighted: ROI 4,4 vs 4,5
  verdadero, intervalo estrecho). Search, social y display, always-on, salen con intervalos
  de 3× a 100× de ancho, verdad dentro, inútiles para decidir. Es un problema de
  identificación, no de ruido: **justifica el experimento 04 (calibración) antes que nada.**
- **Hill con priors por defecto es la peor variante** aunque sea la forma que generó los
  datos. Parte es un **bug numérico**: con semanas de gasto cero, nutpie devuelve error de
  logp en el 89 % de draws; con suelo de 1 € desaparece. Parte es prior: curvas degeneradas.
- **Logística por defecto**: 0 divergencias, baseline clavada (78 % vs 75 %), social a la
  mitad de su ROI real.
- **Sampler:** el de PyMC abortó dos veces (`0 < alpha <= 1`); nutpie lo resuelve. 30–40 s
  por ajuste completo en CPU. El coste de cómputo no es una restricción aquí.
- Infra: venv `.venvs/pymc` creado (PyMC-Marketing 1.1.0, nutpie, h5netcdf, h5py).

## 2026-09-04 — Alcance cerrado: todo sintético

- **Los datos de GA también serán sintéticos.** Se cae `data/real/` entero y con él la
  pregunta de qué propiedad de Analytics usar. Decisión buena por dos razones a la vez:
  metodológicamente no se puede evaluar un modelo sin ground truth, y de paso desaparece el
  problema de privacidad.
- El proyecto es tanto **base de conocimiento** como banco de pruebas. Nace `conceptos/`.

## 2026-09-04 — Catálogo ampliado

`libs/CATALOGO.md` es ahora el índice del terreno. 15 herramientas en cuatro familias:

- **MMM:** Meridian, PyMC-Marketing, Robyn (+ LightweightMMM, archivada).
- **Geo / incrementalidad:** Meridian GeoX, GeoLift, CausalImpact, GeoexperimentsResearch.
- **Causalidad general:** CausalPy, DoWhy, EconML, CausalML.
- **Datos sintéticos:** el nuestro, AMSS de Google.
- **MTA:** ChannelAttribution, pathmc — catalogadas con reserva, ver el porqué en el catálogo.

Notas propias escritas: Meridian, PyMC-Marketing, Robyn, Meridian GeoX, GeoLift,
CausalImpact, CausalPy, AMSS.

Tres hallazgos que cambian el plan:

1. **Los tres MMM son tres escuelas distintas, no tres implementaciones.** Robyn no es
   bayesiano: Ridge + optimización evolutiva (Nevergrad), y devuelve un frente de Pareto de
   modelos entre los que eliges tú. Eso hace la comparación mucho más interesante de lo que
   parecía.
2. **`robynpy` es una beta traducida por LLMs** desde el R 3.11.1, todavía en beta en 2026.
   La vía fiable de Robyn es R. Y GeoLift y AMSS también son R. **Hace falta R en la máquina de pruebas**
   para cubrir el catálogo entero — no es opcional.
3. **AMSS es el nivel siguiente de nuestro generador.** Simula un embudo de estados de
   consumidor, no `kpi = f(gasto)`. Nuestro generador prueba el modelo con datos generados
   por el mismo modelo que asume — honesto pero fácil. La prueba dura es generar desde un
   mecanismo distinto. Ver `libs/amss.md`.

## 2026-09-04 — Proyecto creado

- Repo creado (privado en su momento), estructura base.
- Generador de datos sintéticos MMM funcionando: `generators/synthetic_mmm.py`.
  Adstock geométrico + saturación Hill + baseline con tendencia y estacionalidad anual +
  control de precio + ruido. Escribe CSV y `*.truth.json` con los parámetros reales.
  Primer dataset: `data/synthetic/base.csv` (156 semanas, 4 canales, seed 42).
  ROI verdadero: search 5,35 · social 5,50 · video 4,53 · display 2,91 (unidades KPI por €).
  Baseline = 75,1 % del KPI, que es el orden de magnitud realista.

## Siguiente paso propuesto

Sigue siendo el duelo sobre datos con verdad conocida, ahora a tres bandas. Nadie publica
esto porque casi nadie compara contra ground truth:

1. ~~`experiments/01-pymc-vs-verdad/`~~ — hecho 2026-09-04, ver arriba.
2. `experiments/02-meridian-vs-verdad/` — mismos datos, misma tabla.
3. `experiments/03-robyn-vs-verdad/` — mismos datos, en R. Requiere instalar R.
4. `experiments/04-calibracion-experimento/` — inyectar el ROI verdadero de un canal como
   prior y medir cuánto mejora el resto. **Aquí está el valor real del MMM moderno**, y es lo
   que más quiero entender.

Antes del 1, dos tareas de infraestructura pequeñas: instalar R, y `generators/synthetic_ga4.py`.

## Pendiente / abierto

- **`generators/synthetic_ga4.py`** — eventos/sesiones estilo GA4 coherentes con el gasto del
  generador MMM: mismas campañas, mismos UTM, mismo calendario. Que la conversión agregada por
  semana cuadre con el `kpi` del CSV de MMM. Así se puede pasar del dato de sesión al dato de
  MMM y ver *dónde se pierde la información* al agregar — que es media disciplina.
- ~~**R en la máquina de pruebas**~~ — **cerrado 2026-09-05**: R 4.3.3 (apt, Jesús) + Robyn, GeoLift,
  CausalImpact en `~/R/library`. Receta y trampas de CRAN en la entrada del 2026-09-05.
- **Cabeceras reales de Meta, TikTok y Amazon** — los tres importadores de FEAT-002 están
  bloqueados a propósito hasta que alguien pegue la fila de cabecera de un export real en su
  `expected_headers.json` y ponga `confirmed: true`. Solo la cabecera: ni cifras, ni IDs de
  cuenta, ni nombres de campaña. Pasos en cada `SKILL.md`.
- **Validador de FEAT-001: distinguir `spend` vacio de `spend` negativo** — hoy ambos dan la
  misma linea (`must be a non-negative number`), lo que cuesta un rato de depuracion cuando el
  export trae celdas en blanco. Detectado revisando FEAT-002 (edge case 11 de su §4), que no
  puede arreglarlo porque tocar ese validador esta fuera de su alcance.
- ~~**Extender el generador a geo**~~ y ~~**a intervenciones puntuales**~~ — **cerrados el
  2026-09-11** con `generators/synthetic_geo_mmm.py`, que los cubre a los dos: eran el mismo
  objeto. Queda `synthetic_ga4.py` como el generador que falta, y sigue siendo de primera línea.
- **`experiments/06-geo-vs-verdad/`** — el duelo GeoX contra GeoLift sobre el panel nuevo, mismo
  efecto verdadero. Ya solo depende de correrlo.
- **Issue en pymc-marketing**: reproducir en aislamiento el error de logp de `HillSaturation`
  con gasto cero bajo nutpie (exp. 01) y abrirlo.
- **Sensibilidad a seed**: repetir `logistic-default` con 5 datasets para separar sesgo de
  forma funcional de azar de la muestra.
- **Encuestas, siguientes**: lift heterogéneo fuerte (para que la no respuesta muerda),
  covariable no medida en el observacional, pre/post y autodeclarada en el generador.
- **Familias pendientes de abrir**: uplift modeling (`causalml`), conjoint/MaxDiff (`xlogit`),
  medición unificada (método, sin librería; ahí encaja la IA aplicada).
- **Guías "Cómo usarla"** pendientes en: Meridian, Robyn, CausalImpact, CausalPy, GeoLift, y
  notas nuevas para DoWhy, EconML, CausalML, ChannelAttribution.
- **IA aplicada**: pendiente definir en concreto. Candidato inicial: un paso que lea el
  posterior de un MMM y escriba el diagnóstico en lenguaje llano (qué canal saturó, qué
  intervalo es demasiado ancho para decidir nada, qué experimento haría falta a continuación).
