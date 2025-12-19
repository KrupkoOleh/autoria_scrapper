#!/bin/sh
set -e

echo "Чекаємо PostgreSQL..."
while ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER"; do
  sleep 1
done
echo "PostgreSQL готов!"

echo "Застосовуємо міграції..."
alembic upgrade head

echo "Запускаемл застосунок..."
exec "$@"
