#!/bin/bash

# Остановка и удаление существующего контейнера

if sudo docker ps -a | grep -q mobilede; then
    sudo docker stop mobilede
    sudo docker rm mobilede
fi

# Сборка образа
sudo docker build -t mobilede-parser:latest -f ../docker/Dockerfile ..

# Запуск контейнера с volumes
sudo docker run -d --name mobilede \
  -v /var/www/mobile:/app/var/www/mobile \
  -v $(pwd)/../logs:/app/logs \
  -v $(pwd)/../configuration.yaml:/app/configuration.yaml \
  -v $(pwd)/../proxies.txt:/app/proxies.txt \
  mobilede-parser:latest
