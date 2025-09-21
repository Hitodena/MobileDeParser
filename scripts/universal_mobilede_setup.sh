#!/bin/bash

# ===================================================================
# УНИВЕРСАЛЬНЫЙ СКРИПТ УПРАВЛЕНИЯ MOBILEDE PARSER
# ===================================================================
# Измените эти переменные для настройки копии парсера:

# === НАСТРОЙКИ КОПИИ ===
SERVICE_PREFIX="mobilede"          # Префикс для systemd служб (mobilede_bot.service, mobilede_configwatch.service)
CONTAINER_NAME="mobilede"          # Имя Docker контейнера
PROJECT_DIR="/var/www/mobile/parser"  # Путь к проекту
IMAGE_NAME="mobilede-parser:latest"   # Имя Docker образа

# === ДОПОЛНИТЕЛЬНЫЕ НАСТРОЙКИ ===
DATA_DIR="/var/www/mobile"         # Директория с данными
CONFIG_FILE="configuration.yaml"   # Имя конфигурационного файла
PROXY_FILE="proxies.txt"          # Имя файла с прокси

# ===================================================================
# НЕ МЕНЯЙТЕ НИЧЕГО НИЖЕ ЭТОЙ СТРОКИ
# ===================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYSTEMD_DIR="/etc/systemd/system"

BOT_SERVICE="${SERVICE_PREFIX}_bot.service"
CONFIGWATCH_SERVICE="${SERVICE_PREFIX}_configwatch.service"
CONFIGWATCH_PATH="${SERVICE_PREFIX}_configwatch.path"

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для вывода с цветом
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Функция для вывода справки
show_help() {
    echo "Универсальный скрипт управления MobileDe Parser"
    echo
    echo "Использование: $0 [КОМАНДА]"
    echo
    echo "Текущие настройки копии:"
    echo "  Префикс служб: $SERVICE_PREFIX"
    echo "  Контейнер: $CONTAINER_NAME"
    echo "  Проект: $PROJECT_DIR"
    echo "  Образ: $IMAGE_NAME"
    echo
    echo "Команды:"
    echo "  start     - Запустить контейнер"
    echo "  stop      - Остановить контейнер"
    echo "  restart   - Перезапустить контейнер"
    echo "  status    - Показать статус"
    echo "  logs      - Показать логи контейнера"
    echo "  install   - Установить systemd службы (автоматически заменяя старые)"
    echo "  uninstall - Удалить systemd службы"
    echo "  check     - Проверить готовность системы"
    echo "  help      - Показать эту справку"
    echo
    echo "Для изменения настроек отредактируйте переменные в начале скрипта"
}

# Функция проверки прав root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "Этот скрипт должен запускаться с правами root"
        echo "Попробуйте: sudo $0 $1"
        exit 1
    fi
}

# Функция запуска контейнера
start_container() {
    print_info "=== Запуск $CONTAINER_NAME в Docker ==="

    # Переходим в директорию скриптов
    cd "$SCRIPT_DIR" || {
        print_error "Не удалось перейти в директорию скриптов: $SCRIPT_DIR"
        exit 1
    }

    # Остановка и удаление существующего контейнера
    print_info "Проверка существующего контейнера..."
    if sudo docker ps -a | grep -q "$CONTAINER_NAME"; then
        print_warning "Остановка существующего контейнера..."
        sudo docker stop "$CONTAINER_NAME" 2>/dev/null
        print_info "Удаление существующего контейнера..."
        sudo docker rm "$CONTAINER_NAME" 2>/dev/null
    fi

    # Сборка образа
    print_info "Сборка Docker образа..."
    sudo docker build -t "$IMAGE_NAME" -f "$PROJECT_DIR/docker/Dockerfile" "$PROJECT_DIR"

    if [ $? -ne 0 ]; then
        print_error "Ошибка при сборке Docker образа"
        exit 1
    fi

    # Запуск контейнера
    print_info "Запуск нового контейнера..."
    sudo docker run -d --name "$CONTAINER_NAME" \
      --restart=unless-stopped \
      -v "$DATA_DIR:/app/var/www/mobile" \
      -v "$PROJECT_DIR/logs:/app/logs" \
      -v "$PROJECT_DIR/$CONFIG_FILE:/app/$CONFIG_FILE" \
      -v "$PROJECT_DIR/$PROXY_FILE:/app/$PROXY_FILE" \
      "$IMAGE_NAME"

    if [ $? -eq 0 ]; then
        print_status "Контейнер $CONTAINER_NAME успешно запущен"

        # Ждем немного и проверяем статус
        sleep 10
        if sudo docker ps | grep -q "$CONTAINER_NAME"; then
            print_status "Контейнер работает корректно"
            sudo docker ps | grep "$CONTAINER_NAME"
        else
            print_error "Контейнер остановился после запуска"
            echo "Логи контейнера:"
            sudo docker logs "$CONTAINER_NAME"
            exit 1
        fi
    else
        print_error "Ошибка при запуске контейнера"
        exit 1
    fi

    print_info "=== Запуск завершен ==="
}

