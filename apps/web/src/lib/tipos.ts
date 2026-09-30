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
  erro: string | null;
  processamento: { status: StatusJob; progresso: number; mensagem: string } | null;
  criado_em: string;
  atualizado_em: string;
  enviado_em: string | null;
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
  atualizado_em: string | null;
};

export type PosicaoLogo = "topo_esquerda" | "topo_direita" | "base_esquerda" | "base_direita";

export type Marca = {
  logo: boolean;
  posicao: PosicaoLogo;
  tamanho: number;
  opacidade: number;
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

export type Projeto = {
  id: string;
  midia_id: string;
  nome: string;
  tipo: "reel" | "story";
  modelo_id: string | null;
  proporcao: Proporcao;
  partes: Parte[];
  silencios: { intensidade: Intensidade | null };
  enquadramento: { x: number; y: number; zoom: number };
  audio: { normalizar: boolean };
  marca: Marca;
  textos: TextoProjeto[];
  fundo: Fundo;
  cor: Cor;
  musica: MusicaProjeto;
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
