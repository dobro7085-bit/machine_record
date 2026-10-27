@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo   소모품 교체 준수 판정기
echo ============================================
echo.

set "PYLAUNCH="
py -3 -c "pass" >nul 2>nul && set "PYLAUNCH=py -3"
if not defined PYLAUNCH (
    py -c "pass" >nul 2>nul && set "PYLAUNCH=py"
)
if not defined PYLAUNCH (
    python -c "pass" >nul 2>nul && set "PYLAUNCH=python"
)
if not defined PYLAUNCH (
    python3 -c "pass" >nul 2>nul && set "PYLAUNCH=python3"
)

if not defined PYLAUNCH (
    echo [오류] 실행 가능한 Python을 Windows PATH 에서 찾지 못했습니다.
    echo.
    echo   Git Bash 에서는 python 이 되는데 이 창에서는 안 될 수 있습니다.
    echo   아래 중 하나로 해결하세요.
    echo.
    echo    1. https://www.python.org/downloads/ 에서 Python 재설치 시
    echo       "Add python.exe to PATH" 와 "Install launcher for all users" 를 체크
    echo    2. 또는 설정 - "앱 실행 별칭 관리" 에서 python.exe / python3.exe 의
    echo       Microsoft Store 연결 을 끄기
    echo    3. 또는 Git Bash 에서 실행.sh 를 사용: ./실행.sh
    echo.
    pause
    exit /b 1
)

echo 사용할 Python: %PYLAUNCH%
echo.

if not exist ".venv\Scripts\python.exe" (
    echo 최초 실행: 가상환경을 만들고 필요한 패키지를 설치합니다...
    echo 처음 한 번만 몇 분 걸립니다.
    echo.
    %PYLAUNCH% -m venv .venv
    if not exist ".venv\Scripts\python.exe" (
        echo [오류] 가상환경 생성에 실패했습니다.
        pause
        exit /b 1
    )
    call ".venv\Scripts\python.exe" -m pip install --upgrade pip
    call ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [오류] 패키지 설치에 실패했습니다.
        pause
        exit /b 1
    )
    echo.
    echo 설치 완료.
    echo.
)

echo 프로그램을 실행합니다...
call ".venv\Scripts\python.exe" -m src.gui
if errorlevel 1 (
    echo.
    echo [오류] 프로그램 실행 중 문제가 발생했습니다. 위 메시지를 확인하세요.
    pause
    exit /b 1
)

endlocal