# Функция остановки контейнера
stop_container() {
    print_info "=== Остановка $CONTAINER_NAME ==="

    # Проверяем, существует ли контейнер
    if sudo docker ps -a | grep -q "$CONTAINER_NAME"; then
        print_info "Остановка контейнера $CONTAINER_NAME..."

        # Мягкая остановка
        sudo docker stop "$CONTAINER_NAME"

        if [ $? -eq 0 ]; then
            print_status "Контейнер $CONTAINER_NAME остановлен"

            # Удаляем контейнер
            print_info "Удаление контейнера..."
            sudo docker rm "$CONTAINER_NAME"

            if [ $? -eq 0 ]; then
                print_status "Контейнер $CONTAINER_NAME удален"
            else
                print_warning "Не удалось удалить контейнер $CONTAINER_NAME"
            fi
        else
            print_error "Ошибка при остановке контейнера $CONTAINER_NAME"

            # Принудительная остановка
            print_warning "Попытка принудительной остановки..."
            sudo docker kill "$CONTAINER_NAME" 2>/dev/null
            sudo docker rm "$CONTAINER_NAME" 2>/dev/null
        fi
    else
        print_warning "Контейнер $CONTAINER_NAME не найден"
    fi

    print_info "=== Остановка завершена ==="
}

# Функция перезапуска контейнера
restart_container() {
    print_info "=== Перезапуск $CONTAINER_NAME ==="
    stop_container
    sleep 2
    start_container
    print_status "Перезапуск завершен"
}

# Функция показа статуса
show_status() {
    echo "=== Статус $SERVICE_PREFIX ==="
    echo

    # Статус служб
    echo "SystemD службы:"
    if sudo systemctl is-active --quiet "$BOT_SERVICE" 2>/dev/null; then
        print_status "$BOT_SERVICE: активна"
    else
        print_error "$BOT_SERVICE: не активна"
    fi

    if sudo systemctl is-active --quiet "$CONFIGWATCH_SERVICE" 2>/dev/null; then
        print_status "$CONFIGWATCH_SERVICE: активна"
    else
        print_error "$CONFIGWATCH_SERVICE: не активна"
    fi

    echo
    echo "Docker контейнеры:"
    if sudo docker ps | grep -q "$CONTAINER_NAME"; then
        print_status "$CONTAINER_NAME: запущен"
        sudo docker ps | grep "$CONTAINER_NAME"
    else
        print_error "$CONTAINER_NAME: не запущен"
        if sudo docker ps -a | grep -q "$CONTAINER_NAME"; then
            echo "Контейнер существует, но остановлен"
            sudo docker ps -a | grep "$CONTAINER_NAME"
        fi
    fi

    echo
    echo "Файлы проекта:"
    if [ -d "$PROJECT_DIR" ]; then
        print_status "Директория проекта: $PROJECT_DIR"
    else
        print_error "Директория проекта не найдена: $PROJECT_DIR"
    fi

    if [ -f "$PROJECT_DIR/$CONFIG_FILE" ]; then
        print_status "Конфигурационный файл: $PROJECT_DIR/$CONFIG_FILE"
    else
        print_error "Конфигурационный файл не найден: $PROJECT_DIR/$CONFIG_FILE"
    fi

    if [ -f "$PROJECT_DIR/$PROXY_FILE" ]; then
        print_status "Файл прокси: $PROJECT_DIR/$PROXY_FILE"
    else
        print_error "Файл прокси не найден: $PROJECT_DIR/$PROXY_FILE"
    fi
}

# Функция показа логов
show_logs() {
    if sudo docker ps -a | grep -q "$CONTAINER_NAME"; then
        print_info "Логи контейнера $CONTAINER_NAME:"
        sudo docker logs "$CONTAINER_NAME"
    else
        print_error "Контейнер $CONTAINER_NAME не найден"
    fi
}

