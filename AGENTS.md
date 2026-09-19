# AGENTS.md — MMT (Marketing Measurement Toolkit)

Sobre medición de marketing de código abierto: marketing mix modeling (MMM), inferencia
causal / incrementalidad, atribución y uso de IA para medir.

**Tres pilares.** No son fases ni prioridades alternativas:
el repo tiene que servir para las tres cosas a la vez, y una pieza que no sirva a ninguna
sobra.

| Pilar | Qué significa | Dónde vive |
|---|---|---|
| **Banco de pruebas** | Cada método se prueba contra verdad conocida y se anota si acierta | `experiments/`, `generators/` |
| **Curso agent-native** | Cualquiera abre el repo con Claude Code, Codex o similar y aprende **y practica** dentro del agente; el tutor es el agente | `lecciones/`, `lecciones/CONTRATO.md` |
| **Lugar de referencia** | Se viene a consultar qué hace cada herramienta, qué asume y dónde miente cada enfoque — aunque no se curse nada | `libs/`, `conceptos/`, `skills/` |

Los tres comparten un cuello de botella: **los generadores de datos sintéticos**. Sin un
generador con verdad conocida no hay experimento que probar, ni práctica que verificar, ni
referencia honesta sobre si un método funciona. Por eso la calidad de `generators/` no es
infraestructura de apoyo: es el trabajo.

Proyecto nuevo (2026-09-04), sin histórico previo. No es una herramienta para los proyectos de
la cartera; si algo demuestra valor, se traslada al proyecto que lo necesite.

## Ámbito

- **Catálogo de herramientas** — índice en `libs/CATALOGO.md` y una nota por herramienta en
  `libs/<nombre>.md`: qué hace, qué supuestos asume, qué datos pide, cómo se instala, qué
  salió al probarla.
- **Conocimiento** — `conceptos/`: los métodos explicados, no la documentación de la
  herramienta. Empieza por `conceptos/mapa-del-terreno.md`.
- **Datos, todos sintéticos** — generadores con *ground truth* conocido en `generators/`,
  **incluidos los datos tipo Google Analytics**. Sin ground truth no se puede evaluar un
  modelo, y con datos reales nunca hay ground truth. Aquí no entran exports reales.
  Aquí no van a llegar datos reales de nadie, así que la obligación es que lo sintético baste: un generador entra cuando
  sirve para **aprender y practicar**, no solo para que un script termine sin error. En la
  práctica eso pide tres cosas de cada generador — que la verdad esté guardada, que el
  fenómeno que enseña se vea en los datos, y que se pueda romper a propósito para que haya
  algo que diagnosticar.
- **Encuestas de impacto** — brand lift, pre/post, atribución autodeclarada, conjoint. Con
  generador propio de individuos y respuestas, igual que el resto. `conceptos/encuestas-de-impacto.md`.
- **Experimentos** — un directorio por prueba en `experiments/<slug>/`, con su conclusión.
- **IA aplicada a la medición** — LLMs para interpretar posteriors, priorizar experimentos,
  automatizar diagnósticos y traducir salidas de modelo a decisiones de negocio.

Fuera de ámbito: montar un producto de medición para clientes, y meter datos reales en el
repositorio. Las skills de `skills/` sí operan sobre datos del usuario en su máquina —esa es
su función como referencia ejecutable— pero el repo no los guarda ni los versiona.

## Estructura

- `libs/CATALOGO.md` — índice de todo el terreno, con el estado de cada herramienta.
- `libs/<nombre>.md` — nota por herramienta (ver plantilla implícita en las ya escritas).
- `libs/repos/` — clones de repos externos para leer código. **Gitignored**: son repos
  ajenos, no se versionan aquí.
- `conceptos/` — el conocimiento en sí: métodos, vocabulario, dónde miente cada enfoque.
- `generators/` — scripts de datos sintéticos. El código sí se versiona.
- `data/synthetic/` — datasets generados. **Gitignored**: se regeneran. Los generadores
  guardan siempre el ground truth junto al CSV.
- `experiments/<slug>/` — un directorio por experimento: notebook o script + `RESULTADO.md`.
- `lecciones/NN-<slug>/LECCION.md` — las lecciones del curso, con el contrato en
  `lecciones/CONTRATO.md`. Junto a él, `ejercicios.py` y `averia.py` cuando la lección los
  tiene; el arnés compartido es `lecciones/practica.py`. `.progreso/` (gitignored) guarda el
  avance del alumno y su registro de predicciones.
- `NOTES.md` — estado vivo: qué se ha probado, qué falta, decisiones.
- `FORMACION.md` — el itinerario del curso, con tabla de Estado. **Al empezar cada sesión,
  leer la tabla y proponer el siguiente módulo** según lo que haya anotado (profundizar donde
  costó, saltar lo dominado, integrar lo que pida en "Lo que va apareciendo").

## Modo tutor (cualquier agente)

Si el usuario pide "dame la lección NN", "quiero aprender X" o invoca `/leccion`, actúa como tutor:
lee `lecciones/CONTRATO.md` y sigue su protocolo con el `LECCION.md` correspondiente. Las
reglas duras están ahí (el alumno decide, la verdad se mira al final, comprobar antes de
registrar). Codex y otros agentes leen esto directamente; Claude Code tiene además el
comando `.claude/commands/leccion.md`, que solo apunta aquí.

La vía Colab conserva ese protocolo: el
progreso es local salvo que el alumno elija sincronizar únicamente `.progreso/` con su fork.

