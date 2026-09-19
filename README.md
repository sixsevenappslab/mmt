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

Dos licencias, porque aquí hay dos cosas distintas.

- **El código** (los `.py`, `.sh` y la configuración: generadores, arnés de práctica,
  utilidades y tests) va bajo **MIT**, en `LICENSE`. Cógelo y úsalo como quieras, incluso en
  algo comercial. Solo mantén el aviso de copyright.
- **El contenido** (lecciones, conceptos, notas de herramientas y el catálogo de vídeo) va
  bajo **CC BY-SA 4.0**, en `LICENSE-CONTENT`. Puedes copiarlo, traducirlo, adaptarlo y darlo
  en clase, también cobrando. Dos condiciones: cita de dónde viene, y si publicas una versión
  modificada, compártela con la misma licencia.

### Cómo citar

Si reutilizas el contenido, esta es la atribución que pide la licencia, enlace al sitio del
autor incluido:

> MMT · Marketing Measurement Toolkit, por [Jesús Martín Calvo](https://sixsevenapps.com),
> bajo [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
> Original: https://github.com/sixsevenappslab/mmt

```html
<a href="https://github.com/sixsevenappslab/mmt">MMT · Marketing Measurement Toolkit</a>
por <a href="https://sixsevenapps.com">Jesús Martín Calvo</a>,
bajo <a href="https://creativecommons.org/licenses/by-sa/4.0/">CC BY-SA 4.0</a>.
```

Si lo has modificado, escribe "adaptado de" o "traducido de" en lugar de "por": la licencia
obliga a señalar que hubo cambios. En vídeo o papel, donde no cabe un enlace, basta con el
nombre y el dominio en texto.

Lo que no cubre ninguna de las dos licencias: el material de terceros al que enlazamos. Los
vídeos del catálogo son de sus autores y aquí solo hay enlaces y comentarios.
