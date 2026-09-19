# Contrato de lección

Cada lección es un directorio `lecciones/NN-<slug>/` con un `LECCION.md` que sigue este
contrato, y opcionalmente dos ficheros más:

```
lecciones/NN-<slug>/LECCION.md      obligatorio
lecciones/NN-<slug>/ejercicios.py   ejercicios verificables (ver §2)
lecciones/NN-<slug>/averia.py       drills de modelo roto (ver §2)
``` El contrato existe para que **cualquier agente de código** (Claude Code, Codex,
Antigravity u otro) pueda dar la lección sin instrucciones específicas de su plataforma: lee
`AGENTS.md`, lee `LECCION.md`, y sabe qué hacer. Los adaptadores por plataforma
(`.claude/commands/leccion.md`, etc.) solo abren la puerta; el protocolo vive aquí.

### Vía Colab

Añadida el 2026-09-08 para el piloto de la lección 03. El notebook generado
permite practicar con progreso local en el runtime; un fork del alumno puede sincronizar solo
`.progreso/`. El tutor, las cuatro secciones, la predicción y la revelación de la verdad no
cambian.

Escrito 2026-09-05. Se corrige a medida que se prueben lecciones con alumnos reales.

## Bienvenida conversacional

Cuando alguien diga que quiere empezar o aprender MMT por primera vez, el agente ofrece una
bienvenida de una pregunta por turno. Pregunta por interés o decisión, perfil previo, objetivo,
disponibilidad y preferencias ordenadas entre visual, conversacional, vídeo corto y vídeo largo.
Se permite “no sé” u omitir. Después de la primera respuesta, aporta una clasificación
provisional (MMM, experimento, encuesta o atribución) y explica también su límite.

Antes de guardar nada, el agente enseña un resumen editable con una ruta inicial, la primera
microacción y por qué encaja. El perfil estructurado se guarda solo si el alumno confirma, en
`.mmt/perfil.json`: es local, ignorado por git y no viaja con `.progreso/` al fork de Colab.
Se consulta con `python3 lecciones/perfil.py --recommend`; no contiene datos reales ni texto
libre por defecto. Sin perfil, el tutor sigue funcionando con la ruta genérica.

Las preferencias cambian la presentación: visual usa esquema textual, conversacional incluye
preguntas socráticas, y vídeo corto/largo ajusta el tamaño de los bloques. MMT no produce
vídeo propio, pero desde el 2026-09-18 mantiene un catálogo verificado de vídeo ajeno en
`libs/videos.md`, con la serie oficial de Meridian a la cabeza: el agente ofrece de ahí lo que
encaje con la lección y nunca inventa un recurso que no esté en esa lista. Ver un vídeo no
sustituye a Practicar, y un vídeo que revele una avería va después del drill, no antes. Ninguna
preferencia cambia prerrequisitos, Explicar → Practicar → Comprobar → Registrar, la predicción
del alumno ni la revelación de la verdad.

## Estructura de `LECCION.md`

```markdown
# NN · Título

**Pregunta que responde:** una frase.
**Antes:** lecciones previas necesarias, o "ninguna".
**Entorno:** qué venv o runtime hace falta y cómo comprobar que está.
**Duración:** estimación honesta.

## 1 · Explicar
## 2 · Practicar
## 3 · Comprobar
## 4 · Registrar
```

Las cuatro secciones son obligatorias y van en ese orden. Cada una tiene un propósito
distinto y el agente las recorre en secuencia.

### 1 · Explicar

Lo que el alumno tiene que entender, escrito para leerse en voz alta. Lenguaje llano,
frases cortas, jerga solo con aclaración la primera vez. Se apoya en `conceptos/` y
`libs/` para el detalle: enlaza, no repite.

El agente lee esta sección al alumno por partes, para y pregunta si hay dudas antes de
seguir. No suelta todo de golpe.

### 2 · Practicar

Una lista numerada de pasos que el alumno ejecuta **con** el agente, no que el agente
ejecuta solo. Cada paso dice:

- **Haz:** un comando concreto o un cambio concreto en un archivo.
- **Mira:** qué debe fijarse en la salida.
- **Piensa:** una pregunta abierta sobre lo que acaba de ver.

Todo lo que se practica corre sobre datos sintéticos con verdad conocida, del directorio
`generators/`. La verdad se compara siempre. Un ejercicio sin verdad conocida no cabe en
este repo.

El agente corre los comandos si el alumno lo pide, pero le pide al alumno que prediga el
resultado antes de correrlos. Si la predicción falla, eso es la lección.

#### Ejercicios verificables

Que el agente juzgue a ojo si el alumno acertó no basta. Cuando la lección tenga una
respuesta objetiva, va en `ejercicios.py` como una lista `EJERCICIOS` de `Ejercicio`, y se
responde por el arnés compartido:

```
python3 lecciones/practica.py NN --listar
python3 lecciones/practica.py NN e1 --valor video
python3 lecciones/practica.py NN --estado
```

