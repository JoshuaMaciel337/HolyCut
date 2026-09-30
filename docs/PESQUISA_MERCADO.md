# Pesquisa de mercado

Pesquisa feita em 30/09/2026 em duas partes:

- **Parte 1:** Cut.Pro e OpusClip, as ferramentas de cortes com IA mais completas.
- **Parte 2** (no fim do documento): FeedChurch, Doxus e Bíblia IA, ferramentas feitas para igrejas.

A pergunta das duas partes é a mesma: o que oferecem, o que usam por baixo e o que vale trazer para o HolyCut.

# Parte 1: Cut.Pro e OpusClip

**Como foi feita:** visitei a página inicial e as páginas dos menus e rodapés dos dois sites num navegador de verdade, com prints de cada uma, e li as fontes públicas que mostram a tecnologia: a API do Cut.Pro (a especificação OpenAPI e o `llms.txt`), as políticas de privacidade, a central de confiança do OpusClip e as vagas de emprego deles. Tudo aqui é informação pública.

## 1. A proposta de cada um

### Cut.Pro (brasileiro, lançado em janeiro de 2026)

- **Proposta:** "Link, arquivo ou live: um lugar só para criar, editar, legendar, agendar e publicar. A IA faz o trabalho pesado."
- **Público:** streamers da Twitch e do Kick, YouTubers, podcasters e agências. Tem uma página própria **para igrejas**: "Sua mensagem alcançando gente a semana toda, não só no domingo."
- **Preço:**
  - grátis: 15 créditos por mês;
  - Básico: R$ 19,90;
  - Plus: R$ 69,90;
  - Pro: R$ 119,90;
  - 1 crédito = 1 minuto de vídeo analisado, não importa quantos cortes saiam dele;
  - pagamento por PIX e Pix Automático (pelo Asaas), com nota fiscal.
- **Diferenciais:**
  - cortes da live **enquanto ela acontece**, em lotes de 10 minutos;
  - publicação em 12 redes, com o melhor horário sugerido pelo histórico da conta;
  - métricas lidas nas APIs das redes;
  - "campeonatos de cortes": a comunidade corta e disputa prêmio em dinheiro, pago por Pix;
  - app para iPhone e Android;
  - templates feitos pela comunidade;
  - API pública (44 rotas) e servidor MCP;
  - estratégias de corte escritas em linguagem natural e salvas por canal.
- **Ritmo:** 133 novidades publicadas no changelog entre maio e setembro de 2026, quase uma por dia.

### OpusClip (americano, o líder mundial)

