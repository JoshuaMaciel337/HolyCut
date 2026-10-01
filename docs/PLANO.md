# HolyCut — Plano do Projeto

> **Transforme momentos em histórias.**
> Plataforma web com IA que transforma cultos, pregações e louvores em Stories, Reels e cortes prontos para as redes, com a identidade visual de cada igreja.

Versão 1.1 do plano · 29/09/2026 · servidor: notebook Acer Nitro 5 com RTX 3070 Ti

---

## 1. Visão do produto

O HolyCut recebe o vídeo bruto do culto e devolve conteúdo pronto para postar. A IA faz o trabalho pesado: transcreve, corta silêncios, escolhe os melhores trechos, legenda, reenquadra para vertical e aplica a identidade da igreja. A pessoa da mídia só revisa e exporta.

**Para quem é:** equipes de mídia de igrejas, geralmente voluntários com pouco tempo e pouca experiência em edição.

**Promessa central:** "Mesmo conteúdo. Muito mais alcance." Um culto de 2 horas vira 5 a 10 conteúdos em minutos, não em horas.

### Módulos do ecossistema

| Módulo | O que faz | Fase |
|---|---|---|
| **AutoCut** | Motor de edição: remove silêncios e vícios de fala, legenda e reenquadra | 1 |
| **HolyStories** | Stories 9:16 a partir de templates, com frase de destaque e marca da igreja | 1 |
| **HolyReels** | Reels de 15 a 90 s com legenda animada e música | 1 (básico) / 2 (completo) |
| **HolySermon** | Transforma uma pregação longa em vários cortes curtos escolhidos pela IA | 2 |
| **HolyMoments** | Encontra os melhores momentos do culto, inclusive do louvor, sem depender só da fala | 2 |
| **Sua Identidade** | Kit da igreja: logo, cores, fontes, @ e templates aplicados em tudo | 2 |
| **Acervo** (nome provisório) | A biblioteca dos cultos da igreja, no estilo de um streaming: capas, fileiras e, dentro de cada culto, os cortes, os versículos, o estudo e a transcrição | 3 (base) e 2 (conteúdo com IA) |
| **HolyStudy** (nome provisório) | Da pregação saem o resumo, os temas, os versículos citados e um guia de estudo para células, com PDF | 2 |

A referência de mercado (Cut.Pro, OpusClip, FeedChurch, Doxus e Bíblia IA) está em [PESQUISA_MERCADO.md](PESQUISA_MERCADO.md).

### Fora do escopo (decisão tomada)

Não entram no plano: avatar de IA, dublagem, clonagem de voz, lip-sync e correção de contato visual. São os recursos de dificuldade alta ou muito alta, exigem GPU pesada e têm licenças restritivas. Se um dia fizerem sentido, entram como serviço pago de terceiros, sem mudar a arquitetura.

Também ficam de fora, depois da pesquisa de mercado:
- chat que responde como pastor ("pastor virtual") e personagens de IA com rosto de gente;
- cortar pregações de outras igrejas: o HolyCut processa só o conteúdo da própria igreja;
- a API oficial do WhatsApp, que é paga (o link `wa.me` manual resolve);
- integração com outros projetos do dono: o HolyCut é independente.

---

## 2. Princípios técnicos

1. **Projeto é dado, vídeo é resultado.** Transcrição, cortes, enquadramento e estilo ficam num JSON no MongoDB. O FFmpeg só renderiza na exportação. Editar uma palavra da legenda não exige transcrever de novo.
2. **Nada destrutivo.** O arquivo original e a transcrição original nunca são alterados. Edições são guardadas como camadas por cima.
3. **Tudo local, sem custo por uso.** Modelos abertos rodando na própria GPU. Serviço externo só quando for opcional, como o banco de imagens do Pexels.
4. **Workers puxam trabalho.** Os workers de GPU buscam jobs no MongoDB. Assim um worker pode rodar no servidor, num PC com GPU da igreja ou numa GPU alugada por hora, sem mudar código.
5. **Multi-igreja desde o primeiro dia.** Todo documento pertence a uma organização. Isso evita reescrever tudo quando virar SaaS.
6. **Fiel ao que foi pregado.** A IA só organiza o que o pastor disse; ela não gera sermão nem "melhora" a mensagem. Títulos, ganchos, resumos, guias e legendas de post saem da fala real. Quando a IA não tem confiança no que extraiu, ela omite em vez de inventar. Todo texto automático aparece marcado como gerado por IA, para a equipe revisar, e a transcrição não corrige o português do pregador.
7. **A igreja é dona de tudo.** Vídeos, transcrições e estudos saem em formato aberto (MP4, SRT, TXT e PDF). Sair do HolyCut não pode custar o acervo.
8. **Padrões da equipe Polo.** Python com MongoDB via pymongo, funções e variáveis em português no formato `verbo_objeto()`, `logging` em vez de `print`, credenciais via `os.environ.get()`, timezone `America/Sao_Paulo`, upsert com merge e workers que nunca morrem por exceção.

---

## 3. O que mudou em relação às conversas anteriores

| Sugestão anterior | Decisão neste plano | Motivo |
|---|---|---|
| Fila com Redis + Celery | **Fila de jobs no próprio MongoDB** | O padrão da equipe proíbe Redis. Uma fila no Mongo com lease e heartbeat atende bem uma plataforma de vídeo, que tem poucos jobs longos, e elimina um serviço da infraestrutura. |
| Storage local ou MinIO | **Pasta local no MVP, compatível com S3 depois** | Uma camada `storage.py` esconde onde o arquivo está. Na hora de escalar, troca para Cloudflare R2 ou um S3 auto-hospedado sem mexer no resto. |
| Só Inter como fonte | **Montserrat nos títulos e Inter na interface** | É o que aparece no styleboard que você aprovou visualmente. |
| Duas paletas e um símbolo que não batia com o styleboard | **Kit redesenhado e gerado por script** (seção 9) | O kit v1 tinha a paleta certa, mas o símbolo não seguia a referência. O símbolo foi redesenhado em vetor e a paleta do kit v1 foi mantida. |
| Legenda só queimada pelo FFmpeg | **Legenda desenhada no navegador para prévia e em ASS para exportação** | A prévia fica instantânea enquanto a pessoa edita. As duas saídas vêm da mesma especificação de estilo. |
| Upload simples | **Upload retomável (protocolo tus)** | A gravação de um culto passa fácil de 5 GB. Se a internet da igreja cair no meio, o upload continua de onde parou. |
| HolyMoments só com LLM | **Sinais de áudio e vídeo + LLM** | No louvor quase não há fala útil. Os momentos fortes aparecem na energia do áudio, nas mudanças de cena e, opcionalmente, num modelo de visão. |
| Servidor na nuvem ou GPU alugada | **O próprio notebook como servidor, exposto por Cloudflare Tunnel** | Custo zero de hospedagem. O túnel sai do notebook para a Cloudflare, então não precisa abrir porta no roteador nem ter IP fixo (seção 11). |

---

## 4. Arquitetura

