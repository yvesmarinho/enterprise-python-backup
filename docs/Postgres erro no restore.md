---
title: Postgres erro no restore
source: https://github.com/copilot/c/95f7a730-dd17-4471-8ae0-e92afeef76d4
author:
  - "[[GitHub]]"
published:
created: 2026-01-09
description: GitHub is where people build software. More than 150 million people use GitHub to discover, fork, and contribute to over 420 million projects.
tags:
  - postgresql
  - database
  - backup
---
postgres 18 restore chatwoot\_db show bellow error: pg\_restore -U postgres -d chatwoot\_db -c -1 /var/lib/postgresql/data/20260108\_223350\_postgresql\_chatwoot\_db.sql pg\_restore: error: could not execute query: ERROR: constraint "fk\_rails\_c3b3935057" of relation "active\_storage\_attachments" does not exist Command was: ALTER TABLE ONLY public.active\_storage\_attachments DROP CONSTRAINT fk\_rails\_c3b3935057; show me correction

## Análise Técnica Completa: Erro de Restauração PostgreSQL 18 - Chatwoot

## 🔍 Diagnóstico do Problema

O erro ocorre porque:

1. **Flag `-c` (--clean)**: Tenta executar `DROP` statements antes de criar objetos
2. **Constraint inexistente**: A constraint `fk_rails_c3b3935057` não existe no banco de destino
3. **Arquivo `.sql` vs formato custom**: Você está usando `.sql` mas chamando `pg_restore` (que é para dumps binários)

## ⚠️ Identificação do Erro Crítico

bash

```
# ERRO:  Você está usando pg_restore com arquivo .sql
pg_restore -U postgres -d chatwoot_db -c -1 /var/lib/postgresql/data/20260108_223350_postgresql_chatwoot_db.sql
```

**O arquivo `.sql` indica dump em formato texto puro**, gerado com `pg_dump` sem formato custom. O `pg_restore` é para formatos binários (`-Fc`, `-Fd`, `-Ft`).

---

## ✅ Soluções Corretas

### Solução 1: Usar psql para arquivo. sql (RECOMENDADO)

bash

```
#!/bin/bash
# Restauração de arquivo SQL com tratamento de erros

set -euo pipefail

PGUSER="postgres"
DBNAME="chatwoot_db"
BACKUP_FILE="/var/lib/postgresql/data/20260108_223350_postgresql_chatwoot_db.sql"

# Verificar se arquivo existe
if [[ ! -f "$BACKUP_FILE" ]]; then
    echo "ERRO: Arquivo não encontrado: $BACKUP_FILE" >&2
    exit 1
fi

# Opção A: Ignorar erros de DROP (RECOMENDADO para restore inicial)
echo "Restaurando banco de dados (ignorando erros de DROP)..."
psql -U "$PGUSER" -d "$DBNAME" -f "$BACKUP_FILE" -v ON_ERROR_STOP=0 2>&1 | \
    grep -v "does not exist" || true

# Opção B:  Parar em qualquer erro EXCETO DROP
echo "Restaurando banco de dados (rigoroso)..."
psql -U "$PGUSER" -d "$DBNAME" \
     -v ON_ERROR_STOP=1 \
     -f "$BACKUP_FILE"

# Opção C: Recriar banco do zero (MAIS SEGURO)
echo "Recriando banco de dados do zero..."
dropdb -U "$PGUSER" --if-exists "$DBNAME"
createdb -U "$PGUSER" "$DBNAME" -O chatwoot -T template0
psql -U "$PGUSER" -d "$DBNAME" -f "$BACKUP_FILE"

echo "✓ Restauração concluída com sucesso!"
```

### Solução 2: Limpar o SQL antes de restaurar

bash

```
#!/bin/bash
# Remove comandos DROP problemáticos do dump

ORIGINAL="/var/lib/postgresql/data/20260108_223350_postgresql_chatwoot_db.sql"
CLEANED="/tmp/chatwoot_cleaned.sql"

# Remover todas as linhas DROP CONSTRAINT que podem falhar
grep -v "DROP CONSTRAINT.*does not exist\|ALTER TABLE.*DROP CONSTRAINT" "$ORIGINAL" > "$CLEANED"

# OU usar sed para remover DROP CONSTRAINT específico
sed '/ALTER TABLE.*active_storage_attachments.*DROP CONSTRAINT.*fk_rails_c3b3935057/d' \
    "$ORIGINAL" > "$CLEANED"

# Restaurar arquivo limpo
psql -U postgres -d chatwoot_db -f "$CLEANED"

# Limpar arquivo temporário
rm -f "$CLEANED"
```

---

## 🐍 Script Python Completo para Restauração

Python

