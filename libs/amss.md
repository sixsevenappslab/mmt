# AMSS (Google) — Aggregate Marketing System Simulator

**Repo:** https://github.com/google/amss
**Estado en mmt:** catalogada como referencia; no ejecutada (es R).
**Última verificación de datos:** 2026-09-04 (v1.0.1, sin desarrollo activo reciente).

## Qué es

El simulador de datos de marketing agregados de Google. Genera series temporales sintéticas
**y su ground truth**, con el propósito explícito de evaluar metodologías de MMM en un entorno
donde la verdad se conoce. Implementa el marco del paper de Zhang & Vaver.

Es exactamente la misma idea que `generators/synthetic_mmm.py`, pero mucho más ambiciosa: en
vez de generar directamente `kpi = f(gasto)`, simula el **sistema** — una población de
consumidores que se mueve entre estados (desconocimiento → conocimiento → favorabilidad →
intención → compra), y la publicidad actúa sobre las transiciones entre estados.

## Por qué esa diferencia importa (y por qué no es un problema para nosotros)

Nuestro generador simula datos **desde el mismo modelo que el MMM asume**: adstock geométrico
+ saturación Hill. Eso hace la prueba honesta pero fácil: le estás dando al modelo justo la
forma funcional que espera. Si Meridian falla ahí, es un fallo grave; si acierta, no prueba
gran cosa sobre el mundo real.

AMSS genera desde un mecanismo distinto del que el MMM asume. Ahí la pregunta pasa a ser la
buena: *¿recupera el ROI un modelo cuyos supuestos son falsos?* Que es la situación en la que
está todo MMM del mundo real.

**Plan de dos escalones, entonces:**

1. Datos propios (mismo modelo) → detecta bugs y problemas de identificabilidad. Barato.
2. Datos tipo AMSS (modelo distinto) → mide robustez frente a supuestos equivocados. Caro,
   pero es donde está el aprendizaje de verdad.

## El obstáculo

Es un paquete de R sin port a Python, y sin mantenimiento reciente. Tres salidas posibles,
por orden de coste:

- **Correrlo en R** y exportar CSV para consumir desde Python. Lo más fiel, requiere R.
- **Portar el núcleo** del modelo de estados a Python en `generators/`. Trabajo de verdad,
  pero es la vía que más enseña sobre el modelo.
- **Aproximarlo**: añadir a nuestro generador un mecanismo distinto (embudo de estados
  simplificado) sin pretender replicar AMSS. Suficiente para el objetivo, mucho más barato.

La tercera es probablemente la correcta para empezar: el valor está en *generar desde un
modelo distinto al que se estima*, no en replicar AMSS fielmente.

## Pendiente

1. Leer el vignette y el paper de Zhang & Vaver para entender el modelo de estados.
2. Decidir entre las tres salidas de arriba.
