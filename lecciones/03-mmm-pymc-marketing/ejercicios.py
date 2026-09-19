"""Verifiable exercises for lesson 03.

Every expected value is computed from files, never written here: the ground truth in
data/synthetic/*.truth.json and the stored fits in experiments/01-pymc-vs-verdad/results/.
Re-run the experiment with a newer PyMC-Marketing and the checks follow the new numbers.

Learner: reading this file spoils exercise 6, which is the only conceptual one. The rest
you cannot cheat by reading, because the answers live in the data.
"""

from __future__ import annotations

import os
from pathlib import Path

from practica import (
    Ejercicio,
    NoSePuedeComprobar,
    Resultado,
    a_numero,
    aprox,
    cargar_json,
    igual,
)

ROOT = Path(__file__).resolve().parent.parent.parent
RESULTADOS = ROOT / "experiments/01-pymc-vs-verdad/results"
CANALES = ["search", "social", "video", "display"]


def _fit(variante: str) -> dict:
    return cargar_json(RESULTADOS / variante / "summary.json")


def _ancho(canal: dict) -> float:
    return canal["roi_hdi94_high"] - canal["roi_hdi94_low"]


def _canal(resumen: dict, nombre: str) -> dict:
    return next(c for c in resumen["channels"] if c["channel"] == nombre)


# --------------------------------------------------------------------- e1 ----


def _e1(valor: str) -> Resultado:
    """The best-recovered channel is the one with the narrowest ROI interval."""
    fit = _fit("logistic-default")
    mejor = min(fit["channels"], key=_ancho)["channel"]
    return igual(valor, mejor)


# --------------------------------------------------------------------- e2 ----


def _e2(valor: str) -> Resultado:
    fit = _fit("logistic-default")
    fuera = [c["channel"] for c in fit["channels"] if not c["truth_inside_hdi"]]
    if len(fuera) != 1:
        raise NoSePuedeComprobar(
            "este ajuste ya no deja exactamente un canal fuera del intervalo; "
            "reescribe el ejercicio con los resultados nuevos"
        )
    return igual(valor, fuera[0])


# --------------------------------------------------------------------- e3 ----


def _tramo(n: int) -> str:
    if n == 0:
        return "ninguna"
    if n < 100:
        return "decenas"
    if n < 1000:
        return "cientos"
    return "miles"


def _e3(valor: str) -> Resultado:
    fit = _fit("hill-default")
    return igual(valor, _tramo(int(fit["divergences"])))


# --------------------------------------------------------------------- e4 ----


def _e4(valor: str) -> Resultado:
    fit = _fit("hill-default")
    esperado = fit["baseline_share"]["median"]
    res = aprox(a_numero(valor), esperado, tol_rel=0.0, tol_abs=0.05)
    if res.ok:
        verdad = fit["baseline_share"]["true"]
        res.mensaje = (
            f"y la verdad es {verdad:.2f}. Esa distancia es el modelo repartiendo mal "
            "el KPI entre baseline y medios."
        )
    return res


# --------------------------------------------------------------------- e5 ----


def _summary_alumno() -> dict:
    """The fit the learner produced in step 4, with search spend CV raised to 0.7."""
    candidatos = [
        Path(os.environ.get("MMT_CV07_OUT", "/tmp/mmt-search-cv07")) / "summary.json",
        ROOT / "experiments/01-pymc-vs-verdad/results/search-cv07/summary.json",
    ]
    for c in candidatos:
        if c.exists():
            return cargar_json(c)
    raise NoSePuedeComprobar(
        "no encuentro tu ajuste del paso 4. Espero un summary.json en "
        "/tmp/mmt-search-cv07/ (o define MMT_CV07_OUT)"
    )


def _e5(valor: str) -> Resultado:
    antes = _ancho(_canal(_fit("logistic-default"), "search"))
    despues = _ancho(_canal(_summary_alumno(), "search"))
    factor = despues / antes
    res = aprox(a_numero(valor), factor, tol_rel=0.35)
    if res.ok:
        res.mensaje = "el modelo es el mismo; lo único que cambió fue la variación del gasto."
    return res


# --------------------------------------------------------------------- e6 ----


def _e6(valor: str) -> Resultado:
    return igual(valor, "variacion del gasto")


EJERCICIOS = [
    Ejercicio(
        id="e1",
        enunciado="Antes de ajustar nada: ¿qué canal va a recuperar mejor el modelo?",
        tipo="eleccion",
        opciones=CANALES,
        comprobar=_e1,
        pista="«Mejor» es el intervalo más estrecho, no la mediana más cercana a la verdad. "
        "Mira el patrón de gasto de cada canal en el CSV antes de decidir.",
    ),
    Ejercicio(
        id="e2",
        enunciado="En logistic-default, ¿qué canal deja la verdad FUERA de su intervalo?",
        tipo="eleccion",
        opciones=CANALES,
        comprobar=_e2,
        pista="Columna truth_inside_hdi de la tabla del paso 2.",
        requiere="paso 2 de la práctica",
    ),
    Ejercicio(
        id="e3",
        enunciado="¿De qué orden es el número de divergencias en hill-default?",
        tipo="eleccion",
        opciones=["ninguna", "decenas", "cientos", "miles"],
        comprobar=_e3,
        pista="Lo imprime el ajuste del paso 3, y también está en su summary.json.",
        requiere="paso 3 de la práctica",
    ),
    Ejercicio(
        id="e4",
        enunciado="¿Qué cuota de baseline estima hill-default? Un número entre 0 y 1.",
        tipo="numero",
        comprobar=_e4,
        pista="La línea «baseline share» del paso 3. Ojo: te pido la del modelo, no la verdadera.",
        requiere="paso 3 de la práctica",
    ),
    Ejercicio(
        id="e5",
        enunciado="Tras subir la variación del gasto de search a 0,7, ¿por qué factor cambió "
        "el ancho de su intervalo? Por ejemplo 0,5 si se redujo a la mitad.",
        tipo="numero",
        comprobar=_e5,
        pista="Ancho = extremo alto menos extremo bajo, en los dos ajustes. Divide el nuevo "
        "entre el viejo.",
        requiere="paso 4 de la práctica, con su salida guardada",
    ),
    Ejercicio(
        id="e6",
        enunciado="¿Qué es lo que permite al modelo identificar un canal?",
        tipo="eleccion",
        opciones=[
            "variacion del gasto",
            "volumen del gasto",
            "ROI verdadero del canal",
            "numero de semanas activas",
        ],
        comprobar=_e6,
        pista="Compara los dos canales de los ejercicios 1 y 2: uno se identifica y el otro no. "
        "¿En qué se diferencian de verdad?",
    ),
]
