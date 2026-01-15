# Guia de Rotação de Credenciais - SEC-2026-001

**Data:** 2026-01-15  
**Incidente:** SEC-2026-001 (Credenciais expostas no histórico Git)  
**Status:** 🚨 **CRÍTICO - AÇÃO IMEDIATA NECESSÁRIA**

---

## 📋 Resumo Executivo

Durante auditoria de segurança na task **T-SECURITY-002**, foram identificadas credenciais em texto plano no arquivo `vya_backupbd.json` que estavam presentes no histórico Git (3 commits). 

**Ações Concluídas:**
- ✅ Arquivo movido para `.secrets/` (protegido por `.gitignore`)
- ✅ Histórico Git limpo (6 commits reescritos, arquivo removido)
- ✅ Validação confirmada (arquivo não encontrado no histórico)
- ✅ Scan de segurança executado (gitleaks v8.30.0 - sem credenciais expostas)

**Ações Pendentes:**
- ⚠️ **Rotação das 3 credenciais expostas** (detalhadas abaixo)

---

## 🔐 Credenciais que Devem Ser Rotacionadas

### 1. SMTP (Servidor de Email)

**Serviço:** email-ssl.com.br  
**Conta:** no-reply@vya.digital  
**Senha Exposta:** `4uC#9-UK69oTop=U+h2D`  
**Exposição:** 3 commits no histórico Git (já limpo)  
**Prioridade:** 🚨 **CRÍTICA**

#### Procedimento de Rotação:

1. **Acessar Painel de Controle**
   ```bash
   URL: https://email-ssl.com.br/webmail ou painel de controle
   Login: no-reply@vya.digital
   Senha atual: 4uC#9-UK69oTop=U+h2D
   ```

2. **Gerar Nova Senha**
   - Use um gerenciador de senhas para gerar senha forte
   - Requisitos recomendados: 20+ caracteres, alfanuméricos + símbolos
   - Exemplo: `openssl rand -base64 24`

3. **Atualizar Configuração**
   ```bash
   # Editar arquivo protegido
   vim .secrets/vya_backupbd.json
   
   # Alterar linha:
   "smtp_password": "NOVA_SENHA_AQUI"
   ```

4. **Testar Conexão**
   ```bash
   # Testar envio de email
   python -m python_backup.cli test-email
   
   # Ou teste manual
   python -m python_backup.notifiers.smtp test_connection
   ```

5. **Validar em Produção**
   - Aguardar próximo backup agendado
   - Verificar recebimento de email de notificação
   - Consultar logs em `logs/python_backup_YYYY-MM-DD.log`

---

### 2. MySQL (Banco de Dados)

**Servidor:** 154.53.36.3  
**Usuário:** root  
**Senha Exposta:** `Vya2020`  
**Porta:** 3306  
**Exposição:** 3 commits no histórico Git (já limpo)  
**Prioridade:** 🚨 **CRÍTICA**

#### Procedimento de Rotação:

1. **Gerar Nova Senha**
   ```bash
   # Gerar senha forte
   openssl rand -base64 24
   # Exemplo de saída: 7K9mN2pQ8rT4vW6xZ1aB3cD5eF
   ```

2. **Conectar ao Servidor MySQL**
   ```bash
   # Via SSH (se necessário)
   ssh usuario@154.53.36.3
   
   # Conectar ao MySQL
   mysql -h 154.53.36.3 -u root -p
   # Senha atual: Vya2020
   ```

3. **Alterar Senha do Usuário root**
   ```sql
   -- MySQL 5.7+
   ALTER USER 'root'@'%' IDENTIFIED BY 'NOVA_SENHA_AQUI';
   
   -- MySQL 8.0+
   ALTER USER 'root'@'%' IDENTIFIED WITH mysql_native_password BY 'NOVA_SENHA_AQUI';
   
   -- Aplicar mudanças
   FLUSH PRIVILEGES;
   
   -- Verificar alteração
   SELECT User, Host FROM mysql.user WHERE User='root';
   ```

4. **Atualizar Configuração Local**
   ```bash
   # Editar arquivo protegido
   vim .secrets/vya_backupbd.json
   
   # Localizar seção MySQL e alterar:
   {
     "type": "mysql",
     "alias": "mysql_prod",
     "host": "154.53.36.3",
     "user": "root",
     "secret": "NOVA_SENHA_AQUI",  # <-- Alterar aqui
     "port": 3306
   }
   ```

5. **Testar Conexão**
   ```bash
   # Teste de conexão
   python -m python_backup.cli connection-test mysql_prod
   
   # Teste de backup
   python -m python_backup.cli backup --type mysql --alias mysql_prod --test
   ```

6. **Validar em Produção**
   ```bash
   # Executar backup real
   python -m python_backup.cli backup --type mysql --alias mysql_prod
   
   # Verificar logs
   tail -f logs/python_backup_$(date +%Y-%m-%d).log
   ```

---

### 3. PostgreSQL (Banco de Dados)

**Servidor:** 154.53.36.3  
**Usuário:** postgres  
**Senha Exposta:** `Vya2020`  
**Porta:** 5432  
**Exposição:** 3 commits no histórico Git (já limpo)  
**Prioridade:** 🚨 **CRÍTICA**

#### Procedimento de Rotação:

1. **Gerar Nova Senha**
   ```bash
   # Gerar senha forte
   openssl rand -base64 24
   # Exemplo de saída: 9mP2nQ3rT5vW7xZ0aB4cD6eF8gH
   ```

