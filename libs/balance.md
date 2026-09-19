# balance (Meta) — reponderación de muestras sesgadas

**Repo:** https://github.com/facebookresearch/balance · **Docs:** https://import-balance.org
**Estado en mmt:** probada (2026-09-04, v0.23.0). Experimento `experiments/05-encuesta-brand-lift/`.

## Qué es

Librería Python para corregir una muestra que no representa a la población (encuestas con no
respuesta, paneles autoseleccionados). Calcula pesos por respondiente para que la muestra se
parezca a una referencia en las covariables elegidas. Métodos: IPW (regresión logística
muestra vs. referencia, el defecto), raking (ajuste iterativo a marginales), CBPS, post-
estratificación. Trae diagnósticos de calidad de los pesos (ASMD, tamaño efectivo, diseño).

## Cómo usarla

```python
from balance import Sample
sample = Sample.from_frame(respondents[["id", "age_group", "heavy_digital"]], id_column="id")
target = Sample.from_frame(reference[["id", "age_group", "heavy_digital"]], id_column="id")
adjusted = sample.set_target(target).adjust(method="ipw")   # o "rake"
weights = adjusted.df[["id", "weight"]]                      # ids como str
adjusted.diagnostics()                                       # ASMD antes/después, ESS
```

- La referencia es un DataFrame de la población con las mismas covariables. Con solo
  marginales (censo) hay que usar `rake` o construir un frame sintético.
- Convierte los ids a `str` y las numéricas a `float`: cuidado al cruzar los pesos de vuelta.
- Es ruidosa en logs (`logging.getLogger("balance").setLevel(logging.ERROR)`).
- Instala limpia con `uv` en Python 3.12 (venv `.venvs/surveys`, con statsmodels y pingouin).

## Qué salió al probarla

Los pesos devuelven la composición de la población (usuarios digitales del 29 % al 40 %) y el
lift reponderado coincide con el ingenuo en el RCT. En el diseño observacional **no corrige
nada**: el sesgo de confusión entre expuestos y control no es un problema de composición de la
muestra. Es la herramienta correcta para la no respuesta y la incorrecta para la exposición.
