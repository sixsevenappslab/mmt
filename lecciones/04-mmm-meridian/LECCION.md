# 04 · MMM II: la misma tabla con Meridian, y el prior a la vista

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sixsevenappslab/mmt/blob/main/lecciones/04-mmm-meridian/LECCION.ipynb)

**Pregunta que responde:** cuando los datos no saben cuánto vale un canal, ¿quién decide el
número que sale en el informe?
**Antes:** lección 03 (PyMC-Marketing contra la verdad). Esta lección usa los mismos datos y la
misma tabla, y da por sabido qué son adstock, saturación y "la verdad dentro del intervalo".
**Entorno:** venv `.venvs/meridian` con `google-meridian`. Comprobar:
`.venvs/meridian/bin/python -c "import meridian; print(meridian.__version__)"`.
Si no existe: `./setup.sh --only meridian`. Sin GPU va bien: cada ajuste tarda unos 35 s.
**Duración:** 2–3 h.
**Se comprueba solo:** esta lección trae `ejercicios.py` (siete ejercicios verificables contra
los ajustes guardados y contra tu propio ajuste) y `averia.py` (cuatro modelos rotos a
propósito). Protocolo en `lecciones/CONTRATO.md`.

Cifras de esta lección: google-meridian 2.0.0 (backend JAX), 2026-09-05, CPU de 16 núcleos.
Si te salen otras, apunta las tuyas: es información, no un error.

**Vídeo, si te ayuda:** Google publica una serie corta sobre Meridian, un vídeo por concepto.
Los que sirven aquí están en `libs/videos.md` con su duración. Ninguno es obligatorio, y
conviene verlos antes de §1 o después de Registrar: en medio de la práctica te dan la respuesta
que el ejercicio te está pidiendo que adivines.

## 1 · Explicar

### Qué cambia y qué no

La ecuación es la misma que en la lección 03: baseline, más un término por canal con adstock y
saturación, más controles, más ruido. Meridian estima esa ecuación con adstock geométrico y
saturación de Hill, igual que el generador. Lo que cambia es dónde pone la opinión previa, y eso
resulta ser todo.

Tres diferencias prácticas antes de tocar nada:

- **Meridian no tiene tendencia ni estacionalidad como términos.** El baseline es una curva
  suave en el tiempo (un spline) con un número de nudos que eliges tú. Aquí, 13: uno cada 12
  semanas. Con pocos nudos el baseline no puede seguir la subida del KPI, y esa subida se la
  queda algún canal.
- **Meridian quiere impresiones y gasto por separado.** El generador no tiene impresiones, así
  que el gasto hace los dos papeles. Es lo que recomienda su documentación cuando no hay otra
  cosa, y conviene saberlo: la saturación se calcula sobre lo que le pasas como "ejecución".
- **El KPI se declara como ingresos** (`kpi_type="revenue"`) para que el ROI salga en unidades
  de KPI por euro, la misma escala que `base.truth.json` y que la lección 03.

Detalle de instalación y versiones en `libs/meridian.md`.

### Dónde vive el prior, y por qué eso lo cambia todo

En PyMC-Marketing los priors van sobre los parámetros de las curvas: el coeficiente del canal,
la tasa de adstock, la forma de la saturación. El ROI sale después, como consecuencia. Meridian
le da la vuelta: **el prior va directamente sobre el ROI de cada canal.** Por defecto,
`LogNormal(0.2, 0.9)`: mediana 1,2 de KPI por euro, con un intervalo del 95 % que va de 0,2 a
7. El resto de parámetros se reparametrizan para que el ROI resultante sea ese.

Parece un detalle de implementación. No lo es. Recuerda lo que decidía en la lección 03 si un
canal se identifica: la variación de su gasto. Search es always-on, con poca variación, y los
datos no lo separan del baseline. En PyMC-Marketing eso salía como un intervalo inútil de
[1,6 – 12,4]. En Meridian sale como lo que diga el prior. **Donde los datos callan, habla el
prior, y en Meridian el prior habla en unidades de ROI.** Es más fácil de entender, más fácil
de defender delante de un director de marketing, y más fácil de meter una opinión sin darse
cuenta.