```
┌──────────────────────────────────────────────────────────────┐
│  WEB — Next.js (TypeScript)                                  │
│  Landing · Painel · Editor · Sugestões · Exportações · Kit   │
└──────────────┬───────────────────────────────▲───────────────┘
               │ REST + upload tus             │ progresso (SSE)
┌──────────────▼───────────────────────────────┴───────────────┐
│  API — FastAPI (Python)                                      │
│  auth · organizações · mídias · projetos · jobs · exportação │
└──────────────┬───────────────────────────────────────────────┘
               │ cria jobs / lê status
┌──────────────▼───────────────────────────────────────────────┐
│  MongoDB (replica set de 1 nó → change streams)              │
│  organizacoes · usuarios · midias · transcricoes · projetos  │
│  jobs · sugestoes · templates · biblioteca · exportacoes     │
└──────▲──────────────────────────────▲────────────────────────┘
       │ puxa jobs "cpu"              │ puxa jobs "gpu"
┌──────┴───────────────┐   ┌──────────┴─────────────────────────┐
│ Worker CPU           │   │ Worker GPU                          │
│ ingestão (ffprobe,   │   │ transcrição (WhisperX)              │
│ proxy, waveform)     │   │ limpeza de áudio (DeepFilterNet)    │
│ silêncios, cenas     │   │ LLM local (Ollama)                  │
│ legenda .ass         │   │ rostos (MediaPipe)                  │
│ renderização FFmpeg  │   │ render com NVENC (se disponível)    │
└──────────┬───────────┘   └──────────┬──────────────────────────┘
           └──────────────┬───────────┘
                ┌─────────▼──────────┐
                │ Storage            │
                │ local → S3/R2      │
                └────────────────────┘
```

### Fila de jobs no MongoDB

Cada job é um documento com tipo, status, prioridade, tentativas e um prazo de posse (`lease_ate`). O worker pega o próximo job de forma atômica:

```python
job = db.jobs.find_one_and_update(
    {
        "status": "pendente",
        "tipo": {"$in": TIPOS_SUPORTADOS},      # worker GPU só pega jobs de GPU
        "disponivel_em": {"$lte": agora},
    },
    {
        "$set": {"status": "executando", "worker_id": WORKER_ID,
                 "lease_ate": agora + timedelta(minutes=5)},
        "$inc": {"tentativas": 1},
    },
    sort=[("prioridade", -1), ("criado_em", 1)],
    return_document=ReturnDocument.AFTER,
)
```

- **Heartbeat:** enquanto processa, o worker renova o `lease_ate` e grava o progresso em percentual.
- **Recuperação:** um job com lease vencido volta para `pendente`. Isso cobre worker que travou ou caiu.
- **Retry com espera crescente:** 1 min, 5 min e 30 min. Depois de 3 falhas o job vai para `erro` com a mensagem guardada.
- **Pipeline:** ao terminar, cada etapa cria a próxima. Por exemplo, ingestão cria transcrição, que cria a análise.
- **Progresso ao vivo:** a API observa a coleção `jobs` por change stream e envia ao navegador por Server-Sent Events. Change streams exigem replica set, então o Mongo roda como replica set de 1 nó desde o desenvolvimento.

### Decisões que precisam da sua aprovação

O padrão da equipe proíbe tecnologias fora da lista sem aprovação. Um app web precisa de algumas:

| Item | Proposta | Por que | Alternativa |
|---|---|---|---|
| Framework da API | **FastAPI** | O padrão proíbe frameworks web em *scripts de automação*. Isto é uma API web. FastAPI é Python, tipado e gera documentação sozinha. | Flask, mais simples e menos tipado |
| Frontend | **Next.js + TypeScript + Tailwind** | Um editor de vídeo no navegador precisa de React. O Next também serve a landing page com bom SEO. | Vite + React, sem landing integrada |
| Upload grande | **tus** (tus-js-client no navegador, servidor tus na própria API; ver `docs/decisoes/0001`) | Upload retomável de arquivos de vários GB. | Upload em partes feito à mão |
| Containers | **Docker Compose** | A GPU funciona no Windows via WSL2 e o FFmpeg fica igual em todas as máquinas. | Instalar tudo direto no Windows |

---

## 5. Stack e modelos

### Aplicação

| Camada | Tecnologia |
|---|---|
| Frontend | Next.js (App Router), TypeScript, Tailwind CSS, shadcn/ui, TanStack Query, Zustand (estado do editor), Uppy, wavesurfer.js, ícones Lucide |
| API | Python 3.11, FastAPI, Pydantic v2, PyMongo com a API assíncrona nativa, JWT em cookie httpOnly, senhas com argon2 |
| Workers | Python 3.11, pymongo, `logging`, `threading` para heartbeat, `argparse` com `--agora` e `--automatico` |
| Banco | MongoDB 7+ em replica set |
| Mídia | FFmpeg com libass e NVENC |
| Infra | Docker Compose, NVIDIA Container Toolkit, Ollama |

> Python 3.11 nos containers porque PyTorch e WhisperX têm melhor compatibilidade nessa versão. Como tudo roda em Docker, a versão do Python instalada no Windows do notebook não importa.

### Modelos de IA (todos locais)

| Função | Ferramenta | Licença | Observação |
|---|---|---|---|
| Transcrição com tempo por palavra | faster-whisper + WhisperX | MIT / BSD | Modelo `large-v3-turbo` em int8 cabe em cerca de 3 GB de VRAM |
| Separar quem fala | pyannote (via WhisperX) | MIT, modelo com aceite de termos | Opcional. Útil em culto com mais de um pregador |
| Detectar fala x música | Silero VAD | MIT | Base do HolyMoments e do corte de silêncio |
| Limpeza de áudio | DeepFilterNet | MIT / Apache | Remove ruído de ar-condicionado e eco da nave |
| Mudança de cena | PySceneDetect | BSD-3 | |
| Rosto para reenquadrar | MediaPipe Face Detection | Apache 2.0 | **Evitar YOLO da Ultralytics**, que é AGPL |
| LLM (cortes, títulos, legendas de post) | Ollama com Qwen3 ou Gemma 3 | Apache / termos Gemma | Usar saída estruturada com JSON Schema, que o Ollama suporta |
| Visão (opcional, HolyMoments) | Modelo de visão via Ollama, como Qwen2.5-VL ou Gemma 3 | Idem | Pontua quadros-chave: mãos levantadas, plateia, luz |
| Imagens de apoio (B-roll) | API do Pexels | Uso comercial liberado | Única dependência externa, e opcional |

### Hardware

| Uso | Máquina | Situação |
|---|---|---|
| **Servidor do HolyCut** | Acer Nitro 5 com RTX 3070 Ti Laptop, 8 GB de VRAM | Atende bem o MVP e as igrejas piloto. Whisper `large-v3-turbo` em int8 usa cerca de 3 GB e um LLM de 8B quantizado usa cerca de 5 GB. Cabem juntos no limite, então o worker roda **um modelo por vez**. A GPU tem NVENC, que acelera muito a renderização. |
| Crescimento | Desktop com 16 a 24 GB de VRAM, ou GPU alugada por hora | A fila no Mongo permite somar workers sem mudar código. |

