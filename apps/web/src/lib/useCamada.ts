"use client";

import { useEffect, useRef, useState } from "react";

import type { FiguraProjeto, Marca, TextoProjeto } from "@/lib/tipos";

export type PedidoCamada = {
  largura: number;
  altura: number;
  tipo: "logo" | "texto" | "figura";
  marca?: Marca;
  texto?: TextoProjeto;
  figura?: FiguraProjeto;
  /** Para a API achar o PNG enviado. */
  projeto_id?: string;
};

const ESPERA_MS = 250;

/**
 * A camada PNG que o render vai sobrepor ao vídeo, desenhada pela API no tamanho final.
 * O navegador só reduz a imagem, então a prévia sai igual ao vídeo exportado.
 * Enquanto a próxima versão não chega, continua mostrando a anterior (sem piscar).
 */
export function useCamada(pedido: PedidoCamada | null): string | null {
  return useCamadaComCaixa(pedido).url;
}

/** [x0, y0, x1, y1] do elemento, em pixels da camada. */
export type Caixa = [number, number, number, number];

/** A camada e a caixa do elemento dentro dela, para a prévia desenhar a seleção com as alças. */
export function useCamadaComCaixa(pedido: PedidoCamada | null): { url: string | null; caixa: Caixa | null } {
  const chave = pedido ? JSON.stringify(pedido) : null;
  const [url, setUrl] = useState<string | null>(null);
  const [caixa, setCaixa] = useState<Caixa | null>(null);
  const ultima = useRef<string | null>(null);

  useEffect(() => {
    if (!chave) return;
    const controlador = new AbortController();
    const espera = setTimeout(async () => {
      try {
        const resposta = await fetch("/api/arte/camada", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: chave,
          credentials: "same-origin",
          signal: controlador.signal,
        });
        if (!resposta.ok) return;
        const valores = (resposta.headers.get("X-Caixa") ?? "").split(",").map(Number);
        const nova = URL.createObjectURL(await resposta.blob());
        if (ultima.current) URL.revokeObjectURL(ultima.current);
        ultima.current = nova;
        setUrl(nova);
        setCaixa(valores.length === 4 && valores.every(Number.isFinite) && valores[2] > valores[0] ? (valores as Caixa) : null);
      } catch {
        // cancelada por uma edição mais nova, ou sem conexão: fica a versão anterior
      }
    }, ESPERA_MS);
    return () => {
      clearTimeout(espera);
      controlador.abort();
    };
  }, [chave]);

  useEffect(
    () => () => {
      if (ultima.current) URL.revokeObjectURL(ultima.current);
    },
    [],
  );

  return chave ? { url, caixa } : { url: null, caixa: null };
}
