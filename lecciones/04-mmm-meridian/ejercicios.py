"""Verifiable exercises for lesson 04.

Every expected value is computed from files, never written here: the stored Meridian fits
in experiments/02-meridian-vs-verdad/results/ and, for the learner's own prior, the
summary.json that step 5 of the practice writes. Re-run the experiment with a newer Meridian
and the checks follow the new numbers.

Learner: reading this file spoils exercise 7, which is the only conceptual one. The rest
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
RESULTADOS = ROOT / "experiments/02-meridian-vs-verdad/results"
CANALES = ["search", "social", "video", "display"]
VARIANTES = ["roi-default", "roi-wide", "contribution"]


def _fit(variante: str) -> dict:
    return cargar_json(RESULTADOS / variante / "summary.json")


def _canal(resumen: dict, nombre: str) -> dict:
    return next(c for c in resumen["channels"] if c["channel"] == nombre)


def _ancho(canal: dict) -> float:
    return canal["roi_hdi94_high"] - canal["roi_hdi94_low"]


# --------------------------------------------------------------------- e1 ----


def _e1(valor: str) -> Resultado:
    """The default ROI prior leaves exactly one channel's truth outside its interval."""
    fit = _fit("roi-default")
    fuera = [c["channel"] for c in fit["channels"] if not c["truth_inside_hdi"]]
    if len(fuera) != 1:
        raise NoSePuedeComprobar(
            "roi-default ya no deja exactamente un canal fuera del intervalo; "
            "reescribe el ejercicio con los resultados nuevos"
        )
    return igual(valor, fuera[0])


# --------------------------------------------------------------------- e2 ----


def _e2(valor: str) -> Resultado:
    """Narrowest interval in roi-default. It is also the one that misses the truth."""
    fit = _fit("roi-default")
    estrecho = min(fit["channels"], key=_ancho)
    res = igual(valor, estrecho["channel"])
    if res.ok and not estrecho["truth_inside_hdi"]:
        res.mensaje = (
            "y es justo el canal que deja la verdad fuera. Estrecho no significa bien "
            "centrado: aquí es el prior hablando con voz firme."
        )
    return res


# --------------------------------------------------------------------- e3 ----


def _e3(valor: str) -> Resultado:
    antes = _canal(_fit("roi-default"), "search")["roi_median"]
    despues = _canal(_fit("roi-wide"), "search")["roi_median"]
    factor = despues / antes
    res = aprox(a_numero(valor), factor, tol_rel=0.15)
    if res.ok:
        res.mensaje = (
            "misma información, otra opinión previa. Nada cambió en los datos ni en el "
            "modelo; solo dónde estaba centrado el prior."
        )
    return res


# --------------------------------------------------------------------- e4 ----


def _dispersion(nombre: str) -> float:
    medianas = [_canal(_fit(v), nombre)["roi_median"] for v in VARIANTES]
    return (max(medianas) - min(medianas)) / min(medianas)


def _e4(valor: str) -> Resultado:
    estable = min(CANALES, key=_dispersion)
    res = igual(valor, estable)
    if res.ok:
        res.mensaje = (
            "donde hay variación de gasto mandan los datos y el prior apenas lo mueve. "
            "Compáralo con el canal que más cambia: ahí manda el prior."
        )
    return res


# --------------------------------------------------------------------- e5 ----


def _e5(valor: str) -> Resultado:
    fit = _fit("contribution")
    esperado = fit["baseline_share"]["median"]
    res = aprox(a_numero(valor), esperado, tol_rel=0.0, tol_abs=0.05)
    if res.ok:
        verdad = fit["baseline_share"]["true"]
        peor = max(fit["channels"], key=lambda c: abs(c["roi_error_pct"]))
        res.mensaje = (
            f"y la verdad es {verdad:.2f}: la cuota total la clava. Ahora mira el ROI de "
            f"{peor['channel']} en esa misma tabla. Acertar la suma no es acertar el reparto."
        )
    return res


# --------------------------------------------------------------------- e6 ----


def _summary_alumno() -> dict:
    """The fit the learner produced in step 5 with a prior of their own."""
    candidatos = [
        Path(os.environ.get("MMT_ROI_CUSTOM_OUT", "/tmp/mmt-roi-custom")) / "summary.json",
        RESULTADOS / "roi-custom" / "summary.json",
    ]
    for c in candidatos:
        if c.exists():
            return cargar_json(c)
    raise NoSePuedeComprobar(
        "no encuentro tu ajuste del paso 5. Espero un summary.json en "
        "/tmp/mmt-roi-custom/ (o define MMT_ROI_CUSTOM_OUT)"
    )