- **Memória RAM:** 16 GB funcionam. 32 GB deixam Mongo, Docker, Ollama e o site rodando juntos com folga.
- **Troca de modelo:** o worker descarrega um modelo antes de carregar outro. No Ollama isso é o parâmetro `keep_alive`.
- **Desenvolvimento:** o código pode ser escrito em qualquer computador. O Nitro 5 recebe as atualizações pelo Git e roda os containers.

---

## 6. Modelo de dados (MongoDB)

| Coleção | Conteúdo principal | Índices |
|---|---|---|
| `organizacoes` | nome, slug, plano, identidade (logo, cores, fontes, @, templates padrão) | `slug` único |
| `usuarios` | email, senha_hash, organizacao_id, papel (dono, editor, revisor) | `email` único |
| `midias` | arquivo original, metadados do ffprobe, proxy 720p, waveform, miniaturas, duração, status. Para o acervo, a **ficha do culto** (título, data, pregador, série e descrição) e as capas | `organizacao_id + criado_em` |
| `analises` | o que a IA tira de cada culto: blocos (louvor, avisos, oração, oferta, pregação), resumo, temas, palavras-chave, personagens, versículos citados com o momento em que aparecem, guia de estudo | `midia_id` único |
| `transcricoes` | idioma, segmentos e palavras com início, fim, confiança e falante | `midia_id` único |
| `projetos` | tipo, formato, cortes, enquadramento, legenda, áudio, overlays, template, versão | `organizacao_id + atualizado_em` |
| `sugestoes` | trechos sugeridos pela IA com início, fim, título, gancho, nota e motivo | `midia_id + nota` |
| `jobs` | tipo, status, prioridade, tentativas, lease, worker, progresso, entrada, saída, erro | `status + tipo + prioridade + criado_em` |
| `modelos` | visual salvo pela igreja (fundo, cor, logo e textos). Os modelos prontos ficam no código | `organizacao_id + criado_em` |
| `musicas` | faixas da igreja, **cada uma com licença e atribuição**, status e duração. B-roll entra depois, com licença do mesmo jeito | `organizacao_id + criado_em` |
| `exportacoes` | projeto, versão, arquivo final, formato, status, texto do post | `projeto_id + criado_em` |

Uma transcrição de 2 horas tem cerca de 20 mil palavras e ocupa perto de 1,5 MB. Cabe com folga no limite de 16 MB por documento.

### Exemplo de projeto

```json
{
  "_id": "prj_01J…",
  "organizacao_id": "org_01J…",
  "midia_id": "mid_01J…",
  "tipo": "reel",
  "formato": { "largura": 1080, "altura": 1920, "fps": 30 },
  "versao": 7,
  "cortes": [
    { "inicio": 812.40, "fim": 838.95 },
    { "inicio": 841.10, "fim": 866.00 }
  ],
  "enquadramento": {
    "modo": "rosto",
    "keyframes": [{ "t": 812.4, "x": 0.52, "y": 0.40, "zoom": 1.0 },
                  { "t": 830.0, "x": 0.50, "y": 0.38, "zoom": 1.15 }]
  },
  "legenda": {
    "preset": "digno",
    "palavras_por_bloco": 3,
    "posicao": "centro",
    "cor_destaque": "#FFD24D",
    "edicoes": { "w_1832": "Jesus" }
  },
  "audio": { "limpeza": true, "musica_id": null, "volume_musica": 0.15, "lufs_alvo": -14 },
  "overlays": [
    { "tipo": "logo", "posicao": "topo_esquerda" },
    { "tipo": "versiculo", "referencia": "João 3:16", "inicio": 820.0, "fim": 826.0 }
  ],
  "template_id": "tpl_culto_de_hoje"
}
```

- `edicoes` guarda só as palavras alteradas pelo id da palavra, e a transcrição original continua intacta.
- `versao` serve para controle de concorrência. Se duas pessoas editarem ao mesmo tempo, a segunda recebe um aviso em vez de apagar o trabalho da primeira.

---

## 7. Pipeline de processamento

| # | Etapa | Worker | O que faz |
|---|---|---|---|
| 1 | `ingestao` | CPU | ffprobe, extrai áudio WAV 16 kHz mono, gera proxy 720p com faststart, picos de waveform e sprite de miniaturas |
| 2 | `limpeza_audio` | GPU | DeepFilterNet gera uma faixa de áudio limpa. Opcional por projeto |
| 3 | `transcricao` | GPU | WhisperX em português com alinhamento por palavra e, se ligado, separação de falantes |
| 4 | `analise_fala` | CPU | Silêncios, vícios de fala e trechos de música x fala |
| 5 | `analise_video` | CPU/GPU | Mudança de cena e trajetória do rosto para o recorte vertical, com suavização |
| 6 | `analise_momentos` | CPU/GPU | Energia do áudio, cenas e, opcionalmente, nota visual |
| 7 | `sugestao_cortes` | GPU | LLM lê a transcrição em blocos e devolve trechos em JSON, com título, gancho, nota e motivo |
| 8 | `renderizacao` | CPU/GPU | Monta o vídeo final (detalhe abaixo) |
| 9 | `textos_post` | GPU | Legenda do post, hashtags e título para cada rede |

### Detalhes que fazem diferença na qualidade

- **Vícios de fala em português.** Alongamentos como "ééé", "hããã" e "ahn" podem ser removidos automaticamente. Palavras como "né", "tipo" e "então" só aparecem como sugestão, porque às vezes fazem parte da frase.
- **Corte de silêncio natural.** O corte deixa uma margem de 80 a 150 ms antes e depois da fala e aplica um crossfade curto no áudio. Sem isso o vídeo fica "picotado".
- **Reenquadramento.** O recorte 9:16 segue o rosto com suavização, para a câmera não tremer. Quando não há rosto, como no louvor com plateia, o recorte fica no centro ou num ponto escolhido pelo usuário.
- **Zoom dinâmico.** Zooms leves de 1,0x para 1,15x em frases de ênfase, que o LLM marca. Dá ritmo sem precisar de outra câmera.
- **Renderização.** Um único comando FFmpeg faz tudo: recorta e junta os trechos, aplica recorte e zoom, sobrepõe template e logo, queima a legenda ASS, mistura a música abaixando o volume quando há fala e normaliza o áudio em -14 LUFS, o padrão das redes. Saída H.264 em 1080x1920 e AAC, com NVENC quando houver GPU.
- **Sugestões do LLM.** O prompt pede trechos de 30 a 90 s que façam sentido sozinhos, com gancho nos primeiros 3 segundos. As notas vão de 0 a 100 e cada sugestão explica o motivo, para a pessoa confiar no resultado.
- **Versículos.** Referências faladas, como "João 3:16", são detectadas na transcrição e viram um overlay opcional. O texto bíblico precisa ser de uma tradução em domínio público ou licenciada, porque ARA e NVI têm direitos autorais.

