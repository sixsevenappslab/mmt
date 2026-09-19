#!/usr/bin/env bash
# setup.sh — reproducible environment for the mmt course.
#
# Creates one uv venv per library family (they do not coexist in a single venv, see
# AGENTS.md) and, on request, installs the R packages that have no usable Python port
# (Robyn, GeoLift, CausalImpact). Idempotent: re-running only fills what is missing.
#
#   ./setup.sh                 base venv + pymc + meridian + surveys
#   ./setup.sh --r             the above plus the R packages (needs R already installed)
#   ./setup.sh --robyn         also create .venvs/robyn with robynpy (beta, optional)
#   ./setup.sh --only pymc     one family: base | pymc | meridian | surveys | robyn | r
#   ./setup.sh --check         verify only, install nothing; exit 1 if anything is missing
#
# Verified 2026-09-05 on Ubuntu (Python 3.12.3, uv, R 4.3.3, 16 cores). Versions obtained
# that day, for reference when yours differ: pymc-marketing 1.1.0 · nutpie 0.16.11 ·
# google-meridian 2.0.0 (JAX backend) · balance 0.23.0 · Robyn 3.12.1 · GeoLift 2.7.5 ·
# CausalImpact 1.4.1 · bsts 0.9.10.
#
# Packages documented in libs/ but not needed by any lesson yet (causalpy, tfcausalimpact,
# meridian-geox) are NOT installed here. They enter when a lesson uses them.

set -euo pipefail

cd "$(dirname "$0")"

PYTHON_VERSION="3.12"
R_LIB="${R_LIBS_USER:-$HOME/R/library}"

WITH_R=0
WITH_ROBYN=0
CHECK_ONLY=0
ONLY=""

usage() { sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; exit "${1:-0}"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --r) WITH_R=1 ;;
    --robyn) WITH_ROBYN=1 ;;
    --check) CHECK_ONLY=1 ;;
    --only) shift; ONLY="${1:-}"; [ -n "$ONLY" ] || usage 1 ;;
    -h|--help) usage 0 ;;
    *) echo "unknown option: $1" >&2; usage 1 ;;
  esac
  shift
done

MISSING=0
say()  { printf '\n\033[1m== %s\033[0m\n' "$*"; }
ok()   { printf '  \033[32mok\033[0m    %s\n' "$*"; }
miss() { printf '  \033[31mMISSING\033[0m %s\n' "$*"; MISSING=1; }
warn() { printf '  \033[33mwarn\033[0m  %s\n' "$*"; }

want() {
  # want <family>: true if this family is selected by --only / flags
  local fam="$1"
  if [ -n "$ONLY" ]; then [ "$ONLY" = "$fam" ]; return; fi
  case "$fam" in
    base|pymc|meridian|surveys) return 0 ;;
    robyn) [ "$WITH_ROBYN" = 1 ] ;;
    r) [ "$WITH_R" = 1 ] ;;
    *) return 1 ;;
  esac
}

# ---------------------------------------------------------------- Python ----

need_uv() {
  if ! command -v uv >/dev/null 2>&1; then
    miss "uv not found. Install: curl -LsSf https://astral.sh/uv/install.sh | sh"
    return 1
  fi
}

# py_check <venv> <import-name> <dist-name>: print version or mark missing
py_check() {
  local venv="$1" mod="$2" dist="$3" py=".venvs/$1/bin/python" v
  [ "$venv" = "base" ] && py=".venv/bin/python"
  if [ ! -x "$py" ]; then miss "$py (venv not created)"; return 1; fi
  if v=$("$py" -c "from importlib.metadata import version; print(version('$dist'))" 2>/dev/null); then
    ok "$venv: $dist $v"
  else
    miss "$venv: $dist ($mod not importable)"
    return 1
  fi
}

# py_family <venv> <dist...>: create venv if needed, install what is missing
py_family() {
  local venv="$1"; shift
  local py=".venvs/$venv/bin/python"
  say "venv .venvs/$venv"
  if [ "$CHECK_ONLY" = 0 ]; then
    need_uv || return 1
    [ -x "$py" ] || uv venv ".venvs/$venv" --python "$PYTHON_VERSION"
    # uv pip install is a no-op for distributions already present (no -U on purpose:
    # a lesson's numbers are tied to the versions it was written with).
    uv pip install --quiet --python "$py" "$@"
  fi
  local d
  for d in "$@"; do py_check "$venv" "$d" "$d" || true; done
}

if want base; then
  say "base venv (.venv) — pandas, numpy, matplotlib, jupyterlab"
  if [ "$CHECK_ONLY" = 0 ]; then need_uv && uv sync --quiet; fi
  py_check base pandas pandas || true
  py_check base numpy numpy || true
  py_check base matplotlib matplotlib || true
