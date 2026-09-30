# 0001 — Upload tus implementado na própria API

**Data:** 30/09/2026
**Situação:** aceita

## Contexto

O plano aprovou o protocolo **tus** para enviar gravações de vários GB, com retomada quando a internet cai. A proposta original era usar o **tusd** (servidor oficial em Go) como um serviço a mais no Docker, com o **Uppy** no navegador.

Três pontos pesaram contra o tusd:

- **Autenticação.** O tusd não conhece a sessão do HolyCut. Seria preciso configurar ganchos HTTP para ele perguntar à API se cada envio pode começar e avisar quando terminar.
- **Um serviço a mais**, com volume, porta e configuração próprios, para uma parte pequena do protocolo.
- **Estado espalhado.** O progresso de um envio ficaria no tusd, e a mídia no Mongo.

## Decisão

- A API implementa o núcleo do tus 1.0.0 e as extensões `creation` e `termination` em `apps/api/rotas/uploads.py`, com cerca de 250 linhas.
- Cada envio já nasce como uma mídia no Mongo, com status `enviando`. O último pedaço coloca a mídia na fila de ingestão.
- O navegador usa o **tus-js-client**, a mesma biblioteca que o Uppy usa por baixo, com uma interface própria nas cores da marca.
- Os pedaços têm **8 MB**. Isso fica abaixo do limite de 10 MB que o Next.js aplica ao corpo das requisições e longe dos 100 MB por requisição do plano grátis da Cloudflare.
- Antes de aceitar um envio, a API confere o espaço em disco e recusa o arquivo se sobrarem menos de 2 GB livres (`ESPACO_MINIMO_LIVRE_GB`).

## Consequências

- O envio usa o mesmo cookie de sessão de todo o site e funciona igual em casa, no túnel e em produção.
- A posição do envio é sempre o tamanho real do arquivo no disco. Um pedaço repetido é recusado com `409` e a posição certa, e o cliente continua dali.
- Um envio só pode ter um pedaço em andamento por vez. A trava fica na memória, o que basta com um único processo da API. Com várias réplicas, a trava precisa ir para o Mongo.
- Se o armazenamento for para S3 ou R2, `uploads.py` passa a usar upload multipart. O resto do sistema só conhece chaves de armazenamento e não muda.
- Envios abandonados ficam como mídias `enviando`. Uma limpeza periódica fica para depois.
