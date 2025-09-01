#!/bin/bash

# Скрипт для быстрого перезапуска MobileDe Parser (Docker)
# Использование: ./mobilede_restart.sh

echo "=== Перезапуск MobileDe Parser (Docker) ==="

# Останавливаем службы
echo "Остановка служб..."
sudo systemctl stop mobilede_bot.service
sudo systemctl stop mobilede_configwatch.path

# Ждем немного
sleep 2

# Запускаем службы
echo "Запуск служб..."
sudo systemctl start mobilede_bot.service
sudo systemctl start mobilede_configwatch.path

# Ждем немного для запуска контейнера
echo "Ожидание запуска Docker контейнера..."
sleep 5

# Показываем статус
echo "=== Статус служб ==="
sudo systemctl status mobilede_bot.service --no-pager -l
echo
sudo systemctl status mobilede_configwatch.path --no-pager -l

echo
echo "=== Статус Docker контейнера ==="
if sudo docker ps | grep -q mobilede; then
    echo "✓ Контейнер mobilede запущен"
    sudo docker ps | grep mobilede
    echo
    echo "Последние строки логов:"
    sudo docker logs mobilede --tail 5
else
    echo "✗ Контейнер mobilede не запущен"

    # Показываем логи службы для диагностики
    echo "Логи службы для диагностики:"
    sudo journalctl -u mobilede_bot.service --no-pager -n 10
fi

echo "=== Перезапуск завершен ==="
