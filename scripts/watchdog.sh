

CONFIG_FILE="../configuration.yaml"
SETUP_SCRIPT="setup.sh"
CHECK_INTERVAL=30

echo "Starting configuration watcher..."
echo "Watching: $CONFIG_FILE"
echo "Setup script: $SETUP_SCRIPT"
echo "Check interval: ${CHECK_INTERVAL}s"
echo "Press Ctrl+C to stop"

# Получаем начальное время модификации файла
LAST_MODIFIED=$(stat -c %Y "$CONFIG_FILE" 2>/dev/null || stat -f %m "$CONFIG_FILE" 2>/dev/null)

while true; do
    # Получаем текущее время модификации файла
    CURRENT_MODIFIED=$(stat -c %Y "$CONFIG_FILE" 2>/dev/null || stat -f %m "$CONFIG_FILE" 2>/dev/null)

    # Проверяем, изменился ли файл
    if [ "$CURRENT_MODIFIED" != "$LAST_MODIFIED" ]; then
        echo "$(date): Configuration file changed, running setup.sh..."

        # Запускаем setup.sh
        if [ -f "$SETUP_SCRIPT" ]; then
            chmod +x "$SETUP_SCRIPT"
            ./"$SETUP_SCRIPT"
            echo "$(date): Setup completed"
        else
            echo "$(date): Error: $SETUP_SCRIPT not found"
        fi

        # Обновляем время последней модификации
        LAST_MODIFIED=$CURRENT_MODIFIED
    fi

    # Ждем перед следующей проверкой
    sleep $CHECK_INTERVAL
done
