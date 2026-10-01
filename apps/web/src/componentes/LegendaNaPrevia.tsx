"use client";

import { useRef, useState } from "react";

import type { BlocoLegenda, Legenda } from "@/lib/tipos";

/** Ao soltar o gesto: o novo centro do bloco (0 a 1 da moldura) e quanto a letra aumentou. */
export type MudancaLegenda = { x: number; y: number; fator: number };

type Edicao = { selecionada: boolean; aoSelecionar: () => void; aoMudar: (mudanca: MudancaLegenda) => void };

// O mesmo dourado de core/modelos/legenda.py (COR_DOURADA). O Destaque e o Karaokê usam a cor da igreja.
const DOURADO = "#FFD24D";

function blocoNoInstante(blocos: BlocoLegenda[], instante: number): BlocoLegenda | null {
  return blocos.find((bloco) => instante >= bloco.inicio && instante < bloco.fim) ?? null;
}

/** No Karaokê, a palavra acesa é a do momento. Nos outros presets, é a marcada como destaque. */
function indiceAceso(bloco: BlocoLegenda, instante: number, preset: Legenda["preset"]): number {
  if (preset === "karaoke") {
    let aceso = 0;
    bloco.palavras.forEach((palavra, indice) => {
      if (instante >= palavra.inicio) aceso = indice;
    });
    return aceso;
  }
  const destaque = bloco.palavras.findIndex((palavra) => palavra.destaque);
  return destaque >= 0 ? destaque : 0;
}

export function LegendaNaPrevia({
  blocos,
  instante,
  legenda,
  corDestaque,
  edicao,
}: {
  blocos: BlocoLegenda[];
  instante: number;
  legenda: Legenda;
  corDestaque: string;
  /** Com ela, a legenda se arrasta na prévia e muda de tamanho pela alça, como no CapCut. */
  edicao?: Edicao;
}) {
  const elemento = useRef<HTMLParagraphElement>(null);
  const partida = useRef<{ x: number; y: number; cx: number; cy: number; largura: number; altura: number; moveu: boolean } | null>(null);
  const [gesto, setGesto] = useState<{ modo: "mover" | "escala"; dx: number; dy: number; fator: number; soltoEm?: string } | null>(null);
  if (!legenda.ativa) return null;
  const bloco = blocoNoInstante(blocos, instante);
  if (!bloco) return null;
  const aceso = indiceAceso(bloco, instante, legenda.preset);
  const cor = legenda.preset === "digno" ? DOURADO : corDestaque;
  const escala = legenda.escala ?? 1;
  const livre = legenda.x != null || legenda.y != null;
  const chave = `${legenda.x}|${legenda.y}|${escala}`;
  // Depois de soltar, o gesto fica aplicado até a posição nova voltar salva (sem pular de volta)
  const aplicado = gesto && (gesto.soltoEm === undefined || gesto.soltoEm === chave) ? gesto : null;

  function comecar(evento: React.PointerEvent, modo: "mover" | "escala") {
    const moldura = elemento.current?.parentElement;
    if (!edicao || !elemento.current || !moldura) return;
    evento.stopPropagation();
    evento.preventDefault();
    edicao.aoSelecionar();
    const caixa = elemento.current.getBoundingClientRect();
    const quadro = moldura.getBoundingClientRect();
    partida.current = {
      x: evento.clientX, y: evento.clientY,
      cx: caixa.left + caixa.width / 2 - quadro.left, cy: caixa.top + caixa.height / 2 - quadro.top,
      largura: quadro.width, altura: quadro.height, moveu: false,
    };
    (evento.target as Element).setPointerCapture(evento.pointerId);
    setGesto({ modo, dx: 0, dy: 0, fator: 1 });
  }

  function mover(evento: React.PointerEvent) {
    const inicio = partida.current;
    if (!inicio || !gesto || gesto.soltoEm !== undefined) return;
    if (Math.hypot(evento.clientX - inicio.x, evento.clientY - inicio.y) > 3) inicio.moveu = true;
    if (gesto.modo === "mover") setGesto({ ...gesto, dx: evento.clientX - inicio.x, dy: evento.clientY - inicio.y });
    else setGesto({ ...gesto, fator: Math.min(Math.max(1 + (evento.clientY - inicio.y) / 120, 0.4), 3) });
  }

  function soltar() {
    const inicio = partida.current;
    partida.current = null;
    if (!edicao || !gesto || gesto.soltoEm !== undefined) return;
    if (!inicio?.moveu) {
      setGesto(null);
      return;
    }
    edicao.aoMudar({
      x: Math.min(Math.max((inicio.cx + gesto.dx) / inicio.largura, 0), 1),
      y: Math.min(Math.max((inicio.cy + gesto.dy) / inicio.altura, 0), 1),
      fator: gesto.fator,
    });
    setGesto({ ...gesto, soltoEm: chave });
  }

  const deslocamento = aplicado ? ` translate(${aplicado.dx}px, ${aplicado.dy}px) scale(${aplicado.fator})` : "";
  return (
    <p
      ref={elemento}
      role={edicao ? "button" : undefined}
      aria-label={edicao ? "Legenda: arraste para mover" : undefined}
      onPointerDown={edicao ? (evento) => comecar(evento, "mover") : undefined}
      onPointerMove={edicao ? mover : undefined}
      onPointerUp={edicao ? soltar : undefined}
      className={`absolute z-10 w-[84%] text-center font-display font-bold leading-tight text-white ${
        edicao ? "pointer-events-auto cursor-move touch-none" : "pointer-events-none"
      } ${edicao?.selecionada ? "rounded-md outline-2 outline-dashed outline-white/90" : ""} ${
        livre ? "" : legenda.posicao === "centro" ? "left-[8%] top-1/2" : "bottom-[12%] left-[8%]"
      }`}
      style={{
        fontSize: `${3.8 * escala}cqh`,
        WebkitTextStroke: `${0.12 * escala}cqh #000`,
        paintOrder: "stroke fill",
        ...(livre ? { left: `${(legenda.x ?? 0.5) * 100}%`, top: `${(legenda.y ?? 0.5) * 100}%` } : {}),
        transform: `${livre ? "translate(-50%, -50%)" : legenda.posicao === "centro" ? "translateY(-50%)" : ""}${deslocamento}` || undefined,
      }}
    >
      {bloco.palavras.map((palavra, indice) => {
        const acesa = legenda.preset !== "clean" && indice === aceso;
        return (
          <span
            key={`${palavra.id}-${indice}`}
            style={acesa ? { color: cor } : undefined}
            className={acesa && legenda.preset === "digno" ? "font-script text-[1.35em] leading-none" : undefined}
          >
            {indice > 0 ? " " : ""}
            {palavra.texto}
          </span>
        );
      })}
      {edicao?.selecionada ? (
        <span
          role="button"
          aria-label="Arraste para aumentar a legenda"
          onPointerDown={(evento) => comecar(evento, "escala")}
          onPointerMove={mover}
          onPointerUp={soltar}
          className="absolute -bottom-2 -right-2 size-4 cursor-ns-resize touch-none rounded-sm border-2 border-white bg-laranja"
        />
      ) : null}
    </p>
  );
}
