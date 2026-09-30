"use client";

import { BookOpen, Heading, Quote, Trash2 } from "lucide-react";

import { formatarTempo } from "@/lib/formatar";
import type { EstiloTexto, PosicaoTexto, TextoProjeto } from "@/lib/tipos";

const MAX_TEXTOS = 6;

const MODELOS: { tipo: TextoProjeto["tipo"]; rotulo: string; icone: typeof Heading; base: Partial<TextoProjeto> }[] = [
  { tipo: "titulo", rotulo: "Título", icone: Heading, base: { texto: "Culto de hoje", estilo: "manuscrito", posicao: "topo" } },
  { tipo: "frase", rotulo: "Frase", icone: Quote, base: { texto: "", estilo: "destaque", posicao: "base" } },
  { tipo: "versiculo", rotulo: "Versículo", icone: BookOpen, base: { texto: "", referencia: "", estilo: "limpo", posicao: "centro" } },
];
const ESTILOS: { valor: EstiloTexto; rotulo: string }[] = [
  { valor: "destaque", rotulo: "Destaque" },
  { valor: "limpo", rotulo: "Limpo" },
  { valor: "manuscrito", rotulo: "Manuscrito" },
];
const POSICOES: { valor: PosicaoTexto; rotulo: string }[] = [
  { valor: "topo", rotulo: "Topo" },
  { valor: "centro", rotulo: "Centro" },
  { valor: "base", rotulo: "Base" },
];

function novoId(): string {
  return Math.random().toString(36).slice(2, 10);
}

function Opcoes<T extends string>({ rotulo, opcoes, valor, aoMudar }: { rotulo: string; opcoes: { valor: T; rotulo: string }[]; valor: T; aoMudar: (valor: T) => void }) {
  return (
    <div role="radiogroup" aria-label={rotulo} className="flex gap-1 rounded-full border border-borda bg-ink p-1">
      {opcoes.map((opcao) => (
        <button
          key={opcao.valor}
          type="button"
          role="radio"
          aria-checked={valor === opcao.valor}
          onClick={() => aoMudar(opcao.valor)}
          className={`flex-1 whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-semibold transition ${valor === opcao.valor ? "bg-surface-2 text-texto" : "text-suave hover:text-texto"}`}
        >
          {opcao.rotulo}
        </button>
      ))}
    </div>
  );
}

type Props = {
  textos: TextoProjeto[];
  aoMudar: (textos: TextoProjeto[]) => void;
  duracaoFinal: number;
  posicaoFinal: number;
};

