# Preparar o Nitro 5 como servidor do HolyCut

Guia passo a passo para o notebook Acer Nitro 5 com RTX 3070 Ti. No fim, o HolyCut roda no notebook com a GPU e fica acessível pela internet.

Tempo estimado: 1 a 2 horas, a maior parte esperando downloads.

## 1. Espaço em disco

O Docker guarda imagens, banco e modelos de IA. Os modelos sozinhos ocupam dezenas de GB.

- Deixe pelo menos **60 GB livres** no disco onde o Docker vai guardar os dados.
- Se o C: for pequeno, mude o local em **Docker Desktop → Settings → Resources → Advanced → Disk image location** para outro disco.
- Um disco cheio derruba o Mongo e o Docker no meio do trabalho. Vale conferir o espaço de vez em quando.

## 2. Driver da NVIDIA

1. Instale o driver mais recente da RTX 3070 Ti pelo GeForce Experience ou pelo site da NVIDIA.
2. Confira no PowerShell:

```
nvidia-smi
```

Deve aparecer a RTX 3070 Ti com 8 GB.

## 3. WSL2 e Docker Desktop

1. Abra o PowerShell como administrador e rode o comando abaixo. Reinicie o notebook no fim.

```
wsl --install
```

2. Instale o Docker Desktop e escolha o backend WSL2.
3. Em **Settings → General**, marque **Start Docker Desktop when you sign in**.
4. Teste se a GPU chega aos containers:

```
docker run --rm --gpus=all nvcr.io/nvidia/k8s/cuda-sample:nbody nbody -gpu -benchmark
```

O resultado deve citar a RTX 3070 Ti.

## 4. Baixar e configurar o HolyCut

```
git clone <endereço do repositório> HolyCut
cd HolyCut
copy .env.example .env
```

Edite o `.env`:

- `JWT_SEGREDO`: gere um valor com o comando abaixo e cole.
- `MODO_IA=real`
- `PASTA_BACKUP_HOST`: uma pasta fora do notebook, como um HD externo ou o Google Drive.

```
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## 5. Subir tudo

```
docker compose --profile gpu up --build -d
docker compose ps
```

Todos os serviços devem aparecer como `running`. O Mongo aparece como `healthy`.

Abra http://localhost:3000, crie uma conta e clique em **Testar GPU**. O resultado mostra a placa e a versão do Ollama. Se aparecer "nvidia-smi não encontrado", volte ao passo 3.

## 6. Deixar o notebook confiável

Rode no PowerShell como administrador:

```
powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0
powercfg /setacvalueindex SCHEME_CURRENT SUB_BUTTONS LIDACTION 0
powercfg /setactive SCHEME_CURRENT
```

Assim o notebook nunca suspende na tomada e não faz nada ao fechar a tampa.

- **Bateria:** ative o limite de carga em 80% no NitroSense ou no Acer Care Center, se o modelo tiver.
- **Temperatura:** use uma base com cooler.
- **Windows Update:** em **Configurações → Windows Update → Horário ativo**, cubra os horários de culto e de edição.
- **Queda de energia:** os serviços usam `restart: unless-stopped` e voltam sozinhos quando o Docker inicia.

## 7. Acessar de fora de casa

### Para testar, sem domínio

```
docker compose --profile gpu --profile tunel-rapido up -d
docker compose logs tunel-rapido
```

Procure no log um endereço terminado em `trycloudflare.com`. Ele muda a cada reinício.

### Para as igrejas piloto, com domínio próprio

1. Registre o domínio, por exemplo no Registro.br, e aponte os DNS para a Cloudflare.
2. No painel **Cloudflare Zero Trust → Networks → Tunnels**, crie um túnel do tipo Docker e copie o token.
3. Cole o token em `CLOUDFLARE_TUNNEL_TOKEN` no `.env` e defina `COOKIE_SEGURO=true`.
4. Em **Public Hostnames**, crie as rotas:

| Endereço | Serviço |
|---|---|
| `app.seudominio.com.br/api/*` | `http://api:8000` |
| `app.seudominio.com.br` | `http://web:3000` |

5. Suba com o túnel fixo:

```
docker compose --profile gpu --profile tunel up -d
```

## 8. Atualizar

```
git pull
docker compose --profile gpu up --build -d
```

## 9. Backup e restauração

O serviço `backup` grava uma cópia do banco todo dia no horário de `BACKUP_HORA` e guarda os últimos 14 dias.

Para fazer um backup na hora:

```
docker compose run --rm backup python -m backup.agendador_backup --agora
```

Para restaurar, use o `mongorestore` com a pasta do backup:

```
mongorestore --gzip --db holycut <pasta>/backup_DD-MM-AAAA_HH-MM/holycut
```
