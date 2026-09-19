"""Broken-model drill for lesson 03: one deliberate defect, you find it.

The tutor runs this with a number you do not know. It fits the same MMM as experiment 01
on the same synthetic data, with exactly one thing wrong, and prints the usual diagnostic
output. Your job is to say what is wrong from the output alone, before anyone reveals it.

    .venvs/pymc/bin/python lecciones/03-mmm-pymc-marketing/averia.py --n 2
    .venvs/pymc/bin/python lecciones/03-mmm-pymc-marketing/averia.py --n 2 --revelar

LEARNER: stop reading here. Below this line the defects are named. Diagnose first.
Every defect is one an analyst really ships: a missing control, a leaked target, a units
mistake, a broken join. None of them make the sampler complain.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from pymc_marketing.mmm import MMM, GeometricAdstock, LogisticSaturation

ROOT = Path(__file__).resolve().parent.parent.parent

# Signatures below were measured on 2026-09-06 with PyMC-Marketing 1.1.0, 500 draws,
# 2 chains, against experiments/01-pymc-vs-verdad/results/logistic-default/ as the healthy
# reference (search 4.56, social 2.91, video 4.43, display 5.10, baseline share 0.781).
# All four produce zero divergences: none of them makes the sampler complain.
AVERIAS = {
    1: {
        "nombre": "control de tendencia ausente",
        "que_hace": "El KPI sube a lo largo de tres años. El modelo de referencia mete un "
        "regresor de tendencia; esta versión lo quita.",
        "senal": "El canal always-on más grande se come la subida: search pasa de 4,6 a 9,6, "
        "el doble de su ROI sano y casi el doble del verdadero. Lo demás baja un poco. "
        "Trampa: la cuota de baseline se mueve de 0,78 a 0,70, o sea que se ACERCA a la "
        "verdad (0,75) mientras el reparto por canal empeora. Mirar solo el baseline te "
        "diría que este modelo mejoró.",
        "leccion": "Un control ausente no rompe nada visible y puede mejorar una métrica "
        "global mientras estropea la que usas para decidir. Se detecta comparando canales "
        "contra un ajuste de referencia, no mirando el resumen.",
    },
    2: {
        "nombre": "fuga del objetivo en un control",
        "que_hace": "Añade un control 'sessions' construido a partir del propio KPI, como "
        "cuando alguien mete una métrica de web que ya contiene la conversión.",
        "senal": "Los cuatro canales se van a cero a la vez: ROI entre 0,03 y 0,14, errores "
        "del -96 % al -99 %, y la cuota de baseline en 0,995. El modelo explica el KPI casi "
        "entero sin usar los medios.",
        "leccion": "Si un control se calcula después del KPI o a partir de él, es una fuga. "
        "Que TODOS los canales mueran a la vez es la firma: un problema de medios afecta a "
        "unos, una fuga los apaga a todos.",
    },
    3: {
        "nombre": "unidades de un canal mal escaladas",
        "que_hace": "El gasto de display llega dividido por mil, como cuando una fuente "
        "reporta en miles de euros y nadie lo convierte.",
        "senal": "Display sale con ROI 5190 y un intervalo de [2234, 12747]. Tres órdenes de "
        "magnitud por encima del resto, que apenas se mueve.",
        "leccion": "Comprueba las unidades del gasto antes que cualquier otra cosa. Un ROI "
        "que no cabe en la realidad casi siempre es aritmética, no marketing. Y fíjate en que "
        "el modelo no protesta: encaja la escala en el coeficiente y sigue.",
    },
    4: {
        "nombre": "serie de un canal desalineada en el tiempo",
        "que_hace": "El gasto de video va barajado entre semanas, como un cruce de tablas "
        "hecho por una clave equivocada.",
        "senal": "Video, que es el canal mejor identificado del dataset, cae de 4,4 a 0,13 "
        "con intervalo [0,00, 0,68] pegado a cero. Y el ruido se reparte: display sube a 8,6. "
        "El único canal del que el modelo estaba seguro pasa a no existir.",
        "leccion": "Un cruce mal hecho no da error, da un cero. Y un cero se interpreta como "
        "'este canal no funciona', que es la conclusión más cara posible. Sospecha cuando el "
        "canal con más variación de gasto sea justo el que no tiene efecto.",
    },
}


def aplicar(n: int, df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Return the sabotaged frame and the list of control columns to use."""
    df = df.copy()
    df["trend"] = np.arange(len(df)) / len(df)
    controles = ["price_index", "trend"]

    if n == 1:
        controles = ["price_index"]
    elif n == 2:
        rng = np.random.default_rng(7)
        df["sessions"] = df["kpi"] * 0.9 + rng.normal(0, df["kpi"].std() * 0.05, len(df))
        controles = ["price_index", "trend", "sessions"]
    elif n == 3:
        df["spend_display"] = df["spend_display"] / 1000.0
    elif n == 4:
        rng = np.random.default_rng(11)
        df["spend_video"] = rng.permutation(df["spend_video"].to_numpy())
    else:
        raise SystemExit(f"no existe la avería {n}; hay {len(AVERIAS)}")
    return df, controles


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, required=True, help=f"1..{len(AVERIAS)}")
    p.add_argument("--revelar", action="store_true", help="di qué estaba roto")
    p.add_argument("--data", default=ROOT / "data/synthetic/base", type=Path)
    p.add_argument("--draws", type=int, default=500)
    p.add_argument("--tune", type=int, default=500)
    p.add_argument("--chains", type=int, default=2)
    args = p.parse_args()

    if args.n not in AVERIAS:
        raise SystemExit(f"no existe la avería {args.n}; hay {len(AVERIAS)}")

    if args.revelar:
        a = AVERIAS[args.n]
        print(f"Avería {args.n}: {a['nombre']}\n")
        print(f"Qué se hizo:  {a['que_hace']}\n")
        print(f"Cómo se ve:   {a['senal']}\n")
        print(f"La lección:   {a['leccion']}")
        return 0

    df = pd.read_csv(args.data.with_suffix(".csv"), parse_dates=["date"])
    truth = json.loads(Path(f"{args.data}.truth.json").read_text())
    df, controles = aplicar(args.n, df)

    canales = [c for c in df.columns if c.startswith("spend_")]
    X = df[["date", *canales, *controles]]
    y = df["kpi"]

    mmm = MMM(
        date_column="date",
        channel_columns=canales,
        target_column="kpi",
        adstock=GeometricAdstock(l_max=12, parametrization="halflife"),
        saturation=LogisticSaturation(),
        control_columns=controles,
        yearly_seasonality=2,
    )
    mmm.fit(
        X, y, chains=args.chains, draws=args.draws, tune=args.tune,
        cores=min(args.chains, 4), random_seed=42, target_accept=0.95,
        nuts_sampler="nutpie",
    )

    cf = mmm.compute_counterfactual_contributions_dataset()
    contrib = cf[canales].to_array("channel")
    total = contrib.sum("date")
    gasto = df[canales].sum().to_numpy()

    filas = []
    for i, col in enumerate(canales):
        c = total.sel(channel=col).values.ravel()
        roi = c / gasto[i]
        q = np.quantile(roi, [0.03, 0.5, 0.97])
        filas.append({
            "canal": col.removeprefix("spend_"),
            "roi_verdadero": truth["true_roi"][col.removeprefix("spend_")],
            "roi_modelo": float(q[1]),
            "hdi_bajo": float(q[0]),
            "hdi_alto": float(q[2]),
        })
    tabla = pd.DataFrame(filas)
    tabla["error_pct"] = 100 * (tabla["roi_modelo"] / tabla["roi_verdadero"] - 1)

    media = contrib.sum(("date", "channel")).values.ravel()
    baseline = 1 - media / y.sum()
    divergencias = int(mmm.idata.sample_stats["diverging"].sum())

    pd.set_option("display.width", 200)
    print(f"\n--- ajuste con la avería {args.n} ---")
    print(tabla.round(2).to_string(index=False))
    print(f"\ncuota de baseline: verdad {truth['true_baseline_share']:.3f} | "
          f"modelo {np.median(baseline):.3f} "
          f"[{np.quantile(baseline, 0.03):.3f}, {np.quantile(baseline, 0.97):.3f}]")
    print(f"divergencias: {divergencias}")
    print("\nEste modelo tiene exactamente un defecto. ¿Cuál es, y cómo lo ves en la tabla?")
    print("Compara con experiments/01-pymc-vs-verdad/results/logistic-default/ si te hace falta.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