---

## 8. Frontend

### Telas

| Tela | Conteúdo |
|---|---|
| **Landing** | Baseada no moodboard 1: hero com o celular, fluxo "Grave → IA seleciona → Edita → Compartilha", os módulos e o botão "Comece agora" |
| **Login e cadastro** | Cadastro cria a organização (igreja) e o primeiro usuário como dono |
| **Início** | Projetos recentes, uploads em andamento e o botão "Criar agora" |
| **Acervo** | A biblioteca dos cultos da igreja, no estilo de um streaming (detalhado abaixo) |
| **Página do culto** | Banner, ficha e as abas do culto: visão geral, cortes, versículos, estudo, transcrição e gravação |
| **Novo projeto** | Escolha entre HolyStories, HolyReels, HolySermon e HolyMoments, depois o upload |
| **Sugestões** | Grade de cortes sugeridos pela IA, com prévia, nota e motivo. Um clique abre no editor |
| **Editor** | Detalhado abaixo |
| **Exportações** | Galeria dos vídeos prontos, download, texto do post e compartilhamento pelo celular |
| **Sua Identidade** | Logo, cores, fontes, @ da igreja e templates padrão |
| **Configurações** | Membros da equipe, papéis e preferências |

### Acervo (estilo streaming)

Cada igreja tem o seu acervo, e cada pessoa vê só os cultos da própria igreja (tudo filtrado por `organizacao_id`, como o resto do sistema). Um culto é uma gravação com a sua ficha.

- **Ficha do culto:** título (por exemplo, "Inconformados no altar"), data do culto, pregador, série (opcional) e uma descrição curta. O título nasce do nome do arquivo e a data, do dia do envio; a pessoa corrige. Com a IA, o título e a descrição passam a vir sugeridos pela pregação.
- **Capas:** um pôster vertical 2:3, para as fileiras, e um banner 16:9, para o destaque e a página do culto. Os dois são gerados de um quadro da gravação com o título escrito na arte da igreja (fonte, cor de destaque e logo), pelo mesmo `arte.py` dos textos. A pessoa pode trocar o quadro ou enviar a própria imagem.
- **Tela do acervo:**
  - um banner de destaque com o culto mais recente (capa grande, título, pregador, data e os botões "Assistir" e "Ver cortes");
  - fileiras horizontais, como no streaming: "Últimos cultos", uma fileira por série, "Por pregador", "Com cortes prontos" e "Continuar editando";
  - busca no topo: por título e pregador de início, e por versículo, tema ou pergunta quando a IA estiver pronta.
- **Página do culto:** o banner com a capa ao fundo, a ficha e as abas:
  - **Visão geral:** a ficha e, com a IA, o resumo, os temas e os personagens bíblicos;
  - **Cortes:** os Reels e Stories do culto, prontos e em edição, com a aprovação do pastor;
  - **Versículos:** os citados na pregação, cada um levando ao trecho do vídeo em que aparece (IA);
  - **Estudo:** o guia para células, com PDF (IA);
  - **Transcrição:** o texto sincronizado com o vídeo, com download em SRT e TXT (IA);
  - **Gravação:** o player, a forma de onda, os silêncios e, com a IA, os blocos do culto.
- **Sem a IA**, as abas que dependem dela aparecem explicando que o conteúdo chega com a transcrição. A estrutura já nasce pronta para recebê-lo.

### Editor

- **Prévia em formato de celular** com a legenda desenhada por cima em tempo real. A prévia usa o proxy de 720p, então fica leve.
- **Edição pelo texto.** A transcrição aparece como um documento. Apagar uma frase corta o vídeo e corrigir uma palavra corrige a legenda. É o recurso que mais economiza tempo de quem não sabe editar.
- **Linha do tempo** com waveform, trechos e marcadores de silêncio. No MVP ela é simples, e na fase 3 ganha arrastar e soltar.
- **Barra inferior** como no mockup: Cortar, Música, Texto, Filtros, Efeitos e Ajustes.
- **Presets de legenda:** "Digno", com uma palavra em fonte manuscrita e destaque dourado; "Clean"; "Karaokê", com a palavra atual iluminada; e "Destaque", com uma palavra-chave em laranja.
- **Formatos:** 9:16, 1:1, 4:5 e 16:9.
- **PWA instalável**, para usar no celular como app, com o ícone da marca.

> **Risco a controlar:** a legenda da prévia e a legenda do ASS são desenhadas por motores diferentes. As duas precisam ler o mesmo JSON de estilo. O editor também deve ter um botão de "prévia real" que renderiza 5 segundos no servidor, para conferir.

---

## 9. Identidade visual

O brand kit oficial está em [brand/](../brand/README.md). Ele é gerado por um script, então cores e formas mudam num lugar só.

### O que foi feito com o kit v1

- **O símbolo foi redesenhado em vetor.** O SVG do kit da outra conversa não se parecia com o logo do styleboard. O novo segue a referência: um "H" com o play no alto e a perna direita laranja cortada na diagonal.
- **O nome virou contorno.** "HolyCut" é desenhado em Montserrat Bold convertida em vetor, então o logo não depende da fonte instalada.
- **Foram criadas as versões que faltavam.** Logo com e sem slogan, versões para fundo escuro e claro, uma cor só, ícones do app, ícone para PWA, favicon e ícone do iPhone.
- **O "Cut" usa o gradiente quente do styleboard.** No kit v1 ele ia até o violeta. No fundo claro o gradiente fica mais laranja, porque o amarelo some no branco.
- **O kit original ficou guardado** em `brand/referencia/kit-v1-original/`.

### Paleta

Ficaram os valores do kit v1, que são praticamente idênticos aos do styleboard e têm dois níveis de superfície, úteis na interface.

| Token | Cor | Uso |
|---|---|---|
| `--hc-ink` | `#08090F` | Fundo principal |
| `--hc-surface` | `#11131A` | Cards |
| `--hc-surface-2` | `#1A1D26` | Elementos dentro de cards |
| `--hc-border` | `#2A2E3A` | Bordas e divisores |
| `--hc-text` | `#F5F7FA` | Texto principal |
| `--hc-muted` | `#A8AFBD` | Texto secundário |
| `--hc-yellow` | `#FFD24D` | Destaques |
| `--hc-orange` | `#FF8A00` | Acento principal e hover |
| `--hc-coral` | `#FF6A3D` | Detalhes do símbolo |
| `--hc-violet` | `#7B61FF` | Elementos de IA |
| `--hc-magenta` | `#F05BFF` | Acento secundário de IA |
| `--hc-cyan` | `#43D9FF` | Dados e ícones |

- **Gradiente da marca:** `#FFD24D → #FF8A00`, no "Cut" do logo e em destaques quentes.
- **Gradiente dos CTAs:** `#7B61FF → #FF8A00`, como o botão "Comece agora" do mockup.
- **Gradiente de IA:** `#7B61FF → #F05BFF`, em tudo que a IA faz.

### Tipografia

