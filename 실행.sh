#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

echo "============================================"
echo "  소모품 교체 준수 판정기"
echo "============================================"
echo

if command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1; then
    PY=python
else
    echo "[오류] Python이 설치되어 있지 않습니다. Python 3.11 이상을 설치하세요."
    exit 1
fi

if [ ! -x ".venv/bin/python" ]; then
    echo "최초 실행: 가상환경을 만들고 필요한 패키지를 설치합니다... (처음 한 번만 몇 분 소요)"
    echo
    "$PY" -m venv .venv
    ".venv/bin/python" -m pip install --upgrade pip
    ".venv/bin/python" -m pip install -r requirements.txt
    echo
    echo "설치 완료."
    echo
fi

echo "프로그램을 실행합니다..."
exec ".venv/bin/python" -m src.gui