# Функция установки служб
install_services() {
    check_root
    print_info "Установка служб $SERVICE_PREFIX..."

    # Проверяем наличие Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker не установлен. Установите Docker перед продолжением."
        exit 1
    fi

    # Проверяем и удаляем старые службы, если они существуют
    print_info "Проверка существующих служб..."
    if sudo systemctl list-unit-files | grep -q "${SERVICE_PREFIX}_"; then
        print_warning "Найдены существующие службы $SERVICE_PREFIX, удаляем..."
        sudo systemctl stop "${SERVICE_PREFIX}_bot.service" 2>/dev/null
        sudo systemctl stop "${SERVICE_PREFIX}_configwatch.path" 2>/dev/null
        sudo systemctl disable "${SERVICE_PREFIX}_bot.service" 2>/dev/null
        sudo systemctl disable "${SERVICE_PREFIX}_configwatch.path" 2>/dev/null

        sudo rm -f "$SYSTEMD_DIR/${SERVICE_PREFIX}_bot.service"
        sudo rm -f "$SYSTEMD_DIR/${SERVICE_PREFIX}_configwatch.service"
        sudo rm -f "$SYSTEMD_DIR/${SERVICE_PREFIX}_configwatch.path"

        sudo systemctl daemon-reload
        print_info "Старые службы удалены"

        # Также проверяем и удаляем старые скрипты, если они существуют
        if [ -f "$SCRIPT_DIR/${SERVICE_PREFIX}_docker_start.sh" ]; then
            print_warning "Найден старый скрипт ${SERVICE_PREFIX}_docker_start.sh, рекомендуется удалить вручную"
        fi
        if [ -f "$SCRIPT_DIR/${SERVICE_PREFIX}_docker_stop.sh" ]; then
            print_warning "Найден старый скрипт ${SERVICE_PREFIX}_docker_stop.sh, рекомендуется удалить вручную"
        fi
        if [ -f "$SCRIPT_DIR/${SERVICE_PREFIX}_docker_restart.sh" ]; then
            print_warning "Найден старый скрипт ${SERVICE_PREFIX}_docker_restart.sh, рекомендуется удалить вручную"
        fi
    fi

    # Создаем systemd service файлы
    print_info "Создание systemd service файлов..."

    # Bot service
    cat > "$SYSTEMD_DIR/$BOT_SERVICE" << EOF
[Unit]
Description=${SERVICE_PREFIX} Parser Bot
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$SCRIPT_DIR
User=root

ExecStart=$SCRIPT_DIR/universal_mobilede_setup.sh start
ExecStop=$SCRIPT_DIR/universal_mobilede_setup.sh stop

TimeoutStartSec=300
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
EOF

    # Config watch service
    cat > "$SYSTEMD_DIR/$CONFIGWATCH_SERVICE" << EOF
[Unit]
Description=Restart ${SERVICE_PREFIX} Parser on config change

[Service]
Type=oneshot
ExecStart=$SCRIPT_DIR/universal_mobilede_setup.sh restart
EOF

    # Config watch path
    cat > "$SYSTEMD_DIR/$CONFIGWATCH_PATH" << EOF
[Unit]
Description=Watch ${SERVICE_PREFIX} configuration file

[Path]
PathModified=$PROJECT_DIR/$CONFIG_FILE

[Install]
WantedBy=multi-user.target
EOF

    # Перезагружаем systemd
    print_info "Перезагрузка systemd..."
    sudo systemctl daemon-reload

    # Включаем автозапуск служб
    print_info "Включение автозапуска служб..."
    sudo systemctl enable "$BOT_SERVICE"
    sudo systemctl enable "$CONFIGWATCH_PATH"

    print_status "Службы установлены и включены в автозапуск:"
    echo "  - $BOT_SERVICE"
    echo "  - $CONFIGWATCH_SERVICE"
    echo "  - $CONFIGWATCH_PATH"

    print_info "Теперь можно запустить службы:"
    echo "  sudo $0 start"
}

# Функция удаления служб
uninstall_services() {
    check_root
    print_info "Удаление служб $SERVICE_PREFIX..."

    # Останавливаем и отключаем службы
    print_info "Остановка и отключение служб..."
    sudo systemctl stop "$BOT_SERVICE" 2>/dev/null
    sudo systemctl stop "$CONFIGWATCH_PATH" 2>/dev/null

    sudo systemctl disable "$BOT_SERVICE" 2>/dev/null
    sudo systemctl disable "$CONFIGWATCH_PATH" 2>/dev/null

    # Удаляем файлы служб
    print_info "Удаление файлов служб..."
    sudo rm -f "$SYSTEMD_DIR/$BOT_SERVICE"
    sudo rm -f "$SYSTEMD_DIR/$CONFIGWATCH_SERVICE"
    sudo rm -f "$SYSTEMD_DIR/$CONFIGWATCH_PATH"

    # Перезагружаем systemd
    print_info "Перезагрузка systemd..."
    sudo systemctl daemon-reload

    print_status "Службы удалены"
}