```
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo de Restauração PostgreSQL com Tratamento Robusto de Erros. 

Este módulo fornece classes e funções para restaurar backups do PostgreSQL
com validação completa de parâmetros, tratamento de erros e logging detalhado. 

Exemplos: 
    Uso básico via linha de comando:: 

        $ python3 pg_restore_handler.py --db chatwoot_db --file backup.sql

    Uso programático:: 

        >>> from pg_restore_handler import PostgreSQLRestoreManager
        >>> manager = PostgreSQLRestoreManager(
        ...     dbname='chatwoot_db',
        ...     user='postgres',
        ...     host='localhost'
        ... )
        >>> success = manager.restore_from_sql('/path/to/backup.sql')
        >>> if success:
        ...      print("Restauração concluída")

Autor: YvesMarinho
Data: 2026-01-09
Versão: 2.0.0
"""

import os
import sys
import subprocess
import logging
import re
import tempfile
import shutil
from typing import Optional, Union, Dict, List, Tuple
from pathlib import Path
from datetime import datetime
import argparse

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging. FileHandler('/var/log/postgresql/restore.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class PostgreSQLRestoreManager:
    """
    Gerenciador de restauração de backups PostgreSQL com tratamento robusto de erros. 

    Esta classe fornece métodos para restaurar backups do PostgreSQL em diversos
    formatos (SQL, custom, directory, tar), com validação de parâmetros,
    tratamento de erros de constraints e logging detalhado. 

    Args:
        dbname (str): Nome do banco de dados de destino
        user (str): Usuário PostgreSQL (padrão: 'postgres')
        host (str): Host do servidor PostgreSQL (padrão: 'localhost')
        port (int): Porta do servidor PostgreSQL (padrão:  5432)
        password (Optional[str]): Senha do usuário (padrão: None - usa . pgpass)

    Attributes:
        dbname (str): Nome do banco de dados
        user (str): Usuário PostgreSQL
        host (str): Host do servidor
        port (int): Porta do servidor
        password (Optional[str]): Senha do usuário
        env (Dict[str, str]): Variáveis de ambiente para subprocess

    Raises:
        ValueError:  Se parâmetros obrigatórios estiverem vazios ou com tipo inválido
        TypeError: Se tipos de parâmetros forem incompatíveis

    Examples:
        >>> manager = PostgreSQLRestoreManager(
        ...     dbname='test_db',
        ...     user='postgres',
        ...     host='localhost',
        ...     port=5432
        ... )
        >>> isinstance(manager, PostgreSQLRestoreManager)
        True

        >>> # Teste de validação
        >>> try:
        ...     invalid = PostgreSQLRestoreManager(dbname='', user='postgres')
        ... except ValueError as e:
        ...     print("Erro capturado")
        Erro capturado
    """

    def __init__(
        self,
        dbname:  str,
        user: str = 'postgres',
        host:  str = 'localhost',
        port: int = 5432,
        password: Optional[str] = None
    ) -> None:
        """
        Inicializa o gerenciador de restauração PostgreSQL. 

        Args:
            dbname:  Nome do banco de dados (não pode ser vazio)
            user: Nome do usuário PostgreSQL (não pode ser vazio)
            host:  Endereço do servidor (não pode ser vazio)
            port: Porta do servidor (deve ser int entre 1-65535)
            password: Senha opcional do usuário

        Raises: 
            ValueError: Se parâmetros obrigatórios forem inválidos
            TypeError: Se tipos forem incompatíveis

        Examples:
            >>> manager = PostgreSQLRestoreManager('mydb', 'myuser')
            >>> manager.dbname
            'mydb'
            >>> manager.port
            5432
        """
        try:
            # Validação de dbname
            if not isinstance(dbname, str):
                raise TypeError(f"dbname deve ser string, recebido:  {type(dbname).__name__}")
            if not dbname or not dbname.strip():
                raise ValueError("dbname não pode ser vazio")
            
            # Validação de user
            if not isinstance(user, str):
                raise TypeError(f"user deve ser string, recebido: {type(user).__name__}")
            if not user or not user. strip():
                raise ValueError("user não pode ser vazio")
            
            # Validação de host
            if not isinstance(host, str):
                raise TypeError(f"host deve ser string, recebido: {type(host).__name__}")
            if not host or not host.strip():
                raise ValueError("host não pode ser vazio")
            
            # Validação de port
            if not isinstance(port, int):
                raise TypeError(f"port deve ser int, recebido:  {type(port).__name__}")
            if not (1 <= port <= 65535):
                raise ValueError(f"port deve estar entre 1-65535, recebido: {port}")
            
            # Validação de password (opcional)
            if password is not None: 
                if not isinstance(password, str):
                    raise TypeError(f"password deve ser string ou None, recebido: {type(password).__name__}")
            
            # Atribuição após validação
            self.dbname = dbname.strip()
            self.user = user.strip()
            self.host = host.strip()
            self.port = port
            self.password = password. strip() if password else None
            
            # Configurar ambiente
            self.env = os.environ.copy()
            if self.password:
                self. env['PGPASSWORD'] = self.password
            
            logger.info(
                f"PostgreSQLRestoreManager inicializado:  "
                f"db={self.dbname}, user={self.user}, host={self. host}, port={self.port}"
            )
            
        except (ValueError, TypeError) as e:
            logger.error(f"Erro na inicialização do PostgreSQLRestoreManager: {e}")
            raise
        except Exception as e:
            logger.error(f"Erro inesperado na inicialização: {e}")
            return None

    def _validate_file(self, filepath: Union[str, Path]) -> Path:
        """
        Valida se o arquivo de backup existe e é acessível.

        Args:
            filepath: Caminho para o arquivo de backup

        Returns: 
            Path: Objeto Path validado

        Raises:
            ValueError: Se filepath for vazio ou arquivo não existir
            TypeError: Se filepath não for string ou Path
            PermissionError: Se arquivo não for legível

        Examples:
            >>> import tempfile
            >>> manager = PostgreSQLRestoreManager('test_db', 'postgres')
            >>> with tempfile.NamedTemporaryFile(delete=False) as f:
            ...     temp_path = f.name
            >>> result = manager._validate_file(temp_path)
            >>> os.unlink(temp_path)
            >>> result is not False
            True
        """
        try:
            # Validação de tipo
            if not isinstance(filepath, (str, Path)):
                raise TypeError(
                    f"filepath deve ser str ou Path, recebido: {type(filepath).__name__}"
                )
            
            # Validação de vazio
            if isinstance(filepath, str) and (not filepath or not filepath.strip()):
                raise ValueError("filepath não pode ser vazio")
            
            # Converter para Path
            file_path = Path(filepath) if isinstance(filepath, str) else filepath
            
            # Verificar existência
            if not file_path.exists():
                raise ValueError(f"Arquivo não encontrado: {file_path}")
            
            # Verificar se é arquivo
            if not file_path. is_file():
                raise ValueError(f"Caminho não é um arquivo: {file_path}")
            
            # Verificar permissões de leitura
            if not os.access(file_path, os.R_OK):
                raise PermissionError(f"Arquivo sem permissão de leitura: {file_path}")
            
            logger. info(f"Arquivo validado com sucesso: {file_path}")
            return file_path
            
        except (ValueError, TypeError, PermissionError) as e:
            logger.error(f"Erro na validação do arquivo:  {e}")
            return False
        except Exception as e:
            logger.error(f"Erro inesperado na validação do arquivo: {e}")
            return False

    def _detect_backup_format(self, filepath: Path) -> str:
        """
        Detecta o formato do arquivo de backup PostgreSQL.

        Args:
            filepath: Caminho validado para o arquivo

        Returns:
            str:  Formato detectado ('sql', 'custom', 'directory', 'tar', 'unknown')

        Examples:
            >>> manager = PostgreSQLRestoreManager('test_db', 'postgres')
            >>> import tempfile
            >>> with tempfile.NamedTemporaryFile(suffix='.sql', delete=False) as f:
            ...     f.write(b"-- PostgreSQL dump")
            ...     temp_path = f.name
            >>> format_type = manager._detect_backup_format(Path(temp_path))
            >>> os.unlink(temp_path)
            >>> format_type
            'sql'
        """
        try:
            # Validação de parâmetro
            if not isinstance(filepath, Path):
                raise TypeError(f"filepath deve ser Path, recebido: {type(filepath).__name__}")
            
            # Verificar extensão
            suffix = filepath.suffix.lower()
            
            if suffix == '.sql': 
                logger.info(f"Formato detectado por extensão: SQL")
                return 'sql'
            elif suffix in ['.dump', '.backup']:
                # Verificar magic bytes para formato custom
                with open(filepath, 'rb') as f:
                    header = f.read(5)
                    if header == b'PGDMP':
                        logger.info(f"Formato detectado:  Custom")
                        return 'custom'
            elif suffix == '.tar':
                logger.info(f"Formato detectado:  TAR")
                return 'tar'
            elif filepath.is_dir():
                logger.info(f"Formato detectado:  Directory")
                return 'directory'
            
            # Tentar ler primeiros bytes para identificar
            try:
                with open(filepath, 'rb') as f:
                    header = f.read(10)
                    if b'PGDMP' in header:
                        logger.info(f"Formato detectado por magic bytes: Custom")
                        return 'custom'
                    elif b'--' in header or b'CREATE' in header or b'INSERT' in header:
                        logger.info(f"Formato detectado por conteúdo: SQL")
                        return 'sql'
            except Exception as e:
                logger.warning(f"Não foi possível ler header do arquivo: {e}")
            
            logger.warning(f"Formato não identificado para:  {filepath}")
            return 'unknown'
            
        except Exception as e:
            logger.error(f"Erro ao detectar formato do backup: {e}")
            return False

    def clean_sql_drop_constraints(
        self,
        input_file: Union[str, Path],
        output_file: Optional[Union[str, Path]] = None
    ) -> Union[Path, bool]:
        """
        Remove comandos DROP CONSTRAINT problemáticos de arquivo SQL.

        Args:
            input_file: Arquivo SQL original
            output_file: Arquivo SQL de saída (opcional, usa temporário se None)

        Returns:
            Path: Caminho do arquivo limpo ou False em caso de erro

        Examples:
            >>> manager = PostgreSQLRestoreManager('test_db', 'postgres')
            >>> import tempfile
            >>> with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
            ...     f.write("ALTER TABLE test DROP CONSTRAINT fk_test;\\n")
            ...     f. write("CREATE TABLE users (id INT);\\n")
            ...     input_path = f.name
            >>> result = manager.clean_sql_drop_constraints(input_path)
            >>> os.unlink(input_path)
            >>> if result:
            ...     os.unlink(result)
            >>> result is not False
            True
        """
        try:
            # Validar arquivo de entrada
            validated_input = self._validate_file(input_file)
            if not validated_input:
                raise ValueError(f"Arquivo de entrada inválido: {input_file}")
            
            # Determinar arquivo de saída
            if output_file:
                if not isinstance(output_file, (str, Path)):
                    raise TypeError(
                        f"output_file deve ser str ou Path, recebido: {type(output_file).__name__}"
                    )
                output_path = Path(output_file)
            else:
                # Criar arquivo temporário
                fd, temp_path = tempfile. mkstemp(suffix='.sql', prefix='pg_cleaned_')
                os.close(fd)
                output_path = Path(temp_path)
            
            logger.info(f"Limpando arquivo SQL:  {validated_input} -> {output_path}")
            
            # Padrões de linhas problemáticas para remover
            drop_patterns = [
                re.compile(r'^\s*ALTER\s+TABLE.*DROP\s+CONSTRAINT.*fk_rails_.*', re.IGNORECASE),
                re.compile(r'^\s*ALTER\s+TABLE.*DROP\s+CONSTRAINT.*IF\s+EXISTS.*', re.IGNORECASE),
            ]
            
            lines_removed = 0
            lines_kept = 0
            
            # Processar arquivo linha por linha
            with open(validated_input, 'r', encoding='utf-8') as infile, \
                 open(output_path, 'w', encoding='utf-8') as outfile:
                
                for line_num, line in enumerate(infile, 1):
                    # Verificar se linha deve ser removida
                    should_remove = any(pattern.match(line) for pattern in drop_patterns)
                    
                    if should_remove:
                        lines_removed += 1
                        logger.debug(f"Linha {line_num} removida: {line. strip()[:80]}")
                    else:
                        outfile.write(line)
                        lines_kept += 1
            
            logger.info(
                f"Limpeza concluída: {lines_kept} linhas mantidas, "
                f"{lines_removed} linhas removidas"
            )
            
            return output_path
            
        except (ValueError, TypeError, IOError) as e:
            logger.error(f"Erro ao limpar arquivo SQL: {e}")
            return False
        except Exception as e:
            logger.error(f"Erro inesperado ao limpar arquivo SQL: {e}")
            return False

    def restore_from_sql(
        self,
        filepath: Union[str, Path],
        clean_drops: bool = True,
        stop_on_error: bool = False,
        single_transaction: bool = True
    ) -> bool:
        """
        Restaura backup PostgreSQL de arquivo SQL.

        Args:
            filepath: Caminho para o arquivo SQL
            clean_drops: Remove DROP CONSTRAINT problemáticos antes de restaurar
            stop_on_error: Para execução no primeiro erro
            single_transaction:  Executa restore em transação única

        Returns:
            bool: True se restauração foi bem-sucedida, False caso contrário

        Examples:
            >>> manager = PostgreSQLRestoreManager('test_db', 'postgres')
            >>> import tempfile
            >>> with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
            ...     f.write("CREATE TABLE test_table (id INT);\\n")
            ...     temp_path = f.name
            >>> # Nota: este exemplo não executa realmente a restauração
            >>> # result = manager.restore_from_sql(temp_path)
            >>> os.unlink(temp_path)
        """
        try:
            # Validar arquivo
            validated_file = self._validate_file(filepath)
            if not validated_file:
                raise ValueError(f"Arquivo inválido: {filepath}")
            
            # Limpar DROP CONSTRAINT se solicitado
            restore_file = validated_file
            temp_file = None
            
            if clean_drops:
                logger.info("Limpando comandos DROP CONSTRAINT problemáticos...")
                cleaned_file = self.clean_sql_drop_constraints(validated_file)
                if not cleaned_file:
                    logger.warning("Falha ao limpar arquivo, usando original")
                else:
                    restore_file = cleaned_file
                    temp_file = cleaned_file
            
            # Construir comando psql
            cmd = [
                'psql',
                '-U', self.user,
                '-h', self.host,
                '-p', str(self.port),
                '-d', self.dbname,
                '-f', str(restore_file)
            ]
            
            # Adicionar opções
            if single_transaction:
                cmd.extend(['-1'])  # Single transaction
            
            if stop_on_error:
                cmd.extend(['-v', 'ON_ERROR_STOP=1'])
            else:
                cmd.extend(['-v', 'ON_ERROR_STOP=0'])
            
            # Adicionar opções de output
            cmd.extend([
                '-v', 'VERBOSITY=verbose',
                '--echo-errors'
            ])
            
            logger.info(f"Executando comando: {' '.join(cmd)}")
            
            # Executar restauração
            result = subprocess.run(
                cmd,
                env=self.env,
                capture_output=True,
                text=True,
                timeout=3600  # Timeout de 1 hora
            )
            
            # Log de saída
            if result. stdout:
                logger.info(f"STDOUT:\n{result.stdout}")
            if result.stderr:
                # Filtrar avisos "does not exist" se não estamos parando em erros
                stderr_lines = result.stderr.split('\n')
                filtered_stderr = []
                
                for line in stderr_lines: 
                    if not stop_on_error and 'does not exist' in line. lower():
                        logger.debug(f"Aviso ignorado: {line}")
                    else:
                        filtered_stderr.append(line)
                
                if filtered_stderr:
                    stderr_text = '\n'.join(filtered_stderr)
                    if result.returncode != 0:
                        logger.error(f"STDERR:\n{stderr_text}")
                    else:
                        logger. warning(f"STDERR:\n{stderr_text}")
            
            # Limpar arquivo temporário se criado
            if temp_file and temp_file != validated_file:
                try:
                    os.unlink(temp_file)
                    logger.debug(f"Arquivo temporário removido: {temp_file}")
                except Exception as e:
                    logger.warning(f"Não foi possível remover arquivo temporário: {e}")
            
            # Verificar sucesso
            if result.returncode == 0:
                logger. info("✓ Restauração SQL concluída com sucesso!")
                return True
            else:
                logger.error(f"✗ Restauração falhou com código:  {result.returncode}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("Timeout na execução da restauração (>1 hora)")
            return False
        except (ValueError, TypeError, subprocess.SubprocessError) as e:
            logger.error(f"Erro na restauração SQL: {e}")
            return False
        except Exception as e: 
            logger.error(f"Erro inesperado na restauração SQL: {e}")
            return False

    def restore_from_custom(
        self,
        filepath:  Union[str, Path],
        jobs: int = 4,
        clean_before: bool = False
    ) -> bool:
        """
        Restaura backup PostgreSQL de formato custom/binary.

        Args:
            filepath: Caminho para o arquivo de backup custom
            jobs: Número de jobs paralelos para restauração
            clean_before:  Limpa objetos existentes antes de restaurar

        Returns:
            bool: True se restauração foi bem-sucedida, False caso contrário

        Examples:
            >>> manager = PostgreSQLRestoreManager('test_db', 'postgres')
            >>> # Nota: este exemplo requer um arquivo de backup real
            >>> # result = manager. restore_from_custom('/path/to/backup.dump')
        """
        try:
            # Validar arquivo
            validated_file = self._validate_file(filepath)
            if not validated_file:
                raise ValueError(f"Arquivo inválido: {filepath}")
            
            # Validar jobs
            if not isinstance(jobs, int):
                raise TypeError(f"jobs deve ser int, recebido:  {type(jobs).__name__}")
            if jobs < 1:
                raise ValueError(f"jobs deve ser >= 1, recebido: {jobs}")
            
            # Construir comando pg_restore
            cmd = [
                'pg_restore',
                '-U', self.user,
                '-h', self.host,
                '-p', str(self.port),
                '-d', self.dbname,
                '-j', str(jobs),
                '--verbose'
            ]
            
            # Adicionar opções
            if clean_before:
                cmd. append('--clean')
                cmd.append('--if-exists')  # Evita erros se objeto não existe
            
            cmd.append(str(validated_file))
            
            logger.info(f"Executando comando: {' '.join(cmd)}")
            
            # Executar restauração
            result = subprocess.run(
                cmd,
                env=self.env,
                capture_output=True,
                text=True,
                timeout=7200  # Timeout de 2 horas
            )
            
            # Log de saída
            if result.stdout:
                logger. info(f"STDOUT:\n{result.stdout}")
            if result.stderr:
                logger.warning(f"STDERR:\n{result.stderr}")
            
            # Verificar sucesso
            if result. returncode == 0:
                logger.info("✓ Restauração custom concluída com sucesso!")
                return True
            else: 
                logger.error(f"✗ Restauração falhou com código: {result.returncode}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("Timeout na execução da restauração (>2 horas)")
            return False
        except (ValueError, TypeError, subprocess.SubprocessError) as e:
            logger. error(f"Erro na restauração custom: {e}")
            return False
        except Exception as e:
            logger.error(f"Erro inesperado na restauração custom: {e}")
            return False

    def recreate_database(self, owner: Optional[str] = None) -> bool:
        """
        Recria o banco de dados do zero (DROP + CREATE).

        Args:
            owner: Proprietário do novo banco (padrão: self.user)

        Returns:
            bool: True se recriação foi bem-sucedida, False caso contrário

        Warning:
            Esta operação APAGA TODOS OS DADOS do banco de dados existente! 

        Examples:
            >>> manager = PostgreSQLRestoreManager('test_db', 'postgres')
            >>> # Nota: este exemplo não executa realmente a recriação
            >>> # result = manager. recreate_database(owner='myuser')
        """
        try:
            # Validar owner
            if owner is not None: 
                if not isinstance(owner, str):
                    raise TypeError(f"owner deve ser str, recebido: {type(owner).__name__}")
                if not owner.strip():
                    raise ValueError("owner não pode ser vazio")
                db_owner = owner. strip()
            else:
                db_owner = self.user
            
            logger.warning(
                f"⚠ ATENÇÃO: Recriando banco de dados '{self.dbname}' - "
                f"TODOS OS DADOS SERÃO PERDIDOS!"
            )
            
            # Terminar conexões ativas
            logger.info("Terminando conexões ativas...")
            terminate_cmd = [
                'psql',
                '-U', self.user,
                '-h', self.host,
                '-p', str(self.port),
                '-d', 'postgres',
                '-c',
                f"""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = '{self. dbname}'
                  AND pid <> pg_backend_pid();
                """
            ]
            
            subprocess.run(
                terminate_cmd,
                env=self.env,
                capture_output=True,
                timeout=60
            )
            
            # DROP DATABASE
            logger.info(f"Removendo banco de dados: {self. dbname}")
            drop_cmd = [
                'dropdb',
                '-U', self.user,
                '-h', self.host,
                '-p', str(self.port),
                '--if-exists',
                self. dbname
            ]
            
            result_drop = subprocess.run(
                drop_cmd,
                env=self.env,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result_drop.returncode != 0:
                logger.error(f"Erro ao remover banco:  {result_drop.stderr}")
                return False
            
            # CREATE DATABASE
            logger.info(f"Criando banco de dados: {self.dbname}")
            create_cmd = [
                'createdb',
                '-U', self.user,
                '-h', self.host,
                '-p', str(self.port),
                '-O', db_owner,
                '-T', 'template0',
                '-E', 'UTF8',
                self.dbname
            ]
            
            result_create = subprocess.run(
                create_cmd,
                env=self.env,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result_create.returncode != 0:
                logger.error(f"Erro ao criar banco: {result_create.stderr}")
                return False
            
            logger.info(f"✓ Banco de dados '{self.dbname}' recriado com sucesso!")
            return True
            
        except subprocess. TimeoutExpired:
            logger.error("Timeout na recriação do banco de dados")
            return False
        except (ValueError, TypeError, subprocess.SubprocessError) as e:
            logger.error(f"Erro na recriação do banco:  {e}")
            return False
        except Exception as e:
            logger.error(f"Erro inesperado na recriação do banco: {e}")
            return False

    def full_restore_workflow(
        self,
        filepath: Union[str, Path],
        recreate:  bool = False,
        owner: Optional[str] = None
    ) -> bool:
        """
        Workflow completo de restauração com detecção automática de formato.

        Args:
            filepath: Caminho para o arquivo de backup
            recreate: Se True, recria banco antes de restaurar
            owner:  Proprietário do banco (usado se recreate=True)

        Returns:
            bool: True se restauração completa foi bem-sucedida

        Examples:
            >>> manager = PostgreSQLRestoreManager('test_db', 'postgres')
            >>> # result = manager.full_restore_workflow('/path/to/backup.sql', recreate=True)
        """
        try: 
            logger.info("="*80)
            logger.info("INICIANDO WORKFLOW DE RESTAURAÇÃO COMPLETO")
            logger.info("="*80)
            
            # Validar arquivo
            validated_file = self._validate_file(filepath)
            if not validated_file:
                raise ValueError(f"Arquivo inválido: {filepath}")
            
            # Detectar formato
            backup_format = self._detect_backup_format(validated_file)
            logger.info(f"Formato detectado: {backup_format}")
            
            if backup_format == 'unknown':
                logger.error("Formato de backup não reconhecido")
                return False
            
            # Recriar banco se solicitado
            if recreate: 
                logger.info("Recriando banco de dados...")
                if not self.recreate_database(owner):
                    logger.error("Falha ao recriar banco de dados")
                    return False
            
            # Restaurar baseado no formato
            success = False
            
            if backup_format == 'sql':
                logger.info("Restaurando de arquivo SQL...")
                success = self.restore_from_sql(
                    validated_file,
                    clean_drops=True,
                    stop_on_error=False,
                    single_transaction=False
                )
            elif backup_format == 'custom':
                logger.info("Restaurando de formato custom...")
                success = self. restore_from_custom(
                    validated_file,
                    jobs=4,
                    clean_before=not recreate
                )
            elif backup_format in ['tar', 'directory']:
                logger.info(f"Restaurando de formato {backup_format}...")
                success = self.restore_from_custom(
                    validated_file,
                    jobs=4,
                    clean_before=not recreate
                )
            
            if success:
                logger.info("="*80)
                logger.info("✓ RESTAURAÇÃO COMPLETA BEM-SUCEDIDA!")
                logger.info("="*80)
            else:
                logger.error("="*80)
                logger. error("✗ RESTAURAÇÃO FALHOU!")
                logger. error("="*80)
            
            return success
            
        except (ValueError, TypeError) as e:
            logger.error(f"Erro no workflow de restauração: {e}")
            return False
        except Exception as e:
            logger.error(f"Erro inesperado no workflow de restauração: {e}")
            return False

def main():
    """
    Função principal para execução via linha de comando. 

    Examples:
        Executar via terminal:: 

            $ python3 pg_restore_handler.py \\
                --dbname chatwoot_db \\
                --user postgres \\
                --file /path/to/backup.sql \\
                --recreate
    """
    try:
        parser = argparse.ArgumentParser(
            description='Restauração robusta de backups PostgreSQL',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Exemplos de uso:

  # Restaurar arquivo SQL sem recriar banco
  %(prog)s --dbname mydb --file backup.sql

  # Restaurar com recriação completa do banco
  %(prog)s --dbname mydb --file backup. sql --recreate --owner myuser

  # Restaurar formato custom com host remoto
  %(prog)s --dbname mydb --host 192.168.1.100 --file backup.dump

  # Restaurar com autenticação por senha
  %(prog)s --dbname mydb --file backup.sql --password mypass
            """
        )
        
        parser.add_argument(
            '--dbname', '-d',
            required=True,
            help='Nome do banco de dados de destino'
        )
        parser.add_argument(
            '--user', '-U',
            default='postgres',
            help='Usuário PostgreSQL (padrão: postgres)'
        )
        parser.add_argument(
            '--host', '-h',
            default='localhost',
            help='Host do servidor PostgreSQL (padrão:  localhost)'
        )
        parser.add_argument(
            '--port', '-p',
            type=int,
            default=5432,
            help='Porta do servidor PostgreSQL (padrão: 5432)'
        )
        parser.add_argument(
            '--password', '-W',
            help='Senha do usuário (use . pgpass quando possível)'
        )
        parser.add_argument(
            '--file', '-f',
            required=True,
            help='Caminho para o arquivo de backup'
        )
        parser.add_argument(
            '--recreate',
            action='store_true',
            help='Recriar banco de dados antes de restaurar (APAGA DADOS! )'
        )
        parser.add_argument(
            '--owner', '-O',
            help='Proprietário do banco (usado com --recreate)'
        )
        parser.add_argument(
            '--verbose', '-v',
            action='store_true',
            help='Modo verbose (mais detalhes no log)'
        )
        
        args = parser.parse_args()
        
        # Configurar nível de log
        if args.verbose:
            logger.setLevel(logging.DEBUG)
        
        # Criar gerenciador
        manager = PostgreSQLRestoreManager(
            dbname=args.dbname,
            user=args.user,
            host=args.host,
            port=args.port,
            password=args.password
        )
        
        if not manager: 
            logger.error("Falha ao criar gerenciador de restauração")
            return False
        
        # Executar workflow
        success = manager.full_restore_workflow(
            filepath=args.file,
            recreate=args.recreate,
            owner=args.owner
        )
        
        # Retornar código de saída apropriado
        return 0 if success else 1
        
    except KeyboardInterrupt:
        logger. warning("\n\n⚠ Operação cancelada pelo usuário")
        return 130
    except Exception as e: 
        logger.error(f"Erro fatal na execução: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
```

