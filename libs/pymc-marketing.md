# PyMC-Marketing (PyMC Labs) — MMM + CLV bayesiano

**Repo:** https://github.com/pymc-labs/pymc-marketing · **Docs:** https://www.pymc-marketing.io
**Estado en mmt:** probada (2026-09-04, v1.1.0). Experimento `experiments/01-pymc-vs-verdad/`.
**Última verificación de datos:** 2026-09-04.

## Qué es

Caja de herramientas bayesiana de marketing sobre PyMC. Dos familias:

- **MMM** — media mix modeling con adstock y saturación configurables, presupuesto óptimo,
  time-varying parameters.
- **CLV / BTYD** — valor de vida de cliente y modelos buy-till-you-die (BG/NBD, Gamma-Gamma).
  Esto Meridian no lo tiene, y para negocios de suscripción/recurrencia importa más que el MMM.

## Qué lo diferencia de Meridian

- Es **más abierto como modelo**: se puede tocar el grafo de PyMC directamente, poner los
  priors que quieras, meter componentes propios. Meridian es más una caja negra bien hecha.
- Cubre **CLV**, que Meridian no cubre.
- En v1.0.0 el MMM multidimensional es el estándar: geo, producto y canal como dimensiones de
  primera clase en un mismo `xarray.Dataset`. Sampling ~1.5× más rápido; según sus notas, la
  CPU llega a batir a JAX en el MMM de demo — relevante para nosotros, que no tenemos GPU.
- Construido sobre PyMC 6 / ArviZ 1.2 / PyTensor 3 / NumPy 2. API de plotting por namespaces
  con salida interactiva Plotly.

## Instalación (venv propio, ver AGENTS.md)

```
uv venv .venvs/pymc --python 3.12
uv pip install --python .venvs/pymc pymc-marketing
```

No mezclar con el venv de Meridian: PyTensor y TensorFlow Probability se pelean por versiones
de numpy y de compiladores.

## Qué salió al probarla (2026-09-04)

Detalle y tablas en `experiments/01-pymc-vs-verdad/RESULTADO.md`. Lo operativo:

- **Instala limpia** con `uv` en su venv (`.venvs/pymc`, Python 3.12). Trae PyMC 6.2,
  PyTensor 3.2, NumPy 2.4. Para `mmm.save()` hacen falta `h5netcdf` y `h5py` aparte.
- **Usar nutpie** (`pip install nutpie`, `fit(..., nuts_sampler="nutpie")`). El sampler por
  defecto de PyMC abortó dos veces con `0 < alpha <= 1` (NaN transitorio en el tuning), tanto
  con `parametrization="alpha"` como `"halflife"`. nutpie lo trata como divergencia y sigue.
- **`HillSaturation` falla con semanas de gasto cero** bajo nutpie: 89 % de draws con
  `Logp function returned error code: 3`. Con suelo de 1 € en el gasto, cero errores.
  `LogisticSaturation` no tiene el problema. Pendiente abrir issue.
- **Tiempo:** 30–40 s por ajuste (4 cadenas × 4000 iteraciones, 156 semanas, 4 canales) en
  CPU de 16 núcleos. Más ~20 s de compilación. Usable sin GPU, sobradamente.
- **No trae componente de tendencia** en el MMM básico: hay que añadirla como control o usar
  `time_varying_intercept`. Con el KPI subiendo un 30 % en tres años, olvidarla lo rompe todo.
- **Recuperación:** solo el canal con gasto muy variable (video, flighted) sale con intervalo
  estrecho y error < 10 %. Los always-on quedan con intervalos de ROI de 3× a 100× de ancho.
  Es identificación, no ruido: argumento directo para la calibración con experimentos.
- Las contribuciones a escala original salen de `compute_counterfactual_contributions_dataset()`,
  una variable por columna de canal (no hay `channel_contribution` en el posterior).

## Pendiente de probar

1. La misma comparación que Meridian, mismos datos → **este es el experimento que de verdad
   enseña algo**: dos frameworks, un dataset con verdad conocida, quién se acerca más y a qué
   coste de tiempo.
2. Time-varying media effects: ¿detecta que un canal pierde eficacia si lo generamos así?
3. CLV con datos sintéticos de un e-commerce.
