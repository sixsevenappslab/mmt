# 03 · MMM I: la mecánica, con PyMC-Marketing contra la verdad

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sixsevenappslab/mmt/blob/main/lecciones/03-mmm-pymc-marketing/LECCION.ipynb)

**Pregunta que responde:** ¿qué hace un marketing mix model por dentro, y cómo sé si acierta?
**Antes:** lección 00 (mapa del terreno) y 01 (datos sintéticos). Se puede hacer sin ellas si
ya sabes qué es un MMM y por qué aquí todo es sintético.
**Entorno:** venv `.venvs/pymc` con `pymc-marketing`, `nutpie`, `h5netcdf`, `h5py`. Comprobar:
`.venvs/pymc/bin/python -c "import pymc_marketing; print(pymc_marketing.__version__)"`.
Si no existe: `uv venv .venvs/pymc --python 3.12 && uv pip install --python .venvs/pymc
pymc-marketing nutpie h5netcdf h5py`.
**Duración:** 2–3 h. Cada ajuste del modelo tarda 30–60 s en CPU.
**Se comprueba solo:** esta lección trae `ejercicios.py` (seis ejercicios verificables contra
la verdad conocida) y `averia.py` (cuatro modelos rotos a propósito). Protocolo en
`lecciones/CONTRATO.md`.

Cifras de esta lección: PyMC-Marketing 1.1.0, 2026-09-04, CPU de 16 núcleos. Si te salen
otras, apunta las tuyas: es información, no un error.

## 1 · Explicar

### La ecuación que todos comparten

Un MMM es una regresión con dos transformaciones del gasto delante. Meridian, PyMC-Marketing
y Robyn estiman variantes de lo mismo:

```
kpi[t] = baseline[t] + Σ_canal beta_canal · saturación(adstock(gasto_canal))[t] + controles[t] + ruido[t]
```

