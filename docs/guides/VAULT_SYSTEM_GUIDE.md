# Vault System - Guia de Uso

Sistema de gerenciamento seguro de credenciais com criptografia Fernet.

## Visão Geral

O **Vault System** é um sistema interno de armazenamento seguro de credenciais que:

- ✅ Criptografa credenciais com Fernet (chave baseada no hostname)
- ✅ Armazena credenciais em arquivo único `.secrets/vault.json.enc`
- ✅ Fornece interface CLI para gerenciamento CRUD
- ✅ Mantém metadados (timestamps, descrições)
- ✅ Cache em memória para performance
- ✅ Permissões seguras (600 - somente owner)

## Arquitetura

```
┌─────────────────────────────────────────────────────────┐
│                  CLI Commands                           │
│  vault-add | vault-get | vault-list | vault-remove     │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                  VaultManager                           │
│  • set(id, user, pass, desc)                           │
│  • get(id) → {username, password}                       │
│  • remove(id)                                           │
│  • list_credentials()                                   │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│              EncryptionManager                          │
│  • encrypt_bytes() / decrypt_bytes()                    │
│  • Fernet with hostname-based key                       │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│          .secrets/vault.json.enc                        │
│  (arquivo criptografado, permissões 600)                │
└─────────────────────────────────────────────────────────┘
```

## Estrutura do Vault

### Formato Interno (descriptografado)

```json
{
  "version": "1.0.0",
  "credentials": {
    "mysql-prod": {
      "username": "gAAAAABl...",  // criptografado
      "password": "gAAAAABl...",  // criptografado
      "metadata": {
        "created_at": "2026-01-15T19:16:32.869462+00:00",
        "updated_at": "2026-01-15T19:16:32.869466+00:00",
        "description": "MYSQL 154.53.36.3:3306"
      }
    }
  }
}
```

### Arquivo no Disco

O arquivo `.secrets/vault.json.enc` é **completamente criptografado** (não apenas as senhas):

```bash
$ cat .secrets/vault.json.enc
gAAAAABl8rNwq5F...encrypted_binary_data...X2Pz==  # binário criptografado
```

## Comandos CLI

### 1. Adicionar/Atualizar Credencial

#### Modo Individual

```bash
# Adicionar nova credencial
vya-backupdb vault-add \
  --id mysql-prod \
  --username root \
  --password "SecureP@ssw0rd" \
  --description "Production MySQL Server"

# Atualizar credencial existente
vya-backupdb vault-add \
  --id mysql-prod \
  --username admin \
  --password "NewP@ssw0rd"
```

**Saída:**
```
✓ Added: Credential 'mysql-prod'
  Username: root
  Description: Production MySQL Server
  Vault: .secrets/vault.json.enc
```

#### Modo Lote (Batch Import)

```bash
# Importar múltiplas credenciais de um arquivo JSON
vya-backupdb vault-add --from-file credentials.json
```

**Formato do JSON:**
```json
[
  {
    "id": "mysql-prod",
    "username": "root",
    "password": "SecureP@ss123",
    "description": "Production MySQL"
  },
  {
    "id": "postgresql-prod",
    "username": "postgres",
    "password": "PostgresP@ss456"
  }
]
```

**Saída:**
```
Importing credentials from 'credentials.json'...

Adding credential 'mysql-prod'...
Adding credential 'postgresql-prod'...

Import Summary:
  Added: 2
  Updated: 0
  Vault: .secrets/vault.json.enc
```

**Documentação Completa:** [VAULT_BATCH_IMPORT_GUIDE.md](VAULT_BATCH_IMPORT_GUIDE.md)

### 2. Recuperar Credencial

```bash
# Ver credencial (senha oculta)
vya-backupdb vault-get --id mysql-prod

# Ver credencial com senha
vya-backupdb vault-get --id mysql-prod --show-password
```

**Saída:**
```
✓ Found: Credential 'mysql-prod'
  Username: root
  Password: SecureP@ssw0rd
  Description: Production MySQL Server
  Created: 2026-01-15T19:16:32.869462+00:00
  Updated: 2026-01-15T19:16:32.869466+00:00
```

### 3. Listar Credenciais

```bash
vya-backupdb vault-list
```

**Saída:**
```
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┓
┃ ID                 ┃ Username     ┃ Description             ┃ Updated             ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━┩
│ mysql-1            │ root         │ MYSQL 154.53.36.3:3306  │ 2026-01-15T19:16:32 │
│ postgresql-2       │ root         │ POSTGRES 154.53.36.3... │ 2026-01-15T19:16:32 │
└────────────────────┴──────────────┴─────────────────────────┴─────────────────────┘

Vault: .secrets/vault.json.enc
Size: 2.0 KB | Version: 1.0.0
```