- **Proposta:** "1 vídeo longo, 10 clipes virais. Crie 10 vezes mais rápido."
- **Porte:** mais de 10 milhões de usuários e cerca de US$ 20 milhões de receita em 2025, segundo a [Sacra](https://sacra.com/c/opusclip/).
- **Preço:**
  - grátis: 60 minutos por mês, com marca d'água;
  - Starter: US$ 15 por mês;
  - Pro: US$ 29 por mês;
  - Business: sob consulta.
- **Modelos próprios, com nome:**
  - **ClipAnything:** corte multimodal que usa imagem, som e emoção e aceita pedidos em linguagem natural ("ache o refrão");
  - **ReframeAnything:** reenquadramento que segue a pessoa ou o objeto;
  - **layouts dinâmicos:** trocam de tela cheia para tela dividida quando há duas pessoas.
- **Outros recursos:**
  - legendas animadas com "vocabulário da marca", para grafar certo os nomes próprios;
  - B-roll automático tirado do Pexels;
  - modelos de marca com abertura e encerramento;
  - agendador em 6 redes, com legenda e hashtags escritas pela IA;
  - nota de viralidade com sugestões de melhora;
  - exportação para Premiere e DaVinci em XML, com SRT e 30 s de folga em cada ponta;
  - espaço de equipe;
  - API e MCP;
  - **AI Producer**: edição por conversa, sobre a gravação real, sem avatar.
- **Página para igrejas:** "Evangelize digitalmente". Fala em sermão, culto de domingo, arrecadação e transmissão ao vivo, com chamada para ação sobreposta ao vídeo.

## 2. O que eles usam por baixo

| Parte | Cut.Pro | OpusClip | Equivalente aberto e local, para o HolyCut |
|---|---|---|---|
| Transcrição | **Transcrevo**, API brasileira: 6,34% de erro por palavra (WER) em português espontâneo, US$ 0,03 por hora de áudio | Não divulga; diz ter 97% de precisão | faster-whisper e WhisperX, `large-v3-turbo` (já no plano) |
| Escolha dos cortes, títulos e descrições | **OpenAI e Anthropic**: a política de privacidade cita o "processamento temporário" do áudio e do vídeo | "Curadoria por ChatGPT": entende o vídeo inteiro, divide em capítulos, escolhe os trechos e junta pedaços de partes diferentes. A central de confiança lista a OpenAI | LLM local no Ollama (Qwen3 ou Gemma 3), com saída em JSON Schema |
| Entender a imagem | Não divulga ("picos de energia, reação, setup e payoff") | ClipAnything-1.0, comparado com Gemini-1.5 e GPT-4V em testes de vídeo | Modelo de visão local (Qwen2.5-VL), opcional, para a nota visual |
| Reenquadramento | Segue o rosto; a pessoa escolhe quais layouts a IA pode usar; zoom automático; câmera com keyframes | ReframeAnything, com rastreamento de objetos e layouts dinâmicos | MediaPipe (no plano) sobre a nossa moldura com x, y e zoom |
| B-roll | Automático a partir da fala, mais um banco de imagens no editor | Pexels mais IA | Pexels (no plano) |
| Áudio | "Nivelar" em -16 LUFS | Realce de voz; remoção de pausas, vícios de fala e tomadas ruins | -14 LUFS (pronto); DeepFilterNet (no plano) |
| Infraestrutura | AWS, Google Cloud, Vercel e Cloudflare; Asaas e Stripe | Google Cloud, MongoDB, Redis, Python e TypeScript, banco vetorial Milvus; SOC 2 Type 2 | Nitro 5, MongoDB, Docker e túnel da Cloudflare |

Duas observações:

- **Contradição no Cut.Pro:** o `llms.txt` deles afirma que "nenhuma etapa depende de API estrangeira", mas a política de privacidade diz que o áudio e o vídeo passam por OpenAI e Anthropic. O mais provável é que a transcrição seja brasileira e a escolha dos cortes seja feita por um LLM estrangeiro.
- **Formato do corte:** os dois devolvem, para cada corte, título, uma explicação de por que o trecho vale, uma nota e o início e o fim. A API do Cut.Pro mostra os campos `title`, `description`, `rating` (0 a 10), `start_time` e `end_time`. É o mesmo formato previsto para o HolySermon.

## 3. O que o HolyCut já tem, e o que nenhum dos dois tem

**Já temos o equivalente:**
- corte de silêncios em três intensidades;
- linha do tempo com partes em qualquer ordem (o OpusClip destaca justamente "juntar trechos de partes diferentes");
- quatro proporções com zoom;
- identidade da igreja, modelos, filtros de cor e textos;
- áudio em -14 LUFS.

**O que nenhum dos dois oferece:**
- **Música com licença registrada**, com volume que abaixa sob a fala. Nenhum dos dois trata direito autoral da trilha.
- **Aprovação do pastor pelo link**, sem conta. O OpusClip tem só espaço de equipe, e o Cut.Pro tem aprovação apenas nos campeonatos.
- **Envio automático do OBS.** Os dois dependem de alguém colar um link ou enviar o arquivo.
- **Processamento local**, sem custo por minuto e com o vídeo da igreja dentro de casa.

## 4. O que vale trazer para o HolyCut

### Sem IA (dá para fazer já)

1. **Importar pelo link do YouTube ou do Google Drive.** Nos dois, "cole o link do culto" é a entrada principal, porque a maioria das igrejas transmite no YouTube. Daria para usar o yt-dlp (licença Unlicense) no worker. Cuidado: só vídeos da própria igreja, e os termos do YouTube restringem o download.
2. **Exportar para DaVinci e Premiere.** Um XML com as partes, o SRT e os trechos com folga nas pontas. Muitas equipes de mídia de igreja editam no DaVinci.
3. **Escolher a capa** a partir de um quadro do vídeo ou de uma imagem enviada, e um **QR code** para baixar o vídeo pronto no celular.
4. **Abertura, encerramento e chamada** no modelo (por exemplo "Culto domingo 19h" ou "Siga @igreja"), além do envio da **fonte própria da igreja**.
5. **Tela dividida** mostrando o pregador e o telão ao mesmo tempo, com as duas áreas escolhidas à mão. A versão automática vem depois, com IA.
6. **Publicar e agendar** nas redes. Depende das credenciais das redes: o YouTube pede OAuth do Google, e o Instagram pede um app da Meta aprovado.

### Com IA (no Nitro)

1. **Nota, título e motivo** em cada corte sugerido, no mesmo formato dos dois concorrentes.
2. **Estratégia da igreja em linguagem natural**, salva uma vez: "priorize o apelo e a oração", "foque nos testemunhos".
3. **Cortes que juntam trechos de lugares diferentes da pregação.** A estrutura de partes já existe; falta o LLM propor as partes.
4. **Vocabulário da igreja na transcrição:** o nome do pastor, da igreja, dos ministérios, os livros bíblicos. No faster-whisper isso entra por `hotwords` e `initial_prompt`.
5. **Legenda animada** com a palavra-chave em destaque, em maiúsculas e com a fonte da marca.
6. **Edição pelo texto**: apagar uma frase da transcrição corta o vídeo.
7. **B-roll automático** a partir da fala, com o LLM escolhendo a busca no Pexels.
8. **Texto do post e hashtags** para cada rede.
9. **Tradução das legendas** para espanhol e inglês. É só a legenda traduzida, não dublagem.
10. **Meta de qualidade da transcrição:** medir a taxa de erro em pregações reais e comparar com os 6,34% que a Transcrevo publica. A Transcrevo também poderia servir de plano B pago, a US$ 0,03 por hora, para quando o Nitro estiver desligado. Mas isso contraria o princípio de rodar tudo em casa, então a decisão é do dono.

### O que não fazer

- **Voz de IA, dublagem e avatar** (a locução e a dublagem do OpusClip Pro e o Agent Opus, que gera vídeos a partir de roteiro): estão fora do escopo por decisão tomada.
- **"Distração automática"** (vídeo de jogo ao lado do corte): não combina com culto.
- **Campeonatos com prêmio em dinheiro:** não se aplicam a igreja. Talvez, no futuro, uma versão sem dinheiro para os voluntários da mídia.
- **Cortes em tempo real durante o culto:** o agente do OBS com o processamento logo depois do culto já resolve, e o tempo real exigiria a GPU dedicada durante toda a transmissão.

## 5. Referências visuais (dos prints)

- **Cores:** o Cut.Pro usa tema escuro com lilás e laranja, bem perto da paleta do HolyCut. A nossa marca já está definida; serve só para confirmar que o caminho funciona nesse público.
- **Página inicial:**
  - cortes reais com as visualizações que tiveram;
  - os três passos (trazer, a IA corta, publicar);
  - uma lista de "24 coisas que deixam de ser trabalho seu";
  - uma página por público, inclusive igrejas;
  - planos com preço em real.
- **Legendas:** em maiúsculas, com fonte pesada, uma palavra-chave na cor de destaque e duas linhas no centro-baixo.
- **Editor do OpusClip:** vídeo 9:16 no centro e a transcrição ao lado, dividida em seções, onde editar o texto edita o vídeo.
- **Agendador:** calendário do mês e um compositor com legenda, hashtags e horário.

## 6. Preço (referência para a Fase 4)

- **Cut.Pro:** cobra por minuto analisado, aceita PIX e tem plano grátis permanente.
- **OpusClip:** 60 minutos por mês grátis, com marca d'água.
- **HolyCut:** como roda no próprio servidor, o custo de cada minuto a mais é praticamente zero. Isso permite, por exemplo, um plano por igreja com cultos ilimitados. A decisão fica para a Fase 4.

## Fontes

- Cut.Pro: [início](https://cut.pro/pt-BR), [para igrejas](https://cut.pro/pt-BR/solutions/churches), [preços](https://cut.pro/pt-BR/pricing), [changelog](https://cut.pro/pt-BR/changelog), [comparação com o OpusClip](https://cut.pro/pt-BR/alternatives/opusclip), [documentação da API](https://cut.pro/docs), [OpenAPI](https://api.cut.pro/api/v1/openapi.json), [llms.txt](https://cut.pro/llms.txt), [privacidade](https://cut.pro/privacy)
- Transcrevo: [llms.txt](https://transcrevo.com/llms.txt), [precisão](https://transcrevo.com/llms/accuracy.md)
- OpusClip: [início](https://www.opus.pro/pt-br), [para igrejas](https://www.opus.pro/pt-br/business/church), [ClipAnything](https://www.opus.pro/pt-br/clipanything), [AI Reframe](https://www.opus.pro/pt-br/ai-reframe), [B-roll](https://www.opus.pro/pt-br/ai-b-roll), [exportar para XML](https://www.opus.pro/pt-br/export-to-xml), [como funciona](https://www.opus.pro/pt-br/how-does-opus-clip-work), [preços](https://www.opus.pro/pricing), [MCP](https://www.opus.pro/pt-br/mcp), [central de confiança](https://trust.opus.pro/), [AI Producer](https://producer.opus.pro/)
- Sobre a OpusClip: [Sacra](https://sacra.com/c/opusclip/), [vaga de AI Engineer](https://builtinvancouver.org/job/ai-engineer/8226804)

# Parte 2: ferramentas feitas para igrejas

Pesquisa feita em 30/09/2026 com o mesmo método: páginas dos menus e rodapés, prints, políticas de privacidade e as telas dos produtos.

## 1. A proposta de cada um

### FeedChurch (brasileiro, da empresa Reddesk)

- **Proposta:** "Transforme o sermão de domingo em cortes prontos para postar". É a ferramenta mais parecida com o HolyCut.
- **Como funciona:**
  1. Cola-se o link do YouTube.
  2. A IA assiste ao culto inteiro, **separa a mensagem do louvor, dos avisos, da oração e da oferta** e corta só o ensino.
  3. Cerca de 15 minutos depois, os cortes estão prontos e renderizados. Não há tela de escolha no meio, a não ser que a pessoa queira revisar antes.
- **O que entrega:**
  - cortes verticais 9:16 e também vídeos horizontais 16:9 para o YouTube;
  - legenda embutida e o logo da igreja;
  - "ênfase, jump cuts e seguir o pregador";
  - título, descrição e hashtags escritos pela IA.
- **Piloto automático:**
  - o canal da igreja no YouTube é monitorado o tempo todo;
  - quando a live do culto termina, os cortes começam sozinhos;
  - publica no YouTube no horário escolhido para cada corte, com aprovação antes, se a igreja quiser;
  - avisa por WhatsApp e por e-mail;
  - Instagram e TikTok estão "em construção".
- **Preço:**
  - R$ 9,99 por mês (20 vídeos);
  - R$ 19,90 (50 vídeos, com o piloto automático);
  - R$ 50 (200 vídeos).
- **Ponto de atenção:** a vitrine deles corta pregações públicas de pastores conhecidos e publica no canal do próprio FeedChurch, "com crédito". Os termos de uso, porém, proíbem o cliente de processar conteúdo de terceiros sem autorização. O HolyCut deve processar só o conteúdo da própria igreja.

### Doxus

- **Proposta:** "O sermão termina. A Palavra continua." Transforma a transmissão da igreja em um **acervo de sermões** público, gratuito para os membros, sem login.
- **O que cada sermão ganha:**
  - transcrição completa, com os versículos virando link e o texto sincronizado com o vídeo;
  - resumo da mensagem, com o aviso "Gerado por IA — pode conter erros";
  - temas, palavras-chave e personagens bíblicos;
  - **guia de estudo para células** (perguntas para discussão, versículos-chave, aplicação prática e oração), também em PDF;
  - tradução para inglês e espanhol;
  - página própria indexada no Google, com dados estruturados;
  - sermões parecidos de outros canais.
- **Ao vivo:**
  - enquanto o pastor prega, os membros leem a transcrição com poucos segundos de atraso;
  - os versículos citados aparecem como cartões;
  - quem chega atrasado vê um resumo do que já passou.
- **Busca:** em linguagem natural ("sermões sobre fé em tempos difíceis"), por versículo, tema ou personagem bíblico, em todo o acervo.
- **Preço:** gratuito para os membros; as igrejas começam com R$ 200 em créditos.
- **Manifesto:** vale ler inteiro ([doxus.org/pt/manifesto](https://www.doxus.org/pt/manifesto)).
  - A IA nunca gera sermão, só organiza o que foi pregado.
  - Quando não tem confiança no que extraiu, a IA omite em vez de inventar.
  - A transcrição não corrige o português do pastor.
  - Não há chatbot teológico nem avatar.
  - A igreja é dona do conteúdo e pode levar tudo em formato aberto.

### Bíblia IA (brasileiro, APUS Digital)

- **Proposta:** um app de estudo da Bíblia com IA.
- **O que tem:**
  - "Pastor Virtual 24h", que responde perguntas teológicas;
  - biblioteca com várias traduções;
  - posts inspiracionais diários;
  - grupos de estudo com chat;
  - "ilustrações bíblicas" geradas por IA.
- **Preço:** grátis, R$ 4,99 por mês (Premium) ou R$ 49,99 (Igreja, até 100 contas).
- **O que não copiar:** nas telas do app, a lista de chats mistura pastores reais, identificados pela denominação, com **personagens de IA com rosto e nome de gente** ("Bia Santos (IA)", "Juliana Silva (IA)"). Isso esbarra na exclusão de avatares do HolyCut e é justamente o que o Doxus recusa no manifesto.

## 2. O que eles usam por baixo

| | FeedChurch | Doxus | Bíblia IA |
|---|---|---|---|
| IA | **OpenAI** ("análise de transcrições de vídeo") | **OpenAI e Deepgram** ("transcrições e guias de estudo"; a Deepgram faz transcrição em tempo real) | Não divulga |
| Transcrição | Não divulga | Deepgram (muito provavelmente também a ao vivo) | Não se aplica |
| Vídeo | YouTube como fonte; publica no YouTube por OAuth do Google | YouTube como fonte e player embutido: o Doxus não guarda o vídeo | Não se aplica |
| Outros | Stripe; integração com o TikTok citada na política | Clerk (login), Stripe, dados estruturados (schema.org) e sitemap de vídeo. As imagens do site foram geradas no Nano Banana, do Google: um texto de preenchimento ficou esquecido na página | Site feito no SitePad |

Os três usam IA paga de fora. O equivalente local para o HolyCut: Whisper no lugar da Deepgram e da transcrição da OpenAI, e um LLM no Ollama no lugar do GPT, para separar os blocos, resumir e escrever os guias. Tudo sem custo por uso.

## 3. Por que vale a pena: a transcrição do culto já vai existir

A parte cara do trabalho é a transcrição do culto inteiro, e o HolyCut já vai fazê-la para os cortes. Com ela em mãos, o mesmo LLM local gera o resto em poucos minutos, sem custo a mais:

| Ideia | De onde veio | Precisa de | Custo |
|---|---|---|---|
| **Separar o culto em blocos** (louvor, avisos, oração, oferta, pregação) e cortar só a pregação | FeedChurch | Detecção de música e fala (Silero VAD, que roda na CPU) e o LLM para nomear os blocos | Zero |
| **Vídeo horizontal só da pregação**, sem louvor nem avisos, para o YouTube | FeedChurch | Os blocos acima. A versão manual, em que a pessoa marca a pregação, dá para fazer já | Zero |
| **Resumo, temas, palavras-chave, personagens e versículos citados** | Doxus | Transcrição e LLM | Zero |
| **Guia de estudo para células** (perguntas, versículos-chave, aplicação, oração), com PDF | Doxus | Transcrição e LLM | Zero |
| **Monitorar o canal do YouTube** e começar sozinho quando a live termina | FeedChurch | O feed RSS público do canal, sem chave, e a importação pelo link | Zero |
| **Publicar no YouTube** no horário escolhido | FeedChurch | OAuth do Google (as credenciais têm de ser criadas pelo dono) | Zero |
| **Títulos com gancho** (frases fortes da própria pregação) | FeedChurch | LLM, com a regra de fidelidade abaixo | Zero |
| **Busca no acervo da igreja** por versículo, tema ou pergunta | Doxus | Embeddings locais (por exemplo, via Ollama). O acervo de uma igreja cabe na memória | Zero |
| **Tradução** da transcrição e das legendas | Doxus | LLM local | Zero |
| **Transcrição ao vivo** durante o culto (acessibilidade para quem não ouve bem) | Doxus | Whisper em streaming na GPU do Nitro durante todo o culto | Zero em dinheiro, mas ocupa a GPU. Fica para depois |
| **Aviso por WhatsApp** quando os cortes ficam prontos | FeedChurch | A API oficial do WhatsApp **é paga** (a Meta cobra por conversa) | Evitar. O link de WhatsApp manual (`wa.me`), que já usamos na aprovação, é grátis |

## 4. Um princípio para adotar (sugestão)

O manifesto do Doxus resolve de antemão o maior risco de usar IA em conteúdo de igreja: distorcer o que o pastor pregou. A sugestão é adotar regras parecidas no HolyCut:

- **A IA só organiza o que foi pregado.** Título, resumo, guia e legenda do post saem da fala real. Quando a IA não tem confiança, ela omite em vez de inventar.
- **Nada de gancho que distorça.** O título pode ser forte, desde que seja uma frase ou ideia que o pastor de fato disse naquele trecho.
- **Aviso "gerado por IA — revise"** em todo texto automático, e o editor sempre pode corrigir.
- **A igreja é dona de tudo:** exportação em formato aberto (transcrição em SRT/TXT, guia em PDF, vídeos).
- **Só conteúdo da própria igreja:** nada de cortar pregação de outras igrejas.
- Continuam valendo as exclusões já decididas: sem avatar, sem voz de IA, sem chatbot que se passe por pastor.

## 5. O que não fazer

- **"Pastor virtual", personagens de IA e ilustrações geradas** (Bíblia IA): esbarram nas exclusões e no princípio acima.
- **Cortar sermões de outras igrejas** para vitrine (FeedChurch).
- **WhatsApp pela API oficial:** é pago. Use o link manual.
- **Virar uma plataforma pública de sermões**, como o Doxus. O HolyCut é a ferramenta da equipe de mídia. Uma página pública do sermão pode vir como extra, dentro da identidade da própria igreja, mas não é o foco.

## Fontes

- FeedChurch: [início](https://feedchurch.com.br/en/), [cortes](https://feedchurch.com.br/cortes), [guias](https://feedchurch.com.br/en/guides/), [privacidade](https://feedchurch.com.br/privacidade.html), [termos](https://feedchurch.com.br/termos.html)
- Doxus: [início](https://www.doxus.org/pt), [para igrejas](https://www.doxus.org/pt/igrejas), [recursos](https://www.doxus.org/pt/recursos), [guias de estudo](https://www.doxus.org/pt/recursos/estudos), [ao vivo](https://www.doxus.org/pt/recursos/ao-vivo), [transcrições](https://www.doxus.org/pt/recursos/transcricoes), [manifesto](https://www.doxus.org/pt/manifesto), [história](https://www.doxus.org/pt/historia), [privacidade](https://www.doxus.org/pt/privacidade), [exemplo de sermão](https://app.doxus.org/pt/inconformados-no-altar)
- Bíblia IA: [início](https://biblia-ia.com/site/), [planos](https://biblia-ia.com/site/planos/index.html), [sobre](https://biblia-ia.com/site/sobre/index.html)
