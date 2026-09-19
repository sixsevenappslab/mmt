"""Broken-model drill for lesson 04: one deliberate defect in a Meridian fit, you find it.

The tutor runs this with a number you do not know. It fits the same Meridian model as
experiment 02 (variant roi-default) on the same synthetic data, with exactly one thing
wrong, and prints the usual table. Your job is to say what is wrong from the output alone,
before anyone reveals it.

    .venvs/meridian/bin/python lecciones/04-mmm-meridian/averia.py --n 2
    .venvs/meridian/bin/python lecciones/04-mmm-meridian/averia.py --n 2 --revelar

LEARNER: stop reading here. Below this line the defects are named. Diagnose first.
Every defect is one an analyst really ships: a prior copied from another account, a
baseline with no room to move, a units mistake, a broken join. Meridian's ROI prior hides
some of them better than PyMC-Marketing did in lesson 03, and that is the point.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from meridian import backend
from meridian.analysis import analyzer
from meridian.data import data_frame_input_data_builder as builder
from meridian.model import model, prior_distribution, spec

ROOT = Path(__file__).resolve().parent.parent.parent
tfd = backend.tfd
f = backend.np_float_dtype

# Signatures below were measured on 2026-09-18 with google-meridian 2.0.0 (JAX backend),
# 2 chains x (300 adapt + 300 burn-in + 500 keep), against
# experiments/02-meridian-vs-verdad/results/roi-default/ as the healthy reference
# (search 1.76, social 3.87, video 5.35, display 3.72, baseline share 0.817).
AVERIAS = {
    1: {
        "nombre": "baseline sin flexibilidad (un solo nudo)",
        "que_hace": "El KPI sube un 30 % a lo largo de tres años y tiene ciclo anual. El "
        "modelo de referencia le da al baseline un spline con 13 nudos; esta versión lo "
        "deja en uno, o sea, plano.",
        "senal": "Video, el canal que los datos identifican solos, cae de 5,4 a 2,6 con intervalo [0,9 "
        "– 4,4]: la verdad (4,5) queda fuera por primera vez. Social se dobla y pico (3,7 → "
        "9,7) y search abre un intervalo de [0,3 – 14,9]. Trampa: la cuota de baseline pasa "
        "de 0,81 a 0,76, o sea que se ACERCA a la verdad (0,75) mientras el reparto por canal "
        "se rompe. Mirar solo el baseline te diría que este modelo mejoró.",
        "leccion": "Meridian no tiene término de tendencia ni de estacionalidad: todo eso lo "
        "tiene que absorber el spline del baseline. Si no le das nudos, la tendencia se la "
        "queda el canal always-on más grande. Es el mismo fallo que quitar el control de "
        "tendencia en PyMC-Marketing, con otro nombre.",
    },
    2: {
        "nombre": "prior de ROI copiado de otra cuenta",
        "que_hace": "Un prior de ROI estrecho, LogNormal(log 0.8, 0.15), que alguien trajo "
        "de otro cliente porque 'ahí funcionó'. Todo lo demás igual.",
        "senal": "Los cuatro canales en 0,8–0,9 con intervalos de [0,6 – 1,2], iguales entre sí. "
        "Incluido video, que en la referencia sale en 5,4 con los datos a favor. Cuota de "
        "baseline 0,956 con un intervalo de dos centésimas, y cada canal aportando alrededor "
        "del 1 % del KPI. Cero divergencias: el muestreo está encantado.",
        "leccion": "En Meridian el prior es directamente el ROI. Uno estrecho no informa al "
        "modelo: lo sustituye. La firma es que los cuatro canales caen al mismo sitio con "
        "intervalos parecidos, incluido video, que en la referencia los datos identifican "
        "solos. Si un canal con variación real de gasto no se mueve del prior, el prior manda.",
    },
    3: {
        "nombre": "unidades de un canal mal escaladas",
        "que_hace": "El gasto de display llega dividido por mil, como cuando una fuente "
        "reporta en miles de euros y nadie lo convierte.",
        "senal": "Display sale con ROI 1,3 [0,2 – 6,5], que parece razonable, y contribución 0,00 % "
        "del KPI. El resto de canales ni se inmuta. En la lección 03 este mismo defecto daba "
        "un ROI de 5000; aquí el prior de ROI no lo permite y la escala se paga en la "
        "contribución. El ROI de display queda pegado al prior porque el modelo ya no sabe "
        "nada de display.",
        "leccion": "En la lección 03 este mismo error salía como un ROI de 5000: imposible "
        "de no ver. Aquí el prior de ROI no deja que el ROI se vaya a miles, así que el "
        "modelo hace lo único que puede: encoge la contribución del canal hasta casi cero. "
        "El error de unidades se convierte en 'display no funciona'. Comprueba las unidades "
        "antes que nada, y desconfía de un canal cuyo ROI es clavado a la mediana del prior.",
    },
    4: {
        "nombre": "serie de un canal desalineada en el tiempo",
        "que_hace": "El gasto de video va barajado entre semanas, como un cruce de tablas "
        "hecho por una clave equivocada.",
        "senal": "Video, el canal mejor identificado del dataset, cae de 5,4 a 0,5 con intervalo [0,1 "
        "– 1,7] y contribución del 0,7 % (referencia: 7,5 %). El KPI que video ya no explica "
        "se lo queda el baseline (0,81 → 0,89). Ocho divergencias: el muestreo protesta un "
        "poco, pero no lo bastante para que alguien con prisa lo mire.",
        "leccion": "Un cruce mal hecho no da error, da un cero. Video es el canal que mejor "
        "identifican los datos en las tres variantes del experimento 02; si justo ese "
        "aparece sin efecto, sospecha del cruce antes que del canal.",
    },
}


def aplicar(n: int, df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Return the sabotaged frame and the ModelSpec overrides for defect n."""
    df = df.copy()
    ajustes = {"knots": 13, "max_lag": 12, "prior": prior_distribution.PriorDistribution()}

    if n == 1:
        ajustes["knots"] = 1
    elif n == 2:
        ajustes["prior"] = prior_distribution.PriorDistribution(
            roi_m=tfd.LogNormal(f(np.log(0.8)), f(0.15), name="roi_m"),
        )
    elif n == 3:
        df["spend_display"] = df["spend_display"] / 1000.0
    elif n == 4:
        rng = np.random.default_rng(11)
        df["spend_video"] = rng.permutation(df["spend_video"].to_numpy())
    elif n != 0:
        raise SystemExit(f"no existe la avería {n}; hay {len(AVERIAS)}")
    return df, ajustes


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, required=True,
                   help=f"1..{len(AVERIAS)} (0 = sin avería, referencia con este sampler)")
    p.add_argument("--revelar", action="store_true", help="di qué estaba roto")
    p.add_argument("--data", default=ROOT / "data/synthetic/base", type=Path)
    p.add_argument("--chains", type=int, default=2)
    p.add_argument("--adapt", type=int, default=300)
    p.add_argument("--burnin", type=int, default=300)
    p.add_argument("--keep", type=int, default=500)
    args = p.parse_args()

    if args.n not in AVERIAS and args.n != 0:
        raise SystemExit(f"no existe la avería {args.n}; hay {len(AVERIAS)}")

    if args.revelar:
        if args.n == 0:
            print("La 0 no tiene avería: es la referencia con el sampler del drill.")
            return 0
        a = AVERIAS[args.n]
        print(f"Avería {args.n}: {a['nombre']}\n")
        print(f"Qué se hizo:  {a['que_hace']}\n")
        print(f"Cómo se ve:   {a['senal']}\n")
        print(f"La lección:   {a['leccion']}")
        return 0

    df = pd.read_csv(args.data.with_suffix(".csv"), parse_dates=["date"])
    truth = json.loads(Path(f"{args.data}.truth.json").read_text())
    df, ajustes = aplicar(args.n, df)

    spend_cols = [c for c in df.columns if c.startswith("spend_")]
    names = [c.removeprefix("spend_") for c in spend_cols]
    df["time"] = df["date"].dt.strftime("%Y-%m-%d")

    data = (
        builder.DataFrameInputDataBuilder(kpi_type="revenue", default_time_column="time")
        .with_kpi(df, kpi_col="kpi")
        .with_media(df, media_cols=spend_cols, media_spend_cols=spend_cols, media_channels=names)
        .with_controls(df, control_cols=["price_index"])
        .build()
    )
    model_spec = spec.ModelSpec(
        prior=ajustes["prior"],
        paid_media_prior_type="roi",
        max_lag=ajustes["max_lag"],
        knots=ajustes["knots"],
    )
    mmm = model.Meridian(input_data=data, model_spec=model_spec)
    mmm.sample_prior(200, seed=42)
    mmm.sample_posterior(
        n_chains=args.chains, n_adapt=args.adapt, n_burnin=args.burnin, n_keep=args.keep,
        seed=42,
    )

    an = analyzer.Analyzer(mmm)
    roi = np.asarray(an.roi())
    inc = np.asarray(an.incremental_outcome())
    y_total = float(df["kpi"].sum())

    filas = []
    for i, name in enumerate(names):
        r = roi[..., i].ravel()
        q = np.quantile(r, [0.03, 0.5, 0.97])
        filas.append({
            "canal": name,
            "roi_verdadero": truth["true_roi"][name],
            "roi_modelo": float(q[1]),
            "hdi_bajo": float(q[0]),
            "hdi_alto": float(q[2]),
            "contrib_pct": 100 * float(np.median(inc[..., i])) / y_total,
        })
    tabla = pd.DataFrame(filas)
    tabla["error_pct"] = 100 * (tabla["roi_modelo"] / tabla["roi_verdadero"] - 1)

    baseline = 1 - inc.sum(axis=-1).ravel() / y_total
    divergencias = 0
    if "diverging" in mmm.inference_data.sample_stats:
        divergencias = int(mmm.inference_data.sample_stats["diverging"].sum())
    rhat = float(an.rhat_summary()["max_r_hat"].max())

    pd.set_option("display.width", 200)
    print(f"\n--- ajuste con la avería {args.n} ---")
    print(tabla.round(2).to_string(index=False))
    print(f"\ncuota de baseline: verdad {truth['true_baseline_share']:.3f} | "
          f"modelo {np.median(baseline):.3f} "
          f"[{np.quantile(baseline, 0.03):.3f}, {np.quantile(baseline, 0.97):.3f}]")
    print(f"divergencias: {divergencias}  |  r-hat máx: {rhat:.3f}")
    if args.n:
        print("\nEste modelo tiene exactamente un defecto. ¿Cuál es, y cómo lo ves en la tabla?")
        print("Compara con experiments/02-meridian-vs-verdad/results/roi-default/ si te hace falta.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
