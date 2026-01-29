# 🚨 Disaster Recovery Simulation - Task List

**Data**: 27 de Janeiro de 2026  
**Responsável**: Backup Team  
**Objetivo**: Simular recuperação de desastre entre servidores de produção e teste

---

## 📋 Cenário de Teste

### Máquina de Gestão (Controle)
- **Função**: Execução do vya-backupdb
- **Local**: Máquina onde o projeto enterprise-python-backup está instalado
- **Requisitos**:
  - Python 3.13.3+
  - vya-backupdb instalado e configurado
  - Conectividade com ambos servidores (produção e teste)
  - Acesso SSH aos servidores (se necessário)
  - Vault configurado com credenciais

### Servidor de Produção (Origem)
- **Hostname**: wfdb02.vya.digital
- **IP**: 82.197.64.145
- **User**: backup
- **Password**: @W123Mudar#2026
- **Função**: Servidor com dados de produção a serem backupados
- **Requisitos**:
  - PostgreSQL instalado e acessível remotamente
  - MySQL instalado e acessível remotamente
  - Porta 5432 (PostgreSQL) aberta
  - Porta 3306 (MySQL) aberta
  - Usuário backup com permissões adequadas

### Servidor de Teste (Destino)
- **Hostname**: home011
- **IP**: 192.168.15.197
- **User**: backup
- **Password**: @W123Mudar#2026
- **Função**: Servidor com DBs recém-instalados para teste de restore
- **Requisitos**:
  - PostgreSQL instalado e acessível remotamente
  - MySQL instalado e acessível remotamente
  - Porta 5432 (PostgreSQL) aberta
  - Porta 3306 (MySQL) aberta
  - Usuário backup com permissões adequadas
  - Espaço em disco suficiente para restauração

### Databases Envolvidos
- **PostgreSQL**: Databases de produção
- **MySQL**: Databases de produção

---

## 🎯 Objetivos da Simulação

1. ✅ Validar processo completo de backup remoto
2. ✅ Testar restauração em ambiente limpo
3. ✅ Verificar integridade dos dados restaurados
4. ✅ Documentar tempo de recuperação (RTO)
5. ✅ Documentar ponto de recuperação (RPO)
6. ✅ Identificar gaps no processo de DR

---

## 📦 Dependências e Requisitos

### Máquina de Gestão (Controle)

- [x] **T-PRE-001**: Verificar instalação do vya-backupdb ✅
  ```bash
  vya-backupdb --version
  # Esperado: vya-backupdb v2.0.0
  # Resultado: vya-backupdb v2.0.0 (modo desenvolvimento)
  ```

- [x] **T-PRE-002**: Verificar Python e dependências ✅
  ```bash
  python --version
  # Esperado: Python 3.13.3 ou superior
  # Resultado: Python 3.13.3 ✅
  
  uv pip list | grep -E "(sqlalchemy|pydantic|typer|cryptography|psycopg|pymysql)"
  # Resultado: Todas as dependências instaladas ✅
  # - cryptography 42.0.8
  # - psycopg 3.3.2
  # - pydantic 2.12.5
  # - pymysql 1.1.2
  # - pyyaml 6.0.3
  # - rich 13.9.4
  # - sqlalchemy 2.0.45
  # - typer 0.21.1
  ```

- [ ] **T-PRE-003**: Verificar clientes de database instalados
  ```bash
  which pg_dump pg_restore
  which mysqldump mysql
  ```

- [ ] **T-PRE-004**: Testar conectividade com servidor de produção
  ```bash
  # PostgreSQL
  psql -h 82.197.64.145 -U backup -p 5432 -l
  
  # MySQL
  mysql -h 82.197.64.145 -u backup -p'@W123Mudar#2026' -e "SHOW DATABASES;"
  ```
10**: Instalar PostgreSQL (se necessário)
  ```bash
  ssh backup@192.168.15.197
  # Para Ubuntu/Debian
  sudo apt update
  sudo apt install postgresql postgresql-contrib -y
  sudo systemctl status postgresql
  ```

- [ ] **T-PRE-011**: Instalar MySQL (se necessário)
  ```bash
  # Para Ubuntu/Debian
  sudo apt update
  sudo apt install mysql-server -y
  sudo systemctl status mysql
  ```