Léela de dentro afuera. Primero el gasto pasa por **adstock**: la publicidad de esta semana
sigue vendiendo la que viene, así que lo que entra en el modelo es una media ponderada
decreciente del gasto de las últimas semanas. Un parámetro por canal, la tasa de decaimiento:
0,7 significa que la semana siguiente queda el 70 %. Después pasa por **saturación**: el euro
número cien mil rinde menos que el primero. Una curva cóncava, aquí la de Hill, con dos
parámetros: dónde está la mitad del efecto máximo y cómo de brusca es la subida. Sin esta
curva, el modelo recomendaría meterlo todo en el canal con mayor coeficiente. Detalle en
`conceptos/mapa-del-terreno.md`, sección MMM. Si lo prefieres dibujado, Google tiene un vídeo
de 5:51 sobre estas dos curvas, [Adstock and Hill](https://www.youtube.com/watch?v=_RkeKEZ1s_M);
es de la serie de Meridian, pero las dos transformaciones son las mismas en cualquier MMM.

El **baseline** es todo lo que vende sin publicidad: tendencia, estacionalidad, precio.
Cuando un MMM falla, la mitad de las veces es porque una parte del baseline se ha colado en un
canal o al revés.

### Qué significa "acertar"

El modelo devuelve, para cada canal, una distribución sobre su ROI (unidades de KPI por euro).
En datos reales no hay con qué compararla. Aquí sí: `data/synthetic/base.truth.json` tiene el
ROI verdadero de cada canal porque el generador los fabricó con esos parámetros. Acertar tiene
dos partes, y la segunda importa más que la primera:

1. La verdad cae dentro del intervalo del modelo.
2. El intervalo es lo bastante estrecho para decidir algo.

Un intervalo de "entre 1,5 y 167 por euro" contiene la verdad y no sirve para nada.

### Lo que decide si un canal se identifica

Adelanto la lección entera para que la busques en la práctica: **lo que identifica un canal
es la variación de su gasto, no su tamaño.** Un canal que gasta lo mismo cada semana es
indistinguible del baseline por muy grande que sea. Uno que se apaga y se enciende deja
huella. Esto es el argumento entero a favor de los experimentos, y lo verás con números.

## 2 · Practicar

Trabaja desde la raíz del repo. El agente corre los comandos si se lo pides, pero antes de cada
uno dile qué esperas ver.

1. **Haz:** genera los datos y mira qué produce.
   ```
   .venvs/pymc/bin/python generators/synthetic_mmm.py --seed 42 --out data/synthetic/base
   ```
   **Mira:** la salida imprime el ROI verdadero de cada canal y la cuota de baseline. Abre
   `data/synthetic/base.csv` y fíjate en la columna `spend_video`: cuántas semanas están a
   cero.
   **Piensa:** cuatro canales con ROI parecidos (entre 2,9 y 5,5). ¿Cuál crees que va a
   recuperar mejor el modelo, y por qué?
   **Comprueba:** `python3 lecciones/practica.py 03 e1 --valor <canal>`. Contesta antes de
   ajustar nada; el fallo aquí es la mitad de la lección.

2. **Haz:** ajusta el modelo con la saturación que usan los ejemplos oficiales.
   ```
   .venvs/pymc/bin/python experiments/01-pymc-vs-verdad/run.py --saturation logistic-default
   ```
   **Mira:** la tabla final. Por canal, mediana del ROI, intervalo del 94 % y si la verdad
   cae dentro (`truth_inside_hdi`). Y la cuota de baseline: verdad 75 %, ¿modelo?
   **Piensa:** un canal tiene la verdad fuera del intervalo. ¿Es un fallo del modelo o de
   los datos? ¿Cómo lo distinguirías?
   **Comprueba:** `python3 lecciones/practica.py 03 e2 --valor <canal>`.

3. **Haz:** ahora con la misma forma de saturación que usó el generador, Hill, priors por
   defecto.
   ```
   .venvs/pymc/bin/python experiments/01-pymc-vs-verdad/run.py --saturation hill-default
   ```
   **Mira:** las divergencias (miles), el ancho de los intervalos y la cuota de baseline con
   su intervalo.
   **Piensa:** el modelo usa la forma funcional verdadera y sale peor. ¿Qué te dice eso
   sobre "usar el modelo correcto"?
   **Comprueba:** `python3 lecciones/practica.py 03 e3 --valor <orden>` para las divergencias
   y `... e4 --valor <cuota>` para la cuota de baseline que estima este ajuste.

4. **Haz:** cambia los datos, no el modelo. Sube la variación del gasto de search de 0,25 a
   0,7 y regenera. Pídele al agente este snippet o escríbelo tú:
   ```python
   # generators/synthetic_mmm.py exposes generate() and DEFAULT_CHANNELS
   import dataclasses
   import json
   import sys

   sys.path.insert(0, "generators")
   from synthetic_mmm import DEFAULT_CHANNELS, generate

   chans = [dataclasses.replace(c, spend_cv=0.7) if c.name == "search" else c
            for c in DEFAULT_CHANNELS]
   df, truth = generate(156, 42, chans)
   df.to_csv("data/synthetic/search-cv07.csv", index=False)
   with open("data/synthetic/search-cv07.truth.json", "w") as handle:
       json.dump(truth, handle, indent=2)
   ```
   Luego:
   ```
   .venvs/pymc/bin/python experiments/01-pymc-vs-verdad/run.py --saturation logistic-default \
     --data data/synthetic/search-cv07 --out /tmp/mmt-search-cv07
   ```
   **Mira:** el intervalo de search antes y después. Nada ha cambiado en el modelo.
   **Piensa:** en la vida real no puedes cambiar el pasado de un canal. ¿Qué sí puedes
   hacer para conseguir esa variación?
   **Comprueba:** `python3 lecciones/practica.py 03 e5 --valor <factor>`. El arnés lee tu
   propia salida de `/tmp/mmt-search-cv07/`, así que tiene que existir.

5. **Haz:** abre `experiments/01-pymc-vs-verdad/RESULTADO.md` y compara tus números con los
   de la tabla. Anota cualquier diferencia con la versión de PyMC-Marketing que tengas.
   **Comprueba:** `python3 lecciones/practica.py 03 e6 --valor "<qué identifica un canal>"`.

6. **Haz:** el drill de avería. Pídele al agente que elija un número y lo corra sin decírtelo.
   ```
   .venvs/pymc/bin/python lecciones/03-mmm-pymc-marketing/averia.py --n <lo elige el agente>
   ```
   **Mira:** la misma tabla de siempre, pero con un defecto metido a propósito. Compárala con
   `experiments/01-pymc-vs-verdad/results/logistic-default/roi_vs_truth.csv`.
   **Piensa:** ¿qué está roto, y en qué línea de la tabla lo ves? Di tu diagnóstico antes de
   que el agente revele nada. Ninguna de las cuatro averías hace protestar al muestreo: todas
   dan cero divergencias y un modelo de aspecto sano.

   Si aciertas a la primera, pide otra. Es el ejercicio que más se parece a tu trabajo real:
   nadie te va a decir que el modelo que te acaban de pasar está mal.

   **Cuando hayas terminado los drills** (no antes), el vídeo oficial
   [Controls, Mediators and Treatments](https://www.youtube.com/watch?v=rg-CL4hdD5o) (7:09)
   le pone nombre a dos de las cuatro averías. En particular al control que no debiste meter:
   lo llama **mediador**, una variable que está entre el anuncio y la venta, y explica por qué
   fijarla impide que el anuncio se lleve ningún mérito. Más vídeo en `libs/videos.md`.

## 3 · Comprobar

El agente hace estas preguntas de una en una y no pasa a la siguiente sin respuesta.

**P1.** Explica adstock y saturación con un dibujo cada uno (a mano, en texto, como quieras).
¿Cuál de las dos curvas es la que decide cómo repartir presupuesto, y por qué?

<details>
<summary>Referencia</summary>
Adstock: gasto en la semana 0, efecto que decae semana a semana (escalera descendente).
Saturación: eje x gasto, eje y respuesta, curva cóncava que se aplana. La de saturación decide
el reparto: el óptimo está donde los rendimientos marginales de todos los canales se igualan,
no donde el ROI medio es mayor. Confundir ROI medio con marginal es el error más caro del
oficio. Respuesta incompleta si solo describe las curvas sin decir cuál manda en el reparto.
</details>

**P2.** ¿Por qué el modelo identifica video y no search, si search gasta más de media y tiene
mayor ROI verdadero?

<details>
<summary>Referencia</summary>
Porque video se apaga el 55 % de las semanas y tiene un coeficiente de variación de 0,70:
hay semanas con y sin video, y el modelo ve la diferencia. Search es always-on con variación
0,25, así que su efecto se confunde con el baseline. Lo que identifica es la variación del
gasto, no su volumen ni su ROI. El paso 4 lo demuestra: con más variación y el mismo modelo,
el intervalo de search se estrecha. Respuesta incorrecta si atribuye la diferencia al tamaño
del gasto o al ROI.
</details>

**P3.** Un informe de MMM te enseña que display rinde 10,9 por euro, con la verdad (2,9) dentro
del intervalo. ¿Qué le preguntas antes de mover un euro?

<details>
<summary>Referencia</summary>
El intervalo. Si es [1,5 – 167], el modelo no sabe nada de display y la mediana es ruido con
forma de número. La verdad dentro del intervalo es condición necesaria, no suficiente; un
informe que solo muestra la mediana engaña. Segundo nivel, opcional: preguntar por las
divergencias y el ESS del muestreo, porque con Hill por defecto el 89 % de las muestras
tenían error. Respuesta completa si pide el intervalo y explica por qué la mediana sola no vale.
</details>

## 4 · Registrar

Escribe `.progreso/03.md` con el formato del contrato. Además de "me costó" y "quiero
profundizar", apunta la respuesta a esta pregunta abierta, que enlaza con la lección 06
(calibración): **si pudieras hacer un solo experimento para ayudar a este modelo, ¿en qué
canal, y qué harías con el resultado?**

Siguiente lección sugerida: 04 (Meridian, la misma tabla) para ver cómo otro framework
rellena el mismo hueco de información, o 06 (calibración) si ya te pica la pregunta anterior.
