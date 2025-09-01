#!/bin/bash

# Скрипт для остановки MobileDe Parser Docker контейнера
# Используется службой mobilede_bot.service

CONTAINER_NAME="mobilede"

echo "=== Остановка MobileDe Parser Docker контейнера ==="

# Проверяем, существует ли контейнер
if docker ps -a | grep -q "$CONTAINER_NAME"; then
    echo "Остановка контейнера $CONTAINER_NAME..."

    # Мягкая остановка
    docker stop "$CONTAINER_NAME"

    if [ $? -eq 0 ]; then
        echo "✓ Контейнер $CONTAINER_NAME остановлен"

        # Удаляем контейнер
        echo "Удаление контейнера..."
        docker rm "$CONTAINER_NAME"

        if [ $? -eq 0 ]; then
            echo "✓ Контейнер $CONTAINER_NAME удален"
        else
            echo "⚠ Не удалось удалить контейнер $CONTAINER_NAME"
        fi
    else
        echo "✗ Ошибка при остановке контейнера $CONTAINER_NAME"

        # Принудительная остановка
        echo "Попытка принудительной остановки..."
        docker kill "$CONTAINER_NAME" 2>/dev/null
        docker rm "$CONTAINER_NAME" 2>/dev/null
    fi
else
    echo "⚠ Контейнер $CONTAINER_NAME не найден"
fi

echo "=== Остановка завершена ==="
