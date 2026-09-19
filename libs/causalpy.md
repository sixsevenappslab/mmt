# CausalPy (PyMC Labs) — cuasi-experimentos bayesianos

**Repo:** https://github.com/pymc-labs/CausalPy
**Estado en mmt:** no probado todavía.
**Última verificación de datos:** 2026-09-04.

## Qué es

Inferencia causal para situaciones en las que **no pudiste aleatorizar**, que es casi todo lo
que pasa en marketing de verdad. Cuatro métodos clásicos con una API común:

- **Synthetic control** — construye el contrafactual con una combinación de unidades no
  tratadas (lo mismo que hace GeoLift por dentro, pero de propósito general).
- **Interrupted time series** — antes/después con modelo de la serie (primo de CausalImpact).
- **Difference-in-differences** — dos grupos, dos periodos.
- **Regression discontinuity** — efecto en un umbral (p. ej. un descuento que se activa a
  partir de X € de carrito).

Estimación bayesiana con PyMC por defecto (incertidumbre completa) y OLS vía scikit-learn
como alternativa rápida.

## Por qué está en el catálogo

Porque es **la caja de herramientas para lo que no cabe en un MMM ni en un test geo**: un
cambio de precio, un rediseño de landing, una campaña que solo se activó en un segmento, un
partner que empezó a enviar tráfico. Casi todo lo que ocurre en los proyectos de la cartera
tiene esta forma, no la de un experimento limpio.

Y para aprender es la mejor entrada del catálogo: los cuatro métodos son *el* vocabulario de
la inferencia causal aplicada. Entenderlos hace que Meridian GeoX y GeoLift dejen de parecer
magia y se lean como dos elecciones concretas dentro de un espacio conocido.

## Instalación

Comparte stack con PyMC-Marketing:

```
uv pip install --python .venvs/pymc causalpy
```

## Pendiente de probar

1. Los cuatro métodos sobre datos sintéticos con efecto conocido — uno por método, cada uno
   en su `experiments/`.
2. El caso de fallo a propósito en diff-in-diff: violar el supuesto de tendencias paralelas y
   ver qué tan mal miente sin avisar.
3. Comparar synthetic control de CausalPy vs. GeoLift sobre el mismo panel: misma familia de
   método, implementaciones distintas.