def _e6(valor: str) -> Resultado:
    fit = _summary_alumno()
    dentro = _canal(fit, "search")["truth_inside_hdi"]
    res = igual(valor, "si" if dentro else "no")
    if res.ok:
        prior = fit.get("roi_prior") or {}
        mediana = prior.get("median")
        detalle = f"con mediana {mediana:g}" if mediana else "con tu prior"
        defecto = _canal(_fit("roi-default"), "search")["truth_inside_hdi"]
        res.mensaje = (
            f"{detalle}, search queda {'dentro' if dentro else 'fuera'}; con el de la "
            f"librería (mediana 1,2) quedaba {'dentro' if defecto else 'fuera'}. "
            "Lo que has movido es tu opinión, no la evidencia. ¿Podrías defender ese prior "
            "delante de alguien que no ha visto la verdad?"
        )
    return res


# --------------------------------------------------------------------- e7 ----


def _e7(valor: str) -> Resultado:
    return igual(valor, "el prior")


EJERCICIOS = [
    Ejercicio(
        id="e1",
        enunciado="Antes de ajustar nada: con el prior de ROI por defecto de Meridian "
        "(mediana 1,2), ¿qué canal va a quedar con la verdad FUERA de su intervalo?",
        tipo="eleccion",
        opciones=CANALES,
        comprobar=_e1,
        pista="El prior rellena lo que los datos no dicen. ¿Qué canal tenía menos variación "
        "de gasto en la lección 03? Ese es el que más depende del prior.",
    ),
    Ejercicio(
        id="e2",
        enunciado="En roi-default, ¿qué canal tiene el intervalo más ESTRECHO?",
        tipo="eleccion",
        opciones=CANALES,
        comprobar=_e2,
        pista="Ancho = extremo alto menos extremo bajo, en la tabla del paso 2. No lo "
        "confundas con «más cerca de la verdad».",
        requiere="paso 2 de la práctica",
    ),
    Ejercicio(
        id="e3",
        enunciado="Del prior por defecto (roi-default) al prior centrado en 4 (roi-wide), "
        "¿por qué factor se multiplicó la mediana del ROI de search? Por ejemplo 1,5.",
        tipo="numero",
        comprobar=_e3,
        pista="Mediana de search en las dos tablas; divide la nueva entre la vieja.",
        requiere="pasos 2 y 3 de la práctica",
    ),
    Ejercicio(
        id="e4",
        enunciado="Mirando las tres variantes, ¿qué canal cambia MENOS de mediana cuando "
        "cambia el prior?",
        tipo="eleccion",
        opciones=CANALES,
        comprobar=_e4,
        pista="Para cada canal, mediana máxima menos mínima entre las tres tablas, relativa "
        "a la mínima. Uno se mueve un 10 % y otro se duplica.",
        requiere="pasos 2, 3 y 4 de la práctica",
    ),
    Ejercicio(
        id="e5",
        enunciado="Con el prior de contribución, ¿qué cuota de baseline estima el modelo? "
        "Un número entre 0 y 1.",
        tipo="numero",
        comprobar=_e5,
        pista="La línea «baseline share» del paso 4. Te pido la del modelo, no la verdadera.",
        requiere="paso 4 de la práctica",
    ),
    Ejercicio(
        id="e6",
        enunciado="Con TU prior del paso 5, ¿queda la verdad de search dentro de su intervalo? "
        "sí o no.",
        tipo="eleccion",
        opciones=["sí", "no"],
        comprobar=_e6,
        pista="Columna truth_inside_hdi de tu propia salida.",
        requiere="paso 5 de la práctica, con su salida guardada",
    ),
    Ejercicio(
        id="e7",
        enunciado="Cuando los datos no identifican un canal, ¿qué decide su ROI en Meridian?",
        tipo="eleccion",
        opciones=[
            "el prior",
            "el volumen de gasto",
            "la curva de saturacion",
            "la cuota de baseline",
        ],
        comprobar=_e7,
        pista="Compara search en las tres variantes: el modelo es el mismo y los datos son "
        "los mismos. ¿Qué es lo único que cambió entre tablas?",
    ),
]
