#!/bin/bash
# Script para remover arquivos sensíveis do histórico do Git
# Data: 2026-01-30
# Método: git filter-branch (nativo do Git)
# ATENÇÃO: Este script reescreve o histórico do Git!

set -e

PROJECT_DIR="/home/yves_marinho/Documentos/DevOps/Vya-Jobs/enterprise-python-backup"

cd "$PROJECT_DIR"

echo "========================================"
echo "Git History Cleanup Script"
echo "========================================"
echo ""
echo "Backup criado em: enterprise-python-backup.backup-*"
echo ""
echo "Arquivos que serão removidos do histórico:"
echo "  - tmp/.env"
echo "  - .secrets/journey-test.json"
echo "  - .secrets/journey-dev.json"
echo "  - .secrets/vya_backupbd.json"
echo ""

echo "[1/4] Verificando status do repositório..."
git status --short

echo ""
echo "[2/4] Removendo arquivos do histórico com git filter-branch..."
echo "  (Isso pode levar alguns minutos...)"

# Remover os arquivos do histórico
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch tmp/.env .secrets/journey-test.json .secrets/journey-dev.json .secrets/vya_backupbd.json" \
  --prune-empty --tag-name-filter cat -- --all

echo ""
echo "[3/4] Limpando refs e garbage collection..."
rm -rf .git/refs/original/
git reflog expire --expire=now --all
git gc --prune=now --aggressive

echo ""
echo "[4/4] Verificando se arquivos foram removidos do histórico..."
REMOVED_COUNT=0
for file in "tmp/.env" ".secrets/journey-test.json" ".secrets/journey-dev.json" ".secrets/vya_backupbd.json"; do
    if git log --all --oneline -- "$file" 2>/dev/null | grep -q .; then
        echo "  ⚠️  AVISO: $file ainda aparece no histórico!"
    else
        echo "  ✅ $file removido do histórico"
        REMOVED_COUNT=$((REMOVED_COUNT + 1))
    fi
done

echo ""
echo "Tamanho atual do repositório:"
du -sh .git | awk '{print "  " $1}'

echo ""
echo "========================================"
echo "Limpeza concluída!"
echo "========================================"
echo "Arquivos removidos: $REMOVED_COUNT/4"
echo ""
echo "PRÓXIMOS PASSOS:"
echo "1. Verifique as mudanças: git log --all --oneline | head -20"
echo "2. Teste o repositório localmente"
echo "3. Force push para o remote (quando estiver pronto)"
echo "   git push origin --force --all"
echo "   git push origin --force --tags"
echo ""
echo "IMPORTANTE: Este é um force push!"
echo "Outros desenvolvedores precisarão clonar novamente ou fazer:"
echo "  git fetch origin"
echo "  git reset --hard origin/001-phase2-core-development"
echo ""