---

## 🔧 Scripts Bash Adicionais

### Script 1: Correção Direta no Shell

bash

```
#!/bin/bash
# fix_chatwoot_restore.sh

set -euo pipefail

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configurações
PGUSER="${PGUSER:-postgres}"
DBNAME="${DBNAME:-chatwoot_db}"
BACKUP_FILE="${1:-/var/lib/postgresql/data/20260108_223350_postgresql_chatwoot_db.sql}"

echo -e "${YELLOW}[INFO]${NC} Iniciando correção de restauração Chatwoot..."
echo -e "${YELLOW}[INFO]${NC} Banco:  $DBNAME"
echo -e "${YELLOW}[INFO]${NC} Arquivo:  $BACKUP_FILE"

# Função de erro
error_exit() {
    echo -e "${RED}[ERRO]${NC} $1" >&2
    exit 1
}

# Validação
[[ -f "$BACKUP_FILE" ]] || error_exit "Arquivo não encontrado: $BACKUP_FILE"

# Verificar se é arquivo SQL ou dump binário
if file "$BACKUP_FILE" | grep -q "ASCII\|text"; then
    echo -e "${GREEN}[OK]${NC} Arquivo SQL detectado"
    IS_SQL=true
else
    echo -e "${GREEN}[OK]${NC} Arquivo binário detectado"
    IS_SQL=false
fi

# Menu de opções
echo ""
echo "Escolha o método de restauração:"
echo "1) Recriar banco do zero + restaurar (RECOMENDADO)"
echo "2) Restaurar ignorando erros de DROP"
echo "3) Limpar SQL + restaurar"
echo "4) Restaurar formato custom (pg_restore)"
echo ""
read -p "Opção [1-4]: " OPTION

case $OPTION in
    1)
        echo -e "${YELLOW}[INFO]${NC} Recriando banco de dados..."
        
        # Terminar conexões
        psql -U "$PGUSER" -d postgres -c \
            "SELECT pg_terminate_backend(pg_stat_activity. pid)
             FROM pg_stat_activity
             WHERE datname = '$DBNAME' AND pid <> pg_backend_pid();" \
            2>/dev/null || true
        
        # Drop e create
        dropdb -U "$PGUSER" --if-exists "$DBNAME"
        createdb -U "$PGUSER" "$DBNAME" -O chatwoot -T template0 -E UTF8
        
        # Restaurar
        echo -e "${YELLOW}[INFO]${NC} Restaurando backup..."
        psql -U "$PGUSER" -d "$DBNAME" -f "$BACKUP_FILE" \
            -v ON_ERROR_STOP=0 \
            2>&1 | tee restore. log
        
        echo -e "${GREEN}[✓]${NC} Restauração concluída!"
        ;;
        
    2)
        echo -e "${YELLOW}[INFO]${NC} Restaurando com erros ignorados..."
        psql -U "$PGUSER" -d "$DBNAME" -f "$BACKUP_FILE" \
            -v ON_ERROR_STOP=0 \
            2>&1 | grep -v "does not exist" | tee restore. log
        
        echo -e "${GREEN}[✓]${NC} Restauração concluída!"
        ;;
        
    3)
        echo -e "${YELLOW}[INFO]${NC} Limpando arquivo SQL..."
        CLEANED_FILE="/tmp/chatwoot_cleaned_$(date +%s).sql"
        
        # Remover DROP CONSTRAINT problemáticos
        grep -vE "ALTER TABLE.*DROP CONSTRAINT.*fk_rails_" "$BACKUP_FILE" > "$CLEANED_FILE"
        
        echo -e "${YELLOW}[INFO]${NC} Restaurando arquivo limpo..."
        psql -U "$PGUSER" -d "$DBNAME" -f "$CLEANED_FILE" \
            -v ON_ERROR_STOP=0 \
            2>&1 | tee restore.log
        
        rm -f "$CLEANED_FILE"
        echo -e "${GREEN}[✓]${NC} Restauração concluída!"
        ;;
        
    4)
        if [[ "$IS_SQL" == true ]]; then
            error_exit "Arquivo é SQL text, use pg_restore apenas para formatos custom/tar/directory"
        fi
        
        echo -e "${YELLOW}[INFO]${NC} Restaurando formato custom..."
        pg_restore -U "$PGUSER" -d "$DBNAME" \
            --clean \
            --if-exists \
            --no-acl \
            --no-owner \
            -j 4 \
            --verbose \
            "$BACKUP_FILE" \
            2>&1 | tee restore.log
        
        echo -e "${GREEN}[✓]${NC} Restauração concluída!"
        ;;
        
    *)
        error_exit "Opção inválida"
        ;;
esac

# Verificar integridade
echo ""
echo -e "${YELLOW}[INFO]${NC} Verificando integridade..."
psql -U "$PGUSER" -d "$DBNAME" -c "\dt" >/dev/null 2>&1 && \
    echo -e "${GREEN}[✓]${NC} Banco de dados acessível" || \
    echo -e "${RED}[✗]${NC} Erro ao acessar banco"

# Estatísticas
TABLE_COUNT=$(psql -U "$PGUSER" -d "$DBNAME" -t -c \
    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';" 2>/dev/null || echo "0")

echo -e "${GREEN}[✓]${NC} Total de tabelas: $TABLE_COUNT"
echo ""
echo -e "${GREEN}[✓]${NC} Processo finalizado!"
echo -e "${YELLOW}[INFO]${NC} Log salvo em: restore.log"
```

