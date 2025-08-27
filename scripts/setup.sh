#!/bin/bash

# Остановка и удаление существующего контейнера

if docker ps -a | grep -q mobilede; then
    docker stop mobilede
    docker rm mobilede
fi

# Сборка образа
docker build -t mobilede-parser:latest -f ../docker/Dockerfile ..

# Запуск контейнера с volumes
docker run -d --name mobilede \
  -v $(pwd)/var/www/mobile:/app/var/www/mobile \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/configuration.yaml:/app/configuration.yaml \
  -v $(pwd)/proxies.txt:/app/proxies.txt \
  mobilede-parser:latest
