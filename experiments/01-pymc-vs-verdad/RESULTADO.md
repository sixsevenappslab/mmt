# 01 · PyMC-Marketing contra la verdad conocida

**Conclusión:** PyMC-Marketing recupera bien el único canal con gasto muy variable (video:
error del ROI < 10 % e intervalo estrecho) y no permite decidir nada sobre los otros tres:
sus intervalos de ROI van de 3× a 100× de ancho, con la verdad dentro pero inútiles. La
saturación Hill, que es la misma forma funcional que generó los datos, resulta la peor opción
con las priors por defecto (89 % de draws con error en el logp); la saturación logística por
defecto muestrea limpia, clava la cuota de baseline y se equivoca en social por un factor 2.

Fecha: 2026-09-04 · PyMC-Marketing 1.1.0 · PyMC 6.2.0 · nutpie · CPU (16 núcleos, sin GPU).

## Qué se hizo

- Datos: `data/synthetic/base.csv` (156 semanas, 4 canales, seed 42) con
  `base.truth.json`. Generador: `generators/synthetic_mmm.py`.
- Modelo: `MMM` con adstock geométrico (`l_max=12`, parametrización half-life), saturación
  según variante, estacionalidad anual (2 Fourier), controles `price_index` y una tendencia
  lineal añadida a mano (el modelo no trae componente de tendencia y el KPI sube un 30 % en
  tres años; un analista la vería y la pondría).
- Tres variantes, mismo dato, mismo sampler (4 cadenas × 2000 tune + 2000 draws,
  `target_accept=0.95`):
  - `hill-default`: Hill con priors por defecto de la librería. Misma forma que el generador.
  - `logistic-default`: saturación logística, la de los ejemplos oficiales.
  - `hill-informed`: Hill con `kappa ~ Beta(2,2)` (gasto escalado a [0,1]) y
    `slope ~ Gamma(mu=1.5, sd=0.5)`.
- Script: `run.py`. Resultados por variante en `results/<variante>/` (`summary.json`,
  `roi_vs_truth.csv`, `diagnostics.csv`; el `model.nc` no se versiona).

## ROI recuperado (unidades de KPI por €)

Mediana y intervalo central del 94 %. Verdad: search 5,36 · social 5,50 · video 4,53 ·
display 2,91.

| Canal | hill-default | logistic-default | hill-informed |
|---|---|---|---|
| search (5,36) | 7,98 [0,8 – 50] | 4,56 [1,6 – 12,4] | 5,88 [1,7 – 25,5] |
| social (5,50) | 11,75 [1,8 – 85] | 2,91 [1,4 – 5,4] **verdad fuera** | 3,41 [1,4 – 9,2] |
| video (4,53) | 4,15 [2,8 – 5,8] | 4,43 [3,3 – 5,8] | 4,30 [2,9 – 5,9] |
| display (2,91) | 10,88 [1,5 – 167] | 5,10 [1,9 – 11,8] | 5,66 [1,9 – 16,1] |
| cuota baseline (75,1 %) | 33,6 % [-86 – 83] | 78,1 % [63 – 85] | 73,8 % [36 – 84] |
| suma de medianas de medios (24,9 %) | 41,2 % | 21,3 % | 24,6 % |

Diagnósticos:

| | hill-default | logistic-default | hill-informed |
|---|---|---|---|
| divergencias / 8000 | 7139 | 0 | 4507 |
| r_hat máx | 1,08 | 1,004 | 1,011 |
| ESS bulk mín | 51 | 1403 | 452 |
| muestreo | 36 s | 31 s | 42 s |

Adstock (decay alpha, igual en las tres variantes): video 0,70 → 0,71 [0,61 – 0,80]. Los
otros tres, intervalo [0,03 – 0,7]: no aprende nada del carryover de search, social ni display.

## Lo que se aprende

