// Endereços das capas do acervo e a data do culto por extenso.
// As capas mudam quando a ficha muda: a versão vai no endereço para o navegador buscar a nova.

export function urlPoster(midiaId: string, versao: number | null): string {
  return `/api/midias/${midiaId}/arquivos/poster.jpg?v=${versao ?? 0}`;
}

export function urlBanner(midiaId: string, versao: number | null): string {
  return `/api/midias/${midiaId}/arquivos/banner.jpg?v=${versao ?? 0}`;
}

const MESES = ["jan.", "fev.", "mar.", "abr.", "mai.", "jun.", "jul.", "ago.", "set.", "out.", "nov.", "dez."];

/** "2026-08-15" → "15 de ago. de 2026". */
export function dataDoCulto(dataIso: string): string {
  const [ano, mes, dia] = dataIso.split("-").map(Number);
  if (!ano || !mes || !dia) return "";
  return `${dia} de ${MESES[mes - 1]} de ${ano}`;
}

/** Busca simples do acervo: título, pregador, série e descrição, sem acento e sem caixa. */
export function normalizarBusca(texto: string): string {
  return texto
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
}
