"use client";

import { Move } from "lucide-react";
import { type ReactNode, type RefObject, useEffect, useRef, useState } from "react";

import { calcularRecorte, limitesDoCentro, PROPORCOES } from "@/lib/recorte";
import type { Fundo, Proporcao } from "@/lib/tipos";

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
  /** Desfoque e escurecimento do vídeo, como o render aplica antes das camadas. */
  fundo?: Fundo;
  /** Filtro de cor em CSS (url(#...) de um FiltroSvg), aplicado antes do desfoque, como no render. */
  filtroCor?: string;
  /** Giro do vídeo em graus, no sentido do relógio. Gira o quadro já recortado, como o render. */
  rotacao?: number;
  /** Zoom e tremor do quadro já enquadrado, na mesma conta do render. As camadas ficam paradas. */
  transformExtra?: string;
  /** 1 no corte seco. Cai a 0 na emenda quando a transição escurece. */
  opacidade?: number;
  /** Sigma do desfoque nas pontas, em pixels do vídeo final. 0 fora da emenda. */
  desfoqueTransicao?: number;
  /** 0 a 0,8. Mistura uma cópia borrada em tela, como o blend do render. */
  luz?: number;
  /** Frações do quadro final. O mesmo retângulo do drawbox. */
  contorno?: { x: number; y: number; w: number; h: number } | null;
};

function limitar(valor: number, [minimo, maximo]: [number, number]): number {
  return minimo > maximo ? 0.5 : Math.min(Math.max(valor, minimo), maximo);
}

/** Mostra só o que vai para o vídeo final. Arrastar a imagem muda o enquadramento. */
export function PreviaEnquadrada({ player, src, poster, largura, altura, proporcao, enquadramento, aoMudar, alturaMaxima = 620, children, fundo, filtroCor, rotacao = 0, transformExtra = "", opacidade = 1, desfoqueTransicao = 0, luz = 0, contorno = null }: Props) {
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
        className="relative mx-auto touch-none overflow-hidden rounded-[1.75rem] bg-black shadow-[0_30px_80px_rgba(0,0,0,.5)] ring-4 ring-[#1c1f29] [container-type:size]"
        style={{ width: quadroLargura, height: quadroAltura }}
      >
        <div
          className="absolute inset-0 overflow-hidden"
          style={{
            transform: [rotacao ? `rotate(${rotacao}deg)` : "", transformExtra].filter(Boolean).join(" ") || undefined,
            opacity: opacidade,
          }}
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
            // O desfoque do render é em pixels do vídeo final; aqui, na escala da moldura
            filter:
              [
                filtroCor,
                fundo?.desfoque ? `blur(${(fundo.desfoque * quadroLargura) / alvo.largura}px)` : "",
                desfoqueTransicao > 0 ? `blur(${(desfoqueTransicao * quadroLargura) / alvo.largura}px)` : "",
              ].filter(Boolean).join(" ") || undefined,
          }}
        />
        {luz > 0.01 ? (
          <div
            className="pointer-events-none absolute inset-0"
            style={{
              backdropFilter: `blur(${(18 * quadroLargura) / alvo.largura}px)`,
              mixBlendMode: "screen",
              opacity: Math.min(luz, 0.8),
            }}
          />
        ) : null}
        </div>
        {contorno ? (
          <div
            className="pointer-events-none absolute inset-0"
            style={{
              transform: [rotacao ? `rotate(${rotacao}deg)` : "", transformExtra].filter(Boolean).join(" ") || undefined,
            }}
          >
            <div
              className="absolute box-border border-white/90"
              style={{
                left: `${contorno.x * 100}%`,
                top: `${contorno.y * 100}%`,
                width: `${contorno.w * 100}%`,
                height: `${contorno.h * 100}%`,
                borderWidth: "0.556cqw",
              }}
            />
          </div>
        ) : null}
        {fundo?.escurecer ? <div className="pointer-events-none absolute inset-0 bg-black" style={{ opacity: fundo.escurecer }} /> : null}
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
        {/* Por cima da área de enquadrar: o texto e o logo se arrastam sozinhos; o resto do quadro enquadra o vídeo */}
        {children}
        <span className="pointer-events-none absolute left-1/2 top-3 inline-flex -translate-x-1/2 items-center gap-1.5 rounded-full bg-black/60 px-3 py-1 text-xs text-white/90">
          <Move className="size-3.5" aria-hidden /> Arraste para enquadrar
        </span>
      </div>
    </div>
  );
}