### Permissões e Uso

bash

```
# Dar permissão de execução
chmod +x fix_chatwoot_restore.sh

# Executar
./fix_chatwoot_restore.sh

# OU especificar arquivo
./fix_chatwoot_restore.sh /caminho/custom/backup.sql
```

---

## 📊 Comparação de Métodos

| Método | Vantagens | Desvantagens | Quando Usar |
| --- | --- | --- | --- |
| **Recriar DB + Restaurar** | ✅ Mais limpo   ✅ Sem conflitos | ❌ Apaga dados   ❌ Downtime | Ambiente dev/test   Primeiro restore |
| **Ignorar Erros DROP** | ✅ Rápido   ✅ Mantém dados | ⚠️ Pode ter inconsistências | DB já populado   Atualização incremental |
| **Limpar SQL** | ✅ Controle total   ✅ Auditável | ❌ Requer análise manual | Problemas específicos   Debug detalhado |
| **pg\_restore Custom** | ✅ Paralelo (-j)   ✅ Seletivo | ❌ Só funciona com dump custom | Dumps grandes   Restore parcial |

---

## 🛠️ Comandos Vi para Editar SQL Manualmente

vim

```
# Abrir arquivo no vi
vi /var/lib/postgresql/data/20260108_223350_postgresql_chatwoot_db.sql

# Buscar todas as ocorrências de DROP CONSTRAINT
/DROP CONSTRAINT

# Deletar linha atual
dd

# Deletar todas as linhas com padrão
: g/DROP CONSTRAINT.*fk_rails_/d

# Salvar e sair
:wq

# Cancelar sem salvar
:q!

# Buscar e substituir globalmente
:%s/DROP CONSTRAINT fk_rails_/-- DROP CONSTRAINT fk_rails_/g
```

