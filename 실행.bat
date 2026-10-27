@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo   소모품 교체 준수 판정기
echo ============================================
echo.

where py >nul 2>nul
if %errorlevel%==0 (
    set "PYLAUNCH=py -3"
) else (
    where python >nul 2>nul
    if %errorlevel%==0 (
        set "PYLAUNCH=python"
    ) else (
        echo [오류] Python이 설치되어 있지 않습니다.
        echo        https://www.python.org/downloads/ 에서 Python 3.11 이상을 설치하세요.
        echo        설치 시 "Add Python to PATH" 를 반드시 체크하세요.
        echo.
        pause
        exit /b 1
    )
)

if not exist ".venv\Scripts\python.exe" (
    echo 최초 실행: 가상환경을 만들고 필요한 패키지를 설치합니다...
    echo 처음 한 번만 몇 분 걸립니다.
    echo.
    %PYLAUNCH% -m venv .venv
    if errorlevel 1 (
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
