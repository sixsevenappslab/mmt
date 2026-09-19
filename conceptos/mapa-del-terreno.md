# Mapa del terreno: cómo se mide el marketing

Documento de orientación. Para qué sirve cada familia de métodos, qué pregunta responde cada
una y dónde miente. Escrito 2026-09-04, se corrige a medida que probemos cosas.

## Las tres familias, y por qué son tres

No compiten: responden preguntas distintas y operan a escalas distintas.

| | Pregunta | Unidad de análisis | Necesita |
|---|---|---|---|
| **MMM** | ¿Cómo reparto el presupuesto entre canales? | canal × semana, agregado | 2-3 años de historial |
| **Experimentos / incrementalidad** | ¿Esto que hago causa algo? | región o usuario, con control | apagar o encender algo de verdad |
| **Atribución (MTA)** | ¿Qué toques llevaron a esta conversión? | usuario × touchpoint | seguimiento individual |

La respuesta corta al "¿cuál uso?" en 2026: **MMM para repartir, experimentos para calibrar,
atribución solo para operar el día a día** — y sabiendo que sus números no son causales.

## MMM: la mecánica que todos comparten

Los tres frameworks del catálogo (Meridian, PyMC-Marketing, Robyn) estiman variantes de:

```
ventas[t] = baseline[t] + Σ_canal contribución_canal[t] + controles[t] + ruido
```

Y todos transforman el gasto igual, con dos ideas que son el corazón del asunto:

**1. Adstock (arrastre).** La publicidad de esta semana sigue vendiendo la que viene. Se
modela como una media ponderada decreciente del gasto pasado. El parámetro es la tasa de
decaimiento: TV y vídeo arrastran mucho, search de marca casi nada.

**2. Saturación (rendimientos decrecientes).** El euro número 100.000 rinde menos que el
primero. Se modela con una curva Hill o exponencial. Sin esto, el modelo recomendaría meter
todo el presupuesto en el canal con mayor coeficiente, hasta el infinito.

Toda la decisión de presupuesto sale de la curva de saturación: el óptimo está donde los
retornos marginales de todos los canales se igualan, no donde el ROI medio es más alto.
Confundir ROI medio con ROI marginal es probablemente el error más caro de esta disciplina. Google lo explica en 3:47 en
[Incremental Outcome, ROI, mROI, and Response Curves](https://www.youtube.com/watch?v=3GJ5PieyDIc);
más vídeo en `libs/videos.md`.

## Dónde miente un MMM

Vale la pena tenerlo escrito antes de enamorarse de los gráficos:

- **Correlación con buena presentación.** Si search siempre sube cuando suben las ventas, el
  modelo le dará crédito, aunque search suba *porque* la gente ya quería comprar. La demanda
  causa el gasto tanto como el gasto causa la demanda. Los frameworks bayesianos no arreglan
  esto: solo lo expresan con intervalos más anchos, y solo si has puesto priors honestos.
- **Colinealidad.** Si dos canales siempre se encienden juntos, no hay datos para separarlos.
  El modelo devolverá un reparto, y ese reparto será arbitrario. El síntoma es un intervalo
  ancho, no un error visible.
- **Baseline que se come todo.** En nuestros datos sintéticos el baseline es el 75 % del KPI,
  y eso es realista. Casi todo lo que vendes lo venderías igual. El MMM discute el 25 %.
- **Pocos datos para muchos parámetros.** Tres años de datos semanales son 156 filas. Con 5
  canales × 3 parámetros cada uno, más baseline y estacionalidad, estás cerca del límite.

De ahí que la calibración con experimentos sea la novedad importante de esta generación de
herramientas y no un extra: es lo único que rompe el bucle correlación → confianza.

## El bucle que de verdad funciona

```
experimento geo (efecto causal medido en un canal)
        ↓  entra como prior
      MMM calibrado
        ↓  produce reparto + incertidumbre por canal
donde el intervalo es más ancho → siguiente experimento
```

Google lo cuenta en 4:52 en
[Conversion Lift](https://www.youtube.com/watch?v=-ZoAazB-_cE), donde define el reparto entre
tratamiento y control y la diferencia entre hacerlo por usuarios o por geografía; el último
tercio ya es su interfaz. Más, con reservas, en `libs/videos.md`.

Ninguna de las dos piezas sola sirve. El experimento mide bien pero solo una cosa cada vez y
cuesta dinero. El MMM cubre todo pero no distingue causa de correlación. Encadenados, cada
uno tapa el agujero del otro.

## Lo que el comportamiento no ve: encuestas

Las tres familias miden ventas o visitas. Lo que pasa antes (notoriedad, consideración) se
mide preguntando, con sus propios sesgos: `encuestas-de-impacto.md`.

## Por qué la atribución multi-touch se quedó atrás

No fue una decisión metodológica, fue el entorno: ITP/ATT, consent mode, walled gardens que
no exportan el dato a nivel usuario. Un modelo de atribución sobre datos incompletos no es un
modelo peor, es un modelo de una muestra sesgada — y el sesgo va justo en la dirección que más
duele (los canales que peor se rastrean parecen los que menos aportan).

Sirve para operar: qué creatividad pausar, qué anuncio duplicar. No sirve para decidir cuánto
vale un canal. Los dashboards de plataforma son atribución, y por eso nunca cuadran entre sí:
cada uno se apunta la misma conversión.

## Vocabulario mínimo

- **Incrementalidad** — lo que no habría pasado sin la inversión. La única definición de
  "funciona" que aguanta.
- **MDE (minimum detectable effect)** — el efecto más pequeño que un experimento podría
  detectar. Si tu MDE es del 10 % y el efecto real es del 4 %, tu test dirá "no hay efecto" y
  se equivocará. Se calcula *antes* de correr el test.
- **Contrafactual** — qué habría pasado sin la intervención. Todo esto son maneras distintas
  de construirlo.
- **Control sintético** — contrafactual hecho como combinación ponderada de unidades no
  tratadas.
- **Prior** — creencia previa sobre un parámetro, en un modelo bayesiano. Es la puerta por la
  que entra el resultado de un experimento en un MMM.
- **Ground truth** — el valor verdadero. En datos reales no existe; por eso todo lo que
  probamos aquí se prueba primero sobre datos sintéticos.
