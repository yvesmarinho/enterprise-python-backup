#!/bin/bash
set -e

# Este script garante que a senha do postgres seja sempre a configurada no .env
# Mesmo se o banco já existir no volume persistente

echo "Verificando/resetando senha do usuário postgres..."

# Aguardar PostgreSQL estar pronto
until pg_isready -U postgres > /dev/null 2>&1; do
  echo "Aguardando PostgreSQL iniciar..."
  sleep 1
done

# Resetar senha do postgres para a configurada no ambiente
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "postgres" <<-EOSQL
    ALTER USER postgres WITH PASSWORD '$POSTGRES_PASSWORD';
    \echo 'Senha do usuário postgres atualizada com sucesso!'
EOSQL

echo "Password reset completo."
