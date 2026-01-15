# Processo de Backup em Produção - VYA BackupDB

**Última Atualização**: 2026-01-15  
**Status**: ATIVO  
**Ambiente**: Produção

---

## 📋 Visão Geral

O sistema VYA BackupDB em produção opera em conjunto com o Idrive (solução de backup cloud) através de uma sequência cronológica de tarefas automatizadas. **NÃO utiliza retenção local de arquivos**, pois todos os backups são enviados para a cloud e posteriormente removidos.

---

## ⏰ Cronograma de Execução

### 📌 Versão Antiga (Real - Crontab Original)

```cron
# Idrive - A cada 10 minutos (monitora continuamente)
*/10 * * * * systemctl start idrivecron

# Backup VYA - 00:30 (meia-noite e meia)
30 0 * * * sh /usr/local/bin/enterprise/python_backup/python_backup.sh

# Limpeza - 05:00
0 5 * * * /usr/bin/rm -f /tmp/bkpsql/*
0 5 * * * /usr/bin/rm -f /tmp/bkpzip/*
```

**Estrutura de Instalação**:
```
/usr/local/bin/
├── enterprise/python_backup/
│   ├── python_backup.py
│   ├── python_backup.sh
│   └── python_backup.json
└── py_venv/python_backup/
    └── bin/python3
```

---

### 00:30 - Geração de Backups (vya_backupdb)

**Trigger**: Cron job  
**Responsável**: vya_backupdb  
**Ação**: Execução de backups de bancos de dados e arquivos

**Pastas de Destino**:
```bash
/tmp/bkpsql  # Backups de PostgreSQL e MySQL (formato SQL)
/tmp/bkpzip  # Backups compactados (tar.gz)
```

**Operações**:
1. Backup de bancos PostgreSQL → `/tmp/bkpsql/*.sql.gz`
2. Backup de bancos MySQL → `/tmp/bkpsql/*.sql.gz`
3. Backup de arquivos → `/tmp/bkpzip/*.tar.gz`
4. Geração de logs de execução
5. Envio de notificações por email (sucesso/falha)

**Comando Real (Versão Antiga)**:
```bash
# Executado pelo cron às 00:30
sh /usr/local/bin/enterprise/python_backup/python_backup.sh
# Que executa:
/usr/local/bin/py_venv/python_backup/bin/python3 \
  /usr/local/bin/enterprise/python_backup/python_backup.py -b
```

**Comando Novo (v2.0.0)**:
```bash
# Executar às 00:30 (ou outro horário desejado)
python -m python_backup.cli backup --all
```

---

### 00:30-05:00 - Upload para Cloud (Idrive)

**Trigger**: Systemd service a cada 10 minutos  
**Responsável**: Idrive Backup Client  
**Ação**: Monitora e faz upload de backups para cloud

**Pasta Monitorada**:
```bash
/tmp/bkpzip  # Apenas arquivos compactados
```

**Operações**:
1. Idrive monitora `/tmp/bkpzip` continuamente
2. Detecta novos arquivos (gerados às 00:30)
3. Upload para cloud Idrive (automático)
4. Validação de integridade
5. Log de transferência

**Execução**:
```cron
# Roda a cada 10 minutos
*/10 * * * * systemctl start idrivecron
```

**Nota**: 
- `/tmp/bkpsql` não é enviado para o Idrive (apenas arquivos compactados)
- Upload geralmente completa entre 01:00-03:00 dependendo do tamanho

---

### 05:00 - Limpeza Local (Cron)

**Trigger**: Cron job de limpeza  
**Responsável**: Script de manutenção  
**Ação**: Remoção de todos os arquivos de backup locais

**Pastas Limpas**:
```bash
/tmp/bkpsql  # Remove todos os backups SQL
/tmp/bkpzip  # Remove todos os backups compactados
```

**Operações**:
```bash
# Executado pelo cron às 05:00
rm -rf /tmp/bkpsql/*
rm -rf /tmp/bkpzip/*
```

**Resultado**: Sem arquivos locais remanescentes (espaço liberado).

---

## 🔄 Fluxo Completo