- **Montserrat** em títulos, destaques e no logo.
- **Inter** na interface e nos textos.
- **Caveat** nas legendas manuscritas, como "Digno" e "Culto de hoje".

As três estão em `brand/fontes/` com licença OFL, o que permite queimar no vídeo para uso comercial.

### Pendências da marca

- **Revisão de um designer.** O símbolo foi redesenhado a partir de uma imagem gerada por IA. Antes de registrar a marca, vale um designer refinar curvas e proporções.
- **Templates de Stories.** O template do kit v1 é só um rascunho. Os templates de verdade são feitos na Fase 1, junto com o HolyStories.

### Verificação da marca (29/09/2026)

| Item | Resultado |
|---|---|
| INPI, "HOLYCUT" e "HOLY CUT" | Nenhum pedido ou registro, na busca exata nem na radical |
| INPI, "HOLY" sozinha | 23 processos. Os que tocam o HolyCut: registro em vigor na **classe 42** (Blank Design Studio, 2020) e na **classe 41** (2023) |
| holycut.com | Registrado desde 10/09/2025 por um revendedor (Gname), sem site no ar |
| holycut.com.br, holycut.app, holycut.app.br, holycutapp.com | Livres |
| YouTube @holycut | Ocupado, por um canal "Holy Cut" com cerca de 8 vídeos. @holycutapp está livre |
| Instagram e TikTok | Não deu para confirmar automaticamente: o Instagram limitou as consultas e o TikTok bloqueia robôs. Conferir no celular |

Próximos passos:

1. Registrar **holycut.com.br** e **holycut.app** logo, porque são baratos e estão livres.
2. Usar **@holycutapp** nas redes, já que o @holycut do YouTube está ocupado.
3. Antes do depósito no INPI, pedir a opinião de um especialista em marcas sobre as marcas "HOLY" das classes 41 e 42. As classes do HolyCut são a 9 (software), a 41 (edição de vídeo) e a 42 (software como serviço).

---

## 10. Estrutura de pastas

```
HolyCut/
  apps/
    web/                      Next.js (landing + app)
      src/app/                rotas e telas
      src/componentes/        editor, player, timeline, legenda
      src/lib/                cliente da API, estado do editor
    api/
      main.py                 FastAPI
      rotas/                  auth.py, midias.py, projetos.py, jobs.py, exportacoes.py, eventos.py
      esquemas/               modelos Pydantic de entrada e saída
    worker/
      worker_principal.py     loop, lease, heartbeat, --agora / --automatico
      tarefas/
        ingestao.py
        limpeza_audio.py
        transcricao.py
        analise_fala.py
        analise_video.py
        analise_momentos.py
        sugestao_cortes.py
        legenda_ass.py
        renderizacao.py
        textos_post.py
  core/                       pacote Python compartilhado entre API e workers
    config.py                 constantes e variáveis de ambiente
    modelos/                  projeto.py, midia.py, job.py
    utils/
      mongo.py                conexão, índices, upsert com merge
      fila.py                 criar, pegar, renovar e concluir jobs
      storage.py              local agora, S3 depois
      ffmpeg.py               montagem dos comandos
      llm.py                  cliente do Ollama com saída estruturada
  brand/                      pronto (seção 9)
    gerar_brand_kit.py        gera logos, ícones e tokens
    logo/  app-icon/  fontes/  referencia/
    tokens/                   design-tokens.css, cores.json
  compose.yaml                mongo, api, worker-cpu, worker-gpu, ollama, web, backup, túneis
  infra/
    docker/                   Dockerfiles
    backup/                   agendador de backup do Mongo
  docs/
    PLANO.md                  este arquivo
    decisoes/                 registro de decisões de arquitetura
  armazenamento/              gerado em runtime (no .gitignore)
  .env.example
  .gitignore
```

---

## 11. Colocar no ar sem pagar hospedagem

O notebook é o servidor. O **Cloudflare Tunnel** liga o notebook à internet de graça. Um programa pequeno, o `cloudflared`, roda no notebook e abre uma conexão **de saída** até a Cloudflare. Quem acessa o site fala com a Cloudflare, e ela repassa pelo túnel.

**Por que é a melhor opção para o seu caso:**
- **Não precisa abrir porta no roteador.** A conexão sai do notebook, então funciona mesmo com IP dinâmico ou CGNAT, que é comum na internet residencial brasileira.
- **O IP da sua casa fica escondido.** Ninguém de fora enxerga o notebook diretamente.
- **HTTPS automático.** A Cloudflare cuida do certificado.
- **O plano gratuito não cobra por tráfego.**

```
Navegador / celular
        │  https://app.holycut.com.br
        ▼
   Cloudflare (DNS, HTTPS, proteção contra ataque)
        │  túnel criptografado, iniciado pelo notebook
        ▼
┌──────────── Notebook Nitro 5 (Docker Compose) ─────────────┐
│ cloudflared ─┬─ /          → web (Next.js)                 │
│              ├─ /api/*     → api (FastAPI)                 │
│              └─ /arquivos/*→ tusd (upload retomável)       │
│                                                            │
│ mongo · worker-cpu · worker-gpu · ollama   (nunca expostos)│
└────────────────────────────────────────────────────────────┘
```

O próprio túnel divide o tráfego por caminho. Assim site e API ficam no mesmo endereço, o login por cookie funciona sem configuração extra e não precisa de proxy reverso.

### O que custa e o que é de graça

| Item | Custo |
|---|---|
| Cloudflare Tunnel, DNS e HTTPS | Grátis |
| Cloudflare Access para proteger telas de administração | Grátis até 50 usuários |
| Cloudflare Pages para a landing page | Grátis, e o plano permite uso comercial |
| Domínio próprio, como `holycut.com.br` | Cerca de R$ 40 por ano no Registro.br. É o **único custo** da solução recomendada. |
| Energia do notebook ligado o tempo todo | Varia com o uso da GPU |

### Se quiser custo zero absoluto, sem domínio

| Opção | Endereço | Serve para |
|---|---|---|
| **Cloudflare Quick Tunnel** | Aleatório em `trycloudflare.com`, muda a cada reinício | Testes rápidos e mostrar para alguém |
| **Tailscale Funnel** | Fixo em `nome.ts.net`, com HTTPS | Piloto com 1 ou 2 igrejas. O plano grátis é pensado para uso pessoal e tem limite de banda. |
| **ngrok grátis** | Um domínio fixo | **Não recomendado.** Mostra uma página de aviso para os visitantes e tem limite baixo de tráfego mensal, o que não serve para vídeo. |

Recomendação: use o Quick Tunnel enquanto desenvolve e registre o domínio antes de chamar a primeira igreja piloto.

> O Quick Tunnel não entrega Server-Sent Events e aceita no máximo 200 requisições simultâneas, segundo a própria Cloudflare. Testado em 29/09/2026: por ele, o progresso dos jobs só chega quando a conexão fecha. O painel detecta isso e passa a consultar a API a cada 3 segundos. O túnel fixo não tem essa limitação.

### Ajustes obrigatórios por causa do túnel

