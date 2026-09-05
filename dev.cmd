@echo off
setlocal
cd /d "%~dp0"
set "COMPOSE_FILE=infra\docker-compose.yml"

if /I "%~1"=="stop" goto stop
if /I "%~1"=="logs" goto logs
if /I "%~1"=="status" goto status
if /I "%~1"=="verify" goto verify
if not "%~1"=="" goto usage

call :require_docker
if errorlevel 1 exit /b 1

if not exist "apps\api\.env" (
    copy /Y "apps\api\.env.example" "apps\api\.env" >nul
    echo Created apps\api\.env from .env.example.
)

echo Starting the DropBy discovery backend...
docker compose -f "%COMPOSE_FILE%" up --build -d api worker beat
if errorlevel 1 (
    echo.
    echo DropBy failed to start. Run dev.cmd logs to inspect the containers.
    exit /b 1
)

echo Loading the repeatable demo data...
docker compose -f "%COMPOSE_FILE%" exec -T api python -m app.scripts.seed_discovery
if errorlevel 1 (
    echo.
    echo The services started, but demo data could not be loaded.
    echo Run dev.cmd logs for details.
    exit /b 1
)

echo.
echo DropBy is ready at http://localhost:8000/docs
echo Login: explorer@dropbyapp.com / dropby12345
echo.
echo Useful commands:
echo   dev.cmd verify
echo   dev.cmd logs
echo   dev.cmd status
echo   dev.cmd stop
start "" "http://localhost:8000/docs"
exit /b 0

:stop
call :require_docker
if errorlevel 1 exit /b 1
docker compose -f "%COMPOSE_FILE%" down
exit /b %errorlevel%

:logs
call :require_docker
if errorlevel 1 exit /b 1
docker compose -f "%COMPOSE_FILE%" logs -f api worker beat
exit /b %errorlevel%

:status
call :require_docker
if errorlevel 1 exit /b 1
docker compose -f "%COMPOSE_FILE%" ps
exit /b %errorlevel%

:verify
call :require_docker
if errorlevel 1 exit /b 1
docker compose -f "%COMPOSE_FILE%" exec -T api python -m app.scripts.verify_discovery
exit /b %errorlevel%

:require_docker
where docker >nul 2>&1
if errorlevel 1 (
    if exist "%LOCALAPPDATA%\Programs\DockerDesktop\resources\bin\docker.exe" (
        set "PATH=%LOCALAPPDATA%\Programs\DockerDesktop\resources\bin;%PATH%"
    ) else (
        echo Docker Desktop is not installed or is not available in PATH.
        echo Install it from https://docs.docker.com/desktop/setup/install/windows-install/
        echo Then open Docker Desktop and run dev.cmd again.
        exit /b 1
    )
)

docker info >nul 2>&1
if errorlevel 1 (
    echo Docker Desktop is installed but its engine is not running.
    echo Open Docker Desktop, wait until it finishes starting, then run dev.cmd again.
    exit /b 1
)
exit /b 0

:usage
echo Usage:
echo   dev.cmd          Start the backend, migrate, seed, and open Swagger
echo   dev.cmd logs     Follow backend logs
echo   dev.cmd status   Show container status
echo   dev.cmd verify   Test PostGIS, concurrent capacity, and Redis
echo   dev.cmd stop     Stop the DropBy containers
exit /b 1
