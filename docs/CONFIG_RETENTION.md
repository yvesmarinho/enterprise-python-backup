# Configuração de Retenção de Arquivos

## Parâmetro: retention_files

O parâmetro `retention_files` no arquivo `python_backup.json` define a quantidade de arquivos de backup (por banco de dados) que serão mantidos antes de serem removidos automaticamente.

### Localização no JSON

```json
{
  "bkp_system": {
    "path_sql": "/tmp/bkpsql/",
    "path_zip": "/tmp/bkpzip/",
    "retention_files": 7
  }
}
```

### Descrição

- **Tipo**: `int` (número inteiro)
- **Padrão**: `7`
- **Mínimo**: `1`
- **Descrição**: Número de backups a serem mantidos por banco de dados

### Comportamento

1. **Por Banco de Dados**: A retenção é aplicada individualmente para cada banco de dados
2. **Ordem**: Os arquivos mais antigos são removidos primeiro (FIFO - First In, First Out)
3. **Aplicação**: 
   - Arquivos SQL em `path_sql`
   - Arquivos compactados em `path_zip` (quando compressão está habilitada)

### Exemplos de Uso

#### Exemplo 1: Retenção de 7 dias (padrão)
```json
{
  "bkp_system": {
    "retention_files": 7
  }
}
```
- Mantém os últimos 7 backups de cada banco de dados
- Remove automaticamente backups mais antigos

#### Exemplo 2: Retenção de 30 dias
```json
{
  "bkp_system": {
    "retention_files": 30
  }
}
```
- Mantém os últimos 30 backups de cada banco de dados
- Ideal para ambientes de produção com requisitos de auditoria

#### Exemplo 3: Retenção mínima (desenvolvimento)
```json
{
  "bkp_system": {
    "retention_files": 3
  }
}
```
- Mantém apenas os 3 últimos backups
- Ideal para ambientes de desenvolvimento com espaço limitado

### Integração com o Sistema

O valor é utilizado no CLI através do `BackupConfig`:

```python
backup_config = BackupConfig(
    compression="zip" if compression else None,
    retention_days=config.bkp_system.retention_files
)
```

### Recomendações

| Ambiente     | Valor Recomendado | Justificativa                                |
|--------------|-------------------|----------------------------------------------|
| Desenvolvimento | 3-5            | Espaço limitado, backups frequentes          |
| Homologação  | 7-14              | Testes podem precisar dados históricos       |
| Produção     | 30-90             | Conformidade, auditoria, recuperação longa   |

### Considerações de Espaço em Disco

**Cálculo estimado**:
```
Espaço = (Tamanho Médio do Backup) × (retention_files) × (Número de Bancos)
```

**Exemplo**:
- Tamanho médio: 500 MB
- Retention: 30 arquivos
- Bancos: 10
- **Total**: 500 MB × 30 × 10 = **150 GB**

### Monitoramento

Para verificar quantos backups estão sendo mantidos:

```bash
# Listar backups SQL
ls -lth /tmp/bkpsql/ | head -n 10

# Listar backups compactados
ls -lth /tmp/bkpzip/ | head -n 10

# Contar backups por banco
ls /tmp/bkpsql/*.sql | cut -d'_' -f3 | sort | uniq -c
```

### Logs Relacionados

O sistema registra ações de retenção nos logs:

```
[INFO] Applying retention policy: keeping last 7 backups
[DEBUG] Found 12 backup files for database 'myapp'
[INFO] Removing 5 old backup files
[DEBUG] Deleted: /tmp/bkpsql/20260101_120000_mysql_myapp.sql
```

### Troubleshooting

**Problema**: Disco cheio mesmo com retenção configurada
- **Solução**: Reduzir `retention_files` ou aumentar capacidade de disco

**Problema**: Backups necessários foram removidos
- **Solução**: Aumentar `retention_files` ou implementar backup externo adicional

**Problema**: Muitos arquivos acumulados
- **Solução**: Verificar se a limpeza automática está funcionando, reduzir `retention_files`

---

**Data**: 13/01/2026  
**Versão**: 2.0.0  
**Status**: Implementado
