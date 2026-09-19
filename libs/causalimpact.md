# CausalImpact — efecto causal de una intervención en una serie temporal

**Repo original (R):** https://github.com/google/CausalImpact
**Port Python:** https://github.com/WillianFuks/tfcausalimpact (`tfcausalimpact`, TensorFlow Probability)
**Estado en mmt:** instalada en R (1.4.1, 2026-09-05) como dependencia de GeoLift; no probada todavía.
**Última verificación de datos:** 2026-09-04.

## Qué es

Responde a una pregunta distinta de la del MMM: *¿qué habría pasado si no hubiéramos hecho
esto?*. Construye un contrafactual con un modelo bayesiano de series temporales estructurales
(BSTS) a partir de series de control no afectadas por la intervención, y mide la diferencia
contra lo observado.

Casos típicos: apagar una campaña, lanzar una landing, un cambio de precio, una salida en
prensa. Es la herramienta natural para medir cosas puntuales que un MMM semanal no ve.

## Lo que hay que tener claro antes de usarlo

El resultado vale exactamente lo que valgan las series de control. Necesitan:
- no estar afectadas por la intervención (si apagas Meta en toda España, el tráfico directo
  español no es control válido),
- estar correlacionadas con la serie objetivo antes de la intervención.

Sin eso, el intervalo de confianza sale igual de bonito y no significa nada. El error más
común en su uso.

## Alternativas del mismo espacio (por explorar)

- **GeoLift** (Meta, R) — diseño *y* análisis de experimentos geo con synthetic control.
  Va un paso más allá: te dice qué regiones usar como test/control antes de gastar.
- **google/meridian-geox** — la pata de experimentos geo de Meridian.
- **Causmos** (Google Marketing Solutions) — app web tipo CausalImpact, sin código.
- **Awesome-Marketing-Science** (https://github.com/shakostats/Awesome-Marketing-Science) —
  lista curada de recursos de geo testing, MMM, MTA y causal inference. Buen punto de partida
  para no reinventar el catálogo.

## Instalación

**R (2026-09-05):** `CausalImpact` 1.4.1 está instalada en `~/R/library`, pero su cadena
`Boom` → `BoomSpikeSlab` → `bsts` ya no está en CRAN (archivados) y hay que instalarla con
versión fijada desde el archivo. Los pasos exactos están en `libs/geolift.md`.

`tfcausalimpact` trae TensorFlow Probability, así que puede convivir con el venv de Meridian
(mismo stack) mejor que con el de PyMC.

```
uv pip install --python .venvs/meridian tfcausalimpact
```

## Pendiente de probar

1. Generar un dataset sintético con intervención conocida (extender `generators/`) y ver si
   recupera el efecto real.
2. Probar el caso de fallo a propósito: control contaminado por la intervención, y comprobar
   cuánto se equivoca sin avisar.
3. Aplicarlo a algo real: un pico de tráfico inesperado o el lanzamiento de un producto.
