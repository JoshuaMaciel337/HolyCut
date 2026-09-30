# HolyCut — contexto para o Claude

O Claude Code lê este arquivo sozinho ao abrir uma conversa nesta pasta. Ele resume o que já foi decidido e feito, para uma conversa nova (por exemplo, no Nitro 5) continuar de onde a outra parou. O plano completo está em [docs/PLANO.md](docs/PLANO.md).

## Manter este arquivo atualizado

- Toda mudança que altera o estado do projeto atualiza, **no mesmo commit**, a seção "Estado atual" daqui e o checklist do `docs/PLANO.md`. Vale para qualquer máquina.
- Decisão técnica nova que não fica óbvia lendo o código vai para "Decisões técnicas" abaixo. Se for grande, vira um ADR em `docs/decisoes/`.
- Duas máquinas trabalham no mesmo repositório (a de desenvolvimento e o Nitro 5). Rode `git pull` antes de começar e faça o push ao terminar, para as duas conversas verem o mesmo estado.
- Não repita aqui o que o código ou o PLANO já explicam. Este arquivo é o resumo e o "porquê".

## O que é

App web que transforma a gravação do culto em Stories, Reels e cortes da pregação prontos para postar, com a identidade de cada igreja. Roda em máquina própria (o Nitro 5, com RTX 3070 Ti de 8 GB), com modelos de IA abertos e sem custo por uso.

O que os concorrentes (Cut.Pro, OpusClip, FeedChurch, Doxus e Bíblia IA) fazem, o que usam e o que vale trazer está em [docs/PESQUISA_MERCADO.md](docs/PESQUISA_MERCADO.md). Use como referência ao desenhar as etapas de IA.

## Pedidos fixos do dono do projeto

- **Fora do escopo, não propor:** avatar de IA, dublagem, clonagem de voz, lip-sync e correção de olhar.
- **O HolyCut é independente:** não se liga a nenhum outro projeto do dono (como o painel de lives), nem por código, banco, dados ou login. Não propor integração.
- **O repositório é público.** O `.env` nunca vai para o Git. Antes de cada push, procure no diff por senhas, tokens, chaves e e-mails pessoais.
- **Tudo em português:** código, mensagens da interface, logs, testes e commits.
- **Stack aprovado:** FastAPI, Next.js 16 com Tailwind 4, MongoDB, FFmpeg e Docker Compose. É o padrão da equipe: Python, MongoDB via pymongo, `logging` em vez de `print`, fuso `America/Sao_Paulo` e scripts com `argparse --agora --automatico`. **Proibido** usar Redis, bancos SQL e ORM. A fila de jobs roda no próprio Mongo.
- **Git:** identidade local `Joshua Maciel <JoshuaMaciel337@users.noreply.github.com>`. Mensagens no formato "Área: descrição curta.", com acento, um corpo curto dizendo o porquê e o trailer `Co-Authored-By` do Claude. Commits pequenos, um por área, direto na `main`.
- **Licenças:** só bibliotecas e modelos com licença permissiva. Evite AGPL, como o YOLO da Ultralytics: para rosto, use o MediaPipe. Música e texto bíblico só com licença, porque ARA e NVI têm direitos autorais.
- **Prévia igual ao render:** toda diferença entre a prévia no navegador e o vídeo exportado é medida em números, não só no olho.

## Estado atual (atualizado em 30/09/2026)

- **Fase 0 (fundação):** pronta.
- **Fase 1 sem IA:** pronta. Inclui upload retomável (tus), ingestão (proxy 720p, forma de onda, níveis, miniaturas), corte de silêncios, editor de Reel com enquadramento e zoom, render em -14 LUFS, download e compartilhamento.
- **Fase 2 sem IA:** pronta. Inclui Sua Identidade (logo, cor, @), textos sobre o vídeo, HolyStories com modelos, filtros de cor e biblioteca de músicas com licença e volume que abaixa sob a fala.
- **Fase 3 sem IA:** em andamento. Pronto: linha do tempo (dividir, apagar, mover e arrastar partes), agente do OBS com chaves de envio e aprovação pelo celular. O que falta sem IA espera o dono: publicar no YouTube (credenciais OAuth do Google) e B-roll do Pexels (chave da API).
- **Nenhuma IA real foi implementada ainda.** `MODO_IA=simulado`, e o job `teste` só simula as etapas. O job `diagnostico_gpu` confere a GPU no Nitro.

### O que espera o Nitro 5 (ordem sugerida)

1. Seguir [docs/SETUP_NITRO.md](docs/SETUP_NITRO.md), subir com `docker compose --profile gpu up --build -d` e rodar o Diagnóstico no painel Sistema.
2. **Transcrição** com faster-whisper e WhisperX, modelo `large-v3-turbo` em int8, em português e com tempo por palavra. Ela destrava o resto da Fase 1: legendas animadas (4 presets), vícios de fala e edição pelo texto.
3. Limpeza de áudio opcional com DeepFilterNet.
4. **HolySermon:** um LLM no Ollama (Qwen3 ou Gemma 3, com saída em JSON Schema) sugere de 5 a 10 cortes. Depois, títulos, legendas de post e hashtags.
5. Reenquadramento seguindo o rosto (MediaPipe) e zoom nas ênfases.
6. HolyMoments (energia do áudio, cenas, nota visual) e detecção de versículos. O overlay de versículo já existe.
7. NVENC no render como opção (hoje o libx264 roda na CPU).

