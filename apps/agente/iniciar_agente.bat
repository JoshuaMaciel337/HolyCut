@echo off
rem HolyCut - agente que envia sozinho as gravacoes do OBS.
rem Na primeira vez, ele pergunta o endereco do HolyCut, a chave de envio e a pasta do OBS.
rem Para iniciar com o Windows, use um atalho para: iniciar_agente.bat --automatico
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo O Python nao esta instalado. Baixe em https://www.python.org/downloads/ e marque "Add python.exe to PATH".
  pause
  exit /b 1
)
py -3 -m pip install --user --quiet --disable-pip-version-check -r requirements.txt
py -3 agendador_gravacoes.py %*
if /i not "%~1"=="--automatico" pause
