#!/bin/bash
# Script de Reorganização dos Projetos Vya BackupDB
# Data: 09/01/2026
# Autor: Yves Marinho

set -e

echo "🔧 Iniciando reorganização dos projetos..."

# =============================================================================
# PROJETO 1: vya_backupbd (Sistema de Templates)
# =============================================================================
echo ""
echo "📁 [1/3] Reorganizando vya_backupbd..."

cd /home/yves_marinho/Documentos/DevOps/Vya-Jobs/vya_backupbd

# Criar estrutura de pastas
mkdir -p scripts/utils
mkdir -p examples
mkdir -p docs/build
mkdir -p docs/legacy

# Mover arquivos desorganizados
echo "  → Movendo convert_readme.py para scripts/utils/"
[ -f convert_readme.py ] && mv convert_readme.py scripts/utils/

echo "  → Movendo check_versions.sh para scripts/utils/"
[ -f check_versions.sh ] && mv check_versions.sh scripts/utils/

echo "  → Movendo demo_improvements.py para examples/"
[ -f demo_improvements.py ] && mv demo_improvements.py examples/

echo "  → Movendo test_config_improvements.py para tests/"
[ -f test_config_improvements.py ] && mv test_config_improvements.py tests/

echo "  → Movendo README.html para docs/build/"
[ -f README.html ] && mv README.html docs/build/

echo "  → Movendo requirements-old.txt para docs/legacy/"
[ -f requirements-old.txt ] && mv requirements-old.txt docs/legacy/

echo "  → Removendo test_output.txt (arquivo temporário)"
[ -f test_output.txt ] && rm test_output.txt

echo "  ✅ vya_backupbd reorganizado!"

# =============================================================================
# PROJETO 2: enterprise-vya_backupbd (Legacy)
# =============================================================================
echo ""
echo "📁 [2/3] Reorganizando enterprise-vya_backupbd..."

cd /home/yves_marinho/Documentos/DevOps/Vya-Jobs/enterprise-vya_backupbd

# Criar estrutura de pastas
mkdir -p src
mkdir -p scripts/install
mkdir -p scripts/database
mkdir -p docs/corrections

# Mover arquivos desorganizados
echo "  → Movendo main.py para src/"
[ -f main.py ] && mv main.py src/

echo "  → Movendo install_sys.sh para scripts/install/"
[ -f install_sys.sh ] && mv install_sys.sh scripts/install/

echo "  → Movendo create_mysql_backup_user.sql para scripts/database/"
[ -f create_mysql_backup_user.sql ] && mv create_mysql_backup_user.sql scripts/database/

echo "  → Movendo CORRECAO_BACKUP_POSTGRESQL.md para docs/corrections/"
[ -f CORRECAO_BACKUP_POSTGRESQL.md ] && mv CORRECAO_BACKUP_POSTGRESQL.md docs/corrections/

echo "  ✅ enterprise-vya_backupbd reorganizado!"

# =============================================================================
# PROJETO 3: enterprise-vya-backupdb (Principal)
# =============================================================================
echo ""
echo "📁 [3/3] Criando estrutura para enterprise-vya-backupdb..."

cd /home/yves_marinho/Documentos/DevOps/Vya-Jobs/enterprise-vya-backupdb

# Criar estrutura de pastas completa (se não existir)
mkdir -p src/vya_backupbd/{core,modules,utils,config}
mkdir -p docs/{architecture,api,guides,legacy,technical}
mkdir -p scripts/{install,database,maintenance,utils}
mkdir -p tests/{unit,integration,e2e}
mkdir -p examples/configurations
mkdir -p config/templates

# Criar arquivos __init__.py vazios
touch src/vya_backupbd/__init__.py
touch src/vya_backupbd/core/__init__.py
touch src/vya_backupbd/modules/__init__.py
touch src/vya_backupbd/utils/__init__.py
touch src/vya_backupbd/config/__init__.py

echo "  ✅ enterprise-vya-backupdb estruturado!"

# =============================================================================
# Finalização
# =============================================================================
echo ""
echo "✅ Reorganização concluída com sucesso!"
echo ""
echo "📊 Resumo das mudanças:"
echo "  • vya_backupbd: 7 arquivos reorganizados"
echo "  • enterprise-vya_backupbd: 4 arquivos reorganizados"
echo "  • enterprise-vya-backupdb: Estrutura de pastas criada"
echo ""
echo "🚀 Próximos passos:"
echo "  1. Verificar se algum script/código referencia os arquivos movidos"
echo "  2. Atualizar imports e paths nos códigos"
echo "  3. Testar funcionalidades após reorganização"
echo "  4. Commitar mudanças no git"
echo ""
