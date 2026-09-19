# Meridian GeoX (Google) — diseño y análisis de experimentos geo

**Repo:** https://github.com/google/meridian-geox · **PyPI:** `meridian-geox`
**Docs:** https://developers.google.com/meridian/geox
**Estado en mmt:** no probado todavía.
**Última verificación de datos:** 2026-09-04.

## Qué es

La pata de incrementalidad de Meridian, en repo aparte. Mide el efecto incremental real de la
inversión publicitaria repartiendo regiones geográficas en grupos de test y control. Es
cookieless y agnóstico de plataforma: no depende de que Meta o Google te cuenten sus propias
conversiones.

Cubre **las dos mitades del problema**, que es lo que lo diferencia de CausalImpact:

1. **Diseño** — a qué regiones tocar, cuánto presupuesto hace falta y qué efecto mínimo
   detectable (MDE) vas a poder ver. Esto ocurre *antes* de gastar un euro. Ofrece muestreo
   estratificado y aleatorizado.
2. **Inferencia** — análisis del resultado por *time-based regression* (TBR), con inferencia
   placebo para controlar falsos positivos.

Soporta diseños holdback, go-dark y heavy-up, y ejecución multi-celda (varias ramas de
tratamiento contra un control común, que ahorra presupuesto y tiempo frente a correr los
tests uno detrás de otro).

## Por qué importa aquí, más allá de la herramienta

Es la fuente de *ground truth* que calibra el MMM. El bucle completo de la medición moderna es:

```
experimento geo → efecto incremental medido → prior informado → MMM calibrado → decisión de presupuesto
                                                                       ↓
                                              siguiente experimento sobre lo más incierto
```

Un MMM sin ese bucle es un modelo de correlaciones. Con él, empieza a merecer que le confíes
dinero. **Este bucle es lo que más quiero entender de todo el proyecto.**

## Linaje

Sustituye conceptualmente a [GeoexperimentsResearch](https://github.com/google/GeoexperimentsResearch)
(R, el TBR original de Google, sin mantenimiento activo). Ese repo sigue siendo útil para leer
la metodología en su forma más simple.

## Instalación

Mismo stack que Meridian, así que comparte venv:

```
uv pip install --python .venvs/meridian meridian-geox
```

## Pendiente de probar

1. **La parte de diseño primero**, que es la que no se puede improvisar: dado un panel de
   regiones sintético, ¿qué MDE promete y con cuánto presupuesto? Aquí no hace falta correr
   ningún experimento real para aprender.
2. Extender `generators/` con dimensión geo para poder simular un experimento con efecto
   conocido y ver si GeoX lo recupera.
3. Cerrar el bucle: inyectar el resultado de ese experimento simulado como prior en Meridian
   y medir cuánto mejora la recuperación del ROI verdadero de los demás canales.
