# GeoLift (Meta) — lift geo por control sintético

**Repo:** https://github.com/facebookincubator/GeoLift · **Docs:** https://facebookincubator.github.io/GeoLift/
**Estado en mmt:** instalada en R (2.7.5, 2026-09-05), no probada todavía.
**Última verificación de datos:** 2026-09-04 (v2.6.06, 2026-05-19; activo). Licencia MIT.

## Qué es

El equivalente de Meta a Meridian GeoX: metodología end-to-end de experimentos geo, pero
apoyada en **Synthetic Control Methods** en vez de time-based regression. En vez de comparar
test contra un grupo de control elegido, construye un "control sintético" como combinación
ponderada de las regiones no tratadas que mejor reproduce la serie del test antes del
experimento.

Como GeoX, cubre diseño y análisis:

- **Power calculators** que simulan el test antes de gastar: qué mercados tratar, cuánto
  presupuesto, qué efecto serías capaz de detectar.
- **Inferencia y gráficos** para leer el resultado.

## GeoLift vs. Meridian GeoX

Es la comparación interesante de esta familia y no tengo una respuesta prestada que copiar:

| | GeoLift | Meridian GeoX |
|---|---|---|
| Inferencia | Synthetic Control | Time-Based Regression + inferencia placebo |
| Lenguaje | R | Python |
| Casa | Meta | Google |
| Diseños | selección de mercados por power simulation | holdback, go-dark, heavy-up, multi-celda |

El control sintético es más flexible cuando las regiones no son comparables entre sí; el TBR
es más simple y más difícil de sobreajustar. Cuál gana depende de los datos, y es medible:
mismo panel geo sintético, mismo efecto inyectado, quién lo recupera mejor.

## Requisitos e instalación

R ≥ 4.0. No hay port oficial a Python. **Instalada en la máquina de pruebas el 2026-09-05** (R 4.3.3,
paquetes en `~/R/library`), pero no con `remotes::install_github` a secas: dos dependencias
ya no están en CRAN y hay que traerlas a mano, en este orden y con versión fijada.

- `augsynth` (control sintético aumentado) nunca estuvo en CRAN:
  `remotes::install_github("ebenmichael/augsynth")` → 0.2.0.
- `Boom`, `BoomSpikeSlab` y `bsts` (la cadena de CausalImpact / MarketMatching, que GeoLift
  importa) fueron archivados de CRAN. `remotes::install_version("Boom")` **sin versión baja
  la más antigua del archivo** (0.9, de 2013, que ni compila con el Boost actual). Con
  versión sí: `Boom 0.9.15`, `BoomSpikeSlab 1.2.6`, `bsts 0.9.10`.
- Boom compila C++ durante un buen rato. Sin `MAKEFLAGS=-j12` va a un hilo y no acaba en
  10 minutos; con él sí (no medido con precisión, del orden de minutos).
- Después, `install.packages(c("CausalImpact","MarketMatching"))` y
  `remotes::install_github("facebookincubator/GeoLift")` → 2.7.5.

Script completo de la pasada que funcionó: ver `NOTES.md` (2026-09-05).

## Pendiente de probar

1. Instalar R y el paquete; correr el walkthrough oficial con sus datos.
2. Panel geo sintético propio con efecto conocido → ¿lo recupera?
3. **El duelo:** ese mismo panel contra Meridian GeoX. Dos metodologías, un efecto verdadero.
