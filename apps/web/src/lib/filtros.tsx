"use client";

import { useEffect, useState } from "react";

import { chamarApi } from "@/lib/api";
import type { FiltroCor, OperacaoCor } from "@/lib/tipos";

// Os filtros vêm da API (core/utils/cores.py), então a prévia usa exatamente as mesmas operações do render
let cache: Promise<FiltroCor[]> | null = null;

export function useFiltros(): FiltroCor[] {
  const [filtros, setFiltros] = useState<FiltroCor[]>([]);
  useEffect(() => {
    cache ??= chamarApi<FiltroCor[]>("/filtros").catch(() => {
      cache = null;
      return [];
    });
    let cancelado = false;
    cache.then((lista) => {
      if (!cancelado) setFiltros(lista);
    });
    return () => {
      cancelado = true;
    };
  }, []);
  return filtros;
}

const IDENTIDADE = [
  [1, 0, 0],
  [0, 1, 0],
  [0, 0, 1],
];

/** Mesma interpolação do render: cada operação se aproxima da identidade conforme a intensidade diminui. */
function comIntensidade(operacao: OperacaoCor, intensidade: number): OperacaoCor {
  if (operacao.tipo === "matriz") {
    return { tipo: "matriz", valores: operacao.valores.map((linha, i) => linha.map((v, j) => IDENTIDADE[i][j] + (v - IDENTIDADE[i][j]) * intensidade)) };
  }
  return { tipo: "contraste", valor: 1 + (operacao.valor - 1) * intensidade };
}

function valoresDaMatriz(operacao: OperacaoCor): string {
  if (operacao.tipo === "matriz") {
    const [r, g, b] = operacao.valores;
    return [...r, 0, 0, ...g, 0, 0, ...b, 0, 0, 0, 0, 0, 1, 0].map((v) => v.toFixed(4)).join(" ");
  }
  const c = operacao.valor;
  const deslocamento = 0.5 * (1 - c);
  return [c, 0, 0, 0, deslocamento, 0, c, 0, 0, deslocamento, 0, 0, c, 0, deslocamento, 0, 0, 0, 1, 0].map((v) => v.toFixed(4)).join(" ");
}

/**
 * Filtro SVG invisível. Use com style={{ filter: `url(#${id})` }}.
 * color-interpolation-filters="sRGB": a conta é feita nos mesmos valores de cor que o FFmpeg usa.
 * Devolve null quando não há o que fazer (Natural ou intensidade zero).
 */
export function FiltroSvg({ id, filtro, intensidade }: { id: string; filtro: FiltroCor | undefined; intensidade: number }) {
  if (!filtro || filtro.operacoes.length === 0 || intensidade <= 0) return null;
  return (
    <svg width="0" height="0" aria-hidden className="absolute">
      <defs>
        <filter id={id} colorInterpolationFilters="sRGB" x="0" y="0" width="100%" height="100%">
          {filtro.operacoes.map((operacao, indice) => (
            <feColorMatrix key={indice} type="matrix" values={valoresDaMatriz(comIntensidade(operacao, Math.min(intensidade, 1)))} />
          ))}
        </filter>
      </defs>
    </svg>
  );
}

/** O valor de CSS para o filtro, ou vazio quando não há filtro. */
export function cssDoFiltro(id: string, filtro: FiltroCor | undefined, intensidade: number): string {
  return filtro && filtro.operacoes.length > 0 && intensidade > 0 ? `url(#${id})` : "";
}