Cada etapa de IA vira uma tarefa nova em `apps/worker/tarefas/`, registrada em `REGISTRO` (`apps/worker/tarefas/__init__.py`) e em `TAREFAS` com recurso `gpu` (`core/modelos/job.py`). Com 8 GB de VRAM, o worker carrega **um modelo por vez** e descarrega antes de trocar (no Ollama, pelo `keep_alive`).

## Arquitetura em um minuto

- `apps/api` (FastAPI), `apps/worker` (fila), `apps/web` (Next.js), `apps/agente` (script que roda no PC da mídia da igreja, fora do Docker) e `core` (config, Mongo, fila, storage, render, arte e cores, compartilhado entre API e worker).
- **Fila no Mongo:** o job tem lease e heartbeat, e o de prioridade maior sai primeiro. `ErroDefinitivo` manda o job para erro sem novas tentativas. Uma tarefa é `Tarefa(executar(db, job, reportar), ao_falhar)`.
- **Eventos ao vivo:** por SSE, sempre começando com o evento "pronto". Se ele não chegar em 5 s, o site passa a consultar a API a cada 3 s, porque o Quick Tunnel da Cloudflare não entrega SSE.
- **Upload:** tus 1.0.0 dentro da própria API, em pedaços de 8 MB ([ADR 0001](docs/decisoes/0001-upload-tus-na-api.md)).
- **Arquivos:** o resto do sistema só conhece "chaves" (`org_<id>/midias/<id>/...`). Trocar a pasta local por R2 ou S3 é trocar o `core/utils/storage.py`.
- **Isolamento:** toda consulta filtra por `organizacao_id`. Cada igreja só vê o que é dela.

## Decisões técnicas que não aparecem de cara no código

- **Agente do OBS:** `apps/agente` é independente do resto (só stdlib e `requests`), porque roda no Windows da igreja. Ele se autentica com uma chave de envio (`hc_...`); o banco guarda só o SHA-256, e a chave só abre as rotas de upload e `/api/chaves-envio/conferir`. A imagem da API copia a pasta para servir o `.zip`, que já vem com o endereço do site no `.bat` (validado com `fullmatch`, para não virar comando). O `.bat` precisa de CRLF (`.gitattributes`).
- **Aprovação pelo link:** o pedido fica dentro da exportação (`aprovacao`), com o SHA-256 de um token de 256 bits. As rotas `/api/aprovar/{token}` são públicas e só mostram aquele vídeo; a página `/aprovar/[token]` fica fora do `proxy.ts`, com `noindex` e `no-referrer`. Pedir de novo troca o token. Não há convite de equipe ainda: foi uma escolha, para o pastor não precisar de conta.
- **Linha do tempo:** o projeto guarda `partes` (intervalos da gravação na ordem da lista, que podem se repetir). Projetos antigos só têm `trecho`, e o `partes_do_projeto` os converte na leitura.

- **Render numa passada só.** O FFmpeg abre o original uma vez por parte da linha do tempo, seleciona os trechos de cada parte com `select` e `aselect` e emenda as partes com `concat`. Os cortes ficam alinhados a 1/30 s, o áudio vai em blocos de 1600 amostras a 48 kHz, e os limites caem meio quadro antes de cada borda. Sem isso, perdia-se um quadro por corte e o som saía de sincronia.
- **Arte:** logo e textos são desenhados uma vez pelo `core/utils/arte.py`, com Pillow e as fontes da marca. O mesmo PNG vai para a prévia (`/api/arte/camada`) e para o overlay do FFmpeg. O layout é fixo em `Layout.BASIC`, porque o worker tem libraqm e a API não.
- **Cor e fundo em RGB** (`format=gbrp`). Os filtros de cor são matrizes 3×3 e contraste, não LUTs. No navegador viram `feColorMatrix` com `colorInterpolationFilters="sRGB"`, e a prévia sai igual ao render (medido).
- **Música:** o `sidechaincompress` baixa cerca de 14 dB quando há voz (medido). Com `-stream_loop`, a faixa recomeça do 0, não do ponto escolhido. A prévia imita isso pelos picos da forma de onda, de forma aproximada.
- **Next.js 16:** o middleware agora é `proxy.ts`, e `useSearchParams` precisa de `Suspense`. O Next guarda na memória o corpo de toda requisição, inclusive a que vai para `/api`, e cortava em 10 MB. Por isso o `proxyClientMaxBodySize` está em 45 MB, para a música de até 40 MB.
- **FFmpeg 6 e 7:** o arquivo de filtros é passado com `-/filter_complex` no 7 e com `-filter_complex_script` no 6. O CI usa o 6.1.
- **Espaço em disco:** a API recusa um envio que deixaria menos de 2 GB livres (`ESPACO_MINIMO_LIVRE_GB`).

## Rodar e testar

- Tudo: `docker compose up --build`, com o site em http://localhost:3000. Portas e pasta de armazenamento ficam no `.env` (veja o `.env.example`).
- Python: `ruff check .` e `pytest`. Os testes de integração criam um banco `holycut_teste_*` e o apagam no fim, e o `conftest` recusa qualquer outro banco.
- Os testes com FFmpeg são pulados quando ele não está instalado. Em Windows sem FFmpeg, rode-os dentro da imagem do worker, com o repositório montado em `/repo`.
- Site: `npm run lint`, `npm run typecheck` e `npm run build`, dentro de `apps/web`.
- O CI (GitHub Actions) roda lint e testes do Python, com FFmpeg, e lint, tipos e build do site. Todo push precisa terminar verde.
