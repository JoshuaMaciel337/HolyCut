// Formatos que a API devolve. Espelham apps/api/esquemas.py.

export type Usuario = {
  id: string;
  nome: string;
  email: string;
  papel: string;
};

export type Organizacao = {
  id: string;
  nome: string;
  slug: string;
};

export type Sessao = {
  usuario: Usuario;
  organizacao: Organizacao;
};

export type StatusJob = "pendente" | "executando" | "concluido" | "erro";

export type Limpeza = {
  status: string;
  progresso: number;
  mensagem: string;
  erro: string | null;
};

export type CorteSugestao = {
  id: string;
  titulo: string;
  motivo: string;
  nota: number;
  partes: { inicio: number; fim: number }[];
  legenda_post: string;
  hashtags: string[];
};

export type Sugestoes = {
  status: string;
  progresso: number;
  mensagem: string;
  erro: string | null;
  gerado_por_ia: boolean;
  cortes: CorteSugestao[];
};

export type Job = {
  id: string;
  tipo: string;
  recurso: "cpu" | "gpu";
  status: StatusJob;
  progresso: number;
  mensagem: string;
  tentativas: number;
  max_tentativas: number;
  erro: string | null;
  entrada: Record<string, unknown>;
  saida: Record<string, unknown> | null;
  criado_em: string;
  atualizado_em: string;
  iniciado_em: string | null;
  concluido_em: string | null;
  disponivel_em: string | null;
};

export type StatusMidia = "enviando" | "processando" | "pronta" | "erro";

export type Miniaturas = {
  total: number;
  colunas: number;
  linhas: number;
  intervalo: number;
  largura: number;
  altura: number;
};

export type Midia = {
  id: string;
  nome: string;
  nome_original: string;
  status: StatusMidia;
  tamanho_total: number;
  bytes_recebidos: number;
  duracao: number | null;
  video: { codec: string; largura: number; altura: number; fps: number | null; rotacao: number } | null;
  audio: { codec: string; canais: number; taxa: number } | null;
  miniaturas: Miniaturas | null;
  arquivos: string[];
  /** A ficha do culto no acervo. O título é o próprio nome. */
  ficha: FichaCulto;
  /** Onde a mensagem começa e termina. A marcação da pessoa nunca é trocada pela da IA. */
  pregacao: Pregacao | null;
  /** De onde a gravação veio, quando foi importada pelo link. */
  importacao: { origem: "youtube" | "drive"; url: string; titulo: string } | null;
  /** Muda quando o pôster e o banner são redesenhados. */
  capa_versao: number | null;
  capa_personalizada: boolean;
  erro: string | null;
  processamento: { status: StatusJob; progresso: number; mensagem: string } | null;
  criado_em: string;
  atualizado_em: string;
  enviado_em: string | null;
};

/** O canal da igreja no YouTube e o monitor que importa cada live que termina. */
export type CanalYoutube = {
  configurado: boolean;
  canal: string;
  id: string | null;
  handle: string | null;
  monitorar: boolean;
  ultima_verificacao: string | null;
  ultimo_erro: string | null;
};

export type Pregacao = { inicio: number; fim: number; origem: "ia" | "pessoa" };

export type TipoBloco = "louvor" | "oracao" | "avisos" | "oferta" | "ceia" | "pregacao" | "outro";

/** Um bloco do culto. A frase é o começo do que foi dito nele. */
export type Bloco = { inicio: number; fim: number; tipo: TipoBloco; frase: string };

export type Blocos = {
  status: "ausente" | "pendente" | "executando" | "pronta" | "erro";
  progresso: number;
  mensagem: string;
  erro: string | null;
  gerado_por_ia: boolean;
  /** Falso quando os nomes vieram só das palavras-chave. */
  nomes_pelo_modelo: boolean;
  blocos: Bloco[];
  /** A pregação que a análise encontrou. */
  pregacao: { inicio: number; fim: number } | null;
};

export type Transcricao = {
  status: "ausente" | "pendente" | "executando" | "pronta" | "erro";
  progresso: number;
  mensagem: string;
  erro: string | null;
  gerado_por_ia: boolean;
  idioma: string | null;
  modelo: string | null;
  segmentos: {
    id: string;
    inicio: number;
    fim: number;
    texto: string;
  }[];
  versiculos: { referencia: string; citacao: string; inicio: number; fim: number }[];
};

export type QuadroRosto = { t: number; x: number; y: number; zoom: number };

export type Rosto = {
  status: string;
  progresso: number;
  mensagem: string;
  erro: string | null;
  quadros: QuadroRosto[];
};

export type Momento = {
  inicio: number;
  fim: number;
  energia: number;
  nota: number | null;
  assunto: string | null;
};

