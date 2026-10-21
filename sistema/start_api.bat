@echo off
rem Sobe o servidor da loja: aplica migrations e inicia na rede local. Exige set_env.bat preenchido.
if not exist set_env.bat (echo Copie set_env.bat.example para set_env.bat e preencha. & exit /b 1)
call set_env.bat
if "%PIZZARIA_PORT%"=="" set PIZZARIA_PORT=8080
python scripts\aplicar_migrations_pg.py || exit /b 1
rem 0.0.0.0 expoe na rede local; libere a porta so no firewall do Windows para a rede privada da loja.
python -m uvicorn api.main:app --host 0.0.0.0 --port %PIZZARIA_PORT% --no-proxy-headers
