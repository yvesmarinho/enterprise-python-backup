#!/bin/bash
# Script de Verificação Pós-Reorganização
# Data: 09/01/2026
# Autor: Yves Marinho
# Propósito: Verificar se há referências quebradas após reorganização

set -e

echo "🔍 Verificando referências após reorganização..."
echo ""

# =============================================================================
# Função auxiliar para busca
# =============================================================================
buscar_referencias() {
    local arquivo="$1"
    local projeto="$2"
    local caminho="$3"
    
    echo "🔎 Buscando referências a '$arquivo' em $projeto..."
    cd "$caminho"
    
    # Buscar em arquivos Python
    if grep -r --include="*.py" "$arquivo" . 2>/dev/null | grep -v ".pyc" | grep -v "__pycache__"; then
        echo "  ⚠️  Encontradas referências em arquivos Python"
    else
        echo "  ✅ Nenhuma referência em arquivos Python"
    fi
    
    # Buscar em Makefiles
    if grep -r --include="Makefile" "$arquivo" . 2>/dev/null; then
        echo "  ⚠️  Encontradas referências em Makefile"
    else
        echo "  ✅ Nenhuma referência em Makefile"
    fi
    
    # Buscar em shell scripts
    if grep -r --include="*.sh" "$arquivo" . 2>/dev/null; then
        echo "  ⚠️  Encontradas referências em scripts shell"
    else
        echo "  ✅ Nenhuma referência em scripts shell"
    fi
    
    echo ""
}

# =============================================================================
# PROJETO 1: python_backup
# =============================================================================
echo "═══════════════════════════════════════════════════════════════"
echo "📁 [1/2] Verificando python_backup..."
echo "═══════════════════════════════════════════════════════════════"

BASE_VYA="/home/yves_marinho/Documentos/DevOps/Vya-Jobs/python_backup"

buscar_referencias "convert_readme.py" "python_backup" "$BASE_VYA"
buscar_referencias "check_versions.sh" "python_backup" "$BASE_VYA"
buscar_referencias "demo_improvements.py" "python_backup" "$BASE_VYA"
buscar_referencias "test_config_improvements.py" "python_backup" "$BASE_VYA"
buscar_referencias "README.html" "python_backup" "$BASE_VYA"
buscar_referencias "requirements-old.txt" "python_backup" "$BASE_VYA"

# =============================================================================
# PROJETO 2: enterprise-python_backup
# =============================================================================
echo "═══════════════════════════════════════════════════════════════"
echo "📁 [2/2] Verificando enterprise-python_backup..."
echo "═══════════════════════════════════════════════════════════════"

BASE_ENTERPRISE="/home/yves_marinho/Documentos/DevOps/Vya-Jobs/enterprise-python_backup"

buscar_referencias "main.py" "enterprise-python_backup" "$BASE_ENTERPRISE"
buscar_referencias "install_sys.sh" "enterprise-python_backup" "$BASE_ENTERPRISE"
buscar_referencias "create_mysql_backup_user.sql" "enterprise-python_backup" "$BASE_ENTERPRISE"
buscar_referencias "CORRECAO_BACKUP_POSTGRESQL.md" "enterprise-python_backup" "$BASE_ENTERPRISE"

# =============================================================================
# Verificar estrutura criada
# =============================================================================
echo "═══════════════════════════════════════════════════════════════"
echo "📂 Verificando estrutura criada em enterprise-python-backup..."
echo "═══════════════════════════════════════════════════════════════"

BASE_MAIN="/home/yves_marinho/Documentos/DevOps/Vya-Jobs/enterprise-python-backup"

pastas_esperadas=(
    "src/python_backup/core"
    "src/python_backup/modules"
    "src/python_backup/utils"
    "src/python_backup/config"
    "docs/architecture"
    "docs/api"
    "docs/guides"
    "docs/legacy"
    "docs/technical"
    "scripts/install"
    "scripts/database"
    "scripts/maintenance"
    "scripts/utils"
    "tests/unit"
    "tests/integration"
    "tests/e2e"
    "examples/configurations"
    "config/templates"
)

for pasta in "${pastas_esperadas[@]}"; do
    if [ -d "$BASE_MAIN/$pasta" ]; then
        echo "  ✅ $pasta"
    else
        echo "  ❌ $pasta (NÃO ENCONTRADA)"
    fi
done

echo ""

# =============================================================================
# Verificar arquivos __init__.py
# =============================================================================
echo "═══════════════════════════════════════════════════════════════"
echo "🐍 Verificando arquivos __init__.py..."
echo "═══════════════════════════════════════════════════════════════"

init_files=(
    "src/python_backup/__init__.py"
    "src/python_backup/core/__init__.py"
    "src/python_backup/modules/__init__.py"
    "src/python_backup/utils/__init__.py"
    "src/python_backup/config/__init__.py"
)

for init_file in "${init_files[@]}"; do
    if [ -f "$BASE_MAIN/$init_file" ]; then
        echo "  ✅ $init_file"
    else
        echo "  ❌ $init_file (NÃO ENCONTRADO)"
    fi
done

echo ""

# =============================================================================
# Resumo
# =============================================================================
echo "═══════════════════════════════════════════════════════════════"
echo "📊 RESUMO DA VERIFICAÇÃO"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "✅ Verificação concluída!"
echo ""
echo "⚠️  Se houver referências encontradas acima, você precisa:"
echo "   1. Atualizar os imports nos arquivos Python"
echo "   2. Atualizar os paths nos scripts shell"
echo "   3. Atualizar as referências nos Makefiles"
echo ""
echo "🧪 Próximos passos recomendados:"
echo "   1. Executar testes existentes: cd python_backup && pytest tests/"
echo "   2. Testar Makefile: cd python_backup && make help"
echo "   3. Verificar imports: python -m py_compile src/**/*.py"
echo ""
