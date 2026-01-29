# Restore de Fluxos (Workflows) no N8N Versão 2.3.0

## Visão Geral

Procedimento para restaurar workflows de backup no N8N v2.3.0.

## Pré-requisitos

- N8N v2.3.0.
- Arquivos de backup válidos.
- CLI acesso.

## Procedimento de Restore

### Passo 1: Preparação

Pare N8N e faça backup atual.

### Passo 2: Comando de Importação

```bash
n8n import:workflow --separate --input=/backup/fluxos/
```

- `--separate`: Arquivos separados.
- `--input`: Diretório de backup.

### Passo 3: Verificação

Inicie N8N e verifique workflows na UI.

## Considerações Técnicas

- Preserva IDs com --backup.
- Sobrescrita baseada em ID.

## Script

```bash
#!/bin/bash
n8n import:workflow --separate --input="$1"
```

## Troubleshooting

- Verifique criptografia e estrutura JSON.

## Referências

- https://docs.n8n.io/hosting/cli-commands/#import-workflows-and-credentials
- https://github.com/n8n-io/n8n