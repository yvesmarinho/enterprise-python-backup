#!/bin/bash

#############################################################################
# Script de Renomeação do Projeto
# De: enterprise-python-backup
# Para: enterprise-python-backup
#
# Uso: ./scripts/rename_project.sh [github_username]
# Exemplo: ./scripts/rename_project.sh vya-digital
#
# IMPORTANTE: Execute APÓS renomear o repositório no GitHub!
#############################################################################

set -e  # Exit on error

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configurações
OLD_NAME="enterprise-python-backup"
NEW_NAME="enterprise-python-backup"
OLD_PACKAGE="python_backup"
NEW_PACKAGE="python_backup"
BACKUP_DIR="/tmp/backup_${OLD_NAME}_$(date +%Y%m%d_%H%M%S)"

# Usuário GitHub (argumento ou padrão)
GITHUB_USER="${1:-vya-digital}"
OLD_REMOTE="https://github.com/${GITHUB_USER}/${OLD_NAME}.git"
NEW_REMOTE="https://github.com/${GITHUB_USER}/${NEW_NAME}.git"

#############################################################################
# Funções
#############################################################################

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

check_git_status() {
    if [[ -n $(git status -s) ]]; then
        log_error "Existem mudanças não commitadas!"
        git status -s
        echo ""
        read -p "Deseja continuar mesmo assim? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

create_backup() {
    log_info "Criando backup em: ${BACKUP_DIR}"
    mkdir -p "${BACKUP_DIR}"
    
    # Backup de arquivos críticos
    cp -r src "${BACKUP_DIR}/"
    cp pyproject.toml "${BACKUP_DIR}/"
    cp -r docs "${BACKUP_DIR}/"
    cp README.md "${BACKUP_DIR}/" 2>/dev/null || true
    
    log_success "Backup criado com sucesso"
}

update_git_remote() {
    log_info "Atualizando URL do remote..."
    
    # Verificar remote atual
    CURRENT_REMOTE=$(git remote get-url origin)
    log_info "Remote atual: ${CURRENT_REMOTE}"
    
    # Atualizar para novo remote
    git remote set-url origin "${NEW_REMOTE}"
    
    # Verificar
    NEW_REMOTE_URL=$(git remote get-url origin)
    log_success "Novo remote: ${NEW_REMOTE_URL}"
}

rename_package_directory() {
    log_info "Renomeando pasta src/${OLD_PACKAGE}/ → src/${NEW_PACKAGE}/"
    
    if [[ -d "src/${OLD_PACKAGE}" ]]; then
        mv "src/${OLD_PACKAGE}" "src/${NEW_PACKAGE}"
        log_success "Pasta renomeada"
    else
        log_warning "Pasta src/${OLD_PACKAGE} não encontrada"
    fi
}

update_pyproject_toml() {
    log_info "Atualizando pyproject.toml..."
    
    sed -i.bak \
        -e "s/name = \"${OLD_PACKAGE}\"/name = \"${NEW_PACKAGE}\"/" \
        -e "s/${OLD_PACKAGE}/${NEW_PACKAGE}/g" \
        pyproject.toml
    
    rm pyproject.toml.bak
    log_success "pyproject.toml atualizado"
}

update_python_imports() {
    log_info "Atualizando imports Python..."
    
    # Encontrar todos arquivos .py e atualizar imports
    find src tests -name "*.py" -type f -exec sed -i.bak \
        -e "s/from ${OLD_PACKAGE}/from ${NEW_PACKAGE}/g" \
        -e "s/import ${OLD_PACKAGE}/import ${NEW_PACKAGE}/g" \
        {} \;
    
    # Remover backups
    find src tests -name "*.py.bak" -delete
    
    log_success "Imports atualizados"
}

update_documentation() {
    log_info "Atualizando documentação..."
    
    # Atualizar todos arquivos .md
    find docs -name "*.md" -type f -exec sed -i.bak \
        -e "s/${OLD_NAME}/${NEW_NAME}/g" \
        -e "s/${OLD_PACKAGE}/${NEW_PACKAGE}/g" \
        {} \;
    
    # Atualizar README.md
    if [[ -f "README.md" ]]; then
        sed -i.bak \
            -e "s/${OLD_NAME}/${NEW_NAME}/g" \
            -e "s/${OLD_PACKAGE}/${NEW_PACKAGE}/g" \
            README.md
    fi
    
    # Remover backups
    find docs -name "*.md.bak" -delete
    rm -f README.md.bak
    
    log_success "Documentação atualizada"
}

update_copilot_rules() {
    log_info "Atualizando arquivos .copilot-*.md..."
    
    find . -maxdepth 1 -name ".copilot-*.md" -type f -exec sed -i.bak \
        -e "s/${OLD_NAME}/${NEW_NAME}/g" \
        -e "s/${OLD_PACKAGE}/${NEW_PACKAGE}/g" \
        {} \;
    
    # Remover backups
    find . -maxdepth 1 -name ".copilot-*.md.bak" -delete
    
    log_success "Arquivos copilot atualizados"
}

update_scripts() {
    log_info "Atualizando scripts..."
    
    # Atualizar scripts shell
    find scripts -name "*.sh" -type f -exec sed -i.bak \
        -e "s/${OLD_NAME}/${NEW_NAME}/g" \
        -e "s/${OLD_PACKAGE}/${NEW_PACKAGE}/g" \
        {} \;
    
    # Remover backups
    find scripts -name "*.sh.bak" -delete
    
    log_success "Scripts atualizados"
}

update_config_files() {
    log_info "Atualizando arquivos de configuração..."
    
    # Atualizar workspace file
    if [[ -f "${OLD_NAME}.code-workspace" ]]; then
        mv "${OLD_NAME}.code-workspace" "${NEW_NAME}.code-workspace"
        sed -i.bak \
            -e "s/${OLD_NAME}/${NEW_NAME}/g" \
            "${NEW_NAME}.code-workspace"
        rm -f "${NEW_NAME}.code-workspace.bak"
    fi
    
    # Atualizar python_backup.json se existir
    if [[ -f "python_backup.json" ]]; then
        log_warning "Arquivo python_backup.json mantido (usado em produção)"
        log_warning "Renomeie manualmente se necessário"
    fi
    
    log_success "Arquivos de config atualizados"
}

verify_changes() {
    log_info "Verificando mudanças..."
    
    echo ""
    echo "=== Arquivos modificados ==="
    git status -s
    echo ""
    
    echo "=== Estrutura src/ ==="
    ls -la src/
    echo ""
    
    # Verificar se ainda existem referências ao nome antigo
    log_info "Verificando referências ao nome antigo..."
    REFS=$(grep -r "${OLD_PACKAGE}" src/ tests/ docs/ 2>/dev/null | wc -l)
    
    if [[ $REFS -gt 0 ]]; then
        log_warning "Ainda existem ${REFS} referências a '${OLD_PACKAGE}'"
        grep -r "${OLD_PACKAGE}" src/ tests/ docs/ 2>/dev/null | head -10
    else
        log_success "Nenhuma referência ao nome antigo encontrada"
    fi
}

git_commit_changes() {
    log_info "Comitando mudanças..."
    
    # Add all changes
    git add -A
    
    # Commit
    git commit -m "refactor: rename project from ${OLD_NAME} to ${NEW_NAME}

- Rename package: ${OLD_PACKAGE} → ${NEW_PACKAGE}
- Update all Python imports
- Update documentation and README
- Update pyproject.toml
- Update scripts and config files
- Update Git remote to new repository name

Migration script: scripts/rename_project.sh"
    
    log_success "Mudanças commitadas"
}

#############################################################################
# Main
#############################################################################

main() {
    echo ""
    echo "=========================================="
    echo "  Renomeação do Projeto"
    echo "=========================================="
    echo "De: ${OLD_NAME}"
    echo "Para: ${NEW_NAME}"
    echo ""
    echo "Package: ${OLD_PACKAGE} → ${NEW_PACKAGE}"
    echo "Remote: ${NEW_REMOTE}"
    echo "=========================================="
    echo ""
    
    # Confirmação
    read -p "ATENÇÃO: Você JÁ renomeou o repositório no GitHub? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_error "Execute este script APÓS renomear no GitHub!"
        exit 1
    fi
    
    # Verificar se estamos no diretório correto
    if [[ ! -f "pyproject.toml" ]] || [[ ! -d "src/${OLD_PACKAGE}" ]]; then
        log_error "Execute este script a partir da raiz do projeto!"
        exit 1
    fi
    
    # Verificar Git status
    check_git_status
    
    # Criar backup
    create_backup
    
    # Executar mudanças
    update_git_remote
    rename_package_directory
    update_pyproject_toml
    update_python_imports
    update_documentation
    update_copilot_rules
    update_scripts
    update_config_files
    
    # Verificar
    verify_changes
    
    # Commit
    echo ""
    read -p "Deseja fazer commit das mudanças? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git_commit_changes
    else
        log_warning "Mudanças não commitadas. Execute manualmente:"
        echo "  git add -A"
        echo "  git commit -m 'refactor: rename project'"
    fi
    
    # Finalização
    echo ""
    echo "=========================================="
    log_success "Renomeação concluída!"
    echo "=========================================="
    echo ""
    echo "Próximos passos:"
    echo "1. Teste os imports: python -c 'import ${NEW_PACKAGE}'"
    echo "2. Execute os testes: pytest tests/"
    echo "3. Push das mudanças: git push origin main"
    echo "4. Renomeie a pasta local (opcional):"
    echo "   cd .."
    echo "   mv ${OLD_NAME} ${NEW_NAME}"
    echo "   cd ${NEW_NAME}"
    echo ""
    echo "Backup salvo em: ${BACKUP_DIR}"
    echo ""
}

# Executar
main "$@"