La práctica no la juzga el agente a ojo. Hay tres piezas, descritas en el contrato:

- `lecciones/practica.py` — arnés de ejercicios verificables. El valor esperado se calcula
  desde el `truth.json` o desde el `summary.json` de un experimento, nunca se escribe a mano,
  y un fallo devuelve pista, no respuesta. Solo biblioteca estándar.
- `lecciones/NN-*/averia.py` — modelos rotos a propósito para que el alumno diagnostique.
  El agente elige el número, no lo dice, y no revela hasta que el alumno se moja.
- `.progreso/predicciones.md` — registro automático de cada respuesta. `practica.py
  --calibracion` da el acierto a la primera, que es la habilidad que mide el curso.

## Entorno Python

**`./setup.sh` monta todo el entorno** (idempotente; `--check` solo verifica, `--r` añade los
paquetes de R, `--robyn` el venv opcional de robynpy, `--only <familia>` una sola). Es lo primero
que corre cualquier agente antes de dar una lección si la comprobación de la cabecera falla.
Lo que sigue explica qué hace y por qué.

`uv` es el gestor. Base común (pandas, numpy, matplotlib, jupyter) en el `.venv` del
proyecto: `uv sync` (con `uv.lock` versionado).

Extras que no vienen como dependencia: `nutpie` (sampler para PyMC-Marketing), `h5netcdf` +
`h5py` (guardar modelos).

**Las librerías grandes NO van todas en el mismo venv.** Meridian arrastra TensorFlow
Probability y PyMC-Marketing arrastra PyTensor/PyMC; conviven mal y las resoluciones de
dependencias se pelean. Un venv por familia:

```
uv venv .venvs/meridian --python 3.12   # google-meridian (+ meridian-geox, tfcausalimpact cuando entren)
uv venv .venvs/pymc     --python 3.12   # pymc-marketing, nutpie (+ causalpy cuando entre)
uv venv .venvs/robyn    --python 3.12   # robynpy (beta, opcional)
uv venv .venvs/surveys  --python 3.12   # balance, statsmodels, pingouin (encuestas)
```

`setup.sh` instala solo lo que alguna lección usa hoy; las librerías entre paréntesis están
documentadas en `libs/` y entran en el script cuando una lección las necesite.

## Skills (mmm-*)

Las skills MMM viven de forma canónica en `skills/<nombre>/SKILL.md`. Hoy son ocho: las tres
del esquema (`mmm-ready-schema`, `mmm-data-validate`, `mmm-data-diagnose`) y las cinco de
ingesta (`import-google-mmm`, `import-meta-mmm`, `import-tiktok-mmm`, `import-amazon-mmm` y la
paraguas `mmm-import`, que detecta la plataforma por cabecera y une una carpeta entera). Se
invocan directamente con el `.venv` base:
`python3 skills/<nombre>/<script>.py --input <csv> ...`, sobre datos del usuario fuera del repo.
Claude Code las descubre por el symlink `.claude/skills/<nombre>`; Codex no tiene mecanismo de
skills y las descubre leyendo esta misma sección. Cada `SKILL.md` explica la entrada, la salida
y los códigos de error de su script.

Los importadores comparten `skills/_lib/` (guarda de rutas, contratos de cabecera, salida
canónica, resampleo). Cada plataforma declara sus columnas en `expected_headers.json` con un
flag `confirmed`: solo Google lo tiene a `true`, así que Meta, TikTok y Amazon fallan a
propósito con "sin cabecera confirmada" hasta que alguien pegue la cabecera de un export real.
No es un bug — es el diseño, y cerrarlo son cinco minutos con el fichero delante.

Los generadores de datos son numpy/pandas puro a propósito: corren en cualquiera de los venvs.

**R también hace falta.** Robyn (la versión fiable), GeoLift y AMSS son R, sin port oficial
usable. No es opcional si se quiere cubrir el catálogo entero. `./setup.sh --r` instala los
paquetes (con la cadena archivada de CRAN fijada por versión) pero no R en sí: eso es `apt`.

## Reglas de trabajo

1. **Toda herramienta probada deja nota en `libs/<nombre>.md`** y fila en `libs/CATALOGO.md` —
   incluido lo que salió mal. Una librería que no se pudo instalar es información valiosa,
   no un fracaso que ocultar.
2. **Todo experimento acaba en `experiments/<slug>/RESULTADO.md`** con la conclusión en la
   primera línea. Sin conclusión escrita, el experimento no ha terminado.
3. **Datos sintéticos con ground truth guardado** — el generador escribe siempre el JSON de
   parámetros reales junto al CSV. Comparar recuperación vs. verdad es el punto entero.
4. **Fechas absolutas** (YYYY-MM-DD) en versiones y notas: las librerías de este espacio se
   mueven rápido y una nota sin fecha caduca en silencio.
5. **Cifras en euros** cuando haya dinero de por medio (preferencia global). Los datasets de
   ejemplo de las librerías vienen en dólares: anotarlo, no convertir a la ligera.
6. **Nada de datos reales en el repositorio.** Las skills de `skills/` operan sobre datos del
   usuario en su máquina, en rutas ignoradas por git (o pasadas con `--allow-tracked` de forma
   explícita); las credenciales nunca entran en el repo.

## Contexto

- **Idioma:** notas y documentos en español; comentarios de código y commits en inglés.
- **Repo:** público, `sixsevenappslab/mmt`.