export type Momentos = {
  status: string;
  progresso: number;
  mensagem: string;
  erro: string | null;
  gerado_por_ia: boolean;
  momentos: Momento[];
  cenas: number[];
};

/** Uma frase como o pregador disse, com o segundo da gravação em que aparece. */
export type TrechoDito = {
  texto: string;
  inicio: number;
  fim: number | null;
};

/** O HolyStudy: tudo conferido contra a fala; o que não foi dito fica de fora. */
export type Estudo = {
  status: string;
  progresso: number;
  mensagem: string;
  erro: string | null;
  gerado_por_ia: boolean;
  resumo: TrechoDito[];
  temas: string[];
  personagens: string[];
  versiculos_chave: { referencia: string; inicio: number; citacao: string; vezes: number }[];
  perguntas: { pergunta: string; base: TrechoDito }[];
  aplicacoes: TrechoDito[];
  /** Convite fixo: a oração não é escrita pela IA. */
  oracao: string;
};

export type FichaCulto = {
  /** AAAA-MM-DD */
  data: string;
  pregador: string;
  serie: string;
  descricao: string;
};

/** Um culto nas fileiras do acervo. */
export type CultoResumo = FichaCulto & {
  id: string;
  titulo: string;
  duracao: number | null;
  video: boolean;
  capa_versao: number | null;
  cortes: number;
  em_edicao: number;
};

export type Acervo = {
  cultos: CultoResumo[];
  destaque: string | null;
  fileiras: { id: string; titulo: string; ids: string[] }[];
  series: string[];
  pregadores: string[];
  preparando: number;
};

export type Intensidade = "leve" | "media" | "forte";

export type Silencios = {
  intensidade: Intensidade;
  limiar_db: number;
  duracao_minima: number;
  margem: number;
  silencios: [number, number][];
  tempo_cortado: number;
  duracao_final: number;
};

export type Proporcao = "9:16" | "4:5" | "1:1" | "16:9";

export type Identidade = {
  nome_exibicao: string;
  instagram: string;
  cor_destaque: string;
  logo: boolean;
  estrategia: string;
  atualizado_em: string | null;
};

export type PosicaoLogo = "topo_esquerda" | "topo_direita" | "base_esquerda" | "base_direita";

export type Marca = {
  logo: boolean;
  posicao: PosicaoLogo;
  tamanho: number;
  opacidade: number;
  /** Centro arrastado na prévia (0 a 1 da moldura). Sem ele, vale a posição pronta. */
  x?: number | null;
  y?: number | null;
  /** Graus, no sentido do relógio. */
  rotacao?: number;
};

export type EstiloTexto = "destaque" | "limpo" | "manuscrito";
export type PosicaoTexto = "topo" | "centro" | "base";

export type TextoProjeto = {
  id: string;
  tipo: "titulo" | "frase" | "versiculo";
  texto: string;
  referencia: string;
  estilo: EstiloTexto;
  posicao: PosicaoTexto;
  /** Segundos no vídeo final. */
  inicio: number;
  /** null: até o fim do vídeo. */
  fim: number | null;
  /** Escala da fonte, de 0,5 a 2. */
  tamanho: number;
  /** Centro arrastado na prévia (0 a 1 da moldura). Sem ele, vale a posição pronta. */
  x?: number | null;
  y?: number | null;
  /** Graus, no sentido do relógio. */
  rotacao?: number;
};

export type Fundo = {
  /** 0 a 0,8: quanto de preto por cima do vídeo. */
  escurecer: number;
  /** 0 a 30: desfoque, em pixels do vídeo final. */
  desfoque: number;
};

export type FiltroId = "natural" | "quente" | "frio" | "cinema" | "pb" | "vivo";

export type Cor = {
  filtro: FiltroId;
  /** 0 a 1. */
  intensidade: number;
};

export type OperacaoCor = { tipo: "matriz"; valores: number[][] } | { tipo: "contraste"; valor: number };

export type FiltroCor = {
  id: FiltroId;
  nome: string;
  operacoes: OperacaoCor[];
};

export type ChaveEnvio = {
  id: string;
  nome: string;
  /** Começo da chave, para reconhecer na lista. */
  inicio: string;
  criado_em: string;
  ultimo_uso_em: string | null;
};

export type ChaveEnvioCriada = ChaveEnvio & {
  /** A chave inteira. Só vem na resposta da criação. */
  chave: string;
};

export type LicencaMusica = "propria" | "dominio_publico" | "cc_by" | "licenciada";

export type Musica = {
  id: string;
  titulo: string;
  artista: string;
  licenca: LicencaMusica;
  licenca_nome: string;
  atribuicao: string;
  fonte: string;
  status: "aguardando_arquivo" | "processando" | "pronta" | "erro";
  duracao: number | null;
  erro: string | null;
  criado_em: string;
};