### 4. Remover Credencial

```bash
# Remover com confirmação
vya-backupdb vault-remove --id mysql-old

# Remover sem confirmação
vya-backupdb vault-remove --id mysql-old --force
```

**Saída:**
```
✓ Removed: Credential 'mysql-old'
```

### 5. Informações do Vault

```bash
vya-backupdb vault-info
```

**Saída:**
```
Vault: .secrets/vault.json.enc
Version: 1.0.0
Credentials: 3
File Size: 2.04 KB
Cached: 0 credential(s)
Permissions: 600

✓ Vault is healthy
```

## Migração de Credenciais

### Script de Migração Automática

Migra credenciais de `vya_backupbd.json` para o vault:

```bash
# Dry-run (não salva, apenas mostra)
python scripts/utils/migrate_to_vault.py --dry-run

# Migração real
python scripts/utils/migrate_to_vault.py

# Especificar caminhos
python scripts/utils/migrate_to_vault.py \
  --config /path/to/config.json \
  --vault /path/to/vault.json.enc
```

**Saída:**
```
Loading configuration: .secrets/vya_backupbd.json
Vault: .secrets/vault.json.enc

[SMTP] smtp-email-ssl.com.br
  Username: no-reply@vya.digital
  Password: ********************
  Description: SMTP email-ssl.com.br (port 465)
  ✓ Migrated

[MYSQL] mysql-1
  Username: root
  Password: *******
  Description: MYSQL 154.53.36.3:3306
  ✓ Migrated

[POSTGRESQL] postgresql-2
  Username: root
  Password: *******
  Description: POSTGRESQL 154.53.36.3:5432
  ✓ Migrated

============================================================
Migration Summary:
  Credentials: 3
  Status: COMPLETED
  Vault: .secrets/vault.json.enc
============================================================
```

### Credenciais Migradas

- **SMTP**: `smtp-<hostname>` (e.g., `smtp-email-ssl.com.br`)
- **MySQL**: `mysql-<id_dbms>` (e.g., `mysql-1`, `mysql-2`)
- **PostgreSQL**: `postgresql-<id_dbms>` (e.g., `postgresql-2`)
- **Files**: Ignorado (sem credenciais)

## Uso Programático

### Python API

```python
from python_backup.security.vault import VaultManager

# Inicializar
vault = VaultManager(".secrets/vault.json.enc")
vault.load()

# Adicionar credencial
vault.set(
    credential_id="mysql-prod",
    username="admin",
    password="SecureP@ss",
    description="Production MySQL"
)

# Recuperar credencial
cred = vault.get("mysql-prod")
print(f"Username: {cred['username']}")
print(f"Password: {cred['password']}")

# Listar todas
ids = vault.list_credentials()  # ['mysql-prod', 'postgresql-dev', ...]

# Verificar existência
if vault.exists("mysql-prod"):
    print("Credential exists")

# Remover
vault.remove("mysql-old")

# Salvar mudanças
vault.save()
```

### Metadados

```python
# Obter metadados sem descriptografar
metadata = vault.get_metadata("mysql-prod")

print(metadata)
# {
#   'created_at': '2026-01-15T19:16:32.869462+00:00',
#   'updated_at': '2026-01-15T19:16:32.869466+00:00',
#   'description': 'Production MySQL Server'
# }
```

### Cache

```python
# Cache automático em get()
cred1 = vault.get("mysql-prod")  # Descriptografa e cacheia
cred2 = vault.get("mysql-prod")  # Retorna do cache (rápido)

# Limpar cache manualmente
vault.clear_cache()

# Cache é limpo automaticamente em:
# - vault.load()
# - vault.set() (apenas para credential_id atualizado)
# - vault.remove() (apenas para credential_id removido)
```

## Segurança

### Criptografia

- **Algoritmo**: Fernet (AES-128-CBC + HMAC-SHA256)
- **Chave**: Derivada do hostname com SHA-256
- **Nível**: Todo o arquivo é criptografado (não apenas senhas)

### Permissões

```bash
$ ls -la .secrets/vault.json.enc
-rw------- 1 user user 2048 Jan 15 16:16 .secrets/vault.json.enc
          ^^^
          600 - Somente owner pode ler/escrever
```

### Proteção Git

