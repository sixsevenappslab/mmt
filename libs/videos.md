# Vídeos: qué merece la pena ver, y para qué lección

Catálogo curado de vídeo. Misma regla que `libs/CATALOGO.md`: una fila por recurso, con quién
lo publica, cuánto dura y **qué lección sirve**. Lo que no aporta, se dice que no aporta, y se
queda en la lista de rechazados con el motivo.

**Última revisión: 2026-09-18.**

## Cómo se revisa un vídeo antes de entrar aquí

Un enlace que sale en una búsqueda no es una fuente verificada. Dos de las búsquedas que
hicimos devolvían como "oficiales" vídeos de canales personales. El filtro tiene tres pasos y
los tres dejan rastro:

1. **Ficha comprobada.** Título, canal, duración y fecha se leen de YouTube, no del resultado
   de búsqueda. Un vídeo sin ficha comprobable no entra.
2. **Contenido leído.** Se descarga la transcripción y se lee. Sin esto no se puede distinguir
   una clase de método de un tutorial de interfaz, y desde fuera se parecen mucho: el tutorial
   de Brand Lift de Google usa el vocabulario correcto durante cuatro minutos y lo único que
   enseña es dónde hacer clic.
3. **Veredicto: ¿método o producto?** Entra lo que explica **por qué** funciona algo o **cómo**
   falla. Se rechaza lo que explica dónde está el botón, lo que vende una función concreta y lo
   que documenta un producto que ya no existe.

Lo que no se ha podido revisar así se marca **sin revisar**, en vez de colarlo como bueno.

## Cómo encaja el vídeo en este curso

Un vídeo no sustituye a la práctica. Aquí la habilidad se mide por lo que predices antes de
mirar (`lecciones/practica.py --calibracion`), y eso no se entrena viendo a alguien acertar.

- **El vídeo va antes de Explicar o después de Registrar, nunca en medio de Practicar.**
- **Un vídeo que explica una avería va después del drill.** Dos de la serie oficial la
  resuelven entera; ver `Knots in Meridian` antes de diagnosticar deja el ejercicio sin medir
  nada.
- **Ninguna lección exige ver nada.**
- **Las cifras del vídeo no son las tuyas.** Los vídeos oficiales no dicen versión. Las
  nuestras son de google-meridian 2.0.0 (2026-09-05).

## Serie oficial de Meridian (Google Analytics)

