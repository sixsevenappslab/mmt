# Meridian (Google) — MMM bayesiano

**Repo:** https://github.com/google/meridian · **PyPI:** `google-meridian`
**Estado en mmt:** probada (2.0.0, 2026-09-05) — `experiments/02-meridian-vs-verdad/RESULTADO.md`.
**Última verificación de datos:** 2026-09-05 (versión 2.0.0 en PyPI; el día 4 la nota decía 1.8.0).

## Qué es

Framework de marketing mix modeling de Google, open source desde 2026-01. Sustituye a
LightweightMMM (archivado). Bayesiano sobre TensorFlow Probability, con MCMC (NUTS).
Pensado para que un anunciante corra su propio MMM in-house en vez de contratar consultora.

## Qué lo diferencia

- **Calibración con experimentos**: acepta priors informados por resultados de lift tests /
  geo experiments. Es su argumento fuerte y el más interesante para nosotros: un MMM sin
  calibrar es un modelo de correlaciones con buena presentación.
- **Reach & frequency**: modela frecuencia óptima cuando hay datos de R&F, no solo gasto.
- **Efectos geo jerárquicos**: modelo multi-región con pooling parcial. Hay además un repo
  aparte, `google/meridian-geox`, para diseño y análisis de experimentos geo.
- **Scenario Planner** (añadido 2026-02): interfaz sin código para planificación de
  presupuesto, no requiere Python. A revisar si aporta algo sobre la API.

## Requisitos

- Python 3.11 o 3.12 (no 3.13).
- GPU recomendada. Sin GPU los MCMC de un modelo mediano tardan bastante — en la máquina de pruebas
  vamos a CPU, así que empezar con datasets pequeños (≤2 años, ≤5 canales) y pocas cadenas.

## Instalación (venv propio, ver AGENTS.md)

```
uv venv .venvs/meridian --python 3.12
uv pip install --python .venvs/meridian google-meridian
```

Hecho el 2026-09-05: instala `google-meridian` 2.0.0 con TensorFlow 2.21 y `tfp-nightly`
0.26. **En 2.0.0 el sampler y el `Analyzer` devuelven arrays JAX**, no tensores TF: la API
pública (`DataFrameInputDataBuilder`, `ModelSpec`, `Meridian.sample_posterior`, `Analyzer`)
sigue igual, pero los ejemplos antiguos que hacen `.numpy()` sobre la salida se rompen;
`np.asarray()` funciona. Sin GPU en la máquina de pruebas, va por CPU.

## Datos que pide

Panel temporal (semanal o diario) por geo: KPI, gasto por canal, impresiones/reach por
canal si hay, controles, y población por geo. Nuestro `generators/synthetic_mmm.py`
produce el caso national (una sola geo) — para probar la parte geo habrá que extender el
generador con dimensión región.

## Qué salió (2026-09-05)

Experimento 02, tres variantes de prior sobre `base.csv`. En corto: el prior de ROI decide los
canales que los datos no identifican (search cae a un tercio con el prior por defecto y la
verdad queda fuera del intervalo); video, el único canal con variación real de gasto, sale
igual con cualquier prior. 33–39 s por ajuste en CPU. Detalle y tabla en el `RESULTADO.md`.

Drills de la lección 04 (2026-09-18, `lecciones/04-mmm-meridian/averia.py`): el prior de ROI
**esconde** un error de unidades que en PyMC-Marketing saltaba a la vista. Un canal con el gasto
dividido por mil no sale con ROI absurdo, sale con ROI igual al prior y contribución cero. Y con
un solo nudo en el spline del baseline, la cuota de baseline se acerca a la verdad mientras el
reparto por canal se rompe. Ambas cosas son diagnosticables desde la tabla, pero no desde el
resumen.

## Vídeo oficial (verificado 2026-09-18)

Google Analytics mantiene la playlist
[Meridian](https://www.youtube.com/playlist?list=PLI5YfMzCfRtYvZ9AYp1wrtBM4apIsDc1i): 13 vídeos
cortos, uno por concepto, publicados el 2026-03-31 (el de Scenario Planner, en agosto). Duran
entre 2 y 8 minutos y los hace el equipo de la librería. Los mejores para este repo son
`Intro to Priors` (2:17), `Treatment Prior Types` (4:30) y `Knots in Meridian` (5:25), que caen
justo encima de la lección 04 y de una de sus averías. Tabla completa con a qué lección sirve
cada uno en `libs/videos.md`. Ninguno dice con qué versión se grabó: nuestras cifras son de
2.0.0.

Leyendo la transcripción de `Treatment Prior Types` sale un hueco propio: Meridian ofrece
**tres** tipos de prior de tratamiento y el experimento 02 solo prueba dos. Falta el de **mROI**
(retorno de la siguiente unidad de gasto), que es el que la documentación asocia a la
optimización de presupuesto. Anotado como pendiente abajo.

## Documentación oficial en local (2026-09-08)

`libs/docs/meridian/` es un espejo en Markdown de toda `developers.google.com/meridian/*` en
español (433 páginas: guía, modelado avanzado, inferencia causal, pre/post-modelado, planificador
de escenarios, GeoX, notebooks y la referencia completa de la API). Está gitignored, como
`libs/repos/`: contenido de terceros y regenerable con

```bash
uv run --with requests --with beautifulsoup4 --with markdownify \
    python libs/docs/fetch_meridian_docs.py            # --lang en para la versión inglesa
```

Cómo usarlo como tutor: empezar por `libs/docs/meridian/INDEX.md`, que separa lectura
superficial (`mmm.md`, `docs/basics/`, intros de pre y post-modelado) de profundidad
(`docs/advanced-modeling/`, `docs/causal-inference/`, `docs/user-guide/`, `reference/api/`).
Cada página conserva su URL de origen y la fecha de descarga en la cabecera.

## Pendiente de probar

1. ~~Instalar y correr con datos propios sintéticos.~~ Hecho (exp. 02).
2. ~~¿Recupera el ROI verdadero de `base.csv`?~~ Depende del canal y del prior; ver exp. 02.
3. Calibración con prior de experimento: inyectar el ROI verdadero de un canal como prior y
   ver cuánto mejora la recuperación de los demás.
3b. Variante `mroi` en el experimento 02: es el tercer tipo de prior de tratamiento y el que
   Meridian asocia a decidir presupuesto. Detectado el 2026-09-18 viendo el vídeo oficial.
4. Tiempo de sampling en CPU con 156 semanas × 4 canales — dato operativo que decide si esto
   es usable en la máquina de pruebas.