Si prefieres oírlo antes de leerlo, el vídeo oficial [Intro to Priors](https://www.youtube.com/watch?v=v5S5jSholZI)
dura 2:17, aunque solo cuenta la mitad buena: presenta el prior como lo que estabiliza y aporta
contexto de negocio, no como lo que decide el resultado cuando los datos no dicen nada. El reparto entre tipos de prior está en
[Treatment Prior Types](https://www.youtube.com/watch?v=brriIvu2TLY), 4:30.

Por eso Meridian insiste tanto en calibrar con experimentos: si tienes un lift test de search,
lo metes como prior y el hueco lo llena una medida en vez de una opinión. Sin experimento, la
elección del prior **es** la estimación para los canales flojos. Documentación oficial:
[distribuciones a priori predeterminadas](https://developers.google.com/meridian/docs/advanced-modeling/default-prior-distributions?hl=es-419)
y [cómo calibrar los priors](https://developers.google.com/meridian/docs/advanced-modeling/roi-priors-and-calibration?hl=es-419).

### Un intervalo estrecho no es un intervalo mejor

Vas a ver, con números, dos modelos que dicen lo mismo con distinta cara. Para search,
PyMC-Marketing da un intervalo ancho y centrado cerca de la verdad. Meridian por defecto da uno
estrecho y mal centrado, que deja la verdad fuera. El estrecho **parece** mejor. Es peor:
la anchura viene del prior, no de los datos, y un informe que no diga qué prior se usó está
presentando una opinión como si fuera una medida.

La pregunta correcta delante de cualquier intervalo de Meridian es: ¿cuánto de esto es prior?
Meridian trae herramientas para responderla (comparar prior y posterior por canal); en esta
lección lo harás a mano, cambiando el prior y mirando qué canales se mueven.

### Tres formas de decir lo mismo

El experimento 02 ajustó tres variantes, y tú vas a repetirlas:

- `roi-default`: el prior de ROI que trae la librería.
- `roi-wide`: el mismo prior centrado en 4 en vez de en 1,2. Es hacer trampa a medias: no usa
  la verdad exacta, pero sabe por dónde anda.
- `contribution`: en vez de ROI, un prior sobre la cuota del KPI que aporta cada canal ("cada
  canal son unos pocos puntos"). Es lo que Meridian recomienda cuando el KPI no son ingresos.

Y una cuarta, la tuya. En el paso 1 vas a escribir un prior que te parezca defendible **sin
haber visto la verdad**, y en el paso 5 lo vas a correr. Es lo que hace un analista real cada
vez que ajusta un Meridian, y es la parte de la lección que no se puede copiar.

Una cosa que sigue sin explicación y conviene decirla: video sale un 20–30 % alto en las tres
variantes, siempre dentro del intervalo, y PyMC-Marketing con la misma forma de saturación no
tiene ese sesgo. Hay una hipótesis en `experiments/02-meridian-vs-verdad/RESULTADO.md`; no está
comprobada. Si te pica, es un experimento que falta.

## 2 · Practicar

Trabaja desde la raíz del repo. Los ajustes tardan unos 35 s cada uno en CPU. Cada uno imprime
la misma tabla que la lección 03 más una fila de diagnóstico (divergencias, r̂, segundos).

1. **Haz:** comprueba que existen los datos de la lección 03 y, si no, genéralos.
   ```
   .venvs/meridian/bin/python generators/synthetic_mmm.py --seed 42 --out data/synthetic/base
   ```
   Después, **antes de ajustar nada**, escribe en una línea tu prior de ROI para este anunciante:
   una mediana y un sigma para una LogNormal, y por qué. Piensa en qué devuelve un euro de
   medios en un negocio como este, no en lo que viste en la lección 03. No lo cambies después.
   **Mira:** el prior por defecto de Meridian tiene mediana 1,2. ¿Tu mediana está por encima o
   por debajo? ¿Tu sigma es más o menos ancho que 0,9?
   **Piensa:** en la lección 03 un canal se quedaba sin identificar por falta de variación de
   gasto. Con un prior de mediana 1,2, ¿a qué canal le va a pasar factura?
   **Comprueba:** `python3 lecciones/practica.py 04 e1 --valor <canal>`. Contesta antes de
   ajustar; el fallo aquí es la mitad de la lección.

2. **Haz:** el prior por defecto.
   ```
   .venvs/meridian/bin/python experiments/02-meridian-vs-verdad/run.py --variant roi-default
   ```
   **Mira:** la columna `truth_inside_hdi`, y el ancho de cada intervalo (alto menos bajo). Y la
   línea de baseline: verdad 75 %, ¿modelo?
   **Piensa:** el canal con el intervalo más estrecho, ¿es el que mejor recupera la verdad?
   **Comprueba:** `python3 lecciones/practica.py 04 e2 --valor <canal>`.

3. **Haz:** el mismo modelo con el prior centrado en 4.
   ```
   .venvs/meridian/bin/python experiments/02-meridian-vs-verdad/run.py --variant roi-wide
   ```
   **Mira:** la mediana de search en esta tabla y en la anterior. Y la de video.
   **Piensa:** no ha cambiado ni un dato ni una línea del modelo. ¿Qué ha cambiado?
   **Comprueba:** `python3 lecciones/practica.py 04 e3 --valor <factor>`.

4. **Haz:** el prior sobre contribución en vez de sobre ROI.
   ```
   .venvs/meridian/bin/python experiments/02-meridian-vs-verdad/run.py --variant contribution
   ```
   **Mira:** las divergencias, la cuota de baseline con su intervalo, y el ROI de display.
   **Piensa:** con las tres tablas delante, ¿qué canal se ha movido menos, y por qué justo ese?
   ¿Y puede un modelo clavar la cuota total de medios y equivocarse en el reparto?
   **Comprueba:** `python3 lecciones/practica.py 04 e4 --valor <canal>` y
   `python3 lecciones/practica.py 04 e5 --valor <cuota>`.

5. **Haz:** tu prior del paso 1, tal cual lo escribiste.
   ```
   .venvs/meridian/bin/python experiments/02-meridian-vs-verdad/run.py --variant roi-custom \
     --roi-median <tu mediana> --roi-sigma <tu sigma> --out /tmp/mmt-roi-custom
   ```
   **Mira:** search y display, que son los canales que el prior mueve. Compara con las tres
   tablas anteriores.
   **Piensa:** si tuvieras que enseñar esta tabla a alguien que decide presupuesto, ¿qué le
   dirías del prior? ¿Podrías defenderlo sin mencionar la verdad?
   **Comprueba:** `python3 lecciones/practica.py 04 e6 --valor <sí o no>`. El arnés lee tu
   salida de `/tmp/mmt-roi-custom/`, así que tiene que existir.

6. **Haz:** abre `experiments/02-meridian-vs-verdad/RESULTADO.md`. La tabla tiene una columna
   con el mejor ajuste de PyMC-Marketing de la lección 03, canal por canal, para los mismos
   datos.
   **Mira:** search en los dos frameworks. Social: en PyMC la verdad quedaba fuera; en Meridian,
   dentro con cualquier prior.
   **Piensa:** dos frameworks, los mismos datos, y en un canal se contradicen. ¿Cuál tiene
   razón? ¿Es esa la pregunta correcta?
   **Comprueba:** `python3 lecciones/practica.py 04 e7 --valor "<qué decide el ROI>"`.

7. **Haz:** el drill de avería. Pídele al agente que elija un número y lo corra sin decírtelo.
   ```
   .venvs/meridian/bin/python lecciones/04-mmm-meridian/averia.py --n <lo elige el agente>
   ```
   **Mira:** la tabla de siempre con un defecto metido a propósito. Compárala con la de
   `roi-default` del paso 2. Fíjate en la columna `contrib_pct`: la cuota de KPI que el modelo
   atribuye a cada canal.
   **Piensa:** ¿qué está roto, y en qué línea lo ves? Di tu diagnóstico antes de que el agente
   revele nada. Una pista general: en Meridian el prior de ROI tapa cosas que en la lección 03
   saltaban a la vista. Un canal cuyo ROI es clavado a la mediana del prior es un canal del que
   el modelo no sabe nada, y eso puede ser por los datos o por un error tuyo.

   Si aciertas a la primera, pide otra. Hay cuatro.

   **Después** de que el agente te revele las averías que hayas hecho, el vídeo oficial
   [Knots in Meridian](https://www.youtube.com/watch?v=gP-mI82bpAE) (5:25) explica los nudos
   del baseline, que son una de ellas. Antes no: te la regala.

## 3 · Comprobar

El agente hace estas preguntas de una en una y no pasa a la siguiente sin respuesta.

**P1.** ¿En qué difieren los priors de Meridian y los de PyMC-Marketing, y qué consecuencia tiene
esa diferencia para un canal que los datos no identifican?

<details>
<summary>Referencia</summary>
PyMC-Marketing pone priors sobre los parámetros de las curvas (coeficiente, decay, saturación) y
el ROI es una consecuencia; Meridian pone el prior directamente sobre el ROI y reparametriza el
resto. Consecuencia: para un canal sin variación de gasto, PyMC devuelve un intervalo ancho (los
priors de curva son vagos en unidades de ROI) y Meridian devuelve básicamente el prior, con un
intervalo estrecho en unidades de ROI. Lo que en uno es incertidumbre visible, en el otro es
una opinión con aspecto de medida. Respuesta completa si dice dónde va el prior en cada uno Y
qué le pasa al canal flojo. Incompleta si solo describe la diferencia sin la consecuencia.
</details>

**P2.** Para search, Meridian por defecto da [0,3 – 5,3] y PyMC-Marketing [1,6 – 12,4]. ¿Cuál es
mejor, y qué le preguntas al informe antes de decidir?

<details>
<summary>Referencia</summary>
Ninguno es mejor: los dos dicen que los datos no saben cuánto vale search. El estrecho está mal
centrado (deja la verdad fuera) y su anchura viene del prior, no de la evidencia; el ancho es
inútil pero honesto. La pregunta al informe es qué prior se usó y cuánto se movió el posterior
respecto a él; si apenas se movió, el número es el prior. La respuesta de fondo es que search
necesita un experimento, no otro modelo. Respuesta incorrecta si elige el estrecho "porque es
más preciso". Incompleta si dice "ninguno" sin pedir el prior.
</details>

**P3.** ¿Qué es un modelo geo y por qué Meridian apuesta por él?

<details>
<summary>Referencia</summary>
Un modelo jerárquico con una serie por región: cada geo tiene su baseline y sus efectos, y los
parámetros se comparten parcialmente entre regiones (pooling parcial). Da variación entre
unidades además de en el tiempo: un canal always-on que no varía semana a semana sí varía entre
regiones, y eso identifica lo que el modelo nacional no puede. Además multiplica las filas (156
semanas × N geos) para el mismo número de parámetros de canal. Y encaja con la calibración: los
experimentos geo (lección 05) miden en las mismas unidades que el modelo geo. Respuesta
completa si menciona el pooling parcial o la variación entre regiones como fuente de
identificación. Incompleta si solo dice "más datos".
</details>

## 4 · Registrar

Escribe `.progreso/04.md` con el formato del contrato. Además de "me costó" y "quiero
profundizar", apunta la respuesta a esta pregunta abierta, que enlaza con la lección 06
(calibración): **para un cliente nuevo del que no sabes nada, ¿qué prior de ROI usarías, y qué
experimento pedirías antes del segundo ajuste?**

Guarda también el prior que escribiste en el paso 1 y lo que salió con él. Es tu primera
calibración documentada: dentro de unas lecciones querrás compararla.

Si la tercera pregunta te dejó con ganas, el vídeo oficial
[Geo Vs National Level Modeling](https://www.youtube.com/watch?v=apaWURDjGX4) dura 4:47 y la
responde entera. Catálogo completo en `libs/videos.md`.

Siguiente lección sugerida: 05 (experimentos geo e incrementalidad), que es de donde salen los
priors que Meridian querría, o 06 (calibración) si prefieres ver ya cómo entra un experimento
en el modelo.