- **Limite de 100 MB por requisição.** O plano grátis da Cloudflare recusa envios maiores que isso. O upload tus resolve, porque manda o arquivo em pedaços de 50 MB. Nenhum outro endpoint pode receber arquivo inteiro.
- **Vídeo servido com moderação.** Os termos da Cloudflare pedem serviços pagos para quem entrega muito vídeo pela rede deles. Para o piloto isso não pesa, porque a prévia usa o proxy leve de 720p e o download final é um arquivo curto. Se o volume crescer, os vídeos exportados passam para o Cloudflare R2, que tem 10 GB grátis e não cobra download.
- **Velocidade de upload da sua internet.** Cada prévia e cada download saem pela banda de upload da sua casa. Uma fibra com 100 Mbps de upload atende várias pessoas editando ao mesmo tempo. Vale medir a sua.

### Deixar o notebook confiável como servidor

- **Energia.** No Windows, configurar para nunca suspender na tomada e para não fazer nada ao fechar a tampa.
- **Bateria.** Ativar o limite de carga em 80% no NitroSense ou no Acer Care Center, se o modelo tiver. Ficar sempre em 100% na tomada gasta a bateria.
- **Temperatura.** Usar base com cooler. Uma renderização longa esquenta muito um notebook gamer.
- **Reinício automático.** Docker Desktop iniciando com o Windows e todos os serviços com `restart: unless-stopped`. Assim tudo volta sozinho depois de uma queda de energia.
- **Windows Update.** Definir o horário ativo para não reiniciar durante o fim de semana, quando as igrejas mais usam.
- **Página de manutenção.** A landing fica no Cloudflare Pages, sempre online. Se o notebook estiver desligado, o app mostra "servidor em manutenção" em vez de um erro.
- **Backup.** Um agendador no padrão da equipe roda `mongodump` todo dia e copia para um HD externo ou para uma pasta do Google Drive.
- **Espaço em disco.** O vídeo original é apagado 30 dias depois do processamento, e os vídeos exportados ficam guardados.

### Segurança

- Só o `cloudflared` fala com a internet. Mongo, Ollama e workers ficam numa rede interna do Docker, sem porta publicada.
- A documentação automática da API e as telas de administração ficam atrás do Cloudflare Access, com login por e-mail.
- A API limita tentativas de login e o tamanho total de upload por igreja.

### Configuração do túnel

O túnel roda como mais um serviço no Docker Compose, usando o token criado no painel Zero Trust da Cloudflare:

```yaml
cloudflared:
  image: cloudflare/cloudflared:latest
  command: tunnel run
  environment:
    - TUNNEL_TOKEN=${CLOUDFLARE_TUNNEL_TOKEN}   # vem do .env, nunca do código
  restart: unless-stopped
  depends_on: [web, api, tusd]
```

No painel, cada rota aponta para um serviço interno:

| Endereço público | Serviço interno |
|---|---|
| `app.holycut.com.br/api/*` | `http://api:8000` |
| `app.holycut.com.br/arquivos/*` | `http://tusd:8080` |
| `app.holycut.com.br` | `http://web:3000` |

### Quando o notebook não bastar

A arquitetura já está pronta para crescer sem reescrever nada:

1. Vídeos exportados passam para o Cloudflare R2.
2. Site e API vão para uma VPS barata, e o banco para o MongoDB Atlas.
3. O notebook continua como worker de GPU, puxando jobs pela internet, sem precisar receber conexões.
4. Novos workers de GPU entram ao lado dele, próprios ou alugados por hora.

---

## 12. Roteiro

As estimativas consideram 1 pessoa desenvolvendo em tempo integral. Com duas, cai para cerca de dois terços.

### Fase 0 — Fundação (1 a 2 semanas)

- [x] Verificar a marca "HolyCut": busca no INPI, domínios (.com, .com.br, .app) e @ no YouTube. Resultado na seção 9. Instagram e TikTok ficam para conferir no celular
- [x] Iniciar o repositório Git, o `.gitignore` e o `.env.example`
- [x] Brand kit recriado em `brand/`, com símbolo redesenhado em vetor
- [ ] Preparar o Nitro 5: driver NVIDIA atualizado, WSL2, Docker Desktop e ajustes de energia da seção 11
- [x] Docker Compose com Mongo em replica set, Ollama com GPU e FFmpeg nos containers (rodando na máquina de desenvolvimento; o Ollama sobe só no Nitro)
- [x] Confirmar a GPU no Docker via WSL2 com `nvidia-smi` dentro do container. No Nitro, o diagnóstico viu a RTX 3070 Ti de 8 GB e o Ollama 0.35.0
- [x] Cloudflare Quick Tunnel para acessar o notebook de fora durante o desenvolvimento (testado; o painel consulta a API a cada 3 s, porque esse túnel não entrega eventos ao vivo)
- [x] Agendador de backup diário do Mongo
- [x] Pacote `core` com conexão ao Mongo, índices, fila de jobs e storage
- [x] API com cadastro, login e organização
- [x] Web com design tokens, layout escuro, landing, login e tela Início
- [x] Qualidade: ruff e pytest no Python, ESLint e checagem de tipos no web, GitHub Actions rodando tudo

**Pronto quando:** um job de teste sai da API, é pego pelo worker e o progresso aparece no navegador.

**Situação em 29/09/2026:** critério atingido também no Docker da máquina de desenvolvimento, com o site aberto pela internet através do Quick Tunnel. Verificado:

- Cadastro, login, job de teste e progresso ao vivo pelo site, dentro do Docker.
- Backup gravado na pasta do computador e restaurado num banco separado.
- Queda do Docker no meio do teste: os containers voltaram sozinhos e nenhum dado se perdeu.
- Botão "Testar GPU": o worker de GPU achou a RTX 3050 dentro do container.
- CI do GitHub passando a cada push.

O Nitro 5 sobe com `docker compose --profile gpu` e o diagnóstico da GPU passou. Falta o ajuste de energia da seção 11 (não suspender na tomada).

### Fase 1 — MVP: AutoCut + legendas (4 a 6 semanas)