# Функция проверки готовности системы
check_system() {
    print_info "=== Проверка готовности $SERVICE_PREFIX ==="
    echo

    # Проверка директории проекта
    echo "1. Проверка директории проекта..."
    if [ -d "$PROJECT_DIR" ]; then
        print_status "Директория $PROJECT_DIR существует"
    else
        print_error "Директория $PROJECT_DIR не найдена"
        exit 1
    fi

    # Проверка основного файла
    echo "2. Проверка основного файла..."
    if [ -f "$PROJECT_DIR/main.py" ]; then
        print_status "Файл main.py найден"
    else
        print_error "Файл main.py не найден в $PROJECT_DIR"
        exit 1
    fi

    # Проверка конфигурационного файла
    echo "3. Проверка конфигурации..."
    if [ -f "$PROJECT_DIR/$CONFIG_FILE" ]; then
        print_status "Файл $CONFIG_FILE найден"
    else
        print_error "Файл $CONFIG_FILE не найден в $PROJECT_DIR"
        exit 1
    fi

    # Проверка Docker
    echo "4. Проверка Docker..."
    if command -v docker &> /dev/null; then
        print_status "Docker установлен ($(docker --version))"

        # Проверка работы Docker
        if sudo docker ps &> /dev/null; then
            print_status "Docker daemon запущен"
        else
            print_error "Docker daemon не запущен"
            echo "Запустите Docker: sudo systemctl start docker"
            exit 1
        fi
    else
        print_error "Docker не установлен"
        exit 1
    fi

    # Проверка Dockerfile
    echo "5. Проверка Dockerfile..."
    if [ -f "$PROJECT_DIR/docker/Dockerfile" ]; then
        print_status "Файл docker/Dockerfile найден"
    else
        print_error "Файл docker/Dockerfile не найден"
        exit 1
    fi

    # Проверка systemd
    echo "6. Проверка systemd..."
    if sudo systemctl --version &> /dev/null; then
        print_status "systemd доступен"
    else
        print_error "systemd не найден"
        exit 1
    fi

    # Проверка прав доступа
    echo "7. Проверка прав доступа..."
    if [ -w "$SYSTEMD_DIR" ]; then
        print_status "Есть права для записи в $SYSTEMD_DIR"
    elif [[ $EUID -eq 0 ]]; then
        print_status "Запущено с правами root"
    else
        print_warning "Для установки служб потребуются права root"
    fi

    # Проверка существующих служб
    echo "8. Проверка существующих служб..."
    if sudo systemctl list-unit-files | grep -q "${SERVICE_PREFIX}_"; then
        print_warning "Обнаружены существующие службы $SERVICE_PREFIX"
        sudo systemctl list-unit-files | grep "${SERVICE_PREFIX}_" | while read line; do
            echo "  - $line"
        done
    else
        print_status "Службы $SERVICE_PREFIX не установлены"
    fi

    # Проверка Docker контейнеров
    echo "9. Проверка Docker контейнеров..."
    if sudo docker ps -a | grep -q "$CONTAINER_NAME"; then
        print_warning "Обнаружен существующий контейнер $CONTAINER_NAME"
        sudo docker ps -a | grep "$CONTAINER_NAME" | while read line; do
            echo "  $line"
        done
    else
        print_status "Контейнер $CONTAINER_NAME не найден"
    fi

    echo
    print_status "Система готова к установке служб $SERVICE_PREFIX"
    echo
    print_info "Для установки выполните:"
    echo "  sudo $0 install"
    echo "  sudo $0 start"
}

# Основная логика скрипта
case "${1:-help}" in
    "start")
        check_root
        start_container
        ;;
    "stop")
        check_root
        stop_container
        ;;
    "restart")
        check_root
        restart_container
        ;;
    "status")
        show_status
        ;;
    "logs")
        show_logs
        ;;
    "install")
        install_services
        ;;
    "uninstall")
        uninstall_services
        ;;
    "check")
        check_system
        ;;
    "help"|*)
        show_help
        ;;
esac
