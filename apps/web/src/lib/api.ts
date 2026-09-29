// Cliente da API. Tudo passa por /api no mesmo endereço do site,
// então o cookie de sessão vai junto sem configuração extra.

export class ErroApi extends Error {
  constructor(
    public status: number,
    mensagem: string,
  ) {
    super(mensagem);
    this.name = "ErroApi";
  }
}

type Opcoes = {
  metodo?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  corpo?: unknown;
};

function mensagemPadrao(status: number): string {
  if (status >= 500) {
    return "O servidor do HolyCut está fora do ar no momento. Tente de novo em alguns minutos.";
  }
  if (status === 401) return "Faça login para continuar.";
  if (status === 404) return "Não encontrado.";
  return "Algo deu errado. Tente de novo.";
}

export async function chamarApi<T>(caminho: string, opcoes: Opcoes = {}): Promise<T> {
  const temCorpo = opcoes.corpo !== undefined;
  let resposta: Response;
  try {
    resposta = await fetch(`/api${caminho}`, {
      method: opcoes.metodo ?? "GET",
      headers: temCorpo ? { "Content-Type": "application/json" } : undefined,
      body: temCorpo ? JSON.stringify(opcoes.corpo) : undefined,
      credentials: "same-origin",
      cache: "no-store",
    });
  } catch {
    throw new ErroApi(0, "Sem conexão com o servidor. Verifique sua internet.");
  }

  if (resposta.status === 204) return undefined as T;
  const dados = await resposta.json().catch(() => null);
  if (!resposta.ok) {
    const detalhe = typeof dados?.detail === "string" ? dados.detail : mensagemPadrao(resposta.status);
    throw new ErroApi(resposta.status, detalhe);
  }
  return dados as T;
}

/** Aceita só caminhos internos, para o parâmetro ?proximo= não virar redirecionamento para fora. */
export function destinoSeguro(proximo: string | null, padrao = "/app"): string {
  if (!proximo || !proximo.startsWith("/") || proximo.startsWith("//")) return padrao;
  return proximo;
}
