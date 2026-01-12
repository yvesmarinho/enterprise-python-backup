#!/bin/bash
set -e

# Este script é executado APÓS o PostgreSQL estar pronto
# Reseta a senha do postgres para a configurada no .env

echo "🔧 Verificando/atualizando senha do usuário postgres..."

# Resetar senha do postgres
psql -v ON_ERROR_STOP=1 --username "postgres" --dbname "postgres" <<-EOSQL
    ALTER USER postgres WITH PASSWORD '${POSTGRES_PASSWORD}';
EOSQL

echo "✅ Senha do postgres atualizada com sucesso!"
