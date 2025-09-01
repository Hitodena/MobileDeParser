#!/bin/bash

# Скрипт для проверки готовности системы к установке служб MobileDe Parser

PROJECT_DIR="/var/www/mobile"
CONFIG_FILE="$PROJECT_DIR/configuration.yaml"
MAIN_FILE="$PROJECT_DIR/main.py"

echo "=== Проверка готовности MobileDe Parser ==="
echo

# Проверка существования директории проекта
echo "1. Проверка директории проекта..."
if [ -d "$PROJECT_DIR" ]; then
    echo "   ✓ Директория $PROJECT_DIR существует"
else
    echo "   ✗ Директория $PROJECT_DIR не найдена"
    echo "   Необходимо разместить проект в этой директории"
    exit 1
fi

# Проверка основного файла
echo "2. Проверка основного файла..."
if [ -f "$MAIN_FILE" ]; then
    echo "   ✓ Файл main.py найден"
else
    echo "   ✗ Файл main.py не найден в $PROJECT_DIR"
    exit 1
fi

# Проверка конфигурационного файла
echo "3. Проверка конфигурации..."
if [ -f "$CONFIG_FILE" ]; then
    echo "   ✓ Файл configuration.yaml найден"
else
    echo "   ✗ Файл configuration.yaml не найден в $PROJECT_DIR"
    exit 1
fi

# Проверка Docker
echo "4. Проверка Docker..."
if command -v docker &> /dev/null; then
    echo "   ✓ Docker установлен ($(docker --version))"

    # Проверка работы Docker
    if docker ps &> /dev/null; then
        echo "   ✓ Docker daemon запущен"
    else
        echo "   ✗ Docker daemon не запущен"
        echo "   Запустите Docker: sudo systemctl start docker"
        exit 1
    fi
else
    echo "   ✗ Docker не установлен"
    echo "   Установите Docker: https://docs.docker.com/engine/install/"
    exit 1
fi

# Проверка Dockerfile
echo "5. Проверка Dockerfile..."
cd "$PROJECT_DIR"
if [ -f "docker/Dockerfile" ]; then
    echo "   ✓ Файл docker/Dockerfile найден"
else
    echo "   ✗ Файл docker/Dockerfile не найден"
    exit 1
fi

# Проверка systemd
echo "6. Проверка systemd..."
if systemctl --version &> /dev/null; then
    echo "   ✓ systemd доступен"
else
    echo "   ✗ systemd не найден"
    echo "   Этот скрипт работает только в системах с systemd"
    exit 1
fi

# Проверка прав доступа
echo "7. Проверка прав доступа..."
if [ -w "/etc/systemd/system" ]; then
    echo "   ✓ Есть права для записи в /etc/systemd/system"
elif [ "$EUID" -eq 0 ]; then
    echo "   ✓ Запущено с правами root"
else
    echo "   ⚠ Для установки служб потребуются права root"
    echo "   Используйте sudo при установке"
fi

# Проверка существующих служб
echo "8. Проверка существующих служб..."
if systemctl list-unit-files | grep -q "mobilede_"; then
    echo "   ⚠ Обнаружены существующие службы MobileDe"
    echo "   Существующие службы:"
    systemctl list-unit-files | grep "mobilede_" | while read line; do
        echo "     - $line"
    done
    echo "   Для переустановки используйте: sudo ./mobilede_setup.sh uninstall"
else
    echo "   ✓ Службы MobileDe не установлены"
fi

# Проверка Docker контейнеров
echo "9. Проверка Docker контейнеров..."
if docker ps -a | grep -q "mobilede"; then
    echo "   ⚠ Обнаружен существующий контейнер mobilede"
    docker ps -a | grep mobilede | while read line; do
        echo "     $line"
    done
    echo "   Контейнер будет пересоздан при запуске"
else
    echo "   ✓ Контейнер mobilede не найден"
fi

echo
echo "=== Результат проверки ==="
echo "✓ Система готова к установке служб MobileDe Parser (Docker)"
echo
echo "Для установки выполните:"
echo "1. cd $PROJECT_DIR/scripts"
echo "2. chmod +x mobilede_*.sh"
echo "3. sudo ./mobilede_setup.sh install"
echo "4. sudo ./mobilede_setup.sh start"
echo
echo "Для проверки статуса:"
echo "   ./mobilede_setup.sh status"
