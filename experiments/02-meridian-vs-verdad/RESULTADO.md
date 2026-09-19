# 02 · Meridian contra la verdad conocida

**Conclusión:** en Meridian el prior de ROI es el mando que decide los canales que los datos no
identifican. Con el prior por defecto (`LogNormal(0.2, 0.9)`, mediana 1,2), search queda en un
tercio de su ROI verdadero y la verdad fuera del intervalo; centrando el prior donde vive el
generador, search vuelve a estar dentro sin que nada cambie para video, el único canal que los
datos identifican solos (mismo 5,3–5,9 en las tres variantes, siempre un 20–30 % alto). Muestrea
limpio y rápido (33–39 s en CPU, ≤ 49 divergencias de 4000, r̂ ≤ 1,03), y con prior de
contribución clava la cuota de baseline. Misma lección que el 01 vista desde el otro lado: donde
los datos callan, habla el prior, y Meridian lo pone a la vista porque el prior es directamente
el ROI.

Fecha: 2026-09-05 · google-meridian 2.0.0 (backend JAX) · CPU (16 núcleos, sin GPU).

## Qué se hizo

- Datos: los mismos del 01, `data/synthetic/base.csv` (156 semanas, 4 canales, seed 42) con
  `base.truth.json`. Modelo nacional (una geo).
- Sin impresiones en el generador: el gasto hace de variable de ejecución de medios
  (`media_cols = media_spend_cols`), como recomienda la doc cuando no hay otra cosa. KPI
  declarado como `revenue` para que el ROI salga en unidades de KPI por euro, igual que en el 01.
- Adstock geométrico (`max_lag=12`), saturación Hill (la de Meridian, priors por defecto
  `ec_m`, `slope_m`), control `price_index`. Meridian no tiene término de tendencia ni de
  estacionalidad: el baseline es un spline con `knots=13` (uno cada 12 semanas).
- Tres variantes, mismo sampler (4 cadenas × 500 adapt + 500 burn-in + 1000 keep):
  - `roi-default`: prior de ROI por defecto de la librería, `LogNormal(0.2, 0.9)`.
  - `roi-wide`: `LogNormal(log 4, 0.7)`, centrado donde el generador pone los ROI (3–5,5).
    Es hacer trampa a medias: no usa la verdad exacta, pero sabe por dónde anda.
  - `contribution`: prior sobre la cuota de KPI de cada canal, `TruncatedNormal(0.06, 0.05)`
    en [0, 1], en vez de sobre el ROI.
- Script: `run.py`. Resultados por variante en `results/<variante>/` (`summary.json`,
  `roi_vs_truth.csv`, `diagnostics.csv`, `adstock_decay.csv`).

## ROI recuperado (unidades de KPI por €)

Mediana e intervalo central del 94 % (mismos cuantiles que el 01). Verdad: search 5,36 ·
social 5,50 · video 4,53 · display 2,91. Última columna: la mejor variante del 01 como referencia.

| Canal | roi-default | roi-wide | contribution | 01 logistic-default |
|---|---|---|---|---|
| search (5,36) | 1,76 [0,3 – 5,3] **verdad fuera** | 3,38 [1,2 – 6,9] | 3,34 [0,6 – 6,6] | 4,56 [1,6 – 12,4] |
| social (5,50) | 3,87 [1,5 – 7,4] | 4,36 [2,2 – 7,9] | 4,89 [2,2 – 8,9] | 2,91 [1,4 – 5,4] **fuera** |
| video (4,53) | 5,35 [3,2 – 8,4] | 5,70 [3,5 – 8,6] | 5,93 [3,8 – 8,8] | 4,43 [3,3 – 5,8] |
| display (2,91) | 3,72 [0,5 – 9,7] | 5,44 [2,0 – 11,8] | 8,19 [2,8 – 18,4] | 5,10 [1,9 – 11,8] |
| cuota baseline (75,1 %) | 81,7 % [73 – 88] | 76,3 % [69 – 83] | 74,2 % [65 – 82] | 78,1 % [63 – 85] |
| suma de medianas de medios (24,9 %) | 17,5 % | 22,7 % | 25,1 % | 21,3 % |

