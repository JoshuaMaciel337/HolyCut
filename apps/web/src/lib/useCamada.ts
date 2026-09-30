"use client";

import { useEffect, useRef, useState } from "react";

import type { Marca, TextoProjeto } from "@/lib/tipos";

export type PedidoCamada = {
  largura: number;
  altura: number;
  tipo: "logo" | "texto";
  marca?: Marca;
  texto?: TextoProjeto;
};

const ESPERA_MS = 250;

/**
 * A camada PNG que o render vai sobrepor ao vídeo, desenhada pela API no tamanho final.
 * O navegador só reduz a imagem, então a prévia sai igual ao vídeo exportado.
 * Enquanto a próxima versão não chega, continua mostrando a anterior (sem piscar).
 */
export function useCamada(pedido: PedidoCamada | null): string | null {
  const chave = pedido ? JSON.stringify(pedido) : null;
  const [url, setUrl] = useState<string | null>(null);
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
        const nova = URL.createObjectURL(await resposta.blob());
        if (ultima.current) URL.revokeObjectURL(ultima.current);
        ultima.current = nova;
        setUrl(nova);
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

  return chave ? url : null;
}
