"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { formatarTempo } from "@/lib/formatar";

const PASSO_BARRA = 3; // px por barra (2 px de barra + 1 de espaço)
const PASSO_TECLADO_S = 5;

type Props = {
  picos: number[];
  duracao: number;
  tempo: number;
  aoBuscar?: (segundos: number) => void;
  altura?: number;
  /** Trechos marcados na forma de onda, como os silêncios que vão ser cortados. */
  cortes?: [number, number][];
};

/** Desenha a forma de onda num canvas. A parte já tocada fica com o gradiente da marca. */
export function FormaDeOnda({ picos, duracao, tempo, aoBuscar, altura = 72, cortes = [] }: Props) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const [largura, setLargura] = useState(0);

  useEffect(() => {
    const elemento = canvas.current;
    if (!elemento) return;
    const observador = new ResizeObserver(([entrada]) => setLargura(Math.floor(entrada.contentRect.width)));
    observador.observe(elemento);
    return () => observador.disconnect();
  }, []);

  // Junta os picos em uma coluna por barra e normaliza pelo maior pico do áudio
  const barras = useMemo(() => {
    const total = Math.max(1, Math.floor(largura / PASSO_BARRA));
    if (!largura || picos.length === 0) return [];
    const porBarra = picos.length / total;
    const valores: number[] = [];
    let maximo = 1;
    for (let i = 0; i < total; i++) {
      const inicio = Math.floor(i * porBarra);
      const fim = Math.max(Math.floor((i + 1) * porBarra), inicio + 1);
      let valor = 0;
      for (let j = inicio; j < fim; j++) valor = Math.max(valor, picos[j] ?? 0);
      valores.push(valor);
      maximo = Math.max(maximo, valor);
    }
    return valores.map((valor) => valor / maximo);
  }, [picos, largura]);

  useEffect(() => {
    const elemento = canvas.current;
    const contexto = elemento?.getContext("2d");
    if (!elemento || !contexto || !largura) return;
    const escala = window.devicePixelRatio || 1;
    elemento.width = largura * escala;
    elemento.height = altura * escala;
    contexto.setTransform(escala, 0, 0, escala, 0, 0);
    contexto.clearRect(0, 0, largura, altura);

    const estilos = getComputedStyle(document.documentElement);
    const gradiente = contexto.createLinearGradient(0, 0, largura, 0);
    gradiente.addColorStop(0, estilos.getPropertyValue("--hc-violet").trim() || "#7B61FF");
    gradiente.addColorStop(1, estilos.getPropertyValue("--hc-orange").trim() || "#FF8A00");
    const tocado = duracao > 0 ? (tempo / duracao) * largura : 0;
    const paraX = (segundos: number) => (duracao > 0 ? (segundos / duracao) * largura : 0);

    // Trechos cortados: fundo avermelhado atrás das barras
    contexto.fillStyle = "rgba(255, 77, 77, 0.3)";
    for (const [inicio, fim] of cortes) contexto.fillRect(paraX(inicio), 0, Math.max(paraX(fim) - paraX(inicio), 1), altura);
    let corte = 0;

    barras.forEach((valor, indice) => {
      const x = indice * PASSO_BARRA;
      const h = Math.max(2, valor * altura * 0.92);
      while (corte < cortes.length && paraX(cortes[corte][1]) < x) corte++;
      const cortado = corte < cortes.length && paraX(cortes[corte][0]) <= x;
      contexto.fillStyle = cortado ? "rgba(255, 110, 110, 0.35)" : x < tocado ? gradiente : "rgba(255, 255, 255, 0.2)";
      contexto.fillRect(x, (altura - h) / 2, PASSO_BARRA - 1, h);
    });
    contexto.fillStyle = "#ffffff";
    contexto.fillRect(Math.min(tocado, largura - 2), 0, 2, altura);
  }, [barras, tempo, duracao, largura, altura, cortes]);

  function buscarNaPosicao(clienteX: number) {
    if (!aoBuscar || !canvas.current || duracao <= 0) return;
    const retangulo = canvas.current.getBoundingClientRect();
    const fracao = Math.min(Math.max((clienteX - retangulo.left) / retangulo.width, 0), 1);
    aoBuscar(fracao * duracao);
  }

  return (
    <canvas
      ref={canvas}
      className="block w-full cursor-pointer touch-none rounded-lg focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-laranja"
      style={{ height: altura }}
      role="slider"
      tabIndex={0}
      aria-label="Posição na gravação"
      aria-valuemin={0}
      aria-valuemax={Math.round(duracao)}
      aria-valuenow={Math.round(tempo)}
      aria-valuetext={`${formatarTempo(tempo)} de ${formatarTempo(duracao)}`}
      onPointerDown={(evento) => {
        evento.currentTarget.setPointerCapture(evento.pointerId);
        buscarNaPosicao(evento.clientX);
      }}
      onPointerMove={(evento) => {
        if (evento.buttons === 1) buscarNaPosicao(evento.clientX);
      }}
      onKeyDown={(evento) => {
        if (!aoBuscar) return;
        if (evento.key === "ArrowRight") aoBuscar(Math.min(tempo + PASSO_TECLADO_S, duracao));
        else if (evento.key === "ArrowLeft") aoBuscar(Math.max(tempo - PASSO_TECLADO_S, 0));
        else if (evento.key === "Home") aoBuscar(0);
        else if (evento.key === "End") aoBuscar(duracao);
        else return;
        evento.preventDefault();
      }}
    />
  );
}
