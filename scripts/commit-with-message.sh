#!/bin/bash
# Script para commit seguindo regras do projeto
# Uso: ./scripts/commit-with-message.sh COMMIT_MESSAGE_FILE.txt

set -e

if [ $# -eq 0 ]; then
    echo "❌ Erro: Arquivo de mensagem não fornecido"
    echo "Uso: $0 COMMIT_MESSAGE_FILE.txt"
    exit 1
fi

COMMIT_MSG_FILE="$1"

if [ ! -f "$COMMIT_MSG_FILE" ]; then
    echo "❌ Erro: Arquivo não encontrado: $COMMIT_MSG_FILE"
    exit 1
fi

echo "📋 Mensagem de commit:"
echo "─────────────────────────────────────────────"
cat "$COMMIT_MSG_FILE"
echo "─────────────────────────────────────────────"
echo ""

# Mostrar status
echo "📦 Status do repositório:"
git status --short
echo ""

# Confirmar
read -p "✅ Confirmar commit? (s/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Ss]$ ]]; then
    echo "❌ Commit cancelado pelo usuário"
    exit 1
fi

# Executar commit
echo "🚀 Executando commit..."
git commit -F "$COMMIT_MSG_FILE"

# Verificar resultado
if [ $? -eq 0 ]; then
    echo "✅ Commit realizado com sucesso!"
    echo ""
    echo "📝 Últimos commits:"
    git log --oneline -5
    echo ""
    echo "💾 Arquivo de mensagem mantido para referência: $COMMIT_MSG_FILE"
else
    echo "❌ Erro ao executar commit"
    exit 1
fi