```
┌─────────────────────────────────────────────────────────────┐
│ 00:30 - VYA BackupDB                                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐      ┌──────────────┐                   │
│  │ PostgreSQL   │ ───▶ │ /tmp/bkpsql/ │                   │
│  │ MySQL        │      │  - file1.sql │                   │
│  └──────────────┘      │  - file2.sql │                   │
│                        └──────────────┘                    │
│                                                             │
│  ┌──────────────┐      ┌──────────────┐                   │
│  │ Files        │ ───▶ │ /tmp/bkpzip/ │                   │
│  │ (glob)       │      │  - arc1.tar  │                   │
│  └──────────────┘      │  - arc2.tar  │                   │
│                        └──────────────┘                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                           │
                           │ Idrive monitora a cada 10 min
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ 00:30-03:00 - Idrive Upload (automático)                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐                                          │
│  │ /tmp/bkpzip/ │                                          │
│  │  - arc1.tar  │ ─────────┐                              │
│  │  - arc2.tar  │          │                              │
│  └──────────────┘          │                              │
│                            ▼                               │
│                    ┌──────────────┐                        │
│                    │ Idrive Cloud │                        │
│                    │   (Storage)  │                        │
│                    └──────────────┘                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                           │
                           │ 4h30 depois
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ 05:00 - Limpeza Local                                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  rm -rf /tmp/bkpsql/*  ────▶  ✓ Espaço liberado            │
│  rm -rf /tmp/bkpzip/*  ────▶  ✓ Espaço liberado            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔒 Retenção de Backups

### Retenção Local: NÃO APLICÁVEL

**Motivo**: Arquivos são removidos diariamente às 05:00.  
**Resultado**: Zero arquivos locais após limpeza.  
**Benefício**: Economia de espaço em disco local.

### Retenção Cloud: Gerenciada pelo Idrive

**Responsável**: Idrive (configuração externa)  
**Localização**: Cloud Idrive  
**Política**: Definida nas configurações do Idrive (não gerenciada pelo vya_backupdb)

**Nota**: Para consultar ou alterar a política de retenção cloud, acessar o painel de controle do Idrive.

---

## 📊 Configuração Atual

### python_backup.json

```json
{
  "db_config": [
    {
      "id_dbms": 1,
      "dbms": "postgresql",
      "host": "192.168.40.134",
      "port": 5432,
      "username": "postgres",
      "db_list": ["chatwoot_db"],
      "enabled": true
    },
    {
      "id_dbms": 2,
      "dbms": "mysql",
      "host": "192.168.40.134",
      "port": 3306,
      "username": "dsroot",
      "db_list": ["dns_db"],
      "enabled": true
    },
    {
      "id_dbms": 3,
      "dbms": "files",
      "db_list": [
        "/docker/volumes/**/*",
        "/opt/app/config/*.yaml"
      ],
      "enabled": true
    }
  ],
  "bkp_system": {
    "path_pgsql": "/tmp/bkpsql",
    "path_mysql": "/tmp/bkpsql",
    "path_files": "/tmp/bkpzip",
    "retention_pgsql": 1,
    "retention_mysql": 1,
    "retention_files": 1
  }
}
```

**Nota**: `retention_*` configurado como 1, mas não é utilizado pelo sistema de limpeza (removido manualmente às 05:00).

---

## 🛠️ Troubleshooting

### Problema: Espaço em disco cheio

**Causa Provável**: Cron de limpeza às 05:00 não executou.  
**Verificação**:
```bash
ls -lh /tmp/bkpsql/
ls -lh /tmp/bkpzip/
```

**Solução**:
```bash
# Limpeza manual
rm -rf /tmp/bkpsql/*
rm -rf /tmp/bkpzip/*

# Verificar cron
crontab -l | grep cleanup
```

---

### Problema: Backups não aparecem no Idrive

**Causa Provável**: 
1. Serviço Idrive parado
2. Pasta `/tmp/bkpzip` vazia às 03:00
3. Configuração Idrive incorreta

**Verificação**:
```bash
# Verificar serviço Idrive
systemctl status idrive  # ou ps aux | grep idrive

# Verificar se backups foram gerados
ls -lh /tmp/bkpzip/

# Verificar logs do Idrive
tail -f /var/log/idrive.log  # ajustar caminho
```

**Solução**:
1. Reiniciar serviço Idrive
2. Verificar configuração de pastas no Idrive
3. Testar upload manual

---

### Problema: Backup não foi executado

**Causa Provável**: 
1. Cron job não configurado
2. Erro na execução do vya_backupdb
3. Credenciais de banco incorretas

**Verificação**:
```bash
# Verificar cron
crontab -l | grep vya_backupdb

# Verificar logs
tail -f /var/log/vya_backupdb/*.log

# Executar manualmente
python -m python_backup.cli backup --all
```

---

## 📝 Manutenção

### Verificações Diárias

1. **Checar execução de backups (22:00)**
   - Verificar logs de execução
   - Confirmar email de sucesso/falha

2. **Checar upload Idrive (03:00)**
   - Verificar logs do Idrive
   - Confirmar arquivos na cloud

3. **Checar limpeza (05:00)**
   - Verificar se pastas estão vazias
   - Monitorar espaço em disco

### Verificações Semanais

1. **Testar restore de backup**
   - Baixar arquivo do Idrive
   - Executar restore em ambiente de teste
   - Validar integridade dos dados

2. **Revisar logs de erros**
   - Analisar falhas de backup
   - Corrigir problemas recorrentes

---

## 🔗 Referências

- [README.md](../README.md) - Visão geral do projeto
- [FILES_BACKUP_GUIDE.md](../guides/FILES_BACKUP_GUIDE.md) - Guia de backup de arquivos
- [INDEX.md](../INDEX.md) - Índice da documentação
- [TODO.md](../TODO.md) - Tarefas e melhorias

---

## ⚠️ Importante: RetentionManager

### Status Atual

O **RetentionManager** foi implementado na sessão de 2026-01-14, mas:

- ✅ **Código**: Implementado e testado (280 linhas)
- ✅ **Testes**: Completos (unit + integration)
- ❌ **CLI**: NÃO será implementado
- ❌ **Uso em Produção**: NÃO aplicável

### Motivo

O processo de produção **não necessita** de retenção automática porque:
1. Arquivos são removidos manualmente (cron às 05:00)
2. Retenção é gerenciada pelo Idrive (cloud)
3. Não há arquivos locais para reter

### Uso Futuro

O RetentionManager permanece no código para:
- Casos de uso alternativos
- Ambientes sem Idrive
- Implementação de retenção local (se necessário)

---

**Última Revisão**: 2026-01-15 por VYA Development Team  
**Versão**: 1.0.0
