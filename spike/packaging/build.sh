#!/usr/bin/env bash
# Section 6 packaging spike build.
#
# --onedir, not --onefile: the plan's reasoning is that onefile pays an
# unpack-on-launch cost and draws more AV false positives, and section 6.1 adds a
# correctness reason - a path resolved under sys._MEIPASS is DELETED on exit
# under onefile, so a cache defaulting there silently re-scans every launch.
#
# fpcalc is bundled with --add-data. On Windows the separator is ';' and on
# POSIX ':', which is why this is not a bare string.
set -euo pipefail
cd "$(dirname "$0")/../.."

FPCALC="$(python -c "import shutil,os;p=shutil.which('fpcalc');print(os.path.realpath(p) if p else '')")"
if [ -z "$FPCALC" ]; then
  echo "fpcalc not on PATH - check 2 cannot be exercised" >&2
  exit 1
fi

# nicegui-pack shells out to a bare `pyinstaller`, resolved against PATH - it
# does not use the interpreter it was itself launched with, and it does not
# declare PyInstaller as a dependency. Both are spike findings: installing
# nicegui alone is not enough to build, and running nicegui-pack by its full
# venv path is not enough either. The venv's Scripts directory has to be on
# PATH or the build dies in CreateProcess with a bare WinError 2.
export PATH="$(pwd)/.venv/Scripts:${PATH}"

SEP=";"   # Windows
case "$(uname -s 2>/dev/null || echo Windows)" in Linux*|Darwin*) SEP=":";; esac

exec ./.venv/Scripts/nicegui-pack.exe \
  --onedir \
  --windowed \
  --noconfirm \
  --name traktor-nml-spike \
  --add-data "${FPCALC}${SEP}." \
  spike/packaging/spike_app.py
