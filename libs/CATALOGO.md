# Catálogo de herramientas de medición de marketing

Índice del terreno. Una fila por herramienta, con nota propia cuando la hemos mirado en
serio. **Estado** dice hasta dónde hemos llegado nosotros, no la madurez del proyecto.

Última revisión del catálogo: **2026-09-04**.

Vídeo: hay un catálogo aparte y verificado en [videos.md](videos.md) — la serie oficial de
Meridian (13 cortos de Google) y lo poco que merece la pena fuera de ella.

## Marketing Mix Modeling (MMM)

| Herramienta | Quién | Lenguaje | Estado | Nota |
|---|---|---|---|---|
| [Meridian](https://github.com/google/meridian) | Google | Python (TF Probability) | probada (exp. 02, 2026-09-05) | [meridian.md](meridian.md) |
| [PyMC-Marketing](https://github.com/pymc-labs/pymc-marketing) | PyMC Labs | Python (PyMC) | probada 2026-09-04 (exp. 01) | [pymc-marketing.md](pymc-marketing.md) |
| [Robyn](https://github.com/facebookexperimental/Robyn) | Meta | R (+ `robynpy` beta) | instalada (R, 2026-09-05) | [robyn.md](robyn.md) |
| [LightweightMMM](https://github.com/google/lightweight_mmm) | Google | Python (NumPyro) | archivada por Google | sustituida por Meridian; solo valor histórico |

Los tres vivos son las tres escuelas: Meridian es bayesiano y opinado, PyMC-Marketing es
bayesiano y abierto de par en par, Robyn es frecuentista/evolutivo (Ridge + optimización
multiobjetivo con Nevergrad). Comparar los tres sobre el mismo dataset sintético es el
experimento vertebral de este repo.

## Experimentos geo e incrementalidad

| Herramienta | Quién | Lenguaje | Estado | Nota |
|---|---|---|---|---|
| [Meridian GeoX](https://github.com/google/meridian-geox) | Google | Python | catalogada · **datos ya disponibles** | [meridian-geox.md](meridian-geox.md) |
| [GeoLift](https://github.com/facebookincubator/GeoLift) | Meta | R | instalada (R, 2026-09-05) · **datos ya disponibles** | [geolift.md](geolift.md) |
| [CausalImpact](https://github.com/google/CausalImpact) / [tfcausalimpact](https://github.com/WillianFuks/tfcausalimpact) | Google / comunidad | R / Python | instalada (R, 2026-09-05) | [causalimpact.md](causalimpact.md) |
| [GeoexperimentsResearch](https://github.com/google/GeoexperimentsResearch) | Google | R | solo referencia | antecesor de GeoX; útil para entender el TBR original |

Esta familia responde a la pregunta que el MMM no puede responder solo: *¿esto fue causa o
correlación?*. Y es la que alimenta la calibración del MMM con priors reales.

Desde el 2026-09-11 hay con qué probarlas: `generators/synthetic_geo_mmm.py` emite el panel de
regiones con un experimento inyectado y el lift verdadero en su `truth.json`. El duelo que pedía
`geolift.md` —mismo panel, mismo efecto, quién lo recupera mejor— ya solo depende de correrlo.

## Encuestas de impacto publicitario

Brand lift, pre/post, atribución autodeclarada. Método en `conceptos/encuestas-de-impacto.md`.

| Herramienta | Quién | Lenguaje | Estado | Nota |
|---|---|---|---|---|
| [balance](https://github.com/facebookresearch/balance) | Meta | Python | probada 2026-09-04 (exp. 05) | [balance.md](balance.md) |
| statsmodels / pingouin | comunidad | Python | usadas en exp. 05 | regresión ajustada, IC, tests; no necesitan nota |
| [xlogit](https://github.com/arteagac/xlogit) | comunidad | Python | por mirar | conjoint / elección discreta: qué atributo o mensaje pesa |
| Generador propio | mmt | Python | funcionando | `generators/synthetic_brand_lift.py`: RCT u observacional, no respuesta, lift por segmento |

## Inferencia causal general (aplicable a marketing)

| Herramienta | Quién | Lenguaje | Estado | Nota |
|---|---|---|---|---|
| [CausalPy](https://github.com/pymc-labs/CausalPy) | PyMC Labs | Python | catalogada | [causalpy.md](causalpy.md) |
| [DoWhy](https://github.com/py-why/dowhy) | Microsoft / PyWhy | Python | por mirar | interfaz unificada + refutación de supuestos |
| [EconML](https://github.com/py-why/EconML) | Microsoft | Python | por mirar | efectos heterogéneos (CATE) |
| [CausalML](https://github.com/uber/causalml) | Uber | Python | por mirar | uplift modeling |

DoWhy/EconML/CausalML son de propósito general: entran cuando la pregunta es a nivel usuario
(¿a quién impactar?), no a nivel canal (¿cuánto invertir?).

## Generación de datos sintéticos

| Herramienta | Quién | Lenguaje | Estado | Nota |
|---|---|---|---|---|
| `generators/synthetic_mmm.py` | nuestro | Python | **funcionando** | adstock + Hill + estacionalidad, con ground truth |
| [AMSS](https://github.com/google/amss) | Google | R | catalogada | [amss.md](amss.md) |
| `generators/synthetic_geo_mmm.py` | nuestro | Python | **funcionando** (2026-09-11) | panel de regiones + experimento con lift verdadero derivado, no declarado |
| `generators/synthetic_ga4.py` | nuestro | Python | pendiente | eventos/sesiones estilo GA4 coherentes con el MMM |

**Todos los datos de este repo son sintéticos**, incluidos los de Google Analytics. No hay
exports reales y no los va a haber: sin ground truth no se puede evaluar un modelo, y con
datos reales nunca hay ground truth.

## Exports MMM de plataforma

Las cuatro grandes entregan datos "preparados para MMM" como fichero, cada uno con su formato.
No son librerías: son fuentes de datos, y cada una tiene un importador al esquema canónico en
`skills/import-<plataforma>-mmm/`. **Cabecera** dice si el contrato de columnas está confirmado
contra documentación oficial; sin contrato confirmado el importador falla a propósito.

| Export | Quién | Cabecera | Estado | Nota |
|---|---|---|---|---|
| [MMM Data Platform](https://developers.google.com/meridian/docs/pre-modeling/using-mmm-data-platform) (Google Ads + DV360) | Google | confirmada 2026-09-07 | importador funcionando | [skills/import-google-mmm/SKILL.md](../skills/import-google-mmm/SKILL.md) |
| [MMM data export](https://developers.facebook.com/docs/marketing-api/insights/marketing-mix-modeling/) (Ads Reporting) | Meta | candidata sin confirmar (columnas de la API, no de la UI) | importador bloqueado, `--trust-unconfirmed` solo para fixtures | [skills/import-meta-mmm/SKILL.md](../skills/import-meta-mmm/SKILL.md) |
| [Media Mix Modeling data](https://ads.tiktok.com/help/article/how-to-pull-media-mix-modeling-mmm-data-in-tiktok-ads-manager) (Ads Manager) | TikTok | sin documentar | importador bloqueado hasta traer una cabecera real | [skills/import-tiktok-mmm/SKILL.md](../skills/import-tiktok-mmm/SKILL.md) |
| [MMM data feed](https://advertising.amazon.com/en-gb/measurement-analytics/marketing-mix-models) (cuenta manager o S3) | Amazon Ads | sin documentar | importador bloqueado hasta traer una cabecera real | [skills/import-amazon-mmm/SKILL.md](../skills/import-amazon-mmm/SKILL.md) |

La skill paraguas [`mmm-import`](../skills/mmm-import/SKILL.md) detecta la plataforma por
cabecera, delega e une la carpeta entera en una sola tabla canónica. Ninguno de estos
importadores lee una API ni convierte moneda: si el export mezcla monedas o anclas semanales,
paran y explican cómo volver a pedirlo.

## Atribución multi-touch (MTA)

| Herramienta | Quién | Lenguaje | Estado |
|---|---|---|---|
| [ChannelAttribution](https://github.com/DavideAltomare/ChannelAttribution) | comunidad | R / Python | por mirar |
| [pathmc](https://pathmc.pymc-labs.com/) | PyMC Labs | Python | por mirar |

Aviso antes de invertir tiempo aquí: la MTA basada en cookies es la parte del terreno que
peor ha envejecido (ITP, consent mode, walled gardens). Está en el catálogo para entender
por qué la industria se movió a MMM + experimentos, no porque vayamos a construir sobre ella.

## Meta-recursos

- [Awesome-Marketing-Science](https://github.com/shakostats/Awesome-Marketing-Science) — lista
  curada de geo testing, MMM, MTA y causal inference. Punto de partida para no reinventar
  este catálogo.
- [Meridian docs](https://developers.google.com/meridian) — la documentación conceptual de
  Google vale aunque no uses Meridian: explica adstock, saturación y calibración mejor que
  la mayoría de los blogs.
