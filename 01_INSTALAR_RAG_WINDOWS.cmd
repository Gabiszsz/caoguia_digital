@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
if not exist "chatbot\requirements.txt" (
  echo ERRO: coloque este arquivo na raiz do repositorio clonado, com a pasta chatbot.
  pause
  exit /b 1
)
cd chatbot
py -3 --version >nul 2>&1
if errorlevel 1 (
  echo ERRO: instale Python compativel com requirements.txt (3.11/3.12).
  pause
  exit /b 1
)
if not exist .venv\Scripts\python.exe py -3 -m venv .venv
if errorlevel 1 (pause & exit /b 1)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (echo ERRO: a instalacao de dependencias falhou. & pause & exit /b 1)
where ollama >nul 2>&1
if errorlevel 1 (
 echo AVISO: Ollama nao encontrado. Instale em https://ollama.com/download
) else (
 echo Baixando ou validando modelo qwen2.5:1.5b...
 ollama pull qwen2.5:1.5b
)
echo Indexando documentos (pode levar mais tempo na primeira vez)...
python ingest.py
if errorlevel 1 (echo ATENCAO: indexacao falhou, cheque os documentos em data\documents. & pause & exit /b 1)
echo Preparacao concluida.
pause