Playlist: [Meridian](https://www.youtube.com/playlist?list=PLI5YfMzCfRtYvZ9AYp1wrtBM4apIsDc1i) ·
13 vídeos · canal **Google Analytics** · publicados 2026-03-31 salvo donde se indique.

Cortos, uno por concepto, hechos por el equipo de la librería. Es el mejor material de vídeo que
existe hoy sobre Meridian. Las descripciones de abajo salen de leer la transcripción, no la
ficha.

| Vídeo | Dura | Sirve para | Qué dice de verdad |
|---|---|---|---|
| [Intro to Priors](https://www.youtube.com/watch?v=v5S5jSholZI) | 2:17 | **Lección 04, §1** | Por qué existen los priors: estabilizan datos ruidosos y meten conocimiento de negocio ("es raro un ROI mayor que seis en mi sector"). Ojo al sesgo, abajo. |
| [Treatment Prior Types](https://www.youtube.com/watch?v=brriIvu2TLY) | 4:30 | **Lección 04, pasos 2–4** | ROI, mROI y contribución, y cuándo usar cada uno. Nuestras tres variantes son dos de estos tres. |
| [Controls, Mediators and Treatments](https://www.youtube.com/watch?v=rg-CL4hdD5o) | 7:09 | **Lección 03, tras las averías** · módulo 7 | Lo mejor de la serie. Enseña el DAG, distingue confusor, predictor y **mediador**, y dice que meter "visitas a la web" como control bloquea el camino causal: es palabra por palabra nuestra avería 2. |
| [Knots in Meridian](https://www.youtube.com/watch?v=gP-mI82bpAE) | 5:25 | **Lección 04, tras la avería 1** | El spline del baseline y la interpolación entre nudos. Dice explícitamente qué pasa con un solo nudo, que es nuestra avería. Verlo antes la regala. |
| [Adstock and Hill](https://www.youtube.com/watch?v=_RkeKEZ1s_M) | 5:51 | **Lección 03, §1** | Las dos transformaciones, primero con un ejemplo (unos auriculares que no compras esa tarde) y luego con la fórmula. También explica `max_lag`. |
| [Geo Vs National Level Modeling](https://www.youtube.com/watch?v=apaWURDjGX4) | 4:47 | **Lección 04, P3** · módulo 5 | Sin pooling, pooling completo y pooling parcial, con el ejemplo de cuatro ciudades. Responde nuestra P3 entera. |
| [Calibrate Treatment Priors](https://www.youtube.com/watch?v=TtM2pNDHRSI) | 3:09 | **Módulo 6** | Cómo entra el resultado de un experimento como prior. El bucle del curso en tres minutos. |
| [Incremental Outcome, ROI, mROI, and Response Curves](https://www.youtube.com/watch?v=3GJ5PieyDIc) | 3:47 | `conceptos/mapa-del-terreno.md` | ROI medio contra ROI marginal, que es el error más caro del oficio. |
| [Demo of Meridian](https://www.youtube.com/watch?v=GXC8D0SMHMc) | 5:32 | Lección 04, §2 | El flujo de la librería de principio a fin. Nuestro `run.py` hace lo mismo con otra cara. |
| [Intro to Meridian](https://www.youtube.com/watch?v=L2QmrfCVnBQ) | 3:46 | Opcional, antes de §1 | Posicionamiento, no método: qué es un MMM y por qué resiste sin cookies. Cuatro minutos agradables con poca sustancia. |
| [Scenario Planner Overview](https://www.youtube.com/watch?v=X3ksrQ1U1SI) (2026-08-05) | 7:37 | `libs/meridian.md` | **Sin revisar** (no leímos la transcripción). La interfaz sin código. |
| [Partner Stories: Digitl](https://www.youtube.com/watch?v=K2-ihLvakNI) (2026-06-10) | 40:41 | Opcional | Caso de agencia. Cuarenta minutos para lo que los cortos dicen en cinco. |
| [Caso Akulaku](https://www.youtube.com/watch?v=Z5CMNyewzRE) (2025-10-22) | 2:21 | Saltable | Pieza de marketing con una cifra de resultado. Sin método dentro, y sin subtítulos que permitan comprobarlo. |

**Dónde discrepamos de la serie oficial.** `Intro to Priors` presenta el prior como una virtud:
estabiliza, aporta contexto de negocio, da confianza a los jefes. Todo cierto. Lo que no dice es
el otro lado, que es el que enseña la lección 04: cuando los datos no identifican un canal, el
prior **no ayuda a la estimación, es la estimación**, y un intervalo estrecho puede ser
simplemente una opinión firme. Ver el vídeo y la lección en ese orden funciona bien; al revés,
también, pero no te quedes solo con el vídeo.

## Incrementalidad y experimentos

Lo que pedía el módulo 5 y el experimento 06. Aquí lo oficial es flojo y lo bueno viene de
charlas de conferencia.

| Vídeo | Canal | Dura | Fecha | Veredicto |
|---|---|---|---|---|
| [Google Ads Tutorials: Conversion Lift](https://www.youtube.com/watch?v=-ZoAazB-_cE) | Google Ads | 4:52 | 2022-12-01 | **Los dos primeros tercios valen.** Define incrementalidad, tratamiento y control, y la diferencia entre repartir por usuarios o por geografía. Encuadra las tres familias igual que `mapa-del-terreno.md`. El último tercio es montar el estudio en la interfaz: ahí ya puedes parar. |
| [Measuring Media Impact: Practical Geo-Lift Incrementality Testing](https://www.youtube.com/watch?v=azVyCKvOBHs) | PyData | 36:01 | 2025-12-15 | **Recomendado para el módulo 5.** Por qué hace falta geo-lift cuando ya no se puede seguir al usuario, y el "espejismo de la atribución": la plataforma que se corrige su propio examen. |
| [Geo Experimentation at ASOS](https://www.youtube.com/watch?v=ZoRVrurPnnw) | Data Science Festival | 34:40 | 2023-06-24 | **El más denso en método de todos.** Diseño geo en una empresa real: por qué la región y no el usuario (interferencia entre personas que se conocen, la hipótesis SUTVA), cómo elegir la granularidad y qué requisitos tiene que cumplir cada geo. |
| [Using Causal thinking to make Media Mix Modeling](https://www.youtube.com/watch?v=JDw0RGnV2kg) | PyData | 27:06 | 2025-10-05 | **Recomendado para los módulos 3 y 6.** De un principal data scientist de PyMC Labs. Llama al MMM "una regresión glorificada", y para demostrarlo **se fabrica un dataset simulado con contribuciones conocidas**, que es exactamente lo que hace este repo. Su frase para el módulo 6: la calibración no es magia, son matemáticas. |
| [Geo Experiments and Causal Impact in Incrementality Testing](https://www.youtube.com/watch?v=KEhJNM5K73A) | PyData | 34:32 | 2019-11-30 | Secundario. Caso real de HelloFresh con CausalImpact. Sigue valiendo para la intuición; es de 2019. |
| [A Bayesian Approach to Media Mix Modeling](https://www.youtube.com/watch?v=UznM_-_760Y) | PyMC Developers | 29:39 | 2020-11-01 | Secundario. MMM bayesiano en PyMC3, antes de que existiera PyMC-Marketing. Valor histórico y de estructura del modelo. |
| [Attribution, incrementality & MMM: the modern measurement trifecta](https://www.youtube.com/watch?v=33cFdnC6k9A) | Google Ads | 29:44 | 2026-09-02 | **Contexto, no método.** Entrevista a un director de producto de medición. Las tres familias como piezas complementarias, con la analogía del avión. La mitad va de producto (Meridian Studio en Google Cloud, "qualified future conversions"). Útil para saber qué cuenta Google en 2026. |

Sin revisar todavía: [Bayesian Marketing Science, de Thomas Wiecki](https://www.youtube.com/watch?v=RY-M0tvN77s)
(PyData, 30:35, 2023-06-20), del fundador de PyMC Labs.

## Otros, ya citados en las lecciones

| Vídeo | Canal | Dura | Fecha | Veredicto |
|---|---|---|---|---|
| [Bolt's Evolution towards MMM with PyMC](https://www.youtube.com/watch?v=djXoPq60bRM) | PyMC Labs | 66:03 | 2023-08-17 | Lección 03, opcional. Cómo una empresa real llegó al MMM. De 2023: la API que enseña ya no es la de 1.1.0. |
| [Google CausalImpact vs Meta GeoLift](https://www.youtube.com/watch?v=NqMeRRTkGJk) | Marketing Analytics With Kisholoy | 36:10 | 2025-06-30 | Módulo 5 y `experiments/06-geo-vs-verdad/`. Es el duelo que tenemos pendiente, con otro dataset. De un tercero: contrástalo con nuestra verdad conocida. |
| [Full Python Tutorial: Bayesian MMM](https://www.youtube.com/watch?v=lJ_qq_IVUgg) | Matt Dancho (Business Science) | 122:24 | 2024-03-25 | Solo si quieres una sesión larga guiada. Dos horas y de 2024: cuenta con que el código no corra tal cual. |
| [Ep. 2 Incrementality Testing: GeoLift](https://www.youtube.com/watch?v=OYwoR5GVXPs) | Cassandra | 11:48 | 2022-06-10 | Con reservas. De 2022 y GeoLift ha cambiado; sirve para la intuición del diseño geo, no para copiar código. |
| [How Liquid Death measures incrementality](https://www.youtube.com/watch?v=JOG-W_XrFkY) | Google Ads | 1:33 | 2025-05-21 | Motivación del módulo 5. Minuto y medio de por qué se hacen experimentos. Sin método. |

## Revisados y rechazados

Se anotan para que nadie los vuelva a proponer, y porque el motivo enseña algo.

| Recurso | Canal | Por qué no |
|---|---|---|
| [Google Ads Tutorials: Brand Lift](https://www.youtube.com/watch?v=3XcHw9ZoyvM) (4:40, 2025) | Google Ads | Parecía el vídeo del módulo 2. Es un tutorial de interfaz: ve a Objetivos, Medición, pulsa el botón más. Ni una palabra de la metodología de la encuesta, que es lo único que nos interesa. |
| [Experiments to test uplift of Performance Max](https://www.youtube.com/watch?v=Jkkp2l00TEs) (5:52, 2023) | Google Ads | Anuncio de un tipo de campaña con forma de tutorial de experimentos. El dato que repite es de venta, no de método. |
| [Measuring Reach & Frequency with Brand Report](https://www.youtube.com/watch?v=EZ9tYKDSdbY) (2:27, 2025) | Google Ads | Cero términos de método en toda la transcripción. Es un recorrido por un informe. |
| Playlist *Measure Matters* (13 vídeos, 2018) | Google Analytics | Programas en directo de 30–40 minutos sobre machine learning y Data Studio. Ocho años y sobre productos que ya no existen así. |
| Playlist *TV Attribution Fundamentals* (2017) | Google Analytics | Manejo de Google Attribution 360, producto descontinuado. Llega a explicar cómo formatear el fichero de spots de televisión. |
| Playlist *How to use Google Surveys* (2018) | Google Analytics | Google Surveys está cerrado. Documentación de un producto muerto. |
| [Inside Google Marketing: Attribution & Incrementality](https://www.youtube.com/watch?v=9mDMqYM_Img) (10:55, 2021) | Google Ads | Sobre el fin de las cookies, desde 2021. El vídeo de la trifecta de 2026 lo cubre y está al día. |

## Qué no hemos encontrado

- **Nada oficial en serie sobre PyMC-Marketing.** Hay charlas sueltas y buenas, no una serie por
  concepto como la de Google. Corrige lo que decía este fichero el 2026-09-18 por la mañana: sí
  hay material de calidad de PyMC Labs, en formato charla de conferencia.
- **Nada bueno sobre encuestas de impacto** (módulo 2) **ni sobre conjoint** (módulo 9). Lo
  oficial de Google sobre brand lift son tutoriales de interfaz; lo demás son piezas comerciales
  de proveedores de paneles. Sigue siendo un hueco.
- **Nada sobre `balance`, CausalPy ni `meridian-geox`** más allá de menciones dentro de charlas
  más generales.

Si aparece algo, entra con su fila y sus tres pasos de verificación. Lo que salió mal también
se anota.