Diagnósticos:

| | roi-default | roi-wide | contribution |
|---|---|---|---|
| divergencias / 4000 | 49 | 20 | 0 |
| r̂ máx | 1,030 | 1,012 | 1,019 |
| muestreo | 34 s | 33 s | 39 s |

Adstock (decay alpha): video 0,70 → 0,70–0,73 [0,55 – 0,83] en las tres variantes. Search,
social y display: intervalos de [0,02 – 0,9], no aprende nada. Idéntico al 01.

## Lo que se aprende

1. **El prior de ROI de Meridian no es un detalle, es el resultado en los canales flojos.**
   Search es always-on con CV 0,25 y los datos no lo separan del baseline (lo vimos en el 01).
   Meridian rellena ese hueco con el prior: `LogNormal(0.2, 0.9)` tiene mediana 1,2 y mete
   search en 1,76 con un intervalo que **no contiene la verdad**. El mismo modelo con el prior
   en `log 4` lo devuelve a 3,4 y la verdad dentro. No ha cambiado la información; ha cambiado
   la opinión previa. Es la razón por la que Meridian insiste tanto en calibrar con
   experimentos: sin un ROI externo que meter en el prior, la elección del prior es la
   estimación.
2. **Un intervalo estrecho no es un intervalo mejor.** Para search, Meridian por defecto da
   [0,3 – 5,3] y PyMC-Marketing [1,6 – 12,4]. El de Meridian es más estrecho y está mal
   centrado; el de PyMC es inútil pero honesto. Los dos dicen lo mismo con distinta cara: los
   datos no saben cuánto vale search.
3. **Video sale igual haga lo que haga el prior.** 5,35 / 5,70 / 5,93, siempre dentro, siempre
   un 20–30 % alto. Los datos mandan donde hay variación de gasto (apagado el 55 % de las
   semanas, CV 0,70), y el prior no lo mueve. El sesgo al alza es consistente en las tres
   variantes y PyMC (Hill, misma forma) no lo tiene: hipótesis, la saturación Hill de Meridian
   con priors por defecto sobre `ec_m`/`slope_m` y gasto como impresiones. Sin comprobar.
4. **El prior de contribución es la variante más honesta de las tres.** Cero divergencias,
   cuota de baseline 74,2 % (verdad 75,1 %), suma de medios 25,1 % (verdad 24,9 %). Lo que
   pide saber ("cada canal es unos pocos puntos del KPI") es más fácil de defender que un
   ROI concreto. A cambio, display se va a 8,2 (verdad 2,9): la cuota total la clava y el
   reparto entre canales flojos no.
5. **CPU no es problema a este tamaño.** 33–39 s por ajuste con 4 cadenas. La advertencia
   de "GPU recomendada" de la nota aplica a modelos geo con decenas de regiones, no a esto.
6. **Meridian 2.0.0 (2026) devuelve JAX.** Los priors personalizados hay que construirlos con
   `meridian.backend.tfd` y `backend.np_float_dtype`, o el modelo falla al construirse por
   tipos (float32 vs float64). Los ejemplos antiguos con `tfp.distributions` a pelo no valen.

## Preguntas que quedan

- ¿De dónde sale el +20–30 % sistemático en video? Probar `hill_before_adstock`, priors de
  `ec_m`/`slope_m` y pasar impresiones sintéticas en vez de gasto.
- Calibración de verdad (experimento 04): meter el ROI verdadero de video como prior estrecho
  y ver cuánto arrastra a search y social. Es el caso de uso para el que Meridian está hecho.
- Modelo geo: extender el generador a regiones y ver si el pooling parcial estrecha los
  intervalos de los canales always-on. Es la apuesta de diseño de Meridian.