- [ ] **T-PRE-012**: Configurar PostgreSQL para aceitar conexões remotas
  ```bash
  # Editar postgresql.conf
  sudo sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/" /etc/postgresql/*/main/postgresql.conf
  
  # Editar pg_hba.conf
  echo "host    all    backup    0.0.0.0/0    md5" | sudo tee -a /etc/postgresql/*/main/pg_hba.conf
  
  # Reiniciar PostgreSQL
  sudo systemctl restart postgresql
  ```

- [ ] **T-PRE-013**: Configurar MySQL para aceitar conexões remotas
  ```bash
  # Editar my.cnf
  sudo sed -i "s/bind-address.*/bind-address = 0.0.0.0/" /etc/mysql/mysql.conf.d/mysqld.cnf
  
  # Reiniciar MySQL
  sudo systemctl restart mysql
  ```

- [ ] **T-PRE-014**: Criar usuário backup no PostgreSQL
  ```bash
  sudo -u postgres psql
  CREATE USER backup WITH PASSWORD '@W123Mudar#2026';
  ALTER USER backup WITH SUPERUSER;
  
  -- Permitir conexões remotas
  \q
  ```

- [ ] **T-PRE-015**: Criar usuário backup no MySQL
  ```bash
  sudo mysql
  CREATE USER 'backup'@'%' IDENTIFIED BY '@W123Mudar#2026';
  GRANT ALL PRIVILEGES ON *.* TO 'backup'@'%' WITH GRANT OPTION;
  FLUSH PRIVILEGES;
  EXIT;
  ``` (Na Máquina de Gestão)

> **IMPORTANTE**: Todos os comandos vault devem ser executados na máquina de gestão onde o vya-backupdb está instalado.

- [ ] **T-VAULT-001**: Adicionar credenciais PostgreSQL (produção)
  ```bash
  # Na máquina de gestão
  ssh backup@192.168.15.197 "df -h /var/lib/postgresql/ /var/lib/mysql/"
  ```

- [ ] **T-PRE-017**: Testar acesso remoto PostgreSQL (da máquina de gestão)
  ```bash
  # Da máquina de gestão
  psql -h 192.168.15.197 -U backup -p 5432 -l
  ```