fi

if want pymc; then
  py_family pymc pymc-marketing nutpie h5netcdf h5py
fi

if want meridian; then
  py_family meridian google-meridian h5netcdf h5py
fi

if want surveys; then
  py_family surveys balance statsmodels pingouin
fi

if want robyn; then
  py_family robyn robynpy
  warn "robynpy is an LLM-translated beta of Robyn 3.11 (see libs/robyn.md). The reliable Robyn is the R one: ./setup.sh --r"
fi

# --------------------------------------------------------------------- R ----

r_check() {
  # r_check <pkg>: print version or mark missing
  local pkg="$1" v
  if v=$(Rscript -e "cat(as.character(packageVersion('$pkg')))" 2>/dev/null); then
    ok "R: $pkg $v"
  else
    miss "R: $pkg"
    return 1
  fi
}

r_has() { Rscript -e "quit(status = if (requireNamespace('$1', quietly = TRUE)) 0 else 1)" >/dev/null 2>&1; }

r_run() {
  # r_run <label> <R code>: run only when installing
  local label="$1" code="$2"
  say "R: $label"
  MAKEFLAGS="-j$(nproc)" Rscript -e "options(repos = c(CRAN = 'https://cloud.r-project.org')); lib <- '$R_LIB'; $code"
}

if want r; then
  say "R packages (library: $R_LIB)"
  if ! command -v Rscript >/dev/null 2>&1; then
    miss "R not installed. On Debian/Ubuntu: sudo apt install r-base r-base-dev (R >= 4.0). Then re-run ./setup.sh --r"
  else
    ok "R $(Rscript -e 'cat(as.character(getRversion()))')"
    if [ "$CHECK_ONLY" = 0 ]; then
      mkdir -p "$R_LIB"
      if ! grep -qs 'R_LIBS_USER' "$HOME/.Renviron"; then
        echo "R_LIBS_USER=$R_LIB" >> "$HOME/.Renviron"
        ok "added R_LIBS_USER to ~/.Renviron"
      fi
      export R_LIBS_USER="$R_LIB"

      r_has remotes || r_run "remotes" "install.packages('remotes', lib = lib)"

      # augsynth never was on CRAN.
      r_has augsynth || r_run "augsynth (GitHub)" \
        "remotes::install_github('ebenmichael/augsynth', lib = lib, upgrade = 'never')"

      # Boom -> BoomSpikeSlab -> bsts are ARCHIVED on CRAN. install_version without a version
      # number fetches the OLDEST archived release (Boom 0.9, 2013), which no longer compiles.
      # Pin these three. Boom is a long C++ build: MAKEFLAGS above uses all cores.
      r_has Boom || r_run "Boom 0.9.15 (CRAN archive, slow C++ build)" \
        "remotes::install_version('Boom', version = '0.9.15', lib = lib, upgrade = 'never')"
      r_has BoomSpikeSlab || r_run "BoomSpikeSlab 1.2.6 (CRAN archive)" \
        "remotes::install_version('BoomSpikeSlab', version = '1.2.6', lib = lib, upgrade = 'never')"
      r_has bsts || r_run "bsts 0.9.10 (CRAN archive)" \
        "remotes::install_version('bsts', version = '0.9.10', lib = lib, upgrade = 'never')"

      if ! { r_has CausalImpact && r_has MarketMatching; }; then
        r_run "CausalImpact + MarketMatching" \
          "install.packages(c('CausalImpact', 'MarketMatching'), lib = lib)"
      fi

      r_has GeoLift || r_run "GeoLift (GitHub)" \
        "remotes::install_github('facebookincubator/GeoLift', lib = lib, upgrade = 'never')"

      # Robyn: main branch is ahead of the last tagged release. Nevergrad (via reticulate)
      # is NOT configured here; Robyn loads but the hyperparameter search needs it.
      r_has Robyn || r_run "Robyn (GitHub, facebookexperimental/Robyn/R)" \
        "remotes::install_github('facebookexperimental/Robyn/R', lib = lib, upgrade = 'never')"
    fi
    for p in Robyn GeoLift augsynth CausalImpact MarketMatching bsts; do r_check "$p" || true; done
    warn "Robyn's Nevergrad via reticulate is not configured by this script (libs/robyn.md)."
  fi
fi

# ---------------------------------------------------------------- Summary ----

echo
if [ "$MISSING" = 1 ]; then
  echo "Something is missing (see MISSING above)."
  [ "$CHECK_ONLY" = 1 ] && echo "Run ./setup.sh (add --r for the R packages) to install it."
  exit 1
fi
echo "Environment ready. Start with: lecciones/CONTRATO.md, then ask your agent for /leccion 03."
