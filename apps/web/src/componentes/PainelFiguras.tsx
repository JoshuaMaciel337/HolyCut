"use client";

import { BookOpen, Flame, ImagePlus, Star, Trash2 } from "lucide-react";
import type { ComponentType } from "react";

import { formatarTempo } from "@/lib/formatar";
import type { FiguraProjeto, IconeFigura } from "@/lib/tipos";

const MAX_FIGURAS = 8;
const MAX_BYTES = 5 * 1024 * 1024;

function PlusCruz({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round">
      <path d="M12 3v18M5 9h14" />
    </svg>
  );
}

const ICONES: { id: IconeFigura; rotulo: string; icone: ComponentType<{ className?: string }> }[] = [
  { id: "cruz", rotulo: "Cruz", icone: PlusCruz },
  { id: "biblia", rotulo: "Bíblia", icone: BookOpen },
  { id: "chama", rotulo: "Chama", icone: Flame },
  { id: "estrela", rotulo: "Estrela", icone: Star },
];

type Props = {
  figuras: FiguraProjeto[];
  aoMudar: (figuras: FiguraProjeto[]) => void;
  duracaoFinal: number;
  posicaoFinal: number;
  enviando: boolean;
  aoAdicionarIcone: (icone: IconeFigura) => void;
  aoEnviarArquivo: (arquivo: File) => void;
  aoFalhar: (mensagem: string) => void;
};

/** PNG e ícones por cima do vídeo. Os tempos são do vídeo final, já sem os cortes. */
export function PainelFiguras({ figuras, aoMudar, duracaoFinal, posicaoFinal, enviando, aoAdicionarIcone, aoEnviarArquivo, aoFalhar }: Props) {
  const atualizar = (id: string, mudanca: Partial<FiguraProjeto>) =>
    aoMudar(figuras.map((figura) => (figura.id === id ? { ...figura, ...mudanca } : figura)));
  const cheio = figuras.length >= MAX_FIGURAS;

  return (
    <section className="cartao p-6" aria-labelledby="titulo-figuras">
      <h2 id="titulo-figuras" className="font-display text-lg font-bold">
        Figuras
      </h2>
      <p className="mt-1 text-sm text-suave">Arraste na prévia para mover, aumentar e girar.</p>
      <div className="mt-4 flex flex-wrap gap-2">
        {ICONES.map((icone) => (
          <button
            key={icone.id}
            type="button"
            disabled={cheio || enviando}
            onClick={() => aoAdicionarIcone(icone.id)}
            className="botao-contorno px-3 py-1.5 text-xs"
          >
            <icone.icone className="size-3.5" aria-hidden /> {icone.rotulo}
          </button>
        ))}
        <label className={`botao-contorno px-3 py-1.5 text-xs ${cheio || enviando ? "pointer-events-none opacity-50" : "cursor-pointer"}`}>
          <ImagePlus className="size-3.5" aria-hidden /> {enviando ? "Enviando..." : "Enviar imagem"}
          <input
            type="file"
            accept="image/png,image/jpeg,image/webp"
            className="sr-only"
            disabled={cheio || enviando}
            onChange={(evento) => {
              const arquivo = evento.target.files?.[0];
              evento.target.value = "";
              if (!arquivo) return;
              if (arquivo.size > MAX_BYTES) {
                aoFalhar("A imagem pode ter no máximo 5 MB.");
                return;
              }
              aoEnviarArquivo(arquivo);
            }}
          />
        </label>
      </div>
      {figuras.length === 0 ? (
        <p className="mt-3 text-sm text-suave">Uma cruz, uma bíblia ou o PNG da igreja, só na parte do vídeo que você escolher.</p>
      ) : (
        <ul className="mt-4 flex flex-col gap-4">
          {figuras.map((figura) => {
            const trecho = figura.inicio > 0 || figura.fim !== null;
            return (
              <li key={figura.id} className="flex flex-col gap-3 rounded-2xl border border-borda bg-surface-2/50 p-4">
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate text-sm font-semibold">{figura.nome}</span>
                  <button
                    type="button"
                    onClick={() => aoMudar(figuras.filter((item) => item.id !== figura.id))}
                    aria-label={`Remover ${figura.nome}`}
                    className="text-suave hover:text-texto"
                  >
                    <Trash2 className="size-4" aria-hidden />
                  </button>
                </div>
                {figura.credito ? <p className="text-xs text-suave">{figura.credito}</p> : null}
                <label className="flex items-center gap-3 text-sm">
                  <span className="w-16 shrink-0 text-suave">Tamanho</span>
                  <input
                    type="range"
                    min={0.08}
                    max={0.8}
                    step={0.01}
                    value={figura.tamanho}
                    onChange={(evento) => atualizar(figura.id, { tamanho: Number(evento.target.value) })}
                    className="w-full accent-[var(--hc-orange)]"
                  />
                </label>
                <div className="flex flex-wrap items-center gap-2 text-sm">
                  <select
                    value={trecho ? "trecho" : "todo"}
                    onChange={(evento) =>
                      atualizar(
                        figura.id,
                        evento.target.value === "todo"
                          ? { inicio: 0, fim: null }
                          : { inicio: Math.round(posicaoFinal * 10) / 10, fim: Math.min(Math.round(posicaoFinal * 10) / 10 + 5, duracaoFinal) },
                      )
                    }
                    aria-label="Quando a figura aparece"
                    className="rounded-xl border border-borda bg-ink px-3 py-2 outline-none focus:border-violeta"
                  >
                    <option value="todo">O vídeo todo</option>
                    <option value="trecho">Só uma parte</option>
                  </select>
                  {trecho ? (
                    <>
                      <button
                        type="button"
                        onClick={() => atualizar(figura.id, { inicio: Math.min(Math.round(posicaoFinal * 10) / 10, (figura.fim ?? duracaoFinal) - 0.5) })}
                        className="botao-contorno px-3 py-1.5 text-xs"
                      >
                        Começa aqui
                      </button>
                      <button
                        type="button"
                        onClick={() => atualizar(figura.id, { fim: Math.max(Math.round(posicaoFinal * 10) / 10, figura.inicio + 0.5) })}
                        className="botao-contorno px-3 py-1.5 text-xs"
                      >
                        Termina aqui
                      </button>
                      <span className="tabular-nums text-suave">
                        {formatarTempo(figura.inicio)} até {formatarTempo(figura.fim ?? duracaoFinal)}
                      </span>
                    </>
                  ) : null}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
