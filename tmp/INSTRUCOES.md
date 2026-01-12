# Instruções para aplicar a correção no servidor

## 1. Copiar arquivos para o servidor
```bash
scp tmp/docker_entry.sh yves_marinho@192.168.15.197:~/docker-compose/
scp tmp/docker-compose.yaml yves_marinho@192.168.15.197:~/docker-compose/
```

## 2. No servidor, tornar o script executável
```bash
ssh yves_marinho@192.168.15.197
cd ~/docker-compose/
chmod +x docker_entry.sh
```

## 3. Recriar o container
```bash
docker-compose down
docker-compose up -d
```

## 4. Verificar logs
```bash
docker logs postgresql
```

Você deve ver:
```
=== Custom PostgreSQL Entrypoint ===
Iniciando PostgreSQL...
Iniciando processo de reset de senha em background...
PostgreSQL pronto após X tentativas!
Resetando senha do usuário postgres...
✅ Senha do postgres resetada com sucesso!
```

## 5. Testar conexão
```bash
PGPASSWORD='W123Mudar' psql -h 192.168.15.197 -U postgres -d postgres -c 'SELECT version();'
```

## Alternativa: Reset manual sem recriar container

Se preferir não mexer no entrypoint agora:

```bash
ssh yves_marinho@192.168.15.197
docker exec postgresql psql -U postgres -c "ALTER USER postgres WITH PASSWORD 'W123Mudar';"
```

Depois execute o script Python normalmente.
