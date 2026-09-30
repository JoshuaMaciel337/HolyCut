// Contas das partes do vídeo (a linha do tempo). As partes estão no tempo da gravação;
// o "vídeo final" é a emenda delas, na ordem da lista, sem os silêncios cortados.
// O render faz as mesmas contas em core/utils/render.py.
import type { Parte } from "@/lib/tipos";

export const DURACAO_MINIMA_PARTE = 1;
export const MAXIMO_PARTES = 30;

type Intervalo = [number, number];

/** Soma das partes como foram escolhidas, antes do corte de silêncios. */
export function duracaoDasPartes(partes: Parte[]): number {
  return partes.reduce((soma, parte) => soma + (parte.fim - parte.inicio), 0);
}

/** Cortes de silêncio que caem dentro da parte, recortados nas bordas dela. */
export function cortesNaParte(cortes: Intervalo[], parte: Parte): Intervalo[] {
  return cortes
    .filter(([a, b]) => b > parte.inicio && a < parte.fim)
    .map(([a, b]) => [Math.max(a, parte.inicio), Math.min(b, parte.fim)] as Intervalo);
}

/** Quanto a parte dura no vídeo final, já sem os cortes. */
export function duracaoFinalDaParte(parte: Parte, cortes: Intervalo[]): number {
  return parte.fim - parte.inicio - cortes.reduce((soma, [a, b]) => soma + (b - a), 0);
}

/** Posição (em segundos do vídeo final, a partir do começo da parte) de um instante da gravação. */
export function posicaoNaParte(parte: Parte, cortes: Intervalo[], instante: number): number {
  const limitado = Math.min(Math.max(instante, parte.inicio), parte.fim);
  return limitado - parte.inicio - cortes.reduce((soma, [a, b]) => soma + Math.max(0, Math.min(b, limitado) - a), 0);
}

/** Instante da gravação para uma posição dentro da parte (o inverso de posicaoNaParte). */
export function instanteNaParte(parte: Parte, cortes: Intervalo[], posicao: number): number {
  let instante = parte.inicio;
  let restante = Math.max(posicao, 0);
  for (const [a, b] of cortes) {
    if (instante + restante <= a) break;
    restante -= a - instante;
    instante = b;
  }
  return Math.min(instante + restante, parte.fim);
}

export function novoIdDeParte(partes: Parte[]): string {
  let numero = partes.length + 1;
  while (partes.some((parte) => parte.id === `p${numero}`)) numero++;
  return `p${numero}`;
}

/** Move o item de uma posição para outra, sem mudar a lista original. */
export function mover<T>(lista: T[], de: number, para: number): T[] {
  const nova = [...lista];
  const [item] = nova.splice(de, 1);
  nova.splice(para, 0, item);
  return nova;
}
