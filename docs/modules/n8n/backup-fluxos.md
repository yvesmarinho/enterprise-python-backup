# Backup de Fluxos (Workflows) no N8N Versão 2.3.0

## Visão Geral

Este documento explica como fazer backup dos fluxos (workflows) no N8N versão 2.3.0. Workflows são as automações centrais do N8N, contendo nós, conexões e configurações. O backup permite recuperação em caso de perda de dados, migração ou atualizações.

## Pré-requisitos

- N8N v2.3.0 em execução.
- Acesso CLI.
- Diretório de saída para backups.
- Permissões para leitura/escrita.

## Procedimento de Backup

### Passo 1: Parar N8N (Recomendado)

```bash
docker stop <container> || pkill -f n8n
```

### Passo 2: Comando de Exportação

```bash
n8n export:workflow --backup --output=/caminho/backup/fluxos/
```

- `--backup`: Preserva IDs para restauração.
- `--output`: Diretório para arquivos JSON.

#### Exemplo

```bash
mkdir -p /backup/n8n/fluxos
n8n export:workflow --backup --output=/backup/n8n/fluxos/
```

#### Opções

- `--all`: Todas os workflows.
- `--id=<ID>`: Workflow específico.
- `--pretty`: JSON formatado.

### Passo 3: Verificação

```bash
ls -la /backup/n8n/fluxos/
# Verificar arquivos .json válidos
```

### Passo 4: Armazenamento Seguro

- Use Git ou nuvem para versionamento.
- Criptografe se sensível (workflows podem conter dados).

### Passo 5: Reinício

```bash
docker start <container> || n8n start
```

## Considerações Técnicas

- Estrutura JSON: id, name, nodes, connections, settings.
- Compatibilidade: Backups v2.3.0 funcionam em versões futuras.
- Limitações: Apenas workflows ativos.

## Script Automatizado

```bash
#!/bin/bash
BACKUP_DIR="/backup/fluxos/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"
n8n export:workflow --backup --output="$BACKUP_DIR/"
```

## Troubleshooting

- Verifique PATH e permissões.
- Logs em ~/.n8n/logs.

## Referências

- https://docs.n8n.io/hosting/cli-commands/#export-workflows-and-credentials
- https://github.com/n8n-io/n8n