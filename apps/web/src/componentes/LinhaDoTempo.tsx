"use client";

import { useRef, useState } from "react";

import { formatarTempo } from "@/lib/formatar";
import type { Parte } from "@/lib/tipos";

const DISTANCIA_PARA_ARRASTAR_PX = 6;

type Props = {
  partes: Parte[];
  /** Duração de cada parte no vídeo final, já sem os silêncios. */
  duracoes: number[];
  indiceAtual: number;
  posicaoFinal: number;
  aoBuscar: (indice: number, posicaoNaParte: number) => void;
  aoReordenar: (de: number, para: number) => void;
};

/**
 * As partes do vídeo final, lado a lado, com a largura proporcional à duração.
 * Clicar leva a prévia até aquele ponto; arrastar um bloco muda a ordem.
 */
export function LinhaDoTempo({ partes, duracoes, indiceAtual, posicaoFinal, aoBuscar, aoReordenar }: Props) {
  const blocos = useRef<(HTMLButtonElement | null)[]>([]);
  const arraste = useRef<{ indice: number; x: number; ativo: boolean } | null>(null);
  const [destino, setDestino] = useState<{ de: number; x: number } | null>(null);
  const total = duracoes.reduce((soma, duracao) => soma + duracao, 0);

  /** Para onde o bloco iria se fosse solto nesta posição: antes do primeiro bloco cujo meio fica à direita. */
  function posicaoDeSoltar(clienteX: number): number {
    const meios = blocos.current.map((bloco) => {
      const retangulo = bloco?.getBoundingClientRect();
      return retangulo ? retangulo.left + retangulo.width / 2 : 0;
    });
    const antes = meios.findIndex((meio) => clienteX < meio);
    return antes === -1 ? partes.length : antes;
  }

  return (
    <div>
      <div className="relative flex gap-1" role="list" aria-label="Partes do vídeo, na ordem">
        {partes.map((parte, indice) => {
          const atual = indice === indiceAtual;
          const arrastado = destino?.de === indice;
          return (
            <button
              key={parte.id}
              ref={(elemento) => {
                blocos.current[indice] = elemento;
              }}
              type="button"
              role="listitem"
              aria-current={atual}
              aria-label={`Parte ${indice + 1}: ${formatarTempo(parte.inicio)} a ${formatarTempo(parte.fim)} da gravação, ${formatarTempo(duracoes[indice])} no vídeo`}
              className={`relative flex h-14 min-w-10 touch-none flex-col items-start justify-center overflow-hidden rounded-lg border px-2 text-left text-xs transition ${
                atual ? "border-laranja bg-laranja/15" : "border-borda bg-surface-2 hover:border-suave"
              } ${arrastado ? "opacity-40" : ""}`}
              style={{ flexGrow: Math.max(duracoes[indice], 0.5), flexBasis: 0 }}
              onPointerDown={(evento) => {
                evento.currentTarget.setPointerCapture(evento.pointerId);
                arraste.current = { indice, x: evento.clientX, ativo: false };
              }}
              onPointerMove={(evento) => {
                const atualArraste = arraste.current;
                if (!atualArraste) return;
                if (!atualArraste.ativo && Math.abs(evento.clientX - atualArraste.x) < DISTANCIA_PARA_ARRASTAR_PX) return;
                atualArraste.ativo = true;
                setDestino({ de: atualArraste.indice, x: marcadorDeSoltar(blocos.current, posicaoDeSoltar(evento.clientX)) });
              }}
              onPointerUp={(evento) => {
                const atualArraste = arraste.current;
                arraste.current = null;
                setDestino(null);
                if (!atualArraste) return;
                if (atualArraste.ativo) {
                  const para = posicaoDeSoltar(evento.clientX);
                  // Soltar logo antes ou logo depois de si mesmo não muda nada
                  const final = para > atualArraste.indice ? para - 1 : para;
                  if (final !== atualArraste.indice) aoReordenar(atualArraste.indice, final);
                  return;
                }
                const retangulo = evento.currentTarget.getBoundingClientRect();
                const fracao = Math.min(Math.max((evento.clientX - retangulo.left) / retangulo.width, 0), 1);
                aoBuscar(indice, fracao * duracoes[indice]);
              }}
              onPointerCancel={() => {
                arraste.current = null;
                setDestino(null);
              }}
              onKeyDown={(evento) => {
                if (evento.key === "Enter" || evento.key === " ") {
                  evento.preventDefault();
                  aoBuscar(indice, 0);
                }
              }}
            >
              <span className="font-display font-bold">{indice + 1}</span>
              <span className="truncate text-suave">{formatarTempo(duracoes[indice])}</span>
            </button>
          );
        })}
        {destino ? (
          <span
            aria-hidden
            className="pointer-events-none absolute inset-y-0 w-1 -translate-x-1/2 rounded-full bg-laranja"
            style={{ left: destino.x }}
          />
        ) : null}
      </div>
      {total > 0 ? (
        <div className="relative mt-1 h-1 rounded-full bg-ink" aria-hidden>
          <span className="absolute inset-y-0 left-0 rounded-full bg-laranja" style={{ width: `${Math.min(posicaoFinal / total, 1) * 100}%` }} />
        </div>
      ) : null}
    </div>
  );
}

/** Posição horizontal (em px, relativa à faixa) da marca de onde o bloco arrastado vai entrar. */
function marcadorDeSoltar(blocos: (HTMLButtonElement | null)[], para: number): number {
  const faixa = blocos[0]?.parentElement?.getBoundingClientRect();
  if (!faixa) return 0;
  const alvo = blocos[Math.min(para, blocos.length - 1)]?.getBoundingClientRect();
  if (!alvo) return 0;
  return (para >= blocos.length ? alvo.right + 2 : alvo.left - 2) - faixa.left;
}
