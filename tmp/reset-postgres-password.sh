#!/bin/bash
# Script para resetar a senha do postgres no container existente

echo "Resetando senha do usuário postgres para W123Mudar..."

docker exec -it postgresql psql -U postgres -c "ALTER USER postgres WITH PASSWORD 'W123Mudar';"

if [ $? -eq 0 ]; then
    echo "✅ Senha resetada com sucesso!"
    echo "Agora você pode conectar com: psql -h localhost -U postgres -W"
    echo "Senha: W123Mudar"
else
    echo "❌ Erro ao resetar senha. Verifique se o container está rodando e se o usuário postgres existe."
fi