Tres reglas al escribir un ejercicio:

1. **El valor esperado se calcula, no se escribe.** Sale del `truth.json` del generador o
   del `summary.json` de un experimento guardado. Si una versión nueva de la librería mueve
   los números, el ejercicio se mueve con ellos en vez de mentir.
2. **Fallar no revela la respuesta.** El mensaje de fallo es una pista que dice dónde
   mirar. El agente tampoco la parafrasea.
3. **Si faltan datos para comprobar, se dice.** El check lanza `NoSePuedeComprobar` con lo
   que falta, y el alumno vuelve al paso de la práctica que lo produce.

`practica.py` es biblioteca estándar: corre en cualquiera de los venvs.

#### Averías

Leer la salida correcta de un modelo enseña poco. Encontrar el fallo en una rota enseña el
oficio. Una lección puede traer `averia.py` con varios defectos, cada uno de los que un
analista comete de verdad: un control ausente, una fuga del objetivo, unidades mal
escaladas, un cruce de tablas desalineado.

```
.venvs/<venv>/bin/python lecciones/NN-<slug>/averia.py --n 2
.venvs/<venv>/bin/python lecciones/NN-<slug>/averia.py --n 2 --revelar
```

El agente elige el número y no lo dice. Enseña la salida, pregunta qué está roto y cómo se
ve, y solo entonces revela. Un defecto que no se distingue en la salida no vale: al escribir
uno nuevo hay que comprobar que su señal aparece.

### 3 · Comprobar

Tres preguntas, ni más ni menos, con una **respuesta de referencia** oculta al alumno en
un bloque `<details>`. El agente hace las preguntas de una en una, en el orden escrito,
evalúa la respuesta contra la referencia y:

- si es correcta en lo esencial, lo dice y pasa a la siguiente;
- si es incompleta, pregunta por lo que falta, sin dar la respuesta;
- si es incorrecta, vuelve a la parte de Explicar que corresponde y repregunta después.

No se avanza a Registrar con preguntas sin responder. El agente no rebaja el listón porque
el alumno tenga prisa.

### 4 · Registrar

Qué escribe el alumno (o el agente en su nombre) en su archivo de progreso, y qué pregunta
abierta se lleva. El progreso vive en `.progreso/<nn>.md`, ignorado por git, con este formato:

```markdown
# NN · Título
- fecha: YYYY-MM-DD
- estado: hecho | a medias | repetir
- me costó: ...
- quiero profundizar: ...
- comprobar: 3/3
- ejercicios: 5/6
```

Además, `practica.py` mantiene solo `.progreso/predicciones.md`: una fila por respuesta, con
lo que el alumno contestó y si acertó. No se edita a mano. Mide la única cosa que importa a
lo largo del curso, que es la calibración: cuántas veces predices bien antes de mirar.

```
python3 lecciones/practica.py --calibracion
```

El acierto **a la primera** es el número real. Bajar en él después de varias lecciones no es
un retroceso: suele significar que los ejercicios ya no son de memoria.

## Protocolo del agente tutor

Al arrancar una lección, el agente:

1. Lee `AGENTS.md`, `lecciones/CONTRATO.md` y el `LECCION.md` de la lección.
2. Comprueba el entorno con lo que dice la cabecera. Si falta, lo instala o explica cómo,
   antes de nada.
3. Mira `.progreso/` para saber qué lecciones hay hechas y si esta está a medias.
4. Recorre las cuatro secciones en orden. Se para en cada "Piensa" y en cada pregunta de
   Comprobar hasta que el alumno responde.
5. Si hay `ejercicios.py`, los responde el alumno por `practica.py` en el punto de la
   práctica que toque. El agente teclea el comando, pero el valor lo pone el alumno.
6. Si hay `averia.py`, corre al menos un drill antes de Comprobar. Elige el número, no lo
   dice, y no revela hasta que el alumno se moje.
7. Al terminar, escribe `.progreso/<nn>.md` y propone la siguiente lección según
   `FORMACION.md`.

Reglas que no se negocian:

- **El alumno teclea o decide; el agente no hace la lección solo.** Si el alumno pide
  "hazlo tú", el agente lo hace pero le pide una predicción antes y una explicación después.
- **La verdad conocida se mira al final, no al principio.** El agente no revela
  `*.truth.json` hasta que el alumno ha visto la salida del modelo.
- **Fechas absolutas.** Las librerías cambian. Toda cifra de una lección lleva la versión
  y fecha con la que se obtuvo. Si el alumno obtiene otra cosa, eso es un hallazgo que
  anotar, no un error del alumno.
- **El agente no revela una respuesta esperada.** Ni la de un `<details>`, ni la de un
  ejercicio, ni la avería que ha elegido. Da pistas y repregunta. Si el alumno se rinde,
  antes de revelar le pide que diga en voz alta qué descartó y por qué.
- **Idioma:** el de la lección (español). Comentarios de código en inglés.
