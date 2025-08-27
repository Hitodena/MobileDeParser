FROM python:3.12-slim



# Устанавливаем uv
RUN apt-get update && apt-get install -y
RUN pip install --no-cache-dir uv

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем pyproject.toml и uv.lock
COPY pyproject.toml uv.lock ./

# Устанавливаем зависимости
RUN uv sync --frozen

# Копируем код приложения
COPY . .

# Запускаем приложение
CMD ["uv", "run", "main.py"]
