import type { Recorte } from "@/lib/recorte";

// A mesma conta de core/modelos/rosto.py (caixa_contorno).
export const FRACAO_LARGURA_CONTORNO = 0.22;
export const FRACAO_ALTURA_CONTORNO = 0.32;

export type CaixaContorno = { x: number; y: number; w: number; h: number };

/** Frações do vídeo final. O centro é o rosto; o tamanho é a fração da gravação. */
export function caixaContorno(
  x: number,
  y: number,
  recorte: Recorte,
  larguraSaida: number,
  alturaSaida: number,
  larguraOrigem: number,
  alturaOrigem: number,
): CaixaContorno {
  const centroX = ((x * larguraOrigem - recorte.x) / recorte.largura) * larguraSaida;
  const centroY = ((y * alturaOrigem - recorte.y) / recorte.altura) * alturaSaida;
  let largura = (FRACAO_LARGURA_CONTORNO * larguraOrigem / recorte.largura) * larguraSaida;
  let altura = (FRACAO_ALTURA_CONTORNO * alturaOrigem / recorte.altura) * alturaSaida;
  largura = Math.max(Math.round(largura), 2);
  altura = Math.max(Math.round(altura), 2);
  largura -= largura % 2;
  altura -= altura % 2;
  return {
    x: Math.round(centroX - largura / 2) / larguraSaida,
    y: Math.round(centroY - altura / 2) / alturaSaida,
    w: largura / larguraSaida,
    h: altura / alturaSaida,
  };
}