2. **Conectar ao Servidor PostgreSQL**
   ```bash
   # Via SSH (se necessário)
   ssh usuario@154.53.36.3
   
   # Conectar ao PostgreSQL
   psql -h 154.53.36.3 -U postgres -d postgres
   # Senha atual: Vya2020
   ```

3. **Alterar Senha do Usuário postgres**
   ```sql
   -- Alterar senha
   ALTER USER postgres WITH PASSWORD 'NOVA_SENHA_AQUI';
   
   -- Verificar alteração (não mostra senha, apenas confirma existência)
   \du postgres
   
   -- Sair
   \q
   ```

4. **Atualizar Configuração Local**
   ```bash
   # Editar arquivo protegido
   vim .secrets/vya_backupbd.json
   
   # Localizar seção PostgreSQL e alterar:
   {
     "type": "postgresql",
     "alias": "postgres_prod",
     "host": "154.53.36.3",
     "user": "postgres",
     "secret": "NOVA_SENHA_AQUI",  # <-- Alterar aqui
     "port": 5432
   }
   ```

5. **Testar Conexão**
   ```bash
   # Teste de conexão
   python -m python_backup.cli connection-test postgres_prod
   
   # Teste de backup
   python -m python_backup.cli backup --type postgresql --alias postgres_prod --test
   ```

6. **Validar em Produção**
   ```bash
   # Executar backup real
   python -m python_backup.cli backup --type postgresql --alias postgres_prod
   
   # Verificar logs
   tail -f logs/python_backup_$(date +%Y-%m-%d).log
   ```

---

## 🔄 Sequência de Execução Recomendada

Execute as rotações nesta ordem para minimizar indisponibilidade:

1. **SMTP** (menos crítico, afeta apenas notificações)
   - Tempo estimado: 5-10 minutos
   - Impacto: Nulo (backups continuam funcionando)

2. **MySQL** (mais crítico, afeta backups)
   - Tempo estimado: 10-15 minutos
   - Impacto: Médio (backups MySQL ficam indisponíveis durante rotação)
   - Recomendação: Executar fora do horário de backup agendado

3. **PostgreSQL** (mais crítico, afeta backups)
   - Tempo estimado: 10-15 minutos
   - Impacto: Médio (backups PostgreSQL ficam indisponíveis durante rotação)
   - Recomendação: Executar fora do horário de backup agendado

**Tempo Total Estimado:** 25-40 minutos

---

## ✅ Checklist de Validação Final

Após rotacionar todas as credenciais, execute:

```bash
# 1. Testar todas as conexões
python -m python_backup.cli connection-test --all

# 2. Executar backup de teste de todos os tipos
python -m python_backup.cli backup --all --test

# 3. Verificar logs de erro
grep -i "error\|fail\|auth" logs/python_backup_$(date +%Y-%m-%d).log

# 4. Re-executar scan de segurança
/tmp/gitleaks detect --source . --no-git --verbose

# 5. Verificar que arquivo de configuração está protegido
ls -la .secrets/vya_backupbd.json
cat .gitignore | grep -i secrets
```

---

## 📝 Registro de Rotação

Preencher após execução de cada rotação:

| Credencial | Data Rotação | Executor | Nova Senha (últimos 4 caracteres) | Status Teste |
|------------|--------------|----------|-------------------------------------|--------------|
| SMTP       |              |          |                                     | ⬜ Pendente  |
| MySQL      |              |          |                                     | ⬜ Pendente  |
| PostgreSQL |              |          |                                     | ⬜ Pendente  |

---

## 🚨 Ações Pós-Rotação

1. **Atualizar Documentação de Incidente**
   ```bash
   # Adicionar timestamps de rotação em:
   vim docs/SECURITY_AUDIT_2026-01-15.md
   ```

2. **Notificar Equipe**
   - Informar que credenciais foram rotacionadas
   - Atualizar documentação interna de credenciais
   - Atualizar vault/gerenciador de senhas corporativo

3. **Monitorar Logs (48h)**
   ```bash
   # Verificar diariamente por 2 dias
   tail -f logs/python_backup_$(date +%Y-%m-%d).log | grep -i "error\|fail"
   ```

4. **Marcar Task como Concluída**
   ```bash
   # Atualizar status em:
   vim docs/TASK_LIST_V2.0.0.md
   # Marcar T-SECURITY-002 como [✅ CONCLUÍDA]
   ```

---

## 📚 Referências

- **Auditoria de Segurança:** [docs/SECURITY_AUDIT_2026-01-15.md](SECURITY_AUDIT_2026-01-15.md)
- **Relatório de Limpeza Git:** [docs/sessions/GIT_HISTORY_CLEANUP_REPORT_2026-01-15.md](sessions/GIT_HISTORY_CLEANUP_REPORT_2026-01-15.md)
- **Task List v2.0.0:** [docs/TASK_LIST_V2.0.0.md](TASK_LIST_V2.0.0.md)
- **Gitleaks Report:** gitleaks-report.json

---

## ⚠️ Notas de Segurança

1. **NÃO compartilhe novas senhas por email/chat não criptografado**
2. **USE gerenciador de senhas** (1Password, Bitwarden, LastPass, etc.)
3. **HABILITE autenticação de 2 fatores** quando disponível
4. **DOCUMENTE apenas os últimos 4 caracteres** das senhas
5. **ROTACIONE novamente** se houver suspeita de vazamento

---

**Criado em:** 2026-01-15  
**Autor:** GitHub Copilot (T-SECURITY-002)  
**Versão:** 1.0  
**Status:** 🚨 AÇÃO REQUERIDA
