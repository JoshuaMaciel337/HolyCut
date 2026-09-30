// Mesma conta de core/modelos/projeto.py (calcular_recorte), para a prévia bater com o vídeo final.

import type { Proporcao } from "@/lib/tipos";

export const PROPORCOES: Record<Proporcao, { largura: number; altura: number; rotulo: string }> = {
  "9:16": { largura: 1080, altura: 1920, rotulo: "Reels e Stories" },
  "4:5": { largura: 1080, altura: 1350, rotulo: "Feed" },
  "1:1": { largura: 1080, altura: 1080, rotulo: "Quadrado" },
  "16:9": { largura: 1920, altura: 1080, rotulo: "YouTube" },
};
export const ZOOM_MAXIMO = 3;

export type Recorte = { x: number; y: number; largura: number; altura: number };

function par(valor: number): number {
  return Math.max(Math.floor(valor / 2) * 2, 2);
}

export function calcularRecorte(
  largura: number,
  altura: number,
  proporcao: Proporcao,
  x = 0.5,
  y = 0.5,
  zoom = 1,
): Recorte {
  const alvo = PROPORCOES[proporcao];
  const razao = alvo.largura / alvo.altura;
  let recorteLargura: number;
  let recorteAltura: number;
  if (largura / altura > razao) {
    recorteLargura = altura * razao;
    recorteAltura = altura;
  } else {
    recorteLargura = largura;
    recorteAltura = largura / razao;
  }
  const z = Math.min(Math.max(zoom, 1), ZOOM_MAXIMO);
  recorteLargura = par(recorteLargura / z);
  recorteAltura = par(recorteAltura / z);
  const esquerda = Math.min(Math.max(x * largura - recorteLargura / 2, 0), largura - recorteLargura);
  const topo = Math.min(Math.max(y * altura - recorteAltura / 2, 0), altura - recorteAltura);
  return {
    x: esquerda >= 2 ? par(esquerda) : 0,
    y: topo >= 2 ? par(topo) : 0,
    largura: recorteLargura,
    altura: recorteAltura,
  };
}

/** Faixa de centros que mudam o recorte: fora dela, o recorte já encostou na borda. */
export function limitesDoCentro(tamanho: number, recorte: number): [number, number] {
  const meio = recorte / 2 / tamanho;
  return [meio, 1 - meio];
}
