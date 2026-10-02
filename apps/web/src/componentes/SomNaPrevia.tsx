"use client";

import { useEffect, useRef } from "react";

/** Toca o som sintetizado no instante do vídeo final, o mesmo ponto em que o render mistura. */
export function SomNaPrevia({ src, inicio, posicaoFinal, tocando }: { src: string; inicio: number; posicaoFinal: number; tocando: boolean }) {
  const som = useRef<HTMLAudioElement>(null);
  const dentro = posicaoFinal >= inicio && posicaoFinal < inicio + 0.6;

  useEffect(() => {
    const elemento = som.current;
    if (!elemento) return;
    if (!tocando || !dentro) {
      elemento.pause();
      return;
    }
    const alvo = Math.max(0, posicaoFinal - inicio);
    if (Math.abs(elemento.currentTime - alvo) > 0.2) elemento.currentTime = alvo;
    void elemento.play().catch(() => undefined);
  }, [posicaoFinal, inicio, tocando, dentro]);

  return <audio ref={som} src={src} preload="auto" />;
}
