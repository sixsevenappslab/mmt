# Robyn (Meta) — MMM semi-automatizado

**Repo:** https://github.com/facebookexperimental/Robyn · **Python:** `robynpy` (PyPI)
**Estado en mmt:** instalada en R (2026-09-05), no probada todavía.
**Última verificación de datos:** 2026-09-04.

## Qué es

El MMM open source de Meta Marketing Science. Fue el que abrió esta categoría al público
general (2021) y sigue siendo la referencia con la que compara todo el mundo.

Enfoque **distinto al de Meridian y PyMC-Marketing**: no es bayesiano. Es regresión Ridge
sobre variables transformadas (adstock Geometric o Weibull, saturación Hill), con los
hiperparámetros buscados por **optimización evolutiva multiobjetivo** (Nevergrad), minimizando
a la vez error de predicción y "decomposition distance". Devuelve un abanico de modelos
Pareto-óptimos, no un modelo único, y tú eliges.

Eso tiene consecuencias prácticas que conviene tener claras antes de compararlos:

- **No da posteriors.** Da intervalos por bootstrap y un conjunto de soluciones plausibles.
  La incertidumbre es más difícil de leer que en un bayesiano.
- **Elegir modelo es un paso humano.** Robyn te enseña el frente de Pareto y el criterio de
  elección lo pones tú. Puede ser honesto o puede ser una puerta abierta al sesgo, según
  quién lo use.
- **Calibración con experimentos sí la tiene**, vía la variable de calibración con resultados
  de lift. Es la misma idea que Meridian, resuelta de otra manera.

## Versión y estado real

- Release taggeada: **v3.12.0** (2024-12-19). Sin aviso de deprecación a 2026.
- **`robynpy` es beta.** Es una traducción del R 3.11.1 a Python hecha con ayuda de LLMs,
  anunciada en diciembre de 2024. Sigue en beta en 2026.

**Consecuencia para nosotros:** para pruebas serias, la vía fiable es **R**. `robynpy` vale
para trastear y para leer el algoritmo en un lenguaje que dominamos, pero no para colgar una
decisión de presupuesto. Si alguna vez esto sale del banco de pruebas, se corre el R.

## Instalación

**R en la máquina de pruebas (2026-09-05):** R 4.3.3 (`r-base` de apt, instalado 2026-09-04). Paquetes de
usuario en `~/R/library` (`R_LIBS_USER` en `~/.Renviron`). Robyn **3.12.1** (main de GitHub, por encima de la última release taggeada) instalado con
`remotes::install_github("facebookexperimental/Robyn/R", lib="~/R/library")`;
`requireNamespace("Robyn")` devuelve TRUE. Tarda: compila una cola larga de dependencias
(nloptr, glmnet, prophet...). Nevergrad va por `reticulate` y no se ha configurado aún —
es el siguiente paso antes de correr nada.

Alternativa Python:

```
uv pip install --python .venvs/robyn robynpy
```

Venv propio: arrastra Nevergrad y su propio stack de numpy.

## Pendiente de probar

1. Correr `robynpy` sobre `data/synthetic/base.csv` y comparar el ROI recuperado con
   `base.truth.json`, igual que con Meridian y PyMC-Marketing.
2. Ver cuánto se separan entre sí los modelos del frente de Pareto: si dos soluciones
   "igual de buenas" dan ROIs muy distintos por canal, eso es un hallazgo, no un fallo.
3. Comparar R vs. `robynpy` con el mismo input y semilla — cuánto se desvía el port beta.
   Nadie publica esto y es exactamente lo que decidiría si la vía Python es usable.
