#!/bin/bash

# Скрипт для управления службами MobileDe Parser
# Использование: ./mobilede_setup.sh [install|start|stop|restart|status|uninstall]

SERVICE_PREFIX="mobilede"
BOT_SERVICE="${SERVICE_PREFIX}_bot.service"
CONFIGWATCH_SERVICE="${SERVICE_PREFIX}_configwatch.service"
CONFIGWATCH_PATH="${SERVICE_PREFIX}_configwatch.path"

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
SYSTEMD_DIR="/etc/systemd/system"

# Функция для вывода справки
show_help() {
    echo "Управление службами MobileDe Parser"
    echo
    echo "Использование: $0 [КОМАНДА]"
    echo
    echo "Команды:"
    echo "  install    - Установить службы"
    echo "  start      - Запустить службы"
    echo "  stop       - Остановить службы"
    echo "  restart    - Перезапустить службы"
    echo "  status     - Показать статус служб"
    echo "  uninstall  - Удалить службы"
    echo "  help       - Показать эту справку"
}

# Функция для проверки прав root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        echo "Ошибка: Этот скрипт должен запускаться с правами root"
        echo "Попробуйте: sudo $0 $1"
        exit 1
    fi
}

# Функция установки служб
install_services() {
    echo "Установка служб MobileDe Parser..."

    # Проверяем наличие Docker
    if ! command -v docker &> /dev/null; then
        echo "✗ Docker не установлен. Установите Docker перед продолжением."
        exit 1
    fi

    # Делаем Docker скрипты исполняемыми
    chmod +x "$SCRIPT_DIR"/mobilede_docker_*.sh

    # Копируем файлы служб
    cp "$SCRIPT_DIR/$BOT_SERVICE" "$SYSTEMD_DIR/"
    cp "$SCRIPT_DIR/$CONFIGWATCH_SERVICE" "$SYSTEMD_DIR/"
    cp "$SCRIPT_DIR/$CONFIGWATCH_PATH" "$SYSTEMD_DIR/"

    # Перезагружаем systemd
    systemctl daemon-reload

    # Включаем службы
    systemctl enable "$BOT_SERVICE"
    systemctl enable "$CONFIGWATCH_SERVICE"
    systemctl enable "$CONFIGWATCH_PATH"

    echo "Службы установлены и включены в автозагрузку"
    echo "Для запуска используйте: $0 start"
}

# Функция запуска служб
start_services() {
    echo "Запуск служб MobileDe Parser..."

    # Сначала делаем Docker скрипты исполняемыми
    chmod +x /var/www/mobile/parser/scripts/mobilede_docker_*.sh

    systemctl start "$BOT_SERVICE"
    systemctl start "$CONFIGWATCH_PATH"

    echo "Службы запущены"
    echo "Проверка статуса Docker контейнера..."
    sleep 3
    docker ps | grep mobilede || echo "⚠ Контейнер не найден"
}

# Функция остановки служб
stop_services() {
    echo "Остановка служб MobileDe Parser..."

    systemctl stop "$BOT_SERVICE"
    systemctl stop "$CONFIGWATCH_SERVICE"
    systemctl stop "$CONFIGWATCH_PATH"

    echo "Службы остановлены"
}

# Функция перезапуска служб
restart_services() {
    echo "Перезапуск служб MobileDe Parser..."

    systemctl restart "$BOT_SERVICE"
    systemctl restart "$CONFIGWATCH_PATH"

    echo "Службы перезапущены"
}

# Функция показа статуса
show_status() {
    echo "Статус служб MobileDe Parser:"
    echo

    echo "=== Основная служба бота ==="
    systemctl status "$BOT_SERVICE" --no-pager -l
    echo

    echo "=== Мониторинг конфигурации ==="
    systemctl status "$CONFIGWATCH_PATH" --no-pager -l
    echo

    echo "=== Docker контейнер ==="
    if docker ps | grep -q mobilede; then
        echo "✓ Контейнер mobilede запущен"
        docker ps | grep mobilede
        echo
        echo "Последние 10 строк логов контейнера:"
        docker logs mobilede --tail 10
    else
        echo "✗ Контейнер mobilede не запущен"

        # Проверяем остановленные контейнеры
        if docker ps -a | grep -q mobilede; then
            echo "Найден остановленный контейнер:"
            docker ps -a | grep mobilede
        fi
    fi
    echo

    echo "=== Журналы служб ==="
    echo "Последние 10 строк журнала службы:"
    journalctl -u "$BOT_SERVICE" --no-pager -n 10
}

# Функция удаления служб
uninstall_services() {
    echo "Удаление служб MobileDe Parser..."

    # Останавливаем службы
    systemctl stop "$BOT_SERVICE" 2>/dev/null
    systemctl stop "$CONFIGWATCH_SERVICE" 2>/dev/null
    systemctl stop "$CONFIGWATCH_PATH" 2>/dev/null

    # Останавливаем и удаляем Docker контейнер
    echo "Остановка Docker контейнера..."
    if docker ps -a | grep -q mobilede; then
        docker stop mobilede 2>/dev/null
        docker rm mobilede 2>/dev/null
        echo "Docker контейнер удален"
    fi

    # Отключаем службы
    systemctl disable "$BOT_SERVICE" 2>/dev/null
    systemctl disable "$CONFIGWATCH_SERVICE" 2>/dev/null
    systemctl disable "$CONFIGWATCH_PATH" 2>/dev/null

    # Удаляем файлы
    rm -f "$SYSTEMD_DIR/$BOT_SERVICE"
    rm -f "$SYSTEMD_DIR/$CONFIGWATCH_SERVICE"
    rm -f "$SYSTEMD_DIR/$CONFIGWATCH_PATH"

    # Перезагружаем systemd
    systemctl daemon-reload

    echo "Службы удалены"
}

# Основная логика
case "$1" in
    install)
        check_root "$1"
        install_services
        ;;
    start)
        check_root "$1"
        start_services
        ;;
    stop)
        check_root "$1"
        stop_services
        ;;
    restart)
        check_root "$1"
        restart_services
        ;;
    status)
        show_status
        ;;
    uninstall)
        check_root "$1"
        uninstall_services
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "Ошибка: Неизвестная команда '$1'"
        echo
        show_help
        exit 1
        ;;
esac