1. **Lo que identifica un canal es la variación de su gasto, no su tamaño.** Video está
   apagado el 55 % de las semanas y con CV 0,70: es el único canal cuyo ROI, adstock y
   saturación se recuperan con intervalo estrecho, en las tres variantes. Search es
   always-on con CV 0,25 y el modelo no lo separa del intercept. Esto es el argumento entero
   a favor de los experimentos (geo-holdouts, apagados) como fuente de variación: el
   experimento 04 (calibración con prior) va exactamente de eso.
2. **Con la verdad dentro del intervalo y el intervalo inútil, un MMM "correcto" no sirve
   para decidir.** Con 3 años de datos y priors por defecto, el modelo dice que display
   rinde entre 1,5 y 167 por euro. No es un fallo del método: es la información que hay.
   Un informe que solo enseñe la mediana (10,9, casi 4× la verdad) engaña.
3. **Usar la forma funcional verdadera no garantiza nada.** Hill con priors por defecto es
   la peor variante (una parte por el bug numérico con gasto cero, ver abajo, pero no
   solo). Sus tres parámetros por canal, todos `HalfNormal(1,5)`, admiten curvas
   degeneradas (pendiente ≈ 0 en el 12–37 % de los draws) que hacen la contribución del canal
   casi constante e indistinguible del intercept: de ahí la cuota de baseline con intervalo
   [-86 %, 83 %]. Las priors informadas arreglan la cuota de baseline pero no la
   incertidumbre de los canales always-on.
4. **La saturación logística es la opción práctica.** Dos parámetros por canal, cero
   divergencias, ESS > 1400, baseline clavada. Su error grande (social a la mitad, display
   casi el doble) es sesgo por forma funcional, que Hill no tiene, pero que el ancho de
   intervalo de Hill oculta igual.
5. **Tiempo de muestreo: irrelevante.** 30–40 s por ajuste completo en CPU con nutpie. Hay
   margen de sobra para validación cruzada temporal, sensibilidad a priors y bootstrap de
   datasets sintéticos.

## Lo que salió mal (y cómo se resolvió)

- **El sampler por defecto de PyMC abortó dos veces** con `Chain 2 failed with: 0 < alpha <= 1`
  en los primeros pasos del tuning (seed 42), tanto con adstock parametrizado por alpha como
  por half-life. El check de PyMC-Marketing está marcado como no sustituible por `-inf`, así
  que un NaN transitorio en la trayectoria tira la cadena entera. **nutpie** (`nuts_sampler=
  "nutpie"`) lo trata como divergencia y sigue. Es la vía a usar aquí.
- **Las divergencias de Hill son errores de evaluación del logp** (`Logp function returned
  error code: 3` en 7138 de 7139), no divergencias por energía. **Causa: las semanas con
  gasto exactamente cero.** Sustituyendo los ceros por 1 € (`hill-default`, mismo seed,
  1000+1000) las divergencias pasan de 7139 a 0, con ESS mín 497 y r_hat 1,01. El gradiente
  de la fórmula de Hill en `x = 0` es finito en PyTensor puro, así que el fallo está en la
  ruta que compila nutpie (xtensor → numba), no en la matemática. Los ROI con el suelo de
  1 € siguen igual de anchos (display 12,8 [1,4 – 199]): el problema de identificación es
  real y separado del numérico. Workaround práctico: suelo de 1 € en canales con flighting,
  o saturación logística. Pendiente: reproducir en aislamiento y abrir issue en
  pymc-marketing.
- `mmm.save()` necesita `h5netcdf` + `h5py`, que no vienen como dependencia.

## Siguiente

- `02-meridian-vs-verdad/`: mismos datos, misma tabla. La comparación que importa.
- `04-calibracion-experimento/`: inyectar el ROI verdadero de video (el canal "medido con
  experimento") como prior y ver si estrecha search y social. Este experimento dice que sí
  debería, porque el problema es de identificación, no de ruido.
- Sensibilidad: repetir `logistic-default` con 5 seeds del generador para separar sesgo
  de forma funcional de azar del dataset.