```bash
# .secrets/.gitignore
*
!.gitignore
!README.md
!*.example.json
```

### Limitações de Segurança

⚠️ **Importante**:

1. **Chave baseada em hostname**: Credenciais só podem ser descriptografadas no mesmo servidor
2. **Sem senha mestra**: Qualquer usuário com acesso ao arquivo + mesmo hostname pode descriptografar
3. **Não é HSM**: Para segurança enterprise, considere HashiCorp Vault ou AWS Secrets Manager

**Para produção**:
- Proteja acesso ao servidor (SSH keys, firewall)
- Use permissões de arquivo apropriadas (600)
- Monitore acessos ao diretório .secrets/
- Considere vault externo para ambientes multi-servidor

## Troubleshooting

### Erro: "Failed to decrypt"

**Causa**: Vault foi criado em outro servidor (hostname diferente)

**Solução**:
```bash
# Recriar vault no servidor atual
python scripts/utils/migrate_to_vault.py --config .secrets/vya_backupbd.json
```

### Erro: "Permission denied"

**Causa**: Permissões incorretas

**Solução**:
```bash
chmod 600 .secrets/vault.json.enc
```

### Erro: "Credential not found"

**Causa**: ID da credencial não existe

**Solução**:
```bash
# Listar IDs disponíveis
vya-backupdb vault-list

# Verificar ID correto
vya-backupdb vault-get --id <correct-id>
```

### Vault corrompido

**Solução**:
```bash
# Backup atual
mv .secrets/vault.json.enc .secrets/vault.json.enc.bak

# Recriar do config
python scripts/utils/migrate_to_vault.py --config .secrets/vya_backupbd.json
```

## Boas Práticas

### 1. Backup Regular

```bash
# Backup diário
cp .secrets/vault.json.enc .secrets/vault.json.enc.$(date +%Y%m%d)

# Manter últimos 7 dias
find .secrets -name "vault.json.enc.*" -mtime +7 -delete
```

### 2. Rotação de Credenciais

```bash
# 1. Atualizar credencial no vault
vya-backupdb vault-add --id mysql-1 --username root --password "NewPassword"

# 2. Testar conexão
vya-backupdb test-connection --instance 1

# 3. Atualizar no servidor de banco de dados
mysql -u root -p -e "ALTER USER 'root'@'%' IDENTIFIED BY 'NewPassword';"
```

### 3. Auditoria

```bash
# Listar todas as credenciais e datas de atualização
vya-backupdb vault-list

# Ver detalhes de credencial específica
vya-backupdb vault-get --id mysql-prod

# Verificar integridade
vya-backupdb vault-info
```

### 4. Convenção de Nomes

```
Formato: <tipo>-<identificador>

Exemplos:
- mysql-1, mysql-prod, mysql-dev
- postgresql-2, postgres-analytics
- smtp-gmail, smtp-office365
- s3-backup-bucket
- api-github, api-slack
```

## Testes

### Executar Testes Unitários

```bash
# Todos os testes do vault
pytest tests/unit/security/test_vault.py -v

# Com coverage
pytest tests/unit/security/test_vault.py --cov=python_backup.security.vault

# Teste específico
pytest tests/unit/security/test_vault.py::TestCredentialOperations::test_set_new_credential -v
```

### Cobertura de Testes

- ✅ 29 testes unitários
- ✅ Inicialização e persistência
- ✅ Operações CRUD
- ✅ Criptografia/descriptografia
- ✅ Gestão de cache
- ✅ Metadados
- ✅ Tratamento de erros

## Roadmap

### Versão 1.1.0
- [ ] Suporte a múltiplos vaults (produção/desenvolvimento)
- [ ] Exportação/importação de credenciais
- [ ] Rotação automática de credenciais
- [ ] Integração com config/loader.py (fallback automático)

### Versão 2.0.0
- [ ] Senha mestra opcional
- [ ] Suporte a certificados SSL/TLS
- [ ] Auditoria de acessos (log)
- [ ] API REST para gestão remota

## Referências

- **Código**: [src/python_backup/security/vault.py](../../src/python_backup/security/vault.py)
- **Testes**: [tests/unit/security/test_vault.py](../../tests/unit/security/test_vault.py)
- **Migração**: [scripts/utils/migrate_to_vault.py](../../scripts/utils/migrate_to_vault.py)
- **Cryptography**: https://cryptography.io/en/latest/fernet/
- **Fernet Spec**: https://github.com/fernet/spec/blob/master/Spec.md