---

## 🔍 Análise Pós-Restauração

bash

```
#!/bin/bash
# verify_restore.sh

DBNAME="chatwoot_db"
PGUSER="postgres"

echo "=== VERIFICAÇÃO PÓS-RESTAURAÇÃO ==="

# 1. Verificar conexão
echo -e "\n1. Testando conexão..."
psql -U "$PGUSER" -d "$DBNAME" -c "SELECT version();" || exit 1

# 2. Contar tabelas
echo -e "\n2. Contando tabelas..."
psql -U "$PGUSER" -d "$DBNAME" -t -c \
    "SELECT COUNT(*) || ' tabelas' FROM information_schema.tables WHERE table_schema='public';"

# 3. Verificar constraints faltantes
echo -e "\n3. Verificando foreign keys..."
psql -U "$PGUSER" -d "$DBNAME" -c \
    "SELECT conname, conrelid::regclass
     FROM pg_constraint
     WHERE contype = 'f'
     ORDER BY conrelid::regclass:: text;"

# 4. Verificar tabela específica do Chatwoot
echo -e "\n4. Verificando active_storage_attachments..."
psql -U "$PGUSER" -d "$DBNAME" -c \
    "SELECT COUNT(*) || ' registros' FROM active_storage_attachments;" 2>/dev/null || \
    echo "Tabela não encontrada ou vazia"

# 5. Verificar índices
echo -e "\n5. Contando índices..."
psql -U "$PGUSER" -d "$DBNAME" -t -c \
    "SELECT COUNT(*) || ' índices' FROM pg_indexes WHERE schemaname='public';"

# 6. Verificar tamanho do banco
echo -e "\n6. Tamanho do banco..."
psql -U "$PGUSER" -d "$DBNAME" -c \
    "SELECT pg_size_pretty(pg_database_size('$DBNAME'));"

# 7. Verificar usuários/roles
echo -e "\n7. Roles do banco..."
psql -U "$PGUSER" -d "$DBNAME" -c \
    "SELECT DISTINCT grantee FROM information_schema.role_table_grants WHERE table_schema='public';"

echo -e "\n=== VERIFICAÇÃO CONCLUÍDA ==="
```

