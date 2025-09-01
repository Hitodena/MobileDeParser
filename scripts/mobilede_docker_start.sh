#!/bin/bash

# Скрипт для запуска MobileDe Parser в Docker контейнере
# Используется службой mobilede_bot.service

PROJECT_DIR="/var/www/mobile/parser"
SCRIPTS_DIR="$PROJECT_DIR/scripts"
CONTAINER_NAME="mobilede"
IMAGE_NAME="mobilede-parser:latest"

echo "=== Запуск MobileDe Parser в Docker ==="

# Переходим в директорию скриптов
cd "$SCRIPTS_DIR"

# Остановка и удаление существующего контейнера
echo "Проверка существующего контейнера..."
if sudo docker ps -a | grep -q "$CONTAINER_NAME"; then
    echo "Остановка существующего контейнера..."
    sudo docker stop "$CONTAINER_NAME" 2>/dev/null
    echo "Удаление существующего контейнера..."
    sudo docker rm "$CONTAINER_NAME" 2>/dev/null
fi

# Сборка образа
echo "Сборка Docker образа..."
sudo docker build -t "$IMAGE_NAME" -f "$PROJECT_DIR/docker/Dockerfile" "$PROJECT_DIR"

if [ $? -ne 0 ]; then
    echo "Ошибка при сборке Docker образа"
    exit 1
fi

# Запуск контейнера
echo "Запуск нового контейнера..."
sudo docker run -d --name "$CONTAINER_NAME" \
  --restart=unless-stopped \
  -v /var/www/mobile:/app/var/www/mobile \
  -v "$PROJECT_DIR/logs":/app/logs \
  -v "$PROJECT_DIR/configuration.yaml":/app/configuration.yaml \
  -v "$PROJECT_DIR/proxies.txt":/app/proxies.txt \
  "$IMAGE_NAME"

if [ $? -eq 0 ]; then
    echo "✓ Контейнер $CONTAINER_NAME успешно запущен"

    # Ждем немного и проверяем статус
    sleep 5
    if sudo docker ps | grep -q "$CONTAINER_NAME"; then
        echo "✓ Контейнер работает корректно"
        sudo docker ps | grep "$CONTAINER_NAME"
    else
        echo "✗ Контейнер остановился после запуска"
        echo "Логи контейнера:"
        sudo docker logs "$CONTAINER_NAME"
        exit 1
    fi
else
    echo "✗ Ошибка при запуске контейнера"
    exit 1
fi

echo "=== Запуск завершен ==="