- [x] Upload retomável com barra de progresso, pausa e retomada depois de queda de internet
- [x] Ingestão: proxy, waveform e miniaturas (cerca de 21 s para 90 s de vídeo 1080p na CPU da máquina de desenvolvimento)
- [x] Transcrição com WhisperX em português, com o vocabulário da igreja (nome do pastor, da igreja e dos ministérios, livros bíblicos) por `hotwords` e `initial_prompt`. faster-whisper `large-v3-turbo` em int8, alinhamento por palavra, SRT e TXT na aba do culto. A separação de falantes continua de fora (o modelo pede aceite de termos)
- [x] Limpeza de áudio opcional. DeepFilterNet3, por projeto e desligada por padrão. A faixa limpa cobre a gravação inteira; a prévia usa `proxy_limpo.mp4` e a exportação usa `audio_limpo.wav`
- [x] Corte automático de silêncios e vícios de fala, com ajuste de intensidade. Silêncios em leve, médio e forte. Vícios na mesma escala (né e ah no leve; tipo, sabe, tá e ok no médio; então, assim e aí no forte). A pessoa devolve qualquer palavra. "é", "amém" e "Jesus" não saem sozinhos
- [x] Editor com prévia, edição pelo texto e linha do tempo. Corrigir uma palavra só muda a legenda; tirar uma palavra ou uma frase corta esse instante do vídeo. A transcrição original fica intacta
- [x] Legendas animadas com 4 presets (Clean, Karaokê, Destaque e Digno). A palavra em destaque é a mais longa do bloco, na cor da igreja (dourada e manuscrita no Digno). A prévia e o ASS saem dos mesmos blocos
- [x] Reenquadramento 9:16 com recorte central e ponto ajustável (também 4:5, 1:1 e 16:9, com zoom)
- [x] HolyStories: 3 templates de story com frase de destaque e logo (Culto de hoje, Frase da pregação e Versículo; exporta vídeo ou imagem)
- [x] Exportação 1080x1920 com download e compartilhamento pelo celular (27 s escolhidos viraram 22 s de Reel em 17 s de render na CPU de desenvolvimento)

**Pronto quando:** uma pregação de 40 minutos vira um Reel legendado em menos de 15 minutos de trabalho humano. Isso cobre cerca de 70% do uso real de um app como o Captions.

**Validação:** colocar nas mãos da equipe de mídia de 1 ou 2 igrejas reais antes de seguir para a Fase 2. Antes disso, registrar o domínio, trocar para o túnel fixo e publicar a landing no Cloudflare Pages.

### Fase 2 — IA de conteúdo (4 a 6 semanas)

- [x] **HolySermon:** o LLM sugere de 5 a 10 cortes por pregação, e cada um abre no editor com um clique. Cada sugestão traz título, motivo, nota e as partes (pode juntar trechos de lugares diferentes da pregação, na linha do tempo que já existe). Segue a estratégia da igreja, escrita uma vez em linguagem natural ("priorize o apelo e a oração"). Gemma 3 4B no Ollama. O título e a legenda do post precisam ser frases ditas; a hashtag só entra se a palavra aparece na fala
- [ ] Separar o culto em blocos (louvor, avisos, oração, oferta e pregação), para cortar só a pregação: detecção de música e fala e o LLM para nomear os blocos. **Código pronto** (job `blocos_culto`, faixa colorida na aba Gravação): as fronteiras saem do áudio e das palavras, o Gemma só escolhe o nome numa lista fechada e, sem ele, valem as palavras-chave. Com a pregação marcada, o HolySermon e o HolyStudy leem só a mensagem. Testado com um culto sintético; falta calibrar os limiares com cultos reais no Nitro
- [ ] **HolyStudy:** resumo, temas, palavras-chave, personagens bíblicos e versículos citados de cada pregação, e um guia de estudo para células (perguntas, versículos-chave, aplicação e oração), com PDF. **Código pronto** (job `estudo_culto`, abas Visão geral e Estudo, página de impressão em PDF), testado com o modelo simulado; falta rodar com o Gemma no Nitro e conferir a qualidade em pregações reais
- [ ] Busca no acervo por versículo, tema ou pergunta, com embeddings locais
- [ ] Tradução da transcrição e das legendas para espanhol e inglês (só texto, sem dublagem)
- [x] Títulos, legendas de post e hashtags gerados por rede. Saem no mesmo job do HolySermon e ficam no corte e no projeto, marcados como gerados por IA
- [x] Reenquadramento seguindo o rosto e zoom dinâmico nas ênfases. MediaPipe na CPU, desligado por padrão. A prévia e o render usam o mesmo degrau de quadro
- [x] **HolyMoments:** energia do áudio, cenas e nota visual opcional. A nota só aceita pregador, plateia, luz ou outro
- [x] NVENC opcional no render. O botão padrão continua no processador (libx264). O job `renderizacao_nvenc` só roda no worker de GPU; se a placa recusar, o job falha sem cair no processador em silêncio
- [x] **Sua Identidade:** kit da igreja aplicado automaticamente em todo projeto (logo, cor de destaque e @; o logo entra ligado em todo Reel novo)
- [x] Biblioteca de músicas com licença registrada e volume que abaixa sob a fala (a faixa só entra com a licença; CC BY exige o crédito e o editor lembra de pôr na legenda; a música abaixa cerca de 14 dB quando há voz, pelo sidechaincompress do FFmpeg)
- [x] Filtros e correção de cor (Natural, Quente, Frio, Cinema, P&B e Vivo, com intensidade; matrizes de cor em vez de LUTs, para a prévia sair igual ao render)
- [x] Detecção de versículos. A referência (livro, capítulo e versículo) sai da fala e aparece na aba do culto; o texto é o que foi dito, não uma tradução. **Overlay pronto**: título, frase e versículo com referência, digitados, em três estilos
- [x] Sistema de templates editáveis (a igreja salva o visual de qualquer projeto como modelo; fundo com escurecer e desfocar)

### Fase 3 — Produto completo (4 a 6 semanas)

