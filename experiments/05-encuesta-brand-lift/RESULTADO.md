# 05 · Encuesta de brand lift contra la verdad conocida

**Conclusión:** con exposición aleatorizada (holdout real), la diferencia simple de
proporciones recupera el lift verdadero (7,22 vs 7,21 pp) y ni la reponderación ni el ajuste
por covariables aportan nada. Con exposición observacional (quien ve el anuncio se parece a
quien ya iba a decir que sí), la misma diferencia simple infla el lift un 60 % (12,4 vs 7,8 pp),
la reponderación a población **no lo arregla** y el ajuste por regresión sí (7,3 pp). Con el
tamaño típico de un estudio (2000 respuestas), el estudio observacional sale "significativo"
el 100 % de las veces y cubre la verdad el 38 %.

Fecha: 2026-09-04 · `balance` 0.23.0 · statsmodels · venv `.venvs/surveys`.

## Qué se hizo

- Generador: `generators/synthetic_brand_lift.py`. Población de 200.000 personas con
  covariables (edad, uso digital intensivo, cliente actual); exposición aleatoria al 50 %
  (`brandlift_rct`) o dependiente de las covariables (`brandlift_obs`); resultado "sí"
  con baseline por covariables y lift verdadero de 6 pp (9 pp en usuarios digitales
  intensivos); respuesta a la encuesta del 8 %, más alta en mayores y clientes, más baja en
  digitales, y un poco más alta entre expuestos. Solo los ~19.000 respondientes llegan al CSV,
  más una muestra de referencia de la población con covariables (lo que daría un censo).
- Cuatro estimadores en `run.py`: ingenuo, ajustado (logit con covariables, efecto medio en
  expuestos), reponderado (IPW a la referencia con `balance`) y ambos. Más el lift por
  segmento y 200 submuestras de 2000 respuestas.

## Resultados (puntos porcentuales de "sí")

| | RCT (verdad ATT 7,21) | Observacional (verdad ATT 7,79) |
|---|---|---|
| ingenuo | 7,22 ± 1,33 | **12,37** ± 1,33 |
| ajustado (logit) | 6,85 | 7,29 |
| reponderado (`balance`) | 7,26 ± 1,36 | **12,43** ± 1,36 |
| ambos | 6,87 | 7,38 |
| segmento digital=0 (verdad 6,0) | 6,08 ± 1,52 | 6,69 ± 1,61 |
| segmento digital=1 (verdad 9,0) | 9,64 ± 2,62 | 9,77 ± 3,02 |
| n = 2000: lift medio ± IC | 7,16 ± 4,10 | 12,37 ± 4,10 |
| n = 2000: IC excluye 0 / cubre la verdad | 94 % / 96 % | 100 % / 38 % |

## Lo que se aprende

1. **La aleatorización lo es todo.** Es la diferencia entre un estimador ingenuo correcto y
   uno un 60 % inflado, con los mismos datos, la misma encuesta y el mismo tamaño. Los brand
   lift de plataforma (Meta, Google, YouTube) valen porque el holdout lo fija la plataforma
   antes de servir el anuncio. Un "expuestos vs no expuestos" reconstruido después es lo
   segundo.
2. **Reponderar arregla quién responde, no quién fue expuesto.** `balance` hace bien su
   trabajo (los pesos devuelven la composición de la población) y aun así el estimador
   observacional sigue inflado: el sesgo de confusión vive dentro de cada estrato, entre
   expuestos y control. Para eso hace falta ajustar o emparejar por covariables, y solo
   funciona si las covariables que mueven la exposición están medidas. Aquí lo están todas;
   en la realidad, nunca.
3. **El sesgo de no respuesta aquí es pequeño en el lift aunque grande en la muestra.** Los
   digitales intensivos son el 40 % de la población y el 29 % de los respondientes, y son
   quienes tienen más lift; aun así el ingenuo del RCT acierta, porque el lift es parecido en
   los dos grupos y el pequeño empuje "expuesto → responde más" compensa. Es suerte del
   diseño, no una regla. Con lifts muy distintos por segmento, reponderar sí importaría.
4. **El ajuste por logit responde a otra pregunta.** Estima el lift entre los expuestos que
   respondieron (6,85 en RCT, coherente con la composición de los respondientes), no en la
   población (7,21). Y modela el lift como multiplicativo cuando el generador lo hizo aditivo:
   -0,4 pp de error por forma funcional. Pequeño, pero conviene saber de dónde viene.
5. **2000 respuestas dan ± 4 pp.** Para un lift de 7 pp el IC va de 3 a 11: se ve que hay
   efecto, no cuánto. Para lifts de 2–3 pp, típicos en consideración de marcas grandes, un
   estudio de ese tamaño no distingue el efecto de cero. Y en el caso observacional sale
   significativo siempre y acierta un 38 %: la significancia no protege del sesgo.

## Siguiente

- Lift heterogéneo fuerte (por ejemplo 0 pp en un segmento, 15 en otro) para que la no
  respuesta sí muerda y `balance` sea necesario en el RCT.
- Covariable no medida en el observacional: cuánto queda del sesgo cuando el ajuste no puede
  ver lo que mueve la exposición. Es la situación real.
- Pre/post sin control y atribución autodeclarada ("cómo nos conociste"): añadir ambas al
  generador y medir cuánto se equivocan. Ver `conceptos/encuestas-de-impacto.md`.
