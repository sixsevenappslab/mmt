# MMT · Marketing Measurement Toolkit

Un sitio para aprender medición de marketing **haciéndola**: marketing mix modeling,
incrementalidad, experimentos geo y encuestas de impacto, con librerías reales y datos
sintéticos cuya verdad conocemos de antemano.

La idea que lo sostiene es simple. Con datos reales nunca sabes si un modelo acertó, porque
nadie te dice cuál era la respuesta. Aquí los datos los fabricamos nosotros, así que el ROI
verdadero de cada canal está guardado en un fichero al lado del CSV. Puedes comparar lo que
estima el modelo contra lo que de verdad pasó, que es la única forma de saber si una técnica
funciona o solo lo parece.

## Para quién es

Para quien decide sobre inversión en marketing y quiere entender por dentro las herramientas
que le dan los números. Damos por sabido que programas algo de Python. No damos por sabida
la estadística bayesiana.

## Qué hay dentro

| Carpeta | Qué contiene |
|---|---|
| `lecciones/` | El curso. Cada lección explica, hace practicar, comprueba y registra. |
| `conceptos/` | Los métodos explicados. Empieza por `conceptos/mapa-del-terreno.md`. |
| `libs/` | Una nota por herramienta: qué hace, qué asume, qué salió al probarla. Y `libs/videos.md`, vídeo ajeno revisado uno a uno. |
| `generators/` | Los generadores de datos sintéticos. Siempre guardan la verdad junto al CSV. |
| `experiments/` | Una prueba por carpeta, con su conclusión en la primera línea del `RESULTADO.md`. |
| `skills/` | Utilidades para validar y diagnosticar tus propios datos antes de modelar. |

`FORMACION.md` es el itinerario completo, de once módulos.

## Cómo se usa

El curso está pensado para que **el tutor sea un agente de código**. Abres el repo con Claude
Code, Codex o similar, le dices que quieres una lección, y el agente lee el contrato y te la
da: te para antes de cada paso, te pide tu predicción, y solo después te enseña el resultado.

Hay tres formas de correrlo, de mejor a peor:

1. **En tu máquina, con un agente de código.** Clona, ejecuta `./setup.sh` y pide la lección.
   Necesitas Python y un entorno tipo Unix. En Windows, vía WSL.
2. **Con un agente de código en la nube**, contra este repo. Igual de bueno y sin instalar nada.
3. **En Google Colab.** Cada lección tiene su cuaderno con un botón para abrirlo. Practicas,
   pero sin tutor que te obligue a mojarte antes de mirar, que es media asignatura.

## Por qué te hace predecir antes de ver el resultado

Porque un agente puede resolverte el ejercicio en segundos, y entonces mirarías la respuesta
correcta asintiendo sin haber aprendido nada. Lo único que mide de verdad si vas entendiendo
es cuántas veces aciertas **antes** de mirar. El repo lo registra y te lo devuelve con
`python3 lecciones/practica.py --calibracion`. Fallar ahí es información, no una nota.

## Estado

Honestamente: en obra. De los once módulos del itinerario hay **dos lecciones escritas**, la
03 sobre PyMC-Marketing y la 04 sobre Meridian, ambas con ejercicios que se corrigen solos y
con modelos rotos a propósito para que los diagnostiques. El resto del temario está planificado
pero sin escribir.

Lo que sí está completo es la capa de referencia: el catálogo de herramientas, las notas por
librería y los generadores de datos.

## Reglas de la casa

- **Nunca entran datos reales.** Todo lo versionado es sintético y con su verdad al lado.
- **Lo que salió mal también se anota.** Una librería que no se pudo instalar es información.
- **Todo experimento acaba con su conclusión escrita**, o no ha terminado.

## Licencia

Sin definir todavía. Hasta que se publique una licencia explícita, todos los derechos quedan
reservados. Si quieres usar algo de aquí, abre una issue y lo hablamos.
