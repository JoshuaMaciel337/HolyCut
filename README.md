# HolyCut

> Transforme momentos em histórias.

IA que transforma a gravação do culto em Stories, Reels e cortes da pregação prontos para postar, com a identidade visual de cada igreja. Tudo roda em máquina própria, com modelos abertos e sem custo por uso.

- **Plano do projeto:** [docs/PLANO.md](docs/PLANO.md)
- **Preparar o servidor (Nitro 5):** [docs/SETUP_NITRO.md](docs/SETUP_NITRO.md)
- **Pesquisa de mercado (Cut.Pro e OpusClip):** [docs/PESQUISA_MERCADO.md](docs/PESQUISA_MERCADO.md)
- **Marca:** [brand/README.md](brand/README.md)
- **Contexto para o Claude Code** (estado atual, pedidos fixos e decisões): [CLAUDE.md](CLAUDE.md)

## Estrutura

```
apps/web/       Next.js — landing, login e painel
apps/api/       FastAPI — sessão, organizações, jobs e eventos ao vivo
apps/worker/    Worker da fila de jobs (CPU e GPU)
apps/agente/    Agente que envia sozinho as gravações do OBS (roda no PC da mídia)
core/           Código Python compartilhado: config, Mongo, fila, storage
infra/          Dockerfiles e agendador de backup
brand/          Brand kit gerado por script
tests/          Testes unitários e de integração
compose.yaml    Todos os serviços
```

## Rodar com Docker

```
cp .env.example .env        # e defina JWT_SEGREDO
docker compose up --build
```

Abra http://localhost:3000, crie uma conta e envie a gravação de um culto. O teste da fila e da GPU fica em **Diagnóstico**, no painel Sistema.

Os vídeos enviados ficam em `./armazenamento`. Como gravações de culto são grandes, aponte `PASTA_ARMAZENAMENTO_HOST` no `.env` para o disco com mais espaço. A API recusa um envio que deixaria menos de 2 GB livres.

Se alguma porta já estiver em uso no seu computador, troque `MONGO_PORTA`, `API_PORTA` ou `WEB_PORTA` no `.env`. Por exemplo, use `MONGO_PORTA=27019` quando já houver um MongoDB local na 27017.

| Onde | Comando |
|---|---|
| Máquina de desenvolvimento, sem IA | `docker compose up --build` |
| Nitro 5, com GPU | `docker compose --profile gpu up --build -d` |
| Acesso de fora por túnel temporário | acrescente `--profile tunel-rapido` |
| Produção com túnel fixo | acrescente `--profile tunel` |

## Rodar sem Docker

Útil para desenvolver com recarga automática. Precisa de um MongoDB acessível.

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
set PYTHONPATH=.;apps
set MONGO_URI=mongodb://localhost:27017/?directConnection=true

uvicorn api.main:app --reload --port 8000
python -m worker.worker_principal --automatico --recursos cpu
```

Em outro terminal:

```
cd apps/web
npm install
npm run dev
```

O site em http://localhost:3000 repassa `/api` para a API na porta 8000.

> Sem replica set no Mongo, os eventos ao vivo usam consulta a cada 2 segundos. No Docker o Mongo já sobe como replica set.

## Testes e qualidade

```
ruff check .
pytest                      # os testes de integração usam um banco holycut_teste_* e apagam no fim

cd apps/web
npm run lint
npm run typecheck
npm run build
```

O GitHub Actions roda tudo isso a cada push.

## Padrões

O projeto segue os padrões da equipe Polo Infantil Store: Python com MongoDB via pymongo, nomes em português no formato `verbo_objeto()`, `logging` em vez de `print`, credenciais só por variável de ambiente, fuso `America/Sao_Paulo` e scripts agendáveis com `--agora` e `--automatico`.
