@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo   소모품 교체 준수 판정기
echo ============================================
echo.

set "PYLAUNCH="

rem --- 1) PATH 에 등록된 런처부터 실제 실행 검증 (Microsoft Store 0바이트 스텁은 여기서 걸러짐) ---
py -3 -c "pass" >nul 2>nul && set "PYLAUNCH=py -3"
if not defined PYLAUNCH (
    py -c "pass" >nul 2>nul && set "PYLAUNCH=py"
)
if not defined PYLAUNCH (
    python -c "import sys; sys.exit(0 if sys.executable else 1)" >nul 2>nul && set "PYLAUNCH=python"
)
if not defined PYLAUNCH (
    python3 -c "import sys; sys.exit(0 if sys.executable else 1)" >nul 2>nul && set "PYLAUNCH=python3"
)

rem --- 2) PATH 에 없으면 흔한 설치 경로를 직접 탐색 (WindowsApps 스텁은 제외) ---
if not defined PYLAUNCH (
    for %%P in (
        "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python39\python.exe"
        "%ProgramFiles%\Python313\python.exe"
        "%ProgramFiles%\Python312\python.exe"
        "%ProgramFiles%\Python311\python.exe"
        "%ProgramFiles%\Python310\python.exe"
        "C:\Python313\python.exe"
        "C:\Python312\python.exe"
        "C:\Python311\python.exe"
        "%ProgramData%\Anaconda3\python.exe"
        "%LOCALAPPDATA%\Continuum\anaconda3\python.exe"
    ) do (
        if not defined PYLAUNCH if exist "%%~P" (
            "%%~P" -c "pass" >nul 2>nul && set PYLAUNCH="%%~P"
        )
    )
)

if not defined PYLAUNCH (
    echo [오류] 실행 가능한 Python을 찾지 못했습니다.
    echo.
    echo   진단: 이 PC 의 python 은 Microsoft Store 연결용 가짜 실행파일일 수 있습니다.
    echo         ^(where python 이 WindowsApps\python.exe 로만 나오면 그렇습니다^)
    echo   Git Bash 에서는 되는데 이 창에서는 안 되는 이유가 이것입니다.
    echo.
    echo   아래 중 하나로 해결하세요.
    echo.
    echo    1. https://www.python.org/downloads/ 에서 Python 설치
    echo       설치 화면에서 "Add python.exe to PATH" 와
    echo       "Install launcher for all users" 항목을 반드시 체크
    echo    2. 또는 Windows 설정 - 앱 - 고급 앱 설정 - 앱 실행 별칭 관리 에서
    echo       python.exe / python3.exe 의 앱 설치 관리자 연결을 끄기
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
