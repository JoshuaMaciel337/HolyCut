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
  saida: Record<string, unknown> | null;
  criado_em: string;
  atualizado_em: string;
  iniciado_em: string | null;
  concluido_em: string | null;
  disponivel_em: string | null;
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
