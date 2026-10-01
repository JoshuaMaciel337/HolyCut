// Quais palavras saem do vídeo. A mesma regra está em core/modelos/fala.py:
// apagada sai; correção fica; vício sai se a intensidade alcança e a pessoa não devolveu.
// A classificação (leve, médio, forte) vem do servidor, no campo vicio.

import type { Legenda, NivelVicio, PalavraFala } from "@/lib/tipos";

const ORDEM: Record<NivelVicio, number> = { leve: 1, media: 2, forte: 3 };
const FOLGA_ENTRE_CORTES = 0.08;

export function palavraCortada(palavra: PalavraFala, legenda: Legenda): boolean {
  if (legenda.apagadas.includes(palavra.id)) return true;
  if (Object.prototype.hasOwnProperty.call(legenda.edicoes, palavra.id)) return false;
  if (legenda.mantidas.includes(palavra.id)) return false;
  if (!legenda.vicios || !palavra.vicio) return false;
  return ORDEM[palavra.vicio] <= ORDEM[legenda.vicios];
}

export function fundirCortes(cortes: [number, number][]): [number, number][] {
  const ordenados = cortes
    .filter(([inicio, fim]) => fim > inicio)
    .map(([inicio, fim]) => [Math.round(inicio * 100) / 100, Math.round(fim * 100) / 100] as [number, number])
    .sort((um, outro) => um[0] - outro[0] || um[1] - outro[1]);
  const fundidos: [number, number][] = [];
  for (const [inicio, fim] of ordenados) {
    const ultimo = fundidos[fundidos.length - 1];
    if (ultimo && inicio <= ultimo[1] + FOLGA_ENTRE_CORTES) ultimo[1] = Math.max(ultimo[1], fim);
    else fundidos.push([inicio, fim]);
  }
  return fundidos;
}

export function cortesDaFala(palavras: PalavraFala[], legenda: Legenda): [number, number][] {
  const brutos = palavras.filter((palavra) => palavraCortada(palavra, legenda)).map((palavra) => [palavra.inicio, palavra.fim] as [number, number]);
  return fundirCortes(brutos);
}

export function textoDaPalavra(palavra: PalavraFala, legenda: Legenda): string {
  return legenda.edicoes[palavra.id] ?? palavra.texto;
}
