#!/bin/bash
# git-commit-from-file.sh
# Faz commit usando mensagem de um arquivo de texto e depois exclui o arquivo
#
# Uso: ./git-commit-from-file.sh <arquivo-mensagem.txt>
#
# Exemplo:
#   echo "feat: minha feature" > /tmp/commit-msg.txt
#   ./git-commit-from-file.sh /tmp/commit-msg.txt

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
error() {
    echo -e "${RED}❌ Error: $1${NC}" >&2
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

info() {
    echo -e "ℹ️  $1"
}

# Check if file argument is provided
if [ $# -eq 0 ]; then
    error "Nenhum arquivo especificado"
    echo ""
    echo "Uso: $0 <arquivo-mensagem.txt>"
    echo ""
    echo "Exemplo:"
    echo "  $0 /tmp/commit-message.txt"
    exit 1
fi

COMMIT_MSG_FILE="$1"

# Check if file exists
if [ ! -f "$COMMIT_MSG_FILE" ]; then
    error "Arquivo não encontrado: $COMMIT_MSG_FILE"
    exit 1
fi

# Check if file is readable
if [ ! -r "$COMMIT_MSG_FILE" ]; then
    error "Arquivo não pode ser lido: $COMMIT_MSG_FILE"
    exit 1
fi

# Check if file is empty
if [ ! -s "$COMMIT_MSG_FILE" ]; then
    error "Arquivo está vazio: $COMMIT_MSG_FILE"
    exit 1
fi

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    error "Não está em um repositório git"
    exit 1
fi

# Check if there are staged changes
if git diff --cached --quiet; then
    warning "Nenhuma mudança staged para commit"
    info "Use 'git add' para adicionar arquivos antes de fazer commit"
    exit 1
fi

# Show the commit message that will be used
info "Mensagem de commit a ser usada:"
echo ""
echo "---BEGIN COMMIT MESSAGE---"
cat "$COMMIT_MSG_FILE"
echo ""
echo "---END COMMIT MESSAGE---"
echo ""

# Show staged files
info "Arquivos que serão commitados:"
git diff --cached --name-status
echo ""

# Confirm before committing
read -p "Continuar com o commit? (s/N): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[SsYy]$ ]]; then
    warning "Commit cancelado pelo usuário"
    exit 0
fi

# Perform the commit using the file content
info "Realizando commit..."

if git commit -F "$COMMIT_MSG_FILE"; then
    success "Commit realizado com sucesso!"
    
    # Get the commit hash
    COMMIT_HASH=$(git rev-parse --short HEAD)
    info "Commit hash: $COMMIT_HASH"
    
    # Delete the commit message file
    info "Excluindo arquivo de mensagem: $COMMIT_MSG_FILE"
    if rm "$COMMIT_MSG_FILE"; then
        success "Arquivo excluído com sucesso"
    else
        warning "Não foi possível excluir o arquivo: $COMMIT_MSG_FILE"
        warning "Você pode excluí-lo manualmente"
    fi
    
    # Show the commit log
    echo ""
    info "Detalhes do commit:"
    git log -1 --stat
    
    echo ""
    success "Processo concluído!"
    
else
    error "Falha ao realizar commit"
    warning "O arquivo de mensagem NÃO foi excluído: $COMMIT_MSG_FILE"
    exit 1
fi