- [ ] **T-PRE-018**: Testar acesso remoto MySQL (da máquina de gestão)
  ```bash
  # Da máquina de gestão
  mysql -h 192.168.15.197 -u backup -p'@W123Mudar#2026' -e "SHOW DATABASES;" criado
- Permissões: ALL PRIVILEGES ou SELECT, LOCK TABLES, SHOW VIEW
- Configuração bind-address permite conexões remotas
- Porta 3306 aberta no firewall

**Sistema Operacional**:
- Linux (Ubuntu/Debian/CentOS/RHEL)
- Espaço em disco: Mínimo 2x tamanho dos databases
- Memória RAM: Mínimo 2GB disponível

---

## ⚙️ Pré-requisitos

### No Servidor de Produção (wfdb02)

- [ ] **T-PRE-001**: Verificar instalação do vya-backupdb
  ```bash
  ssh backup@82.197.64.145
  vya-backupdb --version
  ```

- [ ] **T-PRE-002**: Verificar conectividade com PostgreSQL
  ```bash
  psql -h localhost -U <postgres_user> -l
  ```

- [ ] **T-PRE-003**: Verificar conectividade com MySQL
  ```bash
  mysql -h localhost -u <mysql_user> -p -e "SHOW DATABASES;"
  ```

- [ ] **T-PRE-004**: Listar databases PostgreSQL disponíveis
  ```bash
  psql -h localhost -U <postgres_user> -l | grep -v template | grep -v postgres
  ```

- [ ] **T-PRE-005**: Listar databases MySQL disponíveis
  ```bash
  mysql -h localhost -u <mysql_user> -p -e "SHOW DATABASES;" | grep -v information_schema | grep -v performance_schema | grep -v mysql | grep -v sys
  ```

### No Servidor de Teste (home011)

- [ ] **T-PRE-006**: Instalar PostgreSQL (se necessário)
  ```bash
  ssh backup@192.168.15.197
  # Para Ubuntu/Debian
  sudo apt update
  sudo apt install postgresql postgresql-contrib -y
  sudo systemctl status postgresql
  ```

- [ ] **T-PRE-007**: Instalar MySQL (se necessário)
  ```bash
  # Para Ubuntu/Debian
  sudo apt update
  sudo apt install mysql-server -y
  sudo systemctl status mysql
  ```

- [ ] **T-PRE-008**: Criar usuário backup no PostgreSQL
  ```bash
  sudo -u postgres psql
  CREATE USER backup WITH PASSWORD '@W123Mudar#2026';
  ALTER USER backup WITH SUPERUSER;
  \q
  ```

- [ ] **T-PRE-009**: Criar usuário backup no MySQL
  ```bash
  sudo mysql
  CREATE USER 'backup'@'localhost' IDENTIFIED BY '@W123Mudar#2026';
  GRANT ALL PRIVILEGES ON *.* TO 'backup'@'localhost' WITH GRANT OPTION;
  FLUSH PRIVILEGES;
  EXIT;
  ```

- [ ] **T-PRE-010**: Verificar espaço em disco disponível
  ```bash
  df -h /var/backups/
  df -h /var/lib/postgresql/
  df -h /var/lib/mysql/
  ```

> **IMPORTANTE**: Todos os comandos config-instance devem ser executados na máquina de gestão. As instâncias apontam para os servidores remotos.

- [ ] **T-INST-001**: Adicionar instância PostgreSQL de produção
  ```bash
  # Na máquina de gestão
  # host aponta para o servidor remoto de produção
  # Clone e instale
  git clone <repository-url>
  cd enterprise-python-backup
  uv venv
  source .venv/bin/activate
  uv pip install -e .
  ```

---

## 📦 Fase 1: Configuração do Vault

### Adicionar Credenciais ao Vault

- [ ] **T-VAULT-001**: Adicionar credenciais PostgreSQL (produção)
  ```bash
  vya-backupdb vault-add \
    --id postgres-wfdb02-prod \
    --username backup \
    --password '@W123Mudar#2026' \
    --description "PostgreSQL wfdb02 production"
  ```

- [ ] **T-VAULT-002**: Adicionar credenciais MySQL (produção)
  ```bash
  vya-backupdb vault-add \
    --id mysql-wfdb02-prod \
    --username backup \
    --password '@W123Mudar#2026' \
    --description "MySQL wfdb02 production"
  ```

- [ ] **T-VAULT-003**: Adicionar credenciais PostgreSQL (teste)
  ```bash
  vya-backupdb vault-add \
    --id postgres-home011-test \
    --username backup \
    --password '@W123Mudar#2026' \
    --description "PostgreSQL home011 test"
  ```

- [ ] **T-VAULT-004**: Adicionar credenciais MySQL (teste)
  ```bash
  vya-backupdb vault-add \
    --id mysql-home011-test \
    --username backup \
    --password '@W123Mudar#2026' \
    --description "MySQL home011 test"
  ```

- [ ] **T-VAULT-005**: Validar credenciais no vault
> **IMPORTANTE**: Todos os backups são executados da máquina de gestão. O vya-backupdb conecta remotamente nos servidores para realizar os backups.

### PostgreSQL Backup

- [ ] **T-BACKUP-001**: Testar conexão PostgreSQL produção
  ```bash
  # Na máquina de gestão
  # Conecta remotamente em 82.197.64.145:5432
  vya-backupdb test-connection --instance wfdb02-postgres-prod
  ```

- [ ] **T-BACKUP-002**: Executar backup PostgreSQL (dry-run)
  ```bash
  # Na máquina de gestão
  vya-backupdb backup \
    --instance wfdb02-postgres-prod \
    --dry-run
  ```

- [ ] **T-BACKUP-003**: Executar backup PostgreSQL COMPLETO
  ```bash
  # Na máquina de gestão
  # Anotar timestamp de início
  date
  
  # Os backups serão salvos localmente na máquina de gestão  --credential postgres-wfdb02-prod \
    --db-ignore "template0,template1,postgres" \
    --config config/disaster-recovery.yaml
  ```

- [ ] **T-INST-002**: Adicionar instância MySQL de produção
  ```bash
  vya-backupdb config-instance-add \
    --id wfdb02-mysql-prod \
    --type mysql \
    --host 82.197.64.145 \
    --port 3306 \
    --credential mysql-wfdb02-prod \
    --db-ignore "information_schema,mysql,sys,performance_schema" \
    --config config/disaster-recovery.yaml
  ```

### Instâncias de Teste (Destino)

- [ ] **T-INST-003**: Adicionar instância PostgreSQL de teste
  ```bash
  vya-backupdb config-instance-add \
    --id home011-postgres-test \
    --type postgresql \
    --host 192.168.15.197 \
    --port 5432 \
    --credential postgres-home011-test \
    --config config/disaster-recovery.yaml
  ```

- [ ] **T-INST-004**: Adicionar instância MySQL de teste
  ```bash
  vya-backupdb config-instance-add \
    --id home011-mysql-test \
    --type mysql \
    --host 192.168.15.197 \
    --port 3306 \
    --credential mysql-home011-test \
    --config config/disaster-recovery.yaml
  ```

- [ ] **T-INST-005**: Listar todas as instâncias configuradas
  ```bash
  vya-backupdb config-instance-list --config config/disaster-recovery.yaml
  ```

---

## 💾 Fase 3: Backup de Produção

### PostgreSQL Backup

- [ ] **T-BACKUP-001**: Testar conexão PostgreSQL produção
  ```bash
  vya-backupdb test-connection --instance wfdb02-postgres-prod
  ```

- [ ] **T-BACKUP-002**: Executar backup PostgreSQL (dry-run)
  ```bash
  vya-backupdb backup \
    --instance wfdb02-postgres-prod \
    --dry-run
  ```

- [ ] **T-BACKUP-003**: Executar backup PostgreSQL COMPLETO
  ```bash
  # Anotar timestamp de início
  date
  
  vya-backupdb backup \
    --instance wfdb02-postgres-prod \
    --output-dir /var/backups/disaster-recovery/postgres
  
  # Anotar timestamp de fim
  date
  ```

- [ ] **T-BACKUP-004**: Validar arquivos de backup PostgreSQL
  ```bash
  ls -lh /var/backups/disaster-recovery/postgres/
  file /var/backups/disaster-recovery/postgres/*.sql.gz
  ```

- [ ] **T-BACKUP-005**: Registrar tamanho dos backups PostgreSQL
  ```bash
  du -sh /var/backups/disaster-recovery/postgres/
  ```

### MySQL Backup

- [ ] **T-BACKUP-006**: Testar conexão MySQL produção
  ```bash
  vya-backupdb test-connection --instance wfdb02-mysql-prod
  ```

- [ ] **T-BACKUP-007**: Executar backup MySQL (dry-run)
  ```bash
> **NOTA**: Esta fase é OPCIONAL se a restauração for feita diretamente da máquina de gestão (recomendado). Os backups já estão na máquina de gestão após a Fase 3.

### Opção A: Restauração Direta (Recomendado)

> Pule esta fase se for restaurar diretamente da máquina de gestão usando vya-backupdb restore, que conecta remotamente no servidor de teste.

### Opção B: Copiar Backups para Servidor de Teste

> Use esta opção apenas se precisar fazer restore manual nos servidores.

- [ ] **T-TRANSFER-001**: Copiar backups PostgreSQL via SCP
  ```bash
  # Na máquina de gestão
  # Copia arquivos locais para servidor remoto
  scp -r /var/backups/disaster-recovery/postgres/* \
    backup@192.168.15.197:/var/backups/disaster-recovery/postgres/
  ```

- [ ] **T-TRANSFER-002**: Copiar backups MySQL via SCP
  ```bash
  # Na máquina de gestão
  # Copia arquivos locais para servidor remoto
  vya-backupdb backup \
    --instance wfdb02-mysql-prod \
    --output-dir /var/backups/disaster-recovery/mysql
  
  # Anotar timestamp de fim
  date
  ```

- [ ] **T-BACKUP-009**: Validar arquivos de backup MySQL
  ```bash
  ls -lh /var/backups/disaster-recovery/mysql/
  file /var/backups/disaster-recovery/mysql/*.sql.gz
  ```

- [ ] **T-BACKUP-010**: Registrar tamanho dos backups MySQL
  ```bash
  du -sh /var/backups/disaster-recovery/mysql/
  ```

---

## 📊 Fase 4: Análise de Dados Produção (Baseline)

### PostgreSQL - Dados de Referência

- [ ] **T-BASELINE-001**: Contar databases PostgreSQL
  ```bash
  psql -h 82.197.64.145 -U backup -l | wc -l
  ```

- [ ] **T-BASELINE-002**: Para cada database PostgreSQL, contar tabelas
  ```bash
  # Para cada database
  psql -h 82.197.64.145 -U backup -d <database_name> -c "\dt" | wc -l
  ```

- [ ] **T-BASELINE-003**: Para cada database PostgreSQL, contar registros
  ```bash
  # Exemplo de contagem
  psql -h 82.197.64.145 -U backup -d <database_name> -c "SELECT schemaname,tablename,n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC;"
  ```

### MySQL - Dados de Referência

- [ ] **T-BASELINE-004**: Contar databases MySQL
  ```bash
> **IMPORTANTE**: A restauração é executada da máquina de gestão. O vya-backupdb conecta remotamente no servidor de teste (192.168.15.197) para realizar a restauração.

### Preparação

- [ ] **T-RESTORE-PG-001**: Listar backups PostgreSQL disponíveis
  ```bash
  # Na máquina de gestão
  ls -lh /var/backups/disaster-recovery/postgres/
  ```

### Restauração Database por Database

- [ ] **T-RESTORE-PG-002**: Identificar database a restaurar
  ```bash
  # Na máquina de gestão
  # Exemplo: my_production_db
  DATABASE_TO_RESTORE="my_production_db"
  BACKUP_FILE="/var/backups/disaster-recovery/postgres/${DATABASE_TO_RESTORE}_backup_*.sql.gz"
  
  echo "Database: ${DATABASE_TO_RESTORE}"
  echo "Backup: ${BACKUP_FILE}"
  ls -lh ${BACKUP_FILE}
  ```

- [ ] **T-RESTORE-PG-003**: Criar database vazio no servidor de teste (remoto)
  ```bash
  # Na máquina de gestão
  # Conecta remotamente e cria database
  psql -h 192.168.15.197 -U backup -c "CREATE DATABASE ${DATABASE_TO_RESTORE}_restored;"
  ```

- [ ] **T-RESTORE-PG-004**: Descompactar backup (se necessário)
  ```bash
  # Na máquina de gestão
  gunzip -k ${BACKUP_FILE}
  ```

- [ ] **T-RESTORE-PG-005**: Executar restore com vya-backupdb
  ```bash
  # Na máquina de gestão
  # Anotar timestamp de início
  date
  
  # vya-backupdb conecta remotamente em 192.168.15.197:5432ssh backup@192.168.15.197 "ls -lh /var/backups/disaster-recovery/postgres/"
  ssh backup@192.168.15.197 "du -sh /var/backups/disaster-recovery/postgres/"
  ```6**: Validar database restaurado
  ```bash
  # Na máquina de gestão
  # Conecta remotamente no servidor de teste
  psql -h 192.168.15.197 -U backup -d ${DATABASE_TO_RESTORE}_restored -c "\dt"
  ```

- [ ] **T-RESTORE-PG-007**: Contar tabelas no database restaurado
  ```bash
  # Na máquina de gestão
  psql -h 192.168.15.197 -U backup -d ${DATABASE_TO_RESTORE}_restored -c "\dt" | wc -l
  ```

- [ ] **T-RESTORE-PG-008**: Contar registros no database restaurado
  ```bash
  # Na máquina de gestão
  psql -h 192.168.15.197

- [ ] **T-RESTORE-PG-001**: Conectar ao servidor de teste
  ```bash
  ssh backup@192.168.15.197
  ```

- [ ] **T-RESTORE-PG-002**: Listar backups PostgreSQL disponíveis
  ```bash
  ls -lh /var/backups/disaster-recovery/postgres/
  ```

### Restauração Database por Database

- [ ] **T-RESTORE-PG-003**: Identificar database a restaurar
  ```bash
  # Exemplo: my_production_db
  DATABASE_TO_RESTORE="my_production_db"
  BACKUP_FILE="/var/backups/disaster-recovery/postgres/${DATABASE_TO_RESTORE}_backup_*.sql.gz"
  ```

- [ ] **T-RESTORE-PG-004**: Criar database vazio no servidor de teste
  ```bash
  psql -h localhost -U backup -c "CREATE DATABASE ${DATABASE_TO_RESTORE}_restored;"
  ```

- [ ] **T-RESTORE-PG-005**: Descompactar backup
  ```bash
  gunzip -k ${BACKUP_FILE}
  ```

- [ ] **T-RESTORE-PG-006**: Executar restore com vya-backupdb
  ```bash
  # Anotar timestamp de início
  date
  
  vya-backupdb restore \
    --instance home011-postgres-test \
    --database ${DATABASE_TO_RESTORE}_restored \
    --backup-file ${BACKUP_FILE%.gz}
  
  # Anotar timestamp de fim
  date
  ```

- [ ] **T-RESTORE-PG-007**: Validar database restaurado
  ```bash
  psql -h localhost -U backup -d ${DATABASE_TO_RESTORE}_restored -c "\dt"
  ```

- [ ] **T-RESTORE-PG-008**: Contar tabelas no database restaurado
  ```bash
  psql -h localhost -U backup -d ${DATABASE_TO_RESTORE}_restored -c "\dt" | wc -l
  ```

- [ ] **T-RESTORE-PG-009**: Contar registros no database restaurado
  ```bash
  psql -h localhost -U backup -d ${DATABASE_TO_RESTORE}_restored -c "SELECT schemaname,tablename,n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC;"
  ```

---

## 🔄 Fase 7: Restauração em Teste (MySQL)

> **IMPORTANTE**: A restauração é executada da máquina de gestão. O vya-backupdb conecta remotamente no servidor de teste (192.168.15.197) para realizar a restauração.

### Preparação

- [ ] **T-RESTORE-MY-001**: Listar backups MySQL disponíveis
  ```bash
  # Na máquina de gestão
  ls -lh /var/backups/disaster-recovery/mysql/
  ```

### Restauração Database por Database

- [ ] **T-RESTORE-MY-002**: Identificar database a restaurar
  ```bash
  # Na máquina de gestão
  # Exemplo: my_app_db
  DATABASE_TO_RESTORE="my_app_db"
  BACKUP_FILE="/var/backups/disaster-recovery/mysql/${DATABASE_TO_RESTORE}_backup_*.sql.gz"
  
  echo "Database: ${DATABASE_TO_RESTORE}"
  echo "Backup: ${BACKUP_FILE}"
  ls -lh ${BACKUP_FILE}
  ```

- [ ] **T-RESTORE-MY-003**: Criar database vazio no servidor de teste (remoto)
  ```bash
  # Na máquina de gestão
  # Conecta remotamente e cria database
  mysql -h 192.168.15.197 -u backup -p'@W123Mudar#2026' -e "CREATE DATABASE ${DATABASE_TO_RESTORE}_restored CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
  ```

- [ ] **T-RESTORE-MY-004**: Descompactar backup (se necessário)
  ```bash
  # Na máquina de gestão
  gunzip -k ${BACKUP_FILE}
  ```

- [ ] **T-RESTORE-MY-005**: Executar restore com vya-backupdb
  ```bash
  # Na máquina de gestão
  # Anotar timestamp de início
  date
  
  # vya-backupdb conecta remotamente em 192.168.15.197:3306
  vya-backupdb restore \
    --instance home011-mysql-test \
    --database ${DATABASE_TO_RESTORE}_restored \
    --backup-file ${BACKUP_FILE%.gz}
  
  # Anotar timestamp de fim
  date
  ```

- [ ] **T-RESTORE-MY-006**: Validar database restaurado
  ```bash
  # Na máquina de gestão
  # Conecta remotamente no servidor de teste
  mysql -h 192.168.15.197 -u backup -p'@W123Mudar#2026' -D ${DATABASE_TO_RESTORE}_restored -e "SHOW TABLES;"
  ```

- [ ] **T-RESTORE-MY-007**: Contar tabelas no database restaurado
  ```bash
  # Na máquina de gestão
  mysql -h 192.168.15.197 -u backup -p'@W123Mudar#2026' -D ${DATABASE_TO_RESTORE}_restored -e "SHOW TABLES;" | wc -l
  ```

- [ ] **T-RESTORE-MY-008**: Contar registros no database restaurado
  ```bash
  # Na máquina de gestão
  mysql -h 192.168.15.197 -u backup -p'@W123Mudar#2026' -D ${DATABASE_TO_RESTORE}_restored -e "SELECT TABLE_NAME, TABLE_ROWS FROM information_schema.TABLES WHERE TABLE_SCHEMA='${DATABASE_TO_RESTORE}_restored';"
  ```

---

## ✅ Fase 8: Validação de Integridade

### PostgreSQL - Comparação com Baseline

- [ ] **T-VALIDATE-PG-001**: Comparar número de databases
  ```bash
  # Produção vs Teste
  # Registrar diferenças
  ```

- [ ] **T-VALIDATE-PG-002**: Comparar número de tabelas por database
  ```bash
  # Para cada database restaurado
  # Comparar com baseline de produção
  ```

- [ ] **T-VALIDATE-PG-003**: Comparar número de registros por tabela
  ```bash
  # Comparar contagens
  # Aceitar diferenças se houver replicação ativa
  ```

- [ ] **T-VALIDATE-PG-004**: Testar queries de exemplo
  ```bash
  # Executar queries típicas da aplicação
  # Validar resultados esperados
  ```

### MySQL - Comparação com Baseline

- [ ] **T-VALIDATE-MY-001**: Comparar número de databases
  ```bash
  # Produção vs Teste
  # Registrar diferenças
  ```

- [ ] **T-VALIDATE-MY-002**: Comparar número de tabelas por database
  ```bash
  # Para cada database restaurado
  # Comparar com baseline de produção
  ```

- [ ] **T-VALIDATE-MY-003**: Comparar número de registros por tabela
  ```bash
  # Comparar contagens
  # Aceitar diferenças se houver replicação ativa
  ```

- [ ] **T-VALIDATE-MY-004**: Testar queries de exemplo
  ```bash
  # Executar queries típicas da aplicação
  # Validar resultados esperados
  ```

---

## 📊 Fase 9: Métricas de Recuperação

### RTO (Recovery Time Objective)

- [ ] **T-METRICS-001**: Calcular tempo total de backup
  ```
  Início backup PostgreSQL: _____
  Fim backup PostgreSQL: _____
  Duração PostgreSQL: _____
  
  Início backup MySQL: _____
  Fim backup MySQL: _____
  Duração MySQL: _____
  
  Tempo total backup: _____
  ```

- [ ] **T-METRICS-002**: Calcular tempo de transferência
  ```
  Início transferência: _____
  Fim transferência: _____
  Duração transferência: _____
  ```

- [ ] **T-METRICS-003**: Calcular tempo de restauração
  ```
  Início restore PostgreSQL: _____
  Fim restore PostgreSQL: _____
  Duração PostgreSQL: _____
  
  Início restore MySQL: _____
  Fim restore MySQL: _____
  Duração MySQL: _____
  
  Tempo total restore: _____
  ```

- [ ] **T-METRICS-004**: Calcular RTO total
  ```
  RTO = Backup + Transferência + Restore
  RTO Total: _____
  ```

### RPO (Recovery Point Objective)

- [ ] **T-METRICS-005**: Identificar RPO
  ```
  Timestamp último backup: _____
  Timestamp simulação desastre: _____
  RPO (diferença): _____
  ```

### Tamanhos e Taxa de Compressão

- [ ] **T-METRICS-006**: Registrar tamanhos de backup
  ```
  PostgreSQL raw: _____
  PostgreSQL comprimido: _____
  Taxa compressão PostgreSQL: _____
  
  MySQL raw: _____
  MySQL comprimido: _____
  Taxa compressão MySQL: _____
  ```

---

## 🧪 Fase 10: Testes de Aplicação (Opcional)

- [ ] **T-APP-001**: Configurar aplicação para usar databases restaurados
  ```bash
  # Atualizar connection strings
  # Apontar para servidor de teste
  ```

- [ ] **T-APP-002**: Iniciar aplicação em modo teste
  ```bash
  # Executar aplicação
  # Verificar logs de conexão
  ```

- [ ] **T-APP-003**: Executar suite de testes funcionais
  ```bash
  # Testes de leitura
  # Testes de escrita
  # Testes de autenticação
  ```

- [ ] **T-APP-004**: Validar funcionalidade crítica
  ```
  [ ] Login funciona
  [ ] Leitura de dados funciona
  [ ] Dashboard carrega
  [ ] Relatórios funcionam
  ```

---

## 🧹 Fase 11: Limpeza

- [ ] **T-CLEANUP-001**: Documentar problemas encontrados
  ```
  Problema 1: _____
  Solução 1: _____
  
  Problema 2: _____
  Solução 2: _____
  ```

- [ ] **T-CLEANUP-002**: Remover databases de teste
  ```bash
  # PostgreSQL
  psql -h localhost -U backup -c "DROP DATABASE IF EXISTS <database>_restored;"
  
  # MySQL
  mysql -h localhost -u backup -p -e "DROP DATABASE IF EXISTS <database>_restored;"
  ```

- [ ] **T-CLEANUP-003**: Remover backups temporários (opcional)
  ```bash
  rm -rf /var/backups/disaster-recovery/postgres/
  rm -rf /var/backups/disaster-recovery/mysql/
  ```

- [ ] **T-CLEANUP-004**: Atualizar documentação de DR
  ```
  [ ] Atualizar tempos de RTO/RPO
  [ ] Documentar lições aprendidas
  [ ] Atualizar runbook de DR
  ```

---

## 📋 Checklist Final

### Validações Obrigatórias

- [ ] ✅ Todos os backups foram criados com sucesso
- [ ] ✅ Todos os backups foram transferidos completamente
- [ ] ✅ Todas as restaurações foram executadas sem erros
- [ ] ✅ Contagens de tabelas/registros batem (±5%)
- [ ] ✅ Queries de teste retornam resultados esperados
- [ ] ✅ RTO calculado e documentado
- [ ] ✅ RPO calculado e documentado
- [ ] ✅ Problemas documentados e solucionados

### Documentação

- [ ] 📄 Relatório de DR gerado
- [ ] 📄 Métricas documentadas
- [ ] 📄 Problemas e soluções registrados
- [ ] 📄 Runbook de DR atualizado
- [ ] 📄 Próximos testes agendados

---

## 📈 Relatório de Execução

### Informações Gerais
```
Data/Hora Início: _____________________
Data/Hora Fim: _______________________
Duração Total: _______________________
Executor: ____________________________
```

### Resultados

| Métrica | Valor | Status |
|---------|-------|--------|
| Databases backupados (PostgreSQL) | _____ | ⬜ |
| Databases backupados (MySQL) | _____ | ⬜ |
| Databases restaurados (PostgreSQL) | _____ | ⬜ |
| Databases restaurados (MySQL) | _____ | ⬜ |
| RTO (minutos) | _____ | ⬜ |
| RPO (minutos) | _____ | ⬜ |
| Taxa sucesso restore | _____ | ⬜ |
| Problemas encontrados | _____ | ⬜ |

### Status Final
- [ ] ✅ Teste completado com sucesso
- [ ] ⚠️ Teste completado com ressalvas
- [ ] ❌ Teste falhou

### Observações
```
_________________________________________________
_________________________________________________
_________________________________________________
```

---

## 🔗 Referências

- [Vault System Guide](VAULT_SYSTEM_GUIDE.md)
- [Quick Setup Guide](QUICK_SETUP_GUIDE.md)
- [Credential Rotation Guide](../CREDENTIAL_ROTATION_GUIDE.md)
- [Production Readiness Plan](../PRODUCTION_READINESS_PLAN_2026-01-13.md)

---

**Última Atualização**: 2026-01-27  
**Versão**: 1.0  
**Status**: 📋 Pronto para execução
