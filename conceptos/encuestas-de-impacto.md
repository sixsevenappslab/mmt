# Encuestas de impacto publicitario

Medir con encuestas lo que la publicidad cambia en la cabeza de la gente: notoriedad,
recuerdo, consideración, intención. Complementan al MMM y a los experimentos, que miden
comportamiento (ventas, visitas), midiendo lo que pasa antes del comportamiento. Y son la
familia donde más fácil es engañarse, porque el dato parece limpio.

Experimento de referencia: `experiments/05-encuesta-brand-lift/`.

## Los cuatro diseños, de mejor a peor

| Diseño | Qué compara | Qué necesita | Dónde miente |
|---|---|---|---|
| **Brand lift con holdout** | Expuestos vs. grupo al que se retuvo el anuncio, asignado al azar antes de servir | Que la plataforma controle la entrega (Meta, Google, YouTube, TikTok lo ofrecen) | Poco. Solo en quién responde a la encuesta, y en que el "control" vio otros anuncios |
| **Expuestos vs. no expuestos reconstruido** | Quien recuerda o consta que vio el anuncio vs. quien no | Solo la encuesta | Mucho. Quien ve el anuncio ya se parecía a quien iba a decir que sí. Exp. 05: +60 % de lift inflado |
| **Pre/post** | La misma pregunta antes y después de la campaña | Dos olas de encuesta | Todo lo que cambió entre olas se atribuye a la campaña: estacionalidad, competencia, noticias |
| **Atribución autodeclarada** ("¿cómo nos conociste?") | Lo que la gente dice que le trajo | Una pregunta en el formulario | Memoria y prestigio: se recuerda lo último y lo notorio; nadie dice "un banner" |

El pre/post y la autodeclarada no son medición causal. Sirven como señal barata y como
contraste con lo que dice el modelo, no como estimación del efecto.

## Los tres sesgos, y qué arregla cada uno

1. **Confusión en la exposición.** Quien ve el anuncio no es una muestra al azar. Lo arregla
   la aleatorización; a falta de ella, ajustar o emparejar por las covariables que mueven la
   exposición, y solo si están medidas. La reponderación a población **no** lo arregla
   (exp. 05, punto 2).
2. **No respuesta.** Quien contesta no es una muestra al azar de la población, y si además
   los expuestos contestan más, el sesgo entra directo en el lift. Lo arregla reponderar a
   una referencia poblacional (`balance`, raking, IPW), si el lift difiere entre los grupos
   que responden distinto. Si no difiere, no hace falta.
3. **Tamaño.** 2000 respuestas → ± 4 pp con un baseline del 30 %. Los lifts reales de marcas
   consolidadas son de 1–3 pp. Antes de encargar el estudio, calcular el tamaño para el lift
   mínimo que cambiaría una decisión, no para "significancia".

## Cómo leer un informe de brand lift

- ¿Quién asignó el control y cuándo? Si fue después de servir, es el diseño 2.
- ¿Lift absoluto (pp) o relativo (%)? Un 30 % relativo sobre un baseline del 5 % son 1,5 pp.
- ¿Intervalo, o solo "significativo"? Sin intervalo no se puede decidir nada.
- ¿Cuántas preguntas se testaron? Con cinco métricas, una sale significativa por azar.
- ¿La muestra se reponderó, y a qué referencia?

## Herramientas

- **`balance`** (Meta): reponderación de muestras sesgadas a una referencia. `libs/balance.md`.
- **statsmodels**: regresión ajustada, IC. No hace falta más.
- **Generador propio**: `generators/synthetic_brand_lift.py`, con verdad conocida y cada
  sesgo con tamaño conocido.

## Dónde encaja con el resto

El brand lift mide el eslabón anterior a la venta. Sirve para (a) canales cuya venta el MMM no
ve bien (vídeo, marca), como prior cualitativo de que hay efecto; (b) decidir creatividades
antes de escalar. No sustituye al geo-experimento para medir incrementalidad en ventas: un
lift en consideración no tiene tipo de cambio a euros.
