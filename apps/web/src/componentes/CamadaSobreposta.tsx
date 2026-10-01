"use client";

import Image from "next/image";
import { useRef, useState } from "react";

import { type PedidoCamada, useCamadaComCaixa } from "@/lib/useCamada";

/** O que muda ao soltar o gesto: o novo centro (0 a 1 da moldura), quanto aumentou e quantos graus girou. */
export type MudancaCamada = { x: number; y: number; fator: number; giro: number };

type Edicao = {
  selecionada: boolean;
  aoSelecionar: () => void;
  aoMudar: (mudanca: MudancaCamada) => void;
};

type Gesto = { modo: "mover" | "escala" | "girar"; dx: number; dy: number; fator: number; giro: number; soltoEm?: string | null };

const ROTULOS = { mover: "Arraste para mover", escala: "Arraste para aumentar", girar: "Arraste para girar" };

/**
 * Uma camada de arte (logo ou texto) por cima da prévia, igual à que vai para o vídeo.
 * Com "edicao", vira um elemento que se clica e arrasta como no CapCut: durante o gesto a imagem
 * só se move no navegador; ao soltar, a nova posição vai para o projeto e a API redesenha a camada.
 */
export function CamadaSobreposta({ pedido, visivel = true, edicao }: { pedido: PedidoCamada | null; visivel?: boolean; edicao?: Edicao }) {
  const { url, caixa } = useCamadaComCaixa(pedido);
  const moldura = useRef<HTMLDivElement>(null);
  const partida = useRef<{ x: number; y: number; cx: number; cy: number; moveu: boolean } | null>(null);
  const [gesto, setGesto] = useState<Gesto | null>(null);
  if (!url || !pedido) return null;

  const largura = pedido.largura;
  const altura = pedido.altura;
  const centro = caixa ? { x: (caixa[0] + caixa[2]) / 2 / largura, y: (caixa[1] + caixa[3]) / 2 / altura } : { x: 0.5, y: 0.5 };
  // Depois de soltar, o gesto continua aplicado até chegar a camada redesenhada (sem pular de volta)
  const aplicado = gesto && (gesto.soltoEm === undefined || gesto.soltoEm === url) ? gesto : null;

  function comecar(evento: React.PointerEvent, modo: Gesto["modo"]) {
    if (!edicao || !moldura.current) return;
    evento.stopPropagation();
    evento.preventDefault();
    edicao.aoSelecionar();
    const retangulo = moldura.current.getBoundingClientRect();
    partida.current = {
      x: evento.clientX,
      y: evento.clientY,
      cx: retangulo.left + centro.x * retangulo.width,
      cy: retangulo.top + centro.y * retangulo.height,
      moveu: false,
    };
    (evento.target as Element).setPointerCapture(evento.pointerId);
    setGesto({ modo, dx: 0, dy: 0, fator: 1, giro: 0 });
  }

  function mover(evento: React.PointerEvent) {
    const inicio = partida.current;
    if (!inicio || !gesto || gesto.soltoEm !== undefined || !moldura.current) return;
    const retangulo = moldura.current.getBoundingClientRect();
    if (Math.hypot(evento.clientX - inicio.x, evento.clientY - inicio.y) > 3) inicio.moveu = true;
    if (gesto.modo === "mover") {
      setGesto({ ...gesto, dx: (evento.clientX - inicio.x) / retangulo.width, dy: (evento.clientY - inicio.y) / retangulo.height });
    } else if (gesto.modo === "escala") {
      const antes = Math.max(Math.hypot(inicio.x - inicio.cx, inicio.y - inicio.cy), 1);
      const agora = Math.hypot(evento.clientX - inicio.cx, evento.clientY - inicio.cy);
      setGesto({ ...gesto, fator: Math.min(Math.max(agora / antes, 0.2), 5) });
    } else {
      const antes = Math.atan2(inicio.y - inicio.cy, inicio.x - inicio.cx);
      const agora = Math.atan2(evento.clientY - inicio.cy, evento.clientX - inicio.cx);
      setGesto({ ...gesto, giro: ((agora - antes) * 180) / Math.PI });
    }
  }

  function soltar() {
    const inicio = partida.current;
    partida.current = null;
    if (!edicao || !gesto || gesto.soltoEm !== undefined) return;
    if (!inicio?.moveu) {
      setGesto(null);   // foi só um clique: seleciona e pronto
      return;
    }
    edicao.aoMudar({
      x: Math.min(Math.max(centro.x + gesto.dx, 0), 1),
      y: Math.min(Math.max(centro.y + gesto.dy, 0), 1),
      fator: gesto.fator,
      giro: gesto.giro,
    });
    setGesto({ ...gesto, soltoEm: url });
  }

  const transformacao = aplicado
    ? {
        transform: `translate(${aplicado.dx * 100}%, ${aplicado.dy * 100}%) rotate(${aplicado.giro}deg) scale(${aplicado.fator})`,
        transformOrigin: `${centro.x * 100}% ${centro.y * 100}%`,
      }
    : undefined;

  return (
    <div ref={moldura} className="pointer-events-none absolute inset-0" style={{ opacity: visivel ? 1 : 0 }}>
      <div className="absolute inset-0" style={transformacao}>
        <Image src={url} alt="" fill unoptimized sizes="400px" className="pointer-events-none" />
        {edicao && caixa && visivel ? (
          <div
            role="button"
            tabIndex={0}
            aria-label={edicao.selecionada ? ROTULOS.mover : "Selecionar"}
            onPointerDown={(evento) => comecar(evento, "mover")}
            onPointerMove={mover}
            onPointerUp={soltar}
            className={`pointer-events-auto absolute cursor-move touch-none rounded-md ${
              edicao.selecionada ? "outline-2 outline-white/90 outline-dashed" : "hover:outline hover:outline-1 hover:outline-white/50"
            }`}
            style={{
              left: `${(caixa[0] / largura) * 100}%`,
              top: `${(caixa[1] / altura) * 100}%`,
              width: `${((caixa[2] - caixa[0]) / largura) * 100}%`,
              height: `${((caixa[3] - caixa[1]) / altura) * 100}%`,
            }}
          >
            {edicao.selecionada ? (
              <>
                <span
                  role="button"
                  aria-label={ROTULOS.girar}
                  onPointerDown={(evento) => comecar(evento, "girar")}
                  onPointerMove={mover}
                  onPointerUp={soltar}
                  className="absolute -top-7 left-1/2 size-4 -translate-x-1/2 cursor-grab touch-none rounded-full border-2 border-white bg-violeta"
                />
                <span
                  role="button"
                  aria-label={ROTULOS.escala}
                  onPointerDown={(evento) => comecar(evento, "escala")}
                  onPointerMove={mover}
                  onPointerUp={soltar}
                  className="absolute -bottom-2 -right-2 size-4 cursor-nwse-resize touch-none rounded-sm border-2 border-white bg-laranja"
                />
              </>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}
