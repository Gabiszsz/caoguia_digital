@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
if not exist "chatbot\.venv\Scripts\python.exe" (
 echo ERRO: execute 01_INSTALAR_RAG_WINDOWS.cmd primeiro.
 pause
 exit /b 1
)
cd chatbot
set PRELOAD_KB=1
start "" "http://127.0.0.1:8001/portal/"
echo Portal: http://127.0.0.1:8001/portal/
echo Chatbot RAG: http://127.0.0.1:8001/
echo Saude da base RAG: http://127.0.0.1:8001/api/v1/health
echo Se o navegador abrir antes do servidor, atualize a pagina.
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
pause
