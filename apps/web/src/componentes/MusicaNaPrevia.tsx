"use client";

import { useEffect, useRef } from "react";

import type { MusicaProjeto } from "@/lib/tipos";

// Aproximação do sidechaincompress do render: a música cai para 20% (cerca de -14 dB, medido no
// vídeo exportado) quando há voz, desce em 15 ms e volta em 400 ms.
const GANHO_NA_FALA = 0.2;
const ATAQUE_S = 0.015;
const SOLTURA_S = 0.4;
const DERIVA_MAXIMA_S = 0.3;

/**
 * Toca a música junto com a prévia. A posição segue o vídeo final (sem os silêncios cortados),
 * então a música não pula quando a prévia pula um silêncio. Ao terminar, recomeça do início,
 * como o render faz.
 */
export function MusicaNaPrevia({
  src,
  duracao,
  musica,
  posicaoFinal,
  tocando,
  falando,
}: {
  src: string;
  duracao: number;
  musica: MusicaProjeto;
  posicaoFinal: number;
  tocando: boolean;
  falando: boolean;
}) {
  const som = useRef<HTMLAudioElement>(null);
  const ganho = useRef(1);
  const ultimoQuadro = useRef(0);
  const esperado = duracao > 0 ? (musica.inicio + posicaoFinal) % duracao : 0;

  useEffect(() => {
    const elemento = som.current;
    if (!elemento) return;
    if (!tocando) {
      elemento.pause();
      ultimoQuadro.current = 0;
      return;
    }
    if (elemento.paused || Math.abs(elemento.currentTime - esperado) > DERIVA_MAXIMA_S) elemento.currentTime = esperado;
    if (elemento.paused) void elemento.play().catch(() => undefined);

    const agora = performance.now() / 1000;
    const passo = ultimoQuadro.current ? Math.min(agora - ultimoQuadro.current, 0.25) : 0;
    ultimoQuadro.current = agora;
    const alvo = musica.abaixar_na_fala && falando ? GANHO_NA_FALA : 1;
    const constante = alvo < ganho.current ? ATAQUE_S : SOLTURA_S;
    ganho.current += (alvo - ganho.current) * (1 - Math.exp(-passo / constante));
    elemento.volume = Math.min(Math.max(musica.volume * ganho.current, 0), 1);
  }, [tocando, esperado, falando, musica.volume, musica.abaixar_na_fala]);

  return <audio ref={som} src={src} loop preload="auto" hidden data-musica-previa />;
}
