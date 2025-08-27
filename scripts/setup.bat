@echo off
chcp 65001 >nul
REM Остановка и удаление контейнера если найден
docker ps -a | findstr mobilede >nul
if %errorlevel% equ 0 (
    echo Контейнер найден, останавливаем...
    docker stop mobilede
    docker rm mobilede
    echo Контейнер остановлен
) else (
    echo Контейнер не найден
)

REM Сборка образа
echo Сборка образа...
docker build -t mobilede-parser:latest -f ../docker/Dockerfile ..

REM Запуск контейнера с volumes
echo Запуск контейнера...
docker run -d --name mobilede ^
  -v %cd%\..\var\www\mobile:/app/var/www/mobile ^
  -v %cd%\..\logs:/app/logs ^
  -v %cd%\..\configuration.yaml:/app/configuration.yaml ^
  -v %cd%\..\proxies.txt:/app/proxies.txt ^
  mobilede-parser:latest

pause
