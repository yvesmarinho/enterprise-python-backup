#!/bin/bash
set -e

# Script de entrypoint customizado para PostgreSQL
# Garante que a senha do postgres seja sempre a do .env, mesmo com volume persistente

echo "=== Custom PostgreSQL Entrypoint ==="

# Função para resetar senha após PostgreSQL estar pronto
reset_password_background() {
    echo "Iniciando processo de reset de senha em background..."
    
    # Aguardar PostgreSQL aceitar conexões (máximo 60 segundos)
    for i in {1..60}; do
        if pg_isready -U postgres > /dev/null 2>&1; then
            echo "PostgreSQL pronto após $i tentativas!"
            break
        fi
        sleep 1
    done
    
    # Resetar senha
    echo "Resetando senha do usuário postgres..."
    psql -U postgres -d postgres <<-EOSQL
        ALTER USER postgres WITH PASSWORD '${POSTGRES_PASSWORD}';
EOSQL
    
    if [ $? -eq 0 ]; then
        echo "✅ Senha do postgres resetada com sucesso!"
    else
        echo "⚠️  Não foi possível resetar senha"
    fi
}

# Iniciar reset de senha em background
(reset_password_background) &

# Executar o entrypoint original do PostgreSQL com todos os argumentos
echo "Iniciando PostgreSQL..."
exec /usr/local/bin/docker-entrypoint.sh "$@"
