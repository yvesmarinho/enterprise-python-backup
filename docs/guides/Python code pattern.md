---
author: Yves Marinho
created: 2024-06-17, 11:55
lead: Python exemplos de códigos utilizados frequentemente
modified: 2024-06-17, 11:55
source-media: internet
source-info: https://yves.eti.br
tags:
  - python
  - commands
  - modelo
version: "0.00"
---
---
## Content Index

- [Lista de comandos](#Lista%20de%20Comandos)
- [Docstring do programa](###Docstring%20do%20programa)
- [Modelo de documentação de Classe ou Função](###Modelo%20de%20documentação%20de%20Classe%20ou%20Função)
- [Informação do inicio e fim do programa](###Informação%20do%20inicio%20e%20fim%20do%20programa)
- [Informação do inicio e fim da função/classe](###Informação%20do%20inicio%20e%20fim%20da%20função/classe)
- [Mostrar dados recebidos](###Mostrar%20dados%20recebidos)
- [Coletar conteúdo da variável do `Airflow`](###Coletar%20conteúdo%20da%20variável%20do%20`Airflow`)
- [Coletar dados da conexão do `Airflow`](###Coletar%20dados%20da%20conexão%20do%20`Airflow`)
- [Tratamento de Ambiente DEV e PROD](###Tratamento%20de%20Ambiente%20DEV%20e%20PROD)
- [Importar módulo Global Functions](###Importar%20módulo%20Global%20Functions)
- [Importar módulo do programa](###Importar%20módulo%20do%20programa)
- [Pasta padrão do Airflow](###Pasta%20padrão%20do%20Airflow)
- [Coletar dados de erro e encapsular:](###Coletar%20dados%20de%20erro%20e%20encapsular:)
- [Dict modelo para usar em passagem de dados para função](###Dict%20modelo%20para%20usar%20em%20passagem%20de%20dados%20para%20função)
- [**Nunca importar toda a biblioteca, somente os módulos necessário**](###**Nunca%20importar%20toda%20a%20biblioteca,%20somente%20os%20módulos%20necessário**)
- [**Todas as funções ou classes devem validar os parâmetros que está recebendo e verifica se contem dados**](###**Todas%20as%20funções%20ou%20classes%20devem%20validar%20os%20parâmetros%20que%20está%20recebendo%20e%20verifica%20se%20contem%20dados**)
- [Exemplo multiprocessamento](###Exemplo%20multiprocessamento)
- [Comando para gerar nome de arquivo aleatório](###Comando%20para%20gerar%20nome%20de%20arquivo%20aleatório)
- [Processo de envio de e-mail com informações](###Processo%20de%20envio%20de%20e-mail%20com%20informações)
- [Módulos do DAG](#Módulos%20do%20DAG)
- [Fim - Área de importação de módulos](#Fim%20-%20Área%20de%20importação%20de%20módulos)
- [Função `failedAlert`](###Função%20`failedAlert`)
- [Pendulum formatado e com timezone Brasil](###Pendulum%20formatado%20e%20com%20timezone%20Brasil)
- [Cria um objeto pendulum](#Cria%20um%20objeto%20pendulum)
- [Formata o objeto pendulum](#Formata%20o%20objeto%20pendulum)
- [Imprime o objeto pendulum formatado](#Imprime%20o%20objeto%20pendulum%20formatado)
- [String para data](###String%20para%20data)
- [Data para String](###Data%20para%20String)
- [F-String com Formatação](###F-String%20com%20Formatação)
- [Cria variável para exibir no logging](###Cria%20variável%20para%20exibir%20no%20logging)
- [loop para em caso de erro na transação do Banco de dados, fazer três tentativas](###loop%20para%20em%20caso%20de%20erro%20na%20transação%20do%20Banco%20de%20dados,%20fazer%20três%20tentativas)
- [Exemplo de `requests` para `API` e `Webhook`](###Exemplo%20de%20`requests`%20para%20`API`%20e%20`Webhook`)
- [Exemplo de código com namedtuple()](###Exemplo%20de%20código%20com%20namedtuple())
- [import módulo](#import%20módulo)
- [cria estrutura](#cria%20estrutura)
- [importa dados](#importa%20dados)
- [Modelo de namedtuple](###Modelo%20de%20namedtuple)
- [dataRecords pode ser uma lista com o resultado de uma query](#dataRecords%20pode%20ser%20uma%20lista%20com%20o%20resultado%20de%20uma%20query)
- [criando um namedtuple com nome de 'cpfControl'](#criando%20um%20namedtuple%20com%20nome%20de%20'cpfControl')
- [com os campos 'id, cpf, contrato'](#com%20os%20campos%20'id,%20cpf,%20contrato')
- [aqui enumeramos a lista e referenciamos os campos em vez de índice de posição](#aqui%20enumeramos%20a%20lista%20e%20referenciamos%20os%20campos%20em%20vez%20de%20índice%20de%20posição)
- [Modelo defaultdict](###Modelo%20defaultdict)
- [Modelo ChainMap](###Modelo%20ChainMap)
- [Modelo de conexão Postgresql](###Modelo%20de%20conexão%20Postgresql)
- [get_integer_length](###get_integer_length)
- [DLT](#DLT)
- [Pathlib](#Pathlib)
	- [Resumo](##Resumo)
	- [Métodos:](##Métodos:)
		- [Criação de Caminhos](###Criação%20de%20Caminhos)
		- [Métodos Comuns](###Métodos%20Comuns)
		- [Exemplo de Uso](###Exemplo%20de%20Uso)
	- [Criar um objeto Path](#Criar%20um%20objeto%20Path)
	- [Verificar se o arquivo existe](#Verificar%20se%20o%20arquivo%20existe)
	- [Ler o conteúdo do arquivo](#Ler%20o%20conteúdo%20do%20arquivo)
	- [Listar arquivos no diretório atual](#Listar%20arquivos%20no%20diretório%20atual)
- [Controle de Memória do Computador](#Controle%20de%20Memória%20do%20Computador)
	- [Dicas Adicionais](##Dicas%20Adicionais)
	- [**`memory-profiler`**](##**`memory-profiler`**)
- [Pandas](#Pandas)
	- [CSV Statistics](##CSV%20Statistics)
- [Mermaid](#Mermaid)
	- [Exemplo código gerar gráfico](##Exemplo%20código%20gerar%20gráfico)
- [Sqlalchemy](#Sqlalchemy)
	- [Modelo de uri](##Modelo%20de%20uri)
- [Matplotlib](#Matplotlib)
	- [Exemplo `matplotlib.pyplot.bar`](###Exemplo%20`matplotlib.pyplot.bar`)


---
### Parâmetros de desenvolvimento

- Imports seletivos
- Log compreensivo
- Log de parâmetros recebidos pela classe/método/função informando tipo e tamanho
- Documentar o código segundo no padrão `reStructuredText` do `Docstring`, incluindo `Doct test`.
- Envolver todo o código em try/except
- Sugestão de tipo, verificação de tipo e validação de dados dos parâmetros recebidos.
- Sempre que possével utilizar `dataclasses`.

### Docstring do programa

```python
# -*- coding: utf-8 -*-
"""
-------------------------------------------------------------------------
NOME..: nome_do_programa.py
LANG..: Python3
TITULO: <<< DESCRIÇÃO DA FUNCIONALIDADE >>>
DATA..: 00/00/0000
VERSÃO: 0.1.00
HOST..: diversos
LOCAL.: diversos
OBS...: colocar nas linhas abaixo informações importantes sobre o programa

DEPEND: (informar nas linhas abaixo os recursos necessários para utilização)

-------------------------------------------------------------------------
Copyright (c) 2022 - Vya.Digital
This script is licensed under GNU GPL version 2.0 or above
-------------------------------------------------------------------------
Modifications.....:
 Date          Rev    Author           Description
 00/00/0000    0      NOME DO AUTOR    Elaboração
-------------------------------------------------------------------------
PARÂMETROS (informar os parâmetros necessários no exemplo de utilização)
-
STATUS: (status emn que se encontra o código DEV/PROD)
DEV - pode adicionar dados adicionais para informar a fase
"""
```

### Modelo de documentação de Classe ou Função

```
"""
    Coleta os arquivos disponíveis na pasta remota.

    :param sendData: Um dicionário contendo os seguintes parâmetros:
    :param sendData['pathLocal']: path local
    :param sendData['pathLocalTmp']: path local temp - optional
    :param sendData['pathLocalAfter']: path local after process - optional
    :param sendData['pathRemote']: path remote
    :param sendData['sftpHost']: host sftp
    :param sendData['sftpUser']: user sftp
    :param sendData['sftpPassword']: password sftp
    :param sendData['sftpPort']: port sftp
    :param sendData['sftpKeyPath']: certify file path
    :param sendData['sftpUseKey']: usa keyPath
    :param sendData['sftpUsePass']: usa password
    :param maxRetries: número máximo de tentativas de conexão
    :param timeOut: tempo em segundos que aguarda o login

    :return listFiles - list: Uma lista com o nome dos arquivos disponíveis para download ou False em caso de erro.

    Modelo JSON:
    sendData = {
        "pathLocal": pathLocal,
        "pathLocalTmp": pathLocalTmp,
        "pathLocalAfter": pathLocalAfter,
        "pathRemote": pathRemote,
        "sftpHost": sftpHost,
        "sftpUser": sftpUser,
        "sftpPassword": sftpPassword,
        "sftpPort": sftpPort,
        "sftpKeyPath": sftpKeyPath,
        "sftpUseKey": sftpUseKey,
        "sftpUsePass": sftpUsePass
    }

    :Example:

    >>> sendData = {
    ...     "pathLocal": "/local/path",
    ...     "pathRemote": "/remote/path",
    ...     "sftpHost": "example.com",
    ...     "sftpUser": "username",
    ...     "sftpPassword": "password",
    ...     "sftpPort": 22,
    ...     "sftpKeyPath": "/path/to/key",
    ...     "sftpUseKey": True,
    ...     "sftpUsePass": False
    ... }
    >>> sftpListFiles(sendData, 2, 10)
    ['file1.txt', 'file2.txt']

    """
```

### Informação do inicio e fim do programa
```python
logging.info("=== Programa: %s ===" % (path.basename(sys._getframe().f_code.co_filename)))
logging.info("=== Termino programa: %s ===" % (path.basename(sys._getframe().f_code.co_filename)))
```
### Informação do inicio e fim da função/classe
```python
logging.info("=== Função: %s ===" % (sys._getframe().f_code.co_name))
logging.info("=== Termino Função: %s ===" % (sys._getframe().f_code.co_name))
```
### Mostrar dados recebidos
```python
logging.info("=== Parâmetros recebidos ===")
logging.info(f"==> VAR: serviceId TYPE: {type(serviceId)}, CONTENT: {serviceId}")
```
### Coletar conteúdo da variável do `Airflow`  
```python
dagName = kwargs['dag_run'].dag_id
dataJson = Variable.get(dagName.lower())
```
### Coletar dados da conexão do `Airflow`
```python
connObject = BaseHook.get_connection("airflow_db")
airflow_db_config = {
    "host": connObject.host,
    "user": connObject.login,
    "password": connObject.password,
    "port": connObject.port,
    "database": connObject.schema,
}
```
### Tratamento de Ambiente DEV e PROD
```python
dagName = None
taskName = None

envType = Variable.get('hyperauto-env').lower()

if envType == "prod":
    dagName = kwargs['dag_run'].dag_id
    taskName = kwargs['task'].dag_id
    dbIdName = "hyper-auto-db"
elif envType == "dev":
    dagName = dagName if dagName else path.basename(sys._getframe().f_code.co_name)
    taskName = taskName if taskName else sys._getframe().f_code.co_name
    dbIdName = "hyper-auto-db"
```
### Importar módulo Global Functions
```python
try:
    myLog.info("=== Importando módulos do programa ===")
    sys.path.append(path.join(getenv('AIRFLOW_HOME'), "utils/vya_global"))
    from error_handler import errorHandler, errorCollected
except ModuleNotFoundError as errorMsg:
    myLog.error(f"Erro ao importar módulos")
    myLog.error("Exception occurred", exc_info=True)
    myLog.error(errorMsg)
    raise ModuleNotFoundError
```
### Importar módulo do programa
```python
fileName = inspect.getframeinfo(inspect.currentframe()).filename
filePath = path.dirname(path.abspath(fileName))
sys.path.append(path.join(filePath, "modules"))
from process_control_export import start
```
### Pasta padrão do Airflow
```python
from airflow.models import Variable
systemDownloadPath = Variable.get("system-download-path")
pathLocal = "cliente/serasa/" # essa informação vem do JSON da variável de controle do programa
pathLocalAfter = "executado/" # essa informação vem do JSON da variável de controle do programa
```
### Coletar dados de erro e encapsular:
#### Exemplo `airflow`:
```python
errorData = dict()
try:
    pass
except BaseException as errorMsg:
    myLog.error(f"mensagem de erro")
    myLog.error("Exception occurred", exc_info=True)
    myLog.error(errorMsg)
    dagName = path.basename(sys._getframe().f_code.co_name)
    taskName = sys._getframe().f_code.co_name
    local_tz = pendulum.timezone("America/Sao_Paulo")
    execDate = pendulum.now(local_tz).format('YYYY-MM-DD HH:mm:ss')
    # se tiver dados com id da tabela process_queue criar uma lista
    errorData = {
        "dag_name": dagName,
        "code_name": taskName,
        "db_id_name": "hyper-auto-db",
        "id_process_queue": [
            0
            ],
        "error_data": {
            "error_title": "Failed Alert",
            "error_date_time": execDate,
            "error_msg": errorMsg,
            "error_traceback": traceback.format_exc(),
            "error_detail_1": f"URL LOG: {urlLog}"
            }
        }
    errorCollected(errorData, kwargs)
```

#### Exemplo `GERAL`:
```python
import pendulum
import logging
errorData = dict()
try:
    pass
except BaseException as errorMsg:
    logging.error(f"mensagem de erro")
    logging.error("Exception occurred", exc_info=True)
    logging.error(errorMsg)
    prog_name = path.basename(sys._getframe().f_code.co_name)
    code_name = sys._getframe().f_code.co_name
    local_tz = pendulum.timezone("America/Sao_Paulo")
    execDate = pendulum.now(local_tz).format('YYYY-MM-DD HH:mm:ss')
    # utilizar id_process para informar dados do DB
    errorData = {
        "prog_name": dagName,
        "code_name": taskName,
        "db_id_name": "hyper-auto-db",
        "id_process": [
            0
            ],
        "error_data": {
            "error_title": "Failed Alert",
            "error_date_time": execDate,
            "error_msg": errorMsg,
            "error_traceback": traceback.format_exc(),
            "error_detail_1": f"URL LOG: {urlLog}"
            }
        }
    errorCollected(errorData, kwargs)
```

### Função para configurar logging
```python
import logging

def config_logging(file_name: str, file_path: str) -> bool:
    """
    Configura o logging para a aplicação.

    :param file_name: Nome do arquivo de log.
    :type file_name: str
    :param file_path: Caminho do arquivo de log.
    :type file_path: str
    :return: True se a configuração foi bem-sucedida.
    :rtype: bool
    """
    logger = logging.getLogger()
    if logger.hasHandlers():
        logging.info("Configuração de logging já existente, mantendo a configuração atual.")
        return True
    
    log_file = Path(file_path).joinpath(file_name)
    
    logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(levelname)s - %(threadName)s - %(funcName)s:%(lineno)d - %(name)s - %(message)s",
            handlers=[
                    logging.FileHandler(log_file),
                    logging.StreamHandler()
            ]
    )
    logging.info(f"=== Função: {__name__} ===")
    return True
```

### Dict modelo para usar em passagem de dados para função
```python
sendData = {
    "fileList": fileList,
    "clientConnection": clientConnection,
    "bucketName": bucketName,
    "pathLocal": pathLocal,
    "pathLocalAfter": pathLocalAfter,
    "pathDest": pathDest
    }
```

### **Nunca importar toda a biblioteca, somente os módulos necessário**
```python
from os import path
```

### **Todas as funções ou classes devem validar os parâmetros que está recebendo e verifica se contem dados**
```python
def load_config(progname_config_ini_path: str, progname: str) -> dict:
	if not progname_config_ini_path or not progname:
	logger.error("Parâmetros inválidos fornecidos para load_config")
	sys.exit(1)
```

### Exemplo multiprocessamento
```python
import multiprocessing as mp

def my_func(x):
    return x * x

if __name__ == "__main__":
    # Create a pool of 4 threads
    pool = mp.Pool(4)

    # Iterate over the range(10) and apply my_func in parallel
    results = pool.map(my_func, range(10))

    # Print the results
    print(results)
```

### Comando para gerar nome de arquivo aleatório
```python
import uuid
nId = uuid.uuid4()
fileNew = path.basename(file).replace(".csv", f"-{nId}.csv")
```

### Processo de envio de e-mail com informações
```python
import json
import pendulum
import sys
from os import path, getenv, rename

# Módulos do DAG
from airflow.hooks.base import BaseHook
from airflow.models import Variable
from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.email import send_email
# Fim - Área de importação de módulos

myLog = LoggingMixin().log
myLog.info("=== Programa: %s" % (sys._getframe().f_code.co_filename))


myLog.info(f"Global Functions Path {path.join(getenv('AIRFLOW_HOME'), 'utils/vya_global')}")
sys.path.append(path.join(getenv('AIRFLOW_HOME'), "utils/vya_global"))
from table_html import gerarCabecalhoTabelaHtml, gerarDadosTabela
from email_template import emailSpecial

vyaEmailRecipients = 
urlPage = Variable.get('urlPage')
if envType == "prod":
    dagName = kwargs["dag_run"].dag_id
    clientsData = Variable.get(dagName.lower())
    vyaEmailRecipients = Variable.get("vya_digital_email")
    taskName = kwargs['ti'].task_id
else:
    dagName = "teste_sftp_upload"
    clientsData = Variable.get('app-serasa-retorno-download')
    vyaEmailRecipients = Variable.get("vya_digital_ti_email")
    taskName = 'sftp'

listToProcess = [
    {"Nome do Arquivo": "R.008.L8302.PEFIN.RET.D230203.H185629.TXT", "Qtde Linhas": "52"},
    {"Nome do Arquivo": "R.008.L8302.PEFIN.RET.D230203.H190622.TXT", "Qtde Linhas": "32"},
    {"Nome do Arquivo": "R.008.L8302.PEFIN.RET.D230203.H191225.TXT", "Qtde Linhas": "72"},
    {"Nome do Arquivo": "R.008.L8302.PEFIN.RET.D230203.H215347.TXT", "Qtde Linhas": "1686"},
    {"Nome do Arquivo": "R.008.L8302.PEFIN.RET.D230201.H223844.TXT", "Qtde Linhas": "42"},
    {"Nome do Arquivo": "R.008.L8302.PEFIN.RET.D230213.H211615.TXT", "Qtde Linhas": "10"},
    {"Nome do Arquivo": "R.008.L8302.PEFIN.RET.D230214.H190252.TXT", "Qtde Linhas": "52"},
    {"Nome do Arquivo": "R.008.L8302.PEFIN.RET.D230306.H175553.TXT", "Qtde Linhas": "16"},
    {"Nome do Arquivo": "R.008.L8302.PEFIN.RET.D230327.H202331.TXT", "Qtde Linhas": "6"},
    {"Nome do Arquivo": "R.008.L8302.PEFIN.RET.D230503.H133230.TXT", "Qtde Linhas": "334"},
    {"Nome do Arquivo": "R.008.L8302.PEFIN.RET.D230620.H135554.TXT", "Qtde Linhas": "806"},
    {"Nome do Arquivo": "R.008.L8302.PEFIN.RET.D230621.H185333.TXT", "Qtde Linhas": "8236"},
    {"Nome do Arquivo": "R.008.L8302.PEFIN.RET.D230621.H211544.TXT", "Qtde Linhas": "2154"}
    ]

dataHeader = ["Nome do Arquivo", "Qtde Linhas"]
bodyHtml = gerarCabecalhoTabelaHtml(dataHeader)
bodyHtml += "<br>"
bodyHtml = ""
for idx, item in enumerate(listToProcess):
    myLog.info(f"idx: {idx}")
    myLog.info(f"item: {item}")
    bodyHtml += gerarDadosTabela(item, idx)
myLog.info(f"Data: \n{bodyHtml}")
emailText = "Teste de e-mail com lista de arquivos"
ItemText = "=== Nome de Arquivo ==="
tituloText = f'Vya.Digital - Hyperauto - Teste lista de arquivos'
message = emailSpecial.replace("REPLACEDAG", dagName)
message = message.replace("REPLACETEXTO", emailText)
message = message.replace("REPLACEITEMTITLE", ItemText)
message = message.replace("REPLACESERVER", urlPage)
message = message.replace("REPLACEHERE", bodyHtml)
send_email(to=vyaEmailRecipients, subject=tituloText, html_content=message, conn_id=smtpName)
```

### Função `failedAlert`
```python
myLog.info("=== Importando módulos do programa ===")
sys.path.append(path.join(getenv('AIRFLOW_HOME'), "utils/vya_global"))
from error_handler import errorCollected

def failedAlert(context):
    """
    Callback task that can be used in DAG to alert of failure task completion
    Args:
    context (dict): Context variable passed in from Airflow
    Returns:
    None: Calls the errorHandler to send e-mail to Support System
    NOTE:
    Change code to use new errorCollected format and function to replace url
    """
    myLog.error("=== FAILED ALERT  ===")
    urlPage = Variable.get('urlPage')

    def replace_urls(match):
        url = match.group(0)
        return urlPage  # Certifique-se de que urlPage seja definido em algum lugar do seu código

    taskName = context.get("task_instance").task_id
    dagname = context.get("task_instance").dag_id
    exec_date = context.get("execution_date")
    log_url = context.get("task_instance")
    url_pattern = r'https?://\S+|www\.\S+'
    urlLog = re.sub(url_pattern, replace_urls, log_url)
    errorData = {
    "dag_name": dagname,
    "code_name": taskName,
    "db_id_name": "hyper-auto-db",
    "id_process_queue": [ 0 ],
    "error_data": {
        "error_title": "Failed Alert",
        "error_date_time": exec_date,
        "error_msg": "DAG error automatic information",
        "error_traceback": "N/I",
        "error_detail_1": f"URL LOG: {urlLog}"
        }
    }
    errorCollected(errorData, errorMsg=None, **context)

    # Encerre a DAG com status "success" após o processamento
    context['task_instance'].success()

myLog.info("Criando a variável com os parâmetros da DAG.")
args = {
        "owner": ownerName,
        "retries": nRetry,
        "retry_delay": dRetry,
        "on_failure_callback": failedAlert,
        "on_success_callback": None,
        "provide_context": True
        }
```

### Pendulum formatado e com timezone Brasil
```python
import pendulum
local_tz = pendulum.timezone("America/Sao_Paulo")

# Cria um objeto pendulum
pendulum_object = pendulum.now(local_tz)

# Formata o objeto pendulum
formatted_pendulum_object = pendulum_object.instance('YYYY-MM-DD HH:mm:ss')

# Imprime o objeto pendulum formatado
print(formatted_pendulum_object)
```

### String para data
```python
datetime_str = '2023-09-22 13:55:26'
datetime_object = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
```

### Data para String
```python
datetime_object = datetime.now()
datetime_str = datetime_object.strftime('%Y-%m-%d %H:%M:%S')****
```

### F-String com Formatação
```python
>>> balance = 5425.9292
>>> f"Balance: ${balance:.2f}"
'Balance: $5425.93'

>>> heading = " Centered string "
>>> f"{heading:=^30}"
'====== Centered string ======='

>>> heading = " Centered string"
>>> f"{heading:=>30}"
'============== Centered string'


>>> integer = -1234567
>>> f"Comma as thousand separators: {integer:,}"
'Comma as thousand separators: -1,234,567'

>>> sep = "_"
>>> f"User's thousand separators: {integer:{sep}}"
'User's thousand separators: -1_234_567'

>>> floating_point = 1234567.9876
>>> f"Comma as thousand separators and two decimals: {floating_point:,.2f}"
'Comma as thousand separators and two decimals: 1,234,567.99'

>>> date = (9, 6, 2023)
>>> f"Date: {date[0]:02}-{date[1]:02}-{date[2]}"
'Date: 09-06-2023'

>>> from datetime import datetime
>>> date = datetime(2023, 9, 26)
>>> f"Date: {date:%m/%d/%Y}"
'Date: 09/26/2023'
```

**Tabela com os tipos de dados utilizados na `f-string`**

| Tipo | Significado                                                                                                                            |
| ---- | -------------------------------------------------------------------------------------------------------------------------------------- |
| s    | String format. This is the default type for strings                                                                                    |
| d    | Decimal Integer. This uses a comma as the number separator character.                                                                  |
| n    | Number. This is the same as d except that it uses the current locale setting to insert the appropriate number separator characters.    |
| e    | Exponent notation. Prints the number in scientific notation using the letter ‘e’ to indicate the exponent. The default precision is 6. |
| f    | Fixed-point notation. Displays the number as a fixed-point number. The default precision is 6.                                         |
| %    | Percentage. Multiplies the number by 100 and displays in fixed ('f') format, followed by a percent sign.                               |

### Cria variável para exibir no logging
```python
key_value_pairs = '\n'.join([f"{key}: {value}" for key, value in sendData.items()])
```

### loop para em caso de erro na transação do Banco de dados, fazer três tentativas 
```python
from time import sleep
countTimes = 0
statusTransaction = None
while True:
    countTimes += 1
    try:
      result = executeQueryTrans(dbConnId, sqlCmd)
  
      if not result and countTimes < 3:
          myLog.warning("Problema na transação com o Banco de dados")
          myLog.warning(f"===> Tentativa {countTimes} <===")
          sleep(1)
      elif not result and countTimes == 3:
        myLog.error("Problema na transação com o Banco de dados")
        statusTransaction = False
      else:
        statusTransaction = True
        break
    except BaseException as errorMsg:
      myLog.warning("Erro inesperado")
      myLog.warning(errorMsg)
    if statusTransaction is None or statusTransaction is True:
      myLog.debug("Transação do banco de dados com sucesso")
    else:
      myLog.error("Problema na transação do banco de dados, interrompendo o programa.")
      return False
```

### Exemplo de `requests` para `API` e `Webhook`
```python
response = request("POST", url=webHookUrl, headers=headerwebhook, json=sendData, verify=False, timeout=5)
```

### Exemplo de código com namedtuple()
`Criar uma função global para criar uma namedtuple`
```python
# import módulo
from collections import namedtuple
#cria estrutura
EmployeeRecord = namedtuple('EmployeeRecord', 'name, age, title, department, paygrade')
# importa dados
import sqlite3
conn = sqlite3.connect('/companydata')
cursor = conn.cursor()
cursor.execute('SELECT name, age, title, department, paygrade FROM employees')
for emp in map(EmployeeRecord._make, cursor.fetchall()):
    print(emp.name, emp.title)
```

### Modelo de namedtuple
```python
from collections import namedtuple
dataRecords = [
    (1, 13399722870, 6927648638),
    (2, 23484879128, 8862267070),
    (3, 36290590217, 7584285548),
    (4, 36290590217, 6079297397),
    (5, 36290590217, 4397410537),
    (6, 36290590217, 7711562958)]
# dataRecords pode ser uma lista com o resultado de uma query
print(f"dataRecords type {type(dataRecords)}, len {len(dataRecords)}")
"""
Tuplas nomeadas atribuem significado a cada posição em uma tupla e permitem
um código mais legível e autodocumentado. Eles podem ser usados sempre que tuplas
regulares são usadas e adicionam a capacidade de acessar campos por nome em
vez de índice de posição.
"""
# criando um namedtuple com nome de 'cpfControl'
# com os campos 'id, cpf, contrato'
cpfLidos = namedtuple('cpfControl', 'id, cpf, contrato')
# aqui enumeramos a lista e referenciamos os campos em vez de índice de posição
for cpf in map(cpfLidos._make, dataRecords):
    print(cpf.cpf, cpf.contrato)
```

### Modelo defaultdict
```python
#https://www.geeksforgeeks.org/defaultdict-in-python/
from collections import defaultdict
s = [('yellow', 1), ('blue', 2), ('yellow', 3), ('blue', 4), ('red', 1)]
d = defaultdict(list)
for k, v in s:
    d[k].append(v)
sorted(d.items())
[('blue', [2, 4]), ('red', [1]), ('yellow', [1, 3])]
```

### Modelo ChainMap
```python
from collections import ChainMap
baseline = {'music': 'bach', 'art': 'rembrandt'}
adjustments = {'art': 'van gogh', 'opera': 'carmen'}
list(ChainMap(adjustments, baseline))
['music', 'art', 'opera']
class DeepChainMap(ChainMap):
  'Variant of ChainMap that allows direct updates to inner scopes'

  def __setitem__(self, key, value):
    for mapping in self.maps:
      if key in mapping:
        mapping[key] = value
        return
    self.maps[0][key] = value

  def __delitem__(self, key):
    for mapping in self.maps:
      if key in mapping:
        del mapping[key]
        return
    raise KeyError(key)
d = DeepChainMap({'zebra': 'black'}, {'elephant': 'blue'}, {'lion': 'yellow'})
d['lion'] = 'orange'         # update an existing key two levels down
d['snake'] = 'red'           # new keys get added to the topmost dict
del d['elephant']            # remove an existing key one level down
d                            # display result
DeepChainMap({'zebra': 'black', 'snake': 'red'}, {}, {'lion': 'orange'})
```

### Modelo de conexão Postgresql
```python
import psycopg2
conn = psycopg2.connect(dbname="db_name",
                        user="user_name",
                        host="127.0.0.1",
                        password="******",
                        port="5432")
cursor = conn.cursor()
cursor.execute('SELECT * FROM information_schema.tables')
rows = cursor.fetchall()
for table in rows:
    print(table)
conn.close()
```

### get_integer_length
```python
import math
def get_integer_length(integer):
    if integer > 0:
        return int(math.log10(integer)) + 1
    elif integer == 0:
        return 1
    else:
        return int(math.log10(-integer)) + 2
```
---
# DLT

Biblioteca para etl simplificado
[[Installation  dlt Docs]]


---
# Pathlib

No Python 3, tanto `os.path` quanto `pathlib` são usados para manipular caminhos de arquivos e diretórios, mas eles têm abordagens diferentes.`os.path` 
- **Estilo Funcional** : Utiliza funções para realizar operações, como `os.path.join()`, `os.path.exists()`, etc.
 
- **Compatibilidade** : É parte da biblioteca padrão desde as versões anteriores do Python, então é muito amplamente utilizado.
 
- **Cadeias de Caracteres** : Os caminhos são tratados como strings, o que pode levar a erros de manipulação de strings se não forem cuidadosos.
`pathlib` 
- **Estilo Orientado a Objetos** : Introduzido no Python 3.4, permite trabalhar com caminhos de forma mais intuitiva usando classes, como `Path`.
 
- **Métodos Integrados** : Oferece métodos que tornam o código mais legível e fácil de usar, como `path.exists()` e `path.joinpath()`.
 
- **Facilidade de Uso** : Permite operações como divisão de caminhos usando o operador `/`, o que pode deixar o código mais claro.
 
- **Suporte a Vários Sistemas Operacionais** : Lida melhor com as diferenças entre sistemas operacionais, como separadores de caminho.

## Resumo 
 
- **Escolha** : Se você está começando um novo projeto ou deseja um código mais legível, `pathlib` é geralmente a melhor escolha. Se você está trabalhando em um código legado ou precisa de compatibilidade com versões muito antigas do Python, `os.path` pode ser mais apropriado.

## Métodos: 

Claro! Aqui estão alguns dos principais métodos e atributos da classe `Path` do módulo `pathlib`:
### Criação de Caminhos 
 
- `Path('caminho')`: Cria um objeto `Path` a partir de uma string de caminho.
 
- `Path.home()`: Retorna o diretório home do usuário.

### Métodos Comuns 
 
- **Verificação de Propriedades**  
  - `path.exists()`: Verifica se o caminho existe.
 
  - `path.is_file()`: Verifica se o caminho é um arquivo.
 
  - `path.is_dir()`: Verifica se o caminho é um diretório.
 
  - `path.is_symlink()`: Verifica se o caminho é um link simbólico.
 
- **Manipulação de Caminhos**  
  - `path.joinpath(*paths)`: Junta um ou mais caminhos ao caminho atual.
 
  - `path.with_name(name)`: Retorna um novo caminho com um novo nome de arquivo.
 
  - `path.with_suffix(suffix)`: Retorna um novo caminho com uma nova extensão.
 
  - `path.parent`: Retorna o diretório pai do caminho.
 
  - `path.name`: Retorna o nome do arquivo ou diretório.
 
- **Operações de Entrada/Saída**  
  - `path.read_text()`: Lê o conteúdo de um arquivo de texto.
 
  - `path.write_text(data)`: Escreve dados em um arquivo de texto.
 
  - `path.read_bytes()`: Lê o conteúdo de um arquivo em bytes.
 
  - `path.write_bytes(data)`: Escreve bytes em um arquivo.
 
  - `path.mkdir()`: Cria um diretório.
 
  - `path.rmdir()`: Remove um diretório (deve estar vazio).
 
  - `path.unlink()`: Remove um arquivo ou link simbólico.
 
- **Listagem de Conteúdo**  
  - `path.iterdir()`: Retorna um iterador sobre os arquivos e diretórios no caminho.
 
  - `path.glob(pattern)`: Retorna todos os caminhos que correspondem a um padrão (wildcard).
 
  - `path.rglob(pattern)`: Busca recursivamente por todos os caminhos que correspondem a um padrão.

### Exemplo de Uso 

Aqui está um exemplo simples que demonstra algumas dessas funcionalidades:


```python
from pathlib import Path

# Criar um objeto Path
p = Path('exemplo.txt')

# Verificar se o arquivo existe
if not p.exists():
    # Criar e escrever no arquivo
    p.write_text('Olá, mundo!')

# Ler o conteúdo do arquivo
conteudo = p.read_text()
print(conteudo)

# Listar arquivos no diretório atual
for arquivo in Path('.').iterdir():
    print(arquivo)
```
Esses são apenas alguns dos métodos e funcionalidades da `pathlib`. A biblioteca é poderosa e oferece muitas outras opções para manipulação de arquivos e diretórios!

---
# Controle de Memória do Computador
## Dicas Adicionais

- **Profiling Regular**: Use ferramentas de profiling regularmente durante o desenvolvimento para identificar vazamentos de memória.
- **Limpeza Manual**: Em alguns casos, pode ser útil definir variáveis como `None` para liberar memória mais rapidamente.

##  **`memory-profiler`**

- **Descrição**: Permite medir o uso de memória em funções específicas.
- **Uso**: Você pode decorá-las para monitorar o consumo de memória linha a linha.
- **Instalação**: `pip install memory-profiler`
- **Exemplo**:
```python
from memory_profiler import profile

@profile
def my_function():
    a = [i for i in range(100000)]
    return a

my_function()

```

---
# Pandas

## CSV Statistics
```python
#https://datatofish.com/use-pandas-to-calculate-stats-from-an-imported-csv-file/
import pandas as pd

df = pd.read_csv(r'C:\Users\Ron\Desktop\stats.csv')

# block 1 - simple stats
mean1 = df['salary'].mean()
sum1 = df['salary'].sum()
max1 = df['salary'].max()
min1 = df['salary'].min()
count1 = df['salary'].count()
median1 = df['salary'].median()
std1 = df['salary'].std()
var1 = df['salary'].var()

# block 2 - group by
groupby_sum1 = df.groupby(['country']).sum()
groupby_count1 = df.groupby(['country']).count()

# print block 1
print('mean salary: ' + str(mean1))
print('sum of salaries: ' + str(sum1))
print('max salary: ' + str(max1))
print('min salary: ' + str(min1))
print('count of salaries: ' + str(count1))
print('median salary: ' + str(median1))
print('std of salaries: ' + str(std1))
print('var of salaries: ' + str(var1))

# print block 2
print('sum of values, grouped by the country: ' + str(groupby_sum1))
print('count of values, grouped by the country: ' + str(groupby_count1))
```

---
# Mermaid

## Exemplo código gerar gráfico
```python
import base64
from IPython.display import Image, display
import matplotlib.pyplot as plt

def mm(graph):
    graphbytes = graph.encode("utf8")
    base64_bytes = base64.b64encode(graphbytes)
    base64_string = base64_bytes.decode("ascii")
    display(Image(url="https://mermaid.ink/img/" + base64_string))

mm("""
graph LR;
    A--> B & C & D;
    B--> A & E;
    C--> A & E;
    D--> A & E;
    E--> B & C & D;
""")
```

---
# Sqlalchemy

## Modelo de uri
```python
"mysql://{username}:{password}@{server}/testdb".format(username, password, server)
```

___
# Matplotlib

### Exemplo `matplotlib.pyplot.bar`
```python
pyplot.bar(x, height, width=0.8, bottom=None, *, align='center', data=None, **kwargs)
"""
:param x..........: float or array-like -The x coordinates of the bars. See also align for the alignment of the bars to the coordinates.
:param heightfloat: float or array-like - The height(s) of the bars.
:param width......: float or array-like, default: 0.8 - The width(s) of the bars.
:param bottom.....: float or array-like, default: 0 - The y coordinate(s) of the bottom side(s) of the bars.
:param align......: {'center', 'edge'}, default: 'center' - Alignment of the bars to the x coordinates:
"""
```

---
# `collections` - Container datatype
[collections doc](https://docs.python.org/3/library/collections.html)

This module implements specialized container datatypes providing alternatives to Python’s general purpose built-in containers, [`dict`](https://docs.python.org/3/library/stdtypes.html#dict "dict"), [`list`](https://docs.python.org/3/library/stdtypes.html#list "list"), [`set`](https://docs.python.org/3/library/stdtypes.html#set "set"), and [`tuple`](https://docs.python.org/3/library/stdtypes.html#tuple "tuple").

|                                                                                                                       |                                                                                                      |
| --------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| [`namedtuple()`](https://docs.python.org/3/library/collections.html#collections.namedtuple "collections.namedtuple")  | factory function for creating tuple subclasses with named fields                                     |
| [`deque`](https://docs.python.org/3/library/collections.html#collections.deque "collections.deque")                   | list-like container with fast appends and pops on either end                                         |
| [`ChainMap`](https://docs.python.org/3/library/collections.html#collections.ChainMap "collections.ChainMap")          | dict-like class for creating a single view of multiple mappings                                      |
| [`Counter`](https://docs.python.org/3/library/collections.html#collections.Counter "collections.Counter")             | dict subclass for counting [hashable](https://docs.python.org/3/glossary.html#term-hashable) objects |
| [`OrderedDict`](https://docs.python.org/3/library/collections.html#collections.OrderedDict "collections.OrderedDict") | dict subclass that remembers the order entries were added                                            |
| [`defaultdict`](https://docs.python.org/3/library/collections.html#collections.defaultdict "collections.defaultdict") | dict subclass that calls a factory function to supply missing values                                 |
| [`UserDict`](https://docs.python.org/3/library/collections.html#collections.UserDict "collections.UserDict")          | wrapper around dictionary objects for easier dict subclassing                                        |
| [`UserList`](https://docs.python.org/3/library/collections.html#collections.UserList "collections.UserList")          | wrapper around list objects for easier list subclassing                                              |
| [`UserString`](https://docs.python.org/3/library/collections.html#collections.UserString "collections.UserString")    | wrapper around string objects for easier string subclassing                                          |

---
# Dataclasses
[Python Dataclasses](https://docs.python.org/3/library/dataclasses.html)

---
# Pycharm

## Live Templates
Atalhos para os templates

- `authorname` - insere o meu nome
- `BVCtrl` - cabeçalho completo
- `compd` - dict comprehension
- `compdi` - dict comprehension with if
- `compg` - generator comprehension
- `compgi` - generator comprehension with if
- `compl` - list comprehension
- `compli` - list comprehension with if
- `comps` - set comprehension
- `compsi` - set comprehension with if
- `date` - data atual
- `filePath` - pasta do arquivo
- `iter` - iterate command
- `itere` - iterate command with enumerate
- `main` - if main
- `mylogdeb` - logging debug
- `mylogerr` - logging error
- `myloginfo` - logging info
- `mylogwarn` - logging warning
- `nomearquivo` - nome do arquivo
- `prop` - property getter
- `props` - property getter and setter
- `propsd` - property getter, setter and deleter
- `SVCtrl` - cabeçalho pequeno
- `super` - super call
---
# UV

## Install
```
sudo apt install rustc cargo
cargo install --git https://github.com/astral-sh/uv uv

# update
apt install --only-upgrade rustc cargo
```

## Create VENV
```

```

---
# Lista de Comandos
```
# instalar o python mysqlclient no Ubuntu 20.04
# pre req
apt install -y python3-dev python3-pip default-libmysqlclient-dev build-essential

# instalar pip no Debian/Ubuntu
apt install python3-pip

## procurar pacotes instalados
pip3 list | egrep -i 'jni|cython'
## final

## gerador de dados para mysql
pip install sqlfaker
# https://pypi.org/project/sqlfaker/

pip install fake2db
# https://github.com/emirozer/fake2db
## final

# gerador de senha emcripitada sha512
python3 -c 'import crypt; print(crypt.crypt("mipass", crypt.METHOD_SHA512))'

# exportar modulos instalados
pip freeze > requirements.txt

# instalar modulos previamente
pip install -r requirements.txt --upgrade --no-cache

# atualizar todos os modulos instalados
pip list --outdated | cut -d ' ' -f1 | xargs -n1 pip install -U

# criar venv
pip3 install virtualenv --upgrade
virtualenv --python=/usr/bin/python3 nome_projeto 
ln -s nome_projeto/bin/activate activate

# ativar venv
source activate

# desativar venv
deactivate

## colocar o shebang no programa python para executar sem ativar o venv. Exemplo..
#!/usr/local/bin/enterprise/vya_sheet_report/bin/python3

# Otimização de import
import pyximport; pyximport.install()

# Estatistica de execução 
python -m cProfile test.py

```