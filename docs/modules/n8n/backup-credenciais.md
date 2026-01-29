# Backup de Credenciais no N8N Versão 2.3.0

## Visão Geral

Este documento descreve o procedimento para realizar backup das credenciais no N8N versão 2.3.0. As credenciais no N8N são essenciais para autenticação com serviços externos, como APIs de terceiros (ex.: Google, Slack, etc.). O backup permite preservar essas credenciais para restauração em caso de falha, migração ou atualização do sistema.

## Pré-requisitos

- N8N versão 2.3.0 instalado e em execução.
- Acesso ao terminal ou linha de comando onde o N8N está rodando (ex.: via Docker, npm ou binário).
- Permissões adequadas para executar comandos CLI do N8N.
- Diretório de saída acessível para armazenar os arquivos de backup.
- Chave de criptografia (N8N_ENCRYPTION_KEY) configurada, pois as credenciais são exportadas criptografadas.

## Procedimento de Backup

### Passo 1: Parar o N8N (Opcional, mas Recomendado)

Para evitar inconsistências durante o backup, especialmente em ambientes de produção, pare o N8N temporariamente:

```bash
# Se usando Docker
docker stop <container_name>

# Se usando npm ou binário
pkill -f n8n
```

### Passo 2: Executar o Comando de Exportação

Use o comando CLI `n8n export:credentials` para exportar todas as credenciais. O flag `--backup` preserva os IDs das credenciais, permitindo restauração precisa. O flag `--output` especifica o diretório ou arquivo de saída.

```bash
n8n export:credentials --backup --output=/caminho/para/backup/credenciais.json
```

- `--backup`: Ativa o modo backup, exportando credenciais com IDs preservados para restauração.
- `--output`: Caminho absoluto ou relativo para o arquivo de saída. Use um diretório para exportar em arquivos separados (recomendado para múltiplas credenciais).

#### Exemplo Completo

```bash
# Criar diretório de backup
mkdir -p /home/user/n8n-backups/credenciais

# Executar exportação
n8n export:credentials --backup --output=/home/user/n8n-backups/credenciais/
```

Isso gera arquivos JSON separados para cada credencial no diretório especificado, facilitando gerenciamento e versionamento.

#### Opções Adicionais

- `--all`: Exporta todas as credenciais (padrão se não especificado).
- `--id=<ID>`: Exporta apenas uma credencial específica pelo ID.
- `--pretty`: Formata o JSON de saída de forma legível (útil para depuração).

```bash
# Exportar credencial específica com formatação bonita
n8n export:credentials --id=abc123 --output=/backup/credencial-especifica.json --pretty
```

### Passo 3: Verificar o Backup

Após a exportação, verifique os arquivos gerados:

```bash
ls -la /caminho/para/backup/credenciais/
```

Certifique-se de que os arquivos JSON existem e não estão vazios. Abra um arquivo para confirmar que os dados estão criptografados e estruturados corretamente (ex.: campos como `id`, `name`, `type`, `data`).

### Passo 4: Armazenar o Backup de Forma Segura

- **Criptografia**: Os backups já são criptografados com a chave N8N_ENCRYPTION_KEY. Mantenha a chave segura separadamente.
- **Localização**: Armazene em local seguro, como disco externo, nuvem criptografada (ex.: AWS S3 com KMS) ou repositório Git encriptado.
- **Versionamento**: Use Git ou ferramentas como rsync para versionar backups.

```bash
# Exemplo de versionamento com Git
cd /caminho/para/backup
git init
git add credenciais/
git commit -m "Backup de credenciais N8N v2.3.0 - $(date)"
```

### Passo 5: Reiniciar o N8N

Após o backup, reinicie o N8N:

```bash
# Se usando Docker
docker start <container_name>

# Se usando npm
npm run start

# Ou binário
n8n start
```

## Considerações Técnicas

- **Criptografia**: As credenciais são sempre exportadas criptografadas. Sem a N8N_ENCRYPTION_KEY, elas não podem ser descriptografadas.
- **Estrutura do Arquivo**: Cada arquivo JSON contém metadados e dados criptografados. Exemplo estrutural (não descriptografado):

```json
{
  "id": "credencial-id",
  "name": "Nome da Credencial",
  "type": "tipo-da-credencial",
  "data": "dados-criptografados-base64"
}
```

- **Limitações**: O comando exporta apenas credenciais ativas. Credenciais deletadas não são incluídas.
- **Performance**: Para instâncias grandes, o backup pode levar tempo; monitore logs do N8N.
- **Compatibilidade**: Backups da v2.3.0 são compatíveis com versões futuras, mas verifique changelogs para mudanças em criptografia.

## Script Automatizado

Para automação, crie um script Bash:

```bash
#!/bin/bash
# backup-credenciais.sh

BACKUP_DIR="/home/user/n8n-backups/credenciais/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "Iniciando backup de credenciais N8N..."
n8n export:credentials --backup --output="$BACKUP_DIR/"
if [ $? -eq 0 ]; then
    echo "Backup concluído com sucesso em $BACKUP_DIR"
    # Opcional: upload para nuvem
    # aws s3 cp "$BACKUP_DIR" s3://meu-bucket-n8n-backups/ --recursive
else
    echo "Erro no backup. Verifique logs do N8N."
    exit 1
fi
```

Agende com cron:

```bash
# Editar crontab
crontab -e

# Adicionar linha para backup diário às 2 AM
0 2 * * * /caminho/para/backup-credenciais.sh
```

## Troubleshooting

- **Erro "Command not found"**: Certifique-se de que o binário N8N está no PATH ou use caminho absoluto.
- **Erro de Permissões**: Execute como usuário com acesso aos diretórios N8N e de backup.
- **Backup Vazio**: Verifique se há credenciais na instância e se a N8N_ENCRYPTION_KEY está configurada.
- **Logs**: Consulte logs do N8N em `/home/node/.n8n/logs` ou equivalente para erros detalhados.

## Referências

- Documentação Oficial N8N: https://docs.n8n.io/hosting/cli-commands/#export-workflows-and-credentials
- Changelog N8N: https://docs.n8n.io/release-notes/
- Repositório GitHub: https://github.com/n8n-io/n8n