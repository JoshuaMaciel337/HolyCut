"use client";

import { Move } from "lucide-react";
import { type ReactNode, type RefObject, useEffect, useRef, useState } from "react";

import { calcularRecorte, limitesDoCentro, PROPORCOES } from "@/lib/recorte";
import type { Proporcao } from "@/lib/tipos";

type Enquadramento = { x: number; y: number; zoom: number };

type Props = {
  player: RefObject<HTMLVideoElement | null>;
  src: string;
  poster?: string;
  largura: number;
  altura: number;
  proporcao: Proporcao;
  enquadramento: Enquadramento;
  aoMudar: (enquadramento: Enquadramento) => void;
  alturaMaxima?: number;
  /** Camadas de arte (logo, textos) desenhadas por cima do vídeo. */
  children?: ReactNode;
};

function limitar(valor: number, [minimo, maximo]: [number, number]): number {
  return minimo > maximo ? 0.5 : Math.min(Math.max(valor, minimo), maximo);
}

/** Mostra só o que vai para o vídeo final. Arrastar a imagem muda o enquadramento. */
export function PreviaEnquadrada({ player, src, poster, largura, altura, proporcao, enquadramento, aoMudar, alturaMaxima = 620, children }: Props) {
  const recipiente = useRef<HTMLDivElement>(null);
  const inicio = useRef<{ px: number; py: number; x: number; y: number } | null>(null);
  const [disponivel, setDisponivel] = useState(0);

  useEffect(() => {
    const elemento = recipiente.current;
    if (!elemento) return;
    const observador = new ResizeObserver(([entrada]) => setDisponivel(entrada.contentRect.width));
    observador.observe(elemento);
    return () => observador.disconnect();
  }, []);

  const alvo = PROPORCOES[proporcao];
  const razao = alvo.largura / alvo.altura;
  const quadroLargura = Math.min(disponivel, alturaMaxima * razao);
  const quadroAltura = quadroLargura / razao;
  const recorte = calcularRecorte(largura, altura, proporcao, enquadramento.x, enquadramento.y, enquadramento.zoom);

  function mover(clienteX: number, clienteY: number) {
    if (!inicio.current || quadroLargura <= 0) return;
    const dx = ((clienteX - inicio.current.px) / quadroLargura) * recorte.largura;
    const dy = ((clienteY - inicio.current.py) / quadroAltura) * recorte.altura;
    aoMudar({
      ...enquadramento,
      x: limitar(inicio.current.x - dx / largura, limitesDoCentro(largura, recorte.largura)),
      y: limitar(inicio.current.y - dy / altura, limitesDoCentro(altura, recorte.altura)),
    });
  }

  return (
    <div ref={recipiente} className="w-full">
      <div
        className="relative mx-auto touch-none overflow-hidden rounded-[1.75rem] bg-black shadow-[0_30px_80px_rgba(0,0,0,.5)] ring-4 ring-[#1c1f29]"
        style={{ width: quadroLargura, height: quadroAltura }}
      >
        <video
          ref={player}
          src={src}
          poster={poster}
          playsInline
          preload="auto"
          className="absolute max-w-none"
          style={{
            width: `${(largura / recorte.largura) * 100}%`,
            height: `${(altura / recorte.altura) * 100}%`,
            left: `${(-recorte.x / recorte.largura) * 100}%`,
            top: `${(-recorte.y / recorte.altura) * 100}%`,
          }}
        />
        {children}
        <div
          className="absolute inset-0 cursor-grab active:cursor-grabbing"
          role="application"
          aria-label="Arraste para enquadrar"
          onPointerDown={(evento) => {
            evento.currentTarget.setPointerCapture(evento.pointerId);
            inicio.current = { px: evento.clientX, py: evento.clientY, x: enquadramento.x, y: enquadramento.y };
          }}
          onPointerMove={(evento) => {
            if (evento.buttons === 1) mover(evento.clientX, evento.clientY);
          }}
          onPointerUp={() => {
            inicio.current = null;
          }}
        />
        <span className="pointer-events-none absolute left-1/2 top-3 inline-flex -translate-x-1/2 items-center gap-1.5 rounded-full bg-black/60 px-3 py-1 text-xs text-white/90">
          <Move className="size-3.5" aria-hidden /> Arraste para enquadrar
        </span>
      </div>
    </div>
  );
}
