@echo off
rem Mostra quem usa a porta; encerre pelo PID com: taskkill /PID <pid> /F
if "%PIZZARIA_PORT%"=="" set PIZZARIA_PORT=8080
netstat -ano | findstr :%PIZZARIA_PORT%