export type MusicaProjeto = {
  /** null: sem música. */
  id: string | null;
  /** 0 a 1. */
  volume: number;
  abaixar_na_fala: boolean;
  /** Segundo da música em que o vídeo começa. */
  inicio: number;
};

export type Modelo = {
  id: string;
  nome: string;
  descricao: string;
  pronto: boolean;
  fundo: Fundo;
  cor: Cor;
  marca: Marca;
  textos: TextoProjeto[];
};

/** Uma parte da gravação que entra no vídeo. As partes seguem a ordem da lista. */
export type Parte = {
  id: string;
  inicio: number;
  fim: number;
};

export type PresetLegenda = "clean" | "karaoke" | "destaque" | "digno";
export type PosicaoLegenda = "base" | "centro";

export type NivelVicio = "leve" | "media" | "forte";

export type Legenda = {
  ativa: boolean;
  preset: PresetLegenda;
  palavras_por_bloco: number;
  posicao: PosicaoLegenda;
  /** Desligado quando null. Leve, médio ou forte tiram vícios de fala sozinhos. */
  vicios: NivelVicio | null;
  /** Palavra → texto da legenda. A transcrição original não muda. */
  edicoes: Record<string, string>;
  /** Palavras tiradas do vídeo. */
  apagadas: string[];
  /** Vícios que a pessoa devolveu para o vídeo. */
  mantidas: string[];
};

/** Palavra da transcrição, no tempo da gravação, para editar pelo texto. */
export type PalavraFala = {
  id: string;
  texto: string;
  inicio: number;
  fim: number;
  vicio: NivelVicio | null;
  segmento: string;
};

export type PalavraLegenda = {
  id: string;
  texto: string;
  inicio: number;
  fim: number;
  destaque: boolean;
};

export type BlocoLegenda = {
  inicio: number;
  fim: number;
  palavras: PalavraLegenda[];
};

/** Blocos no tempo do vídeo final. Os mesmos que o render queima no ASS. */
export type PreviaLegenda = {
  ativa: boolean;
  preset: PresetLegenda;
  posicao: PosicaoLegenda;
  palavras_por_bloco: number;
  cor_destaque: string;
  cor_dourada: string;
  tem_transcricao: boolean;
  blocos: BlocoLegenda[];
  palavras: PalavraFala[];
};

export type Projeto = {
  id: string;
  midia_id: string;
  nome: string;
  tipo: "reel" | "story" | "mensagem";
  modelo_id: string | null;
  proporcao: Proporcao;
  partes: Parte[];
  silencios: { intensidade: Intensidade | null };
  enquadramento: { x: number; y: number; zoom: number; seguir_rosto: boolean };
  audio: { normalizar: boolean; limpeza: boolean };
  marca: Marca;
  textos: TextoProjeto[];
  fundo: Fundo;
  cor: Cor;
  musica: MusicaProjeto;
  legenda: Legenda;
  publicacao?: { legenda: string; hashtags: string[]; gerado_por_ia: boolean } | null;
  versao: number;
  criado_em: string;
  atualizado_em: string;
};

export type Aprovacao = {
  status: "pendente" | "aprovado" | "ajustes";
  /** Para quem o pedido foi feito, ex.: Pr. João. */
  para: string;
  pedido_em: string;
  expira_em: string;
  /** Pedido sem resposta que passou da validade (7 dias). */
  expirada: boolean;
  respondido_por: string | null;
  comentario: string | null;
  respondido_em: string | null;
};

/** O que quem aprova vê pelo link, sem conta. */
export type AprovacaoPublica = {
  igreja: string;
  nome: string;
  formato: "video" | "imagem";
  duracao: number | null;
  largura: number;
  altura: number;
  arquivos: string[];
  aprovacao: Aprovacao;
};

export type Exportacao = {
  id: string;
  projeto_id: string;
  midia_id: string;
  nome: string;
  formato: "video" | "imagem";
  instante: number;
  status: "processando" | "pronta" | "erro";
  processamento: { status: StatusJob; progresso: number; mensagem: string } | null;
  duracao: number | null;
  tamanho: number | null;
  largura: number;
  altura: number;
  arquivos: string[];
  erro: string | null;
  criado_em: string;
  concluido_em: string | null;
  aprovacao: Aprovacao | null;
  /** Muda quando a capa é trocada: vai na URL da capa para o navegador buscar a nova. */
  capa_versao: number;
};

export type FormaDeOnda = {
  versao: number;
  picos_por_segundo: number;
  picos: number[];
};

export type Worker = {
  id: string;
  recursos: string[];
  tipos: string[];
  iniciado_em: string | null;
  visto_em: string;
};

export type Sistema = {
  mongo: boolean;
  modo_ia: string;
  workers: Worker[];
};