/** Títulos, frases e versículos sobre o vídeo. Os tempos são do vídeo final, já sem os cortes. */
export function PainelTextos({ textos, aoMudar, duracaoFinal, posicaoFinal }: Props) {
  const atualizar = (id: string, mudanca: Partial<TextoProjeto>) =>
    aoMudar(textos.map((texto) => (texto.id === id ? { ...texto, ...mudanca } : texto)));

  function adicionar(modelo: (typeof MODELOS)[number]) {
    const texto: TextoProjeto = {
      id: novoId(),
      tipo: modelo.tipo,
      texto: "",
      referencia: "",
      estilo: "destaque",
      posicao: "base",
      inicio: 0,
      fim: null,
      ...modelo.base,
    };
    aoMudar([...textos, texto]);
  }

  return (
    <section className="cartao p-6" aria-labelledby="titulo-textos">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 id="titulo-textos" className="font-display text-lg font-bold">
          Textos
        </h2>
        <div className="flex flex-wrap gap-2">
          {MODELOS.map((modelo) => (
            <button
              key={modelo.tipo}
              type="button"
              disabled={textos.length >= MAX_TEXTOS}
              onClick={() => adicionar(modelo)}
              className="botao-contorno px-3 py-1.5 text-xs"
            >
              <modelo.icone className="size-3.5" aria-hidden /> {modelo.rotulo}
            </button>
          ))}
        </div>
      </div>
      {textos.length === 0 ? (
        <p className="mt-3 text-sm text-suave">Adicione um título, uma frase de destaque ou um versículo.</p>
      ) : (
        <ul className="mt-4 flex flex-col gap-4">
          {textos.map((texto) => {
            const trecho = texto.inicio > 0 || texto.fim !== null;
            const rotulo = MODELOS.find((m) => m.tipo === texto.tipo)?.rotulo ?? "Texto";
            return (
              <li key={texto.id} className="flex flex-col gap-3 rounded-2xl border border-borda bg-surface-2/50 p-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold uppercase tracking-wider text-suave">{rotulo}</span>
                  <button
                    type="button"
                    onClick={() => aoMudar(textos.filter((t) => t.id !== texto.id))}
                    aria-label={`Remover ${rotulo.toLowerCase()}`}
                    className="text-suave hover:text-texto"
                  >
                    <Trash2 className="size-4" aria-hidden />
                  </button>
                </div>
                <textarea
                  value={texto.texto}
                  onChange={(evento) => atualizar(texto.id, { texto: evento.target.value.slice(0, 280) })}
                  rows={2}
                  aria-label={`${rotulo}: texto`}
                  placeholder={texto.tipo === "versiculo" ? "Porque Deus amou o mundo de tal maneira..." : "Escreva aqui"}
                  className="w-full resize-y rounded-xl border border-borda bg-ink px-3 py-2 text-sm outline-none focus:border-violeta"
                />
                {texto.tipo === "versiculo" ? (
                  <input
                    value={texto.referencia}
                    onChange={(evento) => atualizar(texto.id, { referencia: evento.target.value.slice(0, 40) })}
                    placeholder="João 3:16"
                    aria-label="Referência do versículo"
                    className="rounded-xl border border-borda bg-ink px-3 py-2 text-sm outline-none focus:border-violeta"
                  />
                ) : null}
                <div className="grid gap-2 sm:grid-cols-2">
                  <Opcoes rotulo="Estilo" opcoes={ESTILOS} valor={texto.estilo} aoMudar={(estilo) => atualizar(texto.id, { estilo })} />
                  <Opcoes rotulo="Posição" opcoes={POSICOES} valor={texto.posicao} aoMudar={(posicao) => atualizar(texto.id, { posicao })} />
                </div>
                <div className="flex flex-wrap items-center gap-2 text-sm">
                  <select
                    value={trecho ? "trecho" : "todo"}
                    onChange={(evento) =>
                      atualizar(
                        texto.id,
                        evento.target.value === "todo"
                          ? { inicio: 0, fim: null }
                          : { inicio: Math.round(posicaoFinal * 10) / 10, fim: Math.min(Math.round(posicaoFinal * 10) / 10 + 5, duracaoFinal) },
                      )
                    }
                    aria-label="Quando o texto aparece"
                    className="rounded-xl border border-borda bg-ink px-3 py-2 outline-none focus:border-violeta"
                  >
                    <option value="todo">O vídeo todo</option>
                    <option value="trecho">Só uma parte</option>
                  </select>
                  {trecho ? (
                    <>
                      <button
                        type="button"
                        onClick={() => atualizar(texto.id, { inicio: Math.min(Math.round(posicaoFinal * 10) / 10, (texto.fim ?? duracaoFinal) - 0.5) })}
                        className="botao-contorno px-3 py-1.5 text-xs"
                      >
                        Começa aqui
                      </button>
                      <button
                        type="button"
                        onClick={() => atualizar(texto.id, { fim: Math.max(Math.round(posicaoFinal * 10) / 10, texto.inicio + 0.5) })}
                        className="botao-contorno px-3 py-1.5 text-xs"
                      >
                        Termina aqui
                      </button>
                      <span className="tabular-nums text-suave">
                        {formatarTempo(texto.inicio)} até {formatarTempo(texto.fim ?? duracaoFinal)}
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
