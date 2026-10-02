"use client";

import { useEffect, useRef } from "react";

type Props = {
  src: string;
  inicio: number;
  fim: number | null;
  posicaoFinal: number;
};

/** Cobre a prévia com o vídeo de apoio no mesmo intervalo em que o render cobre o quadro. */
export function ApoioNaPrevia({ src, inicio, fim, posicaoFinal }: Props) {
  const video = useRef<HTMLVideoElement>(null);
  const visivel = posicaoFinal >= inicio && (fim === null || posicaoFinal < fim);

  useEffect(() => {
    const elemento = video.current;
    if (!elemento || !visivel) return;
    const alvo = Math.max(0, posicaoFinal - inicio);
    if (Math.abs(elemento.currentTime - alvo) > 0.2) elemento.currentTime = alvo;
  }, [posicaoFinal, inicio, visivel]);

  return (
    <video
      ref={video}
      src={src}
      muted
      playsInline
      className={`pointer-events-none absolute inset-0 size-full object-cover ${visivel ? "" : "hidden"}`}
    />
  );
}