---

## 📝 Checklist de Troubleshooting

Markdown

```
### ANTES DE RESTAURAR
- [ ] Backup do banco atual existe? 
- [ ] Espaço em disco suficiente?  (df -h)
- [ ] PostgreSQL versão compatível?  (psql --version)
- [ ] Arquivo de backup íntegro?  (file backup.sql)
- [ ] Permissões de leitura OK?  (ls -lh backup.sql)

### DURANTE RESTAURAÇÃO
- [ ] Monitorar logs:  tail -f /var/log/postgresql/*. log
- [ ] Monitorar processos: watch 'ps aux | grep postgres'
- [ ] Monitorar disco: watch df -h
- [ ] Conexões ativas: SELECT * FROM pg_stat_activity;

### APÓS RESTAURAÇÃO
- [ ] Tabelas criadas?  \dt
- [ ] Dados presentes? SELECT COUNT(*) FROM <table>;
- [ ] Foreign keys OK? \d <table>
- [ ] Índices criados? \di
- [ ] VACUUM ANALYZE executado?
- [ ] Permissões corretas?  GRANT verificado? 
- [ ] Application conecta?  Testar app
```

---

## 🎯 Solução Definitiva Recomendada

bash

```
#!/bin/bash
# solution_final.sh - SOLUÇÃO COMPLETA

PGUSER="postgres"
DBNAME="chatwoot_db"
BACKUP="/var/lib/postgresql/data/20260108_223350_postgresql_chatwoot_db.sql"

# 1. Validar arquivo
[[ -f "$BACKUP" ]] || { echo "Erro: Arquivo não encontrado"; exit 1; }

# 2. Recriar banco (MAIS SEGURO)
echo "Recriando banco..."
psql -U "$PGUSER" -d postgres <<SQL
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = '$DBNAME';

DROP DATABASE IF EXISTS $DBNAME;
CREATE DATABASE $DBNAME
    OWNER chatwoot
    ENCODING 'UTF8'
    LC_COLLATE 'en_US.UTF-8'
    LC_CTYPE 'en_US.UTF-8'
    TEMPLATE template0;
SQL

# 3. Restaurar
echo "Restaurando..."
psql -U "$PGUSER" -d "$DBNAME" \
    -f "$BACKUP" \
    -v ON_ERROR_STOP=0 \
    --quiet \
    2>&1 | grep -vE "does not exist|already exists" > restore.log

# 4. Verificar
echo "Verificando..."
TABLES=$(psql -U "$PGUSER" -d "$DBNAME" -t -c \
    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';")

if [[ $TABLES -gt 0 ]]; then
    echo "✓ Sucesso!  $TABLES tabelas restauradas"
    exit 0
else
    echo "✗ Falha na restauração"
    cat restore.log
    exit 1
fi
```

