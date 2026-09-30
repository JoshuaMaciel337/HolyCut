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

export type Projeto = {
  id: string;
  midia_id: string;
  nome: string;
  tipo: string;
  proporcao: Proporcao;
  trecho: { inicio: number; fim: number };
  silencios: { intensidade: Intensidade | null };
  enquadramento: { x: number; y: number; zoom: number };
  audio: { normalizar: boolean };
  versao: number;
  criado_em: string;
  atualizado_em: string;
};

export type Exportacao = {
  id: string;
  projeto_id: string;
  midia_id: string;
  nome: string;
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
