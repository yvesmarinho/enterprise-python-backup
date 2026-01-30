#!/bin/bash
# Script para remover arquivos sensíveis do histórico do Git
# Data: 2026-01-30
# ATENÇÃO: Este script reescreve o histórico do Git!

set -e

PROJECT_DIR="/home/yves_marinho/Documentos/DevOps/Vya-Jobs/enterprise-python-backup"
FILES_LIST="$PROJECT_DIR/tmp/files-to-remove.txt"

cd "$PROJECT_DIR"

echo "========================================"
echo "Git History Cleanup Script"
echo "========================================"
echo ""
echo "ATENÇÃO: Este script vai reescrever o histórico do Git!"
echo "Um backup foi criado em: enterprise-python-backup.backup-*"
echo ""
echo "Arquivos que serão removidos do histórico:"
cat "$FILES_LIST"
echo ""
echo "Pressione ENTER para continuar ou Ctrl+C para cancelar..."
read

echo ""
echo "[1/5] Verificando status do repositório..."
git status --short

echo ""
echo "[2/5] Removendo arquivos do histórico com git-filter-repo..."

# Remover cada arquivo do histórico
while IFS= read -r file; do
    if [ -n "$file" ]; then
        echo "  Removendo: $file"
        git filter-repo --invert-paths --path "$file" --force
    fi
done < "$FILES_LIST"

echo ""
echo "[3/5] Limpando refs e garbage collection..."
git reflog expire --expire=now --all
git gc --prune=now --aggressive

echo ""
echo "[4/5] Verificando tamanho do repositório..."
echo "Antes: Ver backup"
du -sh .git | awk '{print "Depois: " $1}'

echo ""
echo "[5/5] Verificando se arquivos foram removidos do histórico..."
for file in $(cat "$FILES_LIST"); do
    if git log --all --oneline -- "$file" | grep -q .; then
        echo "  ⚠️  AVISO: $file ainda aparece no histórico!"
    else
        echo "  ✅ $file removido do histórico"
    fi
done

echo ""
echo "========================================"
echo "Limpeza concluída com sucesso!"
echo "========================================"
echo ""
echo "PRÓXIMOS PASSOS:"
echo "1. Verifique as mudanças: git log --all --oneline | head -20"
echo "2. Teste o repositório localmente"
echo "3. Force push para o remote: git push origin --force --all"
echo "4. Force push das tags: git push origin --force --tags"
echo ""
echo "IMPORTANTE: Informe a equipe sobre o force push!"
echo "Outros desenvolvedores precisarão fazer: git pull --rebase"
echo ""