---

## 💡 Dicas Avançadas

### 1\. Restauração Paralela (Se formato custom)

bash

```
# Converter SQL para custom (para futuros backups)
pg_dump -U postgres -d chatwoot_db -Fc -f chatwoot_custom.dump

# Restaurar com 8 jobs paralelos
pg_restore -U postgres -d chatwoot_db -j 8 chatwoot_custom.dump
```

### 2\. Restaurar Apenas Esquema

bash

```
# Apenas estrutura (sem dados)
pg_restore -U postgres -d chatwoot_db --schema-only backup.dump

# Apenas dados (sem estrutura)
pg_restore -U postgres -d chatwoot_db --data-only backup. dump
```

### 3\. Restaurar Tabelas Específicas

bash

```
# Listar tabelas no backup
pg_restore -l backup.dump | grep "TABLE DATA"

# Restaurar apenas active_storage_attachments
pg_restore -U postgres -d chatwoot_db -t active_storage_attachments backup.dump
```

---

## 🚀 Automação com Cron

bash

```
# Adicionar no crontab
crontab -e

# Backup diário às 2h da manhã
0 2 * * * /usr/local/bin/backup_chatwoot.sh

# Conteúdo de backup_chatwoot.sh
#!/bin/bash
DATE=$(date +\%Y\%m\%d_\%H\%M\%S)
BACKUP_DIR="/var/lib/postgresql/backups"
mkdir -p "$BACKUP_DIR"

pg_dump -U postgres -d chatwoot_db -Fc \
    -f "$BACKUP_DIR/${DATE}_chatwoot. dump"

# Manter apenas últimos 7 dias
find "$BACKUP_DIR" -name "*.dump" -mtime +7 -delete
```

---

**Resumo**: Use a **Solução 1** (psql com arquivo. sql) ou o **script Python completo** para máxima robustez. O erro ocorre porque `pg_restore` é para dumps binários, não arquivos.sql de texto.