@echo off
rem Sobe o servidor da loja: aplica migrations e inicia na rede local. Exige set_env.bat preenchido.
setlocal
cd /d "%~dp0"
if not exist set_env.bat (
  echo Copie set_env.bat.example para set_env.bat e preencha.
  goto :erro
)
call set_env.bat
if "%PIZZARIA_PORT%"=="" set PIZZARIA_PORT=8080
rem Usa o Python do venv (onde estao as dependencias); sem venv, cai no python do PATH.
set "PIZZARIA_PY=python"
if exist "venv\Scripts\python.exe" set "PIZZARIA_PY=venv\Scripts\python.exe"
if "%PIZZARIA_PY%"=="python" echo AVISO: venv nao encontrado em sistema\venv; usando o python do PATH.
"%PIZZARIA_PY%" scripts\aplicar_migrations_pg.py || goto :erro
rem 0.0.0.0 expoe na rede local; libere a porta so no firewall do Windows para a rede privada da loja.
"%PIZZARIA_PY%" -m uvicorn api.main:app --host 0.0.0.0 --port %PIZZARIA_PORT% --no-proxy-headers
exit /b %errorlevel%

:erro
rem Pausa para dar tempo de ler o erro quando aberto com duplo clique.
pause
exit /b 1
