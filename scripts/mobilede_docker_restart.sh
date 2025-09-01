#!/bin/bash

# Скрипт для перезапуска MobileDe Parser при изменении конфигурации
# Используется службой mobilede_configwatch.service

CONTAINER_NAME="mobilede"

echo "=== Перезапуск MobileDe Parser (изменение конфигурации) ==="
echo "$(date): Обнаружено изменение configuration.yaml"

# Остановка контейнера
echo "Остановка контейнера..."
/var/www/mobile/parser/scripts/mobilede_docker_stop.sh

# Небольшая пауза
sleep 2

# Запуск контейнера
echo "Запуск контейнера..."
/var/www/mobile/parser/scripts/mobilede_docker_start.sh

if [ $? -eq 0 ]; then
    echo "$(date): ✓ Перезапуск завершен успешно"
else
    echo "$(date): ✗ Ошибка при перезапуске"
    exit 1
fi