- [x] Linha do tempo completa com arrastar, dividir e reordenar (o projeto tem partes em qualquer ordem, que podem se repetir; o render emenda as partes sem perder a sincronia, medido com clarão e bipe)
- [ ] B-roll pelo Pexels, com busca feita pelo LLM a partir da frase
- [x] Fluxo de aprovação: o editor manda e o pastor ou líder aprova pelo celular (por um link de 7 dias, sem conta: aprova ou pede ajuste com comentário, e o editor vê a resposta sozinho)
- [x] Agente de pasta monitorada: um script no PC da mídia envia sozinho a gravação do OBS quando o culto termina (`apps/agente`, baixado pelo site em .zip; usa uma chave de envio que só serve para enviar e pode ser revogada)
- [ ] Publicação direta no YouTube, no horário escolhido para cada corte e com aprovação antes se a igreja quiser, e depois Instagram e TikTok
- [x] **Acervo da igreja** no estilo de streaming: ficha do culto, capas geradas, fileiras e a página do culto com abas (seção 8). Sem a IA, as abas de versículos, estudo e transcrição explicam o que chega com a transcrição
- [ ] Importar pelo link do YouTube ou do Google Drive (só vídeos da própria igreja). **Código pronto** (job `importar_link` com yt-dlp; do YouTube, só do canal cadastrado em Envio automático; do Drive, com a confirmação da pessoa; live no ar espera sem gastar tentativas). Testado com o yt-dlp simulado; falta reconstruir a imagem do worker e baixar uma live de verdade no Nitro
- [ ] Monitorar o canal do YouTube pelo feed RSS público e começar sozinho quando a live do culto termina. **Código pronto** (o laço do worker lê o feed de cada igreja a cada 10 min; na primeira volta só marca o que já tinha terminado; vídeo com menos de 20 min fica de fora). Testado com o feed simulado; falta conferir com o canal de verdade no Nitro
- [x] Marcar a pregação e exportar o vídeo 16:9 só da mensagem, sem louvor nem avisos (à mão na aba Gravação, ou automático pelos blocos do culto; a marcação da pessoa nunca é trocada pela IA). Testado pela API; a tela ainda não foi aberta no navegador
- [x] Exportar para DaVinci e Premiere: XML com as partes, SRT e folga nas pontas (um .zip no editor: XML do Final Cut 7, que os dois importam, com um clipe por trecho que fica, apontando para a gravação original inteira, e a legenda em SRT no tempo do vídeo final; a gravação original baixa pela aba Gravação). Testado pela estrutura do XML; falta importar num DaVinci e num Premiere de verdade
- [x] Escolher a capa do vídeo exportado e um QR code para baixar no celular (a capa sai do quadro em que o player do vídeo pronto está, sem renderizar de novo; o QR leva um link de 24 h que baixa só aquele vídeo, sem conta)
- [ ] **Editor no estilo do CapCut e do Opus**, em etapas:
  - [x] 1. Casca nova: no computador, a fala à esquerda, a prévia no centro, o painel da ferramenta e a barra de ícones à direita, e a linha do tempo larga embaixo; no celular, a prévia em cima, a linha do tempo e a barra fixa embaixo, com o painel subindo como gaveta. Os painéis são os mesmos de antes
  - [x] 2. Mexer direto na prévia: arrastar, aumentar e girar a legenda, os textos e o logo, e girar o vídeo (a posição vai para o render, medida contra a prévia)
    - [x] Textos e logo: clicar seleciona, arrastar move, a alça laranja aumenta e a roxa gira. Medido: a faixa do texto no vídeo exportado cai a até 2 px da caixa da prévia
    - [x] A legenda automática (arrastar e aumentar; vai para o ASS com `\an5\pos`) e girar o vídeo (botões de 90° e ajuste fino; o render gira o quadro já recortado, com cantos pretos). Comparado quadro a quadro com a prévia
  - [ ] 3. Camadas: imagens, PNG, ícones e figurinhas por cima do vídeo, com entrada e saída na linha do tempo
  - [ ] 4. Efeitos de vídeo (zoom, tremor, brilho, transições entre as partes) e efeitos sonoros com licença
  - [ ] 5. Voltar para a IA depois de reeditar (refazer legenda, títulos e legenda do post a partir do corte novo) ou seguir para exportar
- [ ] **Edição automática com estilos:** a IA edita sozinha seguindo um estilo da biblioteca (por exemplo, "Reel dinâmico" ou "Devocional calmo": ritmo dos cortes, zoom, legenda, filtro, música e posição do logo), e o resultado é um projeto comum, que a pessoa reabre e muda. A liberdade é só na edição, nunca no conteúdo: nada de fala ou título que o pastor não disse. Aprender o estilo a partir de um vídeo de exemplo fica para depois
- [ ] Abertura, encerramento e chamada no modelo, e a fonte própria da igreja
- [ ] Tela dividida com o pregador e o telão

### Fase 4 — SaaS (quando houver demanda)

- [ ] Transcrição ao vivo durante o culto, para quem não ouve bem (Whisper em streaming na GPU, com os versículos aparecendo na hora)
- [ ] Página pública do acervo para os membros, com a identidade da igreja (opcional; o foco continua sendo a equipe de mídia)

- [ ] Planos, cotas de minutos processados e cobrança com Pix (Asaas ou Mercado Pago)
- [ ] Seguir o caminho de crescimento da seção 11: R2, VPS, Atlas e mais workers de GPU
- [ ] Painel administrativo e métricas de uso
- [ ] Versão em inglês ("Turn moments into stories.")

---

## 13. Riscos e cuidados

| Risco | Impacto | Como tratar |
|---|---|---|
| **Direitos das músicas de louvor** | Vídeos silenciados ou removidos pelas redes | Avisar quando o trecho tem música de terceiros. Oferecer troca por música da biblioteca ou exportar sem música para a pessoa usar um som da própria rede. |
| **LGPD e direito de imagem** | Rostos de membros e **crianças** aparecem nos vídeos | Termo de uso de imagem para a igreja, aviso no app e, na fase 2, opção de desfocar rostos em segundo plano. |
| **Licenças de modelos** | Uso comercial proibido em alguns pesos | Só usar os modelos da seção 5. Qualquer modelo novo precisa ter a licença conferida antes de entrar. |
| **Qualidade do LLM em português** | Sugestões fracas | Testar Qwen3 e Gemma 3 com 10 pregações reais. Medir quantas sugestões a equipe aceitaria. Manter o prompt versionado. |
| **GPU de 8 GB do notebook** | Falta de memória com dois modelos carregados | Um modelo carregado por vez e LLM de até 8B quantizado. Jobs de GPU em fila, um de cada vez. |
| **Notebook desligado ou sem internet** | App fora do ar | Landing no Cloudflare Pages com aviso de manutenção, reinício automático dos serviços e ajustes de energia da seção 11. Os jobs pendentes ficam na fila e continuam quando o notebook volta. |
| **Superaquecimento em uso contínuo** | Lentidão e desgaste do notebook | Base com cooler, limite de carga da bateria e no máximo um render de GPU por vez. |
| **Banda de upload de casa** | Prévias lentas com muita gente usando | Proxy leve de 720p e, se crescer, vídeos exportados no R2. |
| **Prévia diferente do vídeo final** | Retrabalho e desconfiança | Mesmo JSON de estilo nas duas saídas e botão de prévia real de 5 segundos. |
| **Arquivos enormes** | Disco cheio e upload falhando | Upload retomável, limite por plano e limpeza automática de proxies antigos. |
| **FFmpeg com arquivo malicioso** | Falha de segurança | Validar com ffprobe, limitar tempo e memória do processo e rodar o worker isolado em container. |
| **Nome já registrado** | Troca de marca depois de lançada | Fazer a verificação da Fase 0 antes de qualquer material público. |

---

## 14. Como medir se está funcionando

| Métrica | Meta do MVP |
|---|---|
| Tempo da gravação ao primeiro Reel pronto | menos de 15 minutos de trabalho humano |
| Palavras corretas na transcrição | 95% ou mais em áudio de púlpito |
| Sugestões de corte aceitas sem mudança grande | 50% ou mais (Fase 2) |
| Exportações que falham | menos de 2% |
| Igrejas usando toda semana | 2 igrejas piloto por 4 semanas seguidas |

---

## 15. Primeiros passos concretos

1. Aprovar as decisões da seção 4: FastAPI, Next.js, tus e Docker.
2. Fazer a verificação de marca, domínio e @.
3. Iniciar o Git e criar a estrutura de pastas da seção 10.
4. Preparar o Nitro 5, subir o Docker Compose e confirmar a GPU dentro do container.
5. Abrir um Quick Tunnel e acessar o notebook pelo celular, fora da rede de casa.
6. Rodar o WhisperX em uma pregação real e medir tempo e qualidade. Esse teste valida a maior premissa técnica do projeto.
7. Construir a fila de jobs e o primeiro fluxo ponta a ponta: upload, transcrição e um vídeo com legenda simples.
