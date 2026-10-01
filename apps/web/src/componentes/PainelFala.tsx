"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";

import { palavraCortada, textoDaPalavra } from "@/lib/fala";
import type { Legenda, NivelVicio, PalavraFala } from "@/lib/tipos";

const OPCOES: { valor: NivelVicio | "desligado"; rotulo: string; dica: string }[] = [
  { valor: "desligado", rotulo: "Desligado", dica: "Não tira vícios sozinho." },
  { valor: "leve", rotulo: "Leve", dica: "Tira né, ah, hum e parecidos." },
  { valor: "media", rotulo: "Médio", dica: "Também tira tipo, sabe, entendeu, tá e ok." },
  { valor: "forte", rotulo: "Forte", dica: "Também tira então, assim e aí. Dá para devolver qualquer palavra." },
];

function semChave(edicoes: Record<string, string>, id: string): Record<string, string> {
  if (!(id in edicoes)) return edicoes;
  const copia = { ...edicoes };
  delete copia[id];
  return copia;
}

function apagarPalavra(legenda: Legenda, id: string): Legenda {
  return {
    ...legenda,
    apagadas: legenda.apagadas.includes(id) ? legenda.apagadas : [...legenda.apagadas, id],
    mantidas: legenda.mantidas.filter((item) => item !== id),
    edicoes: semChave(legenda.edicoes, id),
  };
}

function devolverPalavra(legenda: Legenda, palavra: PalavraFala): Legenda {
  const mantidas = palavra.vicio && !legenda.mantidas.includes(palavra.id) ? [...legenda.mantidas, palavra.id] : legenda.mantidas;
  return { ...legenda, apagadas: legenda.apagadas.filter((item) => item !== palavra.id), mantidas };
}

function corrigirPalavra(legenda: Legenda, palavra: PalavraFala, texto: string): Legenda {
  const escrito = texto.trim().replace(/\s+/g, " ").slice(0, 40);
  if (!escrito) return apagarPalavra(legenda, palavra.id);
  if (escrito === palavra.texto) return { ...legenda, edicoes: semChave(legenda.edicoes, palavra.id) };
  return { ...legenda, edicoes: { ...legenda.edicoes, [palavra.id]: escrito } };
}

export function PainelFala({
  palavras,
  legenda,
  tempo,
  midiaId,
  aoMudar,
  aoSaltar,
}: {
  palavras: PalavraFala[];
  legenda: Legenda;
  tempo: number;
  midiaId: string;
  aoMudar: (legenda: Legenda) => void;
  aoSaltar: (instante: number) => void;
}) {
  const [escolhida, setEscolhida] = useState<string | null>(null);
  const [corrigindo, setCorrigindo] = useState(false);
  const [rascunho, setRascunho] = useState("");
  const ativa = useRef<HTMLButtonElement>(null);
  const lista = useRef<HTMLDivElement>(null);
  const opcao = legenda.vicios ?? "desligado";
  const dica = OPCOES.find((item) => item.valor === opcao)?.dica;
  const palavra = palavras.find((item) => item.id === escolhida) ?? null;
  const cortada = palavra ? palavraCortada(palavra, legenda) : false;

  const linhas = useMemo(() => {
    const grupos: { id: string; palavras: PalavraFala[] }[] = [];
    for (const item of palavras) {
      const ultimo = grupos[grupos.length - 1];
      if (!ultimo || ultimo.id !== item.segmento) grupos.push({ id: item.segmento || item.id, palavras: [item] });
      else ultimo.palavras.push(item);
    }
    return grupos;
  }, [palavras]);

  const idNoTempo = palavras.find((item) => tempo >= item.inicio && tempo < item.fim)?.id ?? null;
  useEffect(() => {
    const item = ativa.current;
    const caixa = lista.current;
    if (!item || !caixa) return;
    const limite = caixa.getBoundingClientRect();
    const caixaItem = item.getBoundingClientRect();
    if (caixaItem.top < limite.top || caixaItem.bottom > limite.bottom) {
      caixa.scrollTop += caixaItem.top - limite.top - caixa.clientHeight / 3;
    }
  }, [idNoTempo]);

  function escolher(item: PalavraFala) {
    setEscolhida(item.id);
    setCorrigindo(false);
    aoSaltar(item.inicio);
  }

  function salvarCorrecao() {
    if (!palavra) return;
    aoMudar(corrigirPalavra(legenda, palavra, rascunho));
    setCorrigindo(false);
  }

  return (
    <section className="cartao p-6" aria-labelledby="titulo-fala">
      <h2 id="titulo-fala" className="font-display text-lg font-bold">
        Fala
      </h2>
      <p className="mt-1 text-sm text-suave">
        Gerado por IA, para revisar. Tirar uma palavra corta esse pedaço do vídeo. Corrigir uma palavra só muda a legenda.
      </p>
      {palavras.length === 0 ? (
        <p className="mt-3 text-sm text-suave">
          Esta gravação ainda não tem transcrição.{" "}
          <Link href={`/app/midias/${midiaId}?aba=transcricao`} className="font-medium text-laranja hover:underline">
            Transcreva na página do culto
          </Link>
          .
        </p>
      ) : (
        <>
          <div role="radiogroup" aria-label="Vícios de fala" className="mt-4 grid grid-cols-4 gap-1 rounded-full border border-borda bg-ink p-1">
            {OPCOES.map((item) => (
              <button
                key={item.valor}
                type="button"
                role="radio"
                aria-checked={opcao === item.valor}
                onClick={() => aoMudar({ ...legenda, vicios: item.valor === "desligado" ? null : item.valor })}
                className={`rounded-full px-2 py-1 text-xs font-semibold ${opcao === item.valor ? "bg-surface-2 text-texto" : "text-suave hover:text-texto"}`}
              >
                {item.rotulo}
              </button>
            ))}
          </div>
          {dica ? <p className="mt-2 text-xs text-suave">{dica}</p> : null}

          {palavra ? (
            <div className="mt-3 flex flex-wrap items-center gap-2">
              {corrigindo ? (
                <form
                  className="flex flex-1 gap-2"
                  onSubmit={(evento) => {
                    evento.preventDefault();
                    salvarCorrecao();
                  }}
                >
                  <input
                    value={rascunho}
                    onChange={(evento) => setRascunho(evento.target.value)}
                    maxLength={40}
                    aria-label="Texto da legenda"
                    className="min-w-0 flex-1 rounded-lg border border-borda bg-ink px-3 py-1.5 text-sm"
                    autoFocus
                  />
                  <button type="submit" className="botao-cta px-3 py-1.5 text-sm">
                    Salvar
                  </button>
                  <button type="button" onClick={() => setCorrigindo(false)} className="botao-contorno px-3 py-1.5 text-sm">
                    Cancelar
                  </button>
                </form>
              ) : (
                <>
                  <button
                    type="button"
                    onClick={() => {
                      setRascunho(textoDaPalavra(palavra, legenda));
                      setCorrigindo(true);
                    }}
                    className="botao-contorno px-3 py-1.5 text-sm"
                  >
                    Corrigir
                  </button>
                  {cortada ? (
                    <button type="button" onClick={() => aoMudar(devolverPalavra(legenda, palavra))} className="botao-contorno px-3 py-1.5 text-sm">
                      Devolver ao vídeo
                    </button>
                  ) : (
                    <button type="button" onClick={() => aoMudar(apagarPalavra(legenda, palavra.id))} className="botao-contorno px-3 py-1.5 text-sm">
                      Tirar do vídeo
                    </button>
                  )}
                </>
              )}
            </div>
          ) : (
            <p className="mt-3 text-xs text-suave">Toque numa palavra para ir até ela na prévia.</p>
          )}

          <div ref={lista} className="mt-3 max-h-80 space-y-3 overflow-y-auto pr-1">
            {linhas.map((linha) => (
              <p key={linha.id} className="text-sm leading-7">
                <button
                  type="button"
                  onClick={() => aoMudar(linha.palavras.reduce((atual, item) => apagarPalavra(atual, item.id), legenda))}
                  className="mr-2 align-middle text-xs text-suave hover:text-texto"
                >
                  Tirar frase
                </button>
                {linha.palavras.map((item) => {
                  const fora = palavraCortada(item, legenda);
                  const noTempo = item.id === idNoTempo;
                  const selecionada = item.id === escolhida;
                  return (
                    <button
                      key={item.id}
                      ref={noTempo ? ativa : undefined}
                      type="button"
                      onClick={() => escolher(item)}
                      aria-pressed={selecionada}
                      className={`mr-1 rounded px-0.5 ${fora ? "text-suave line-through" : ""} ${selecionada ? "bg-laranja/20" : ""} ${noTempo && !fora ? "text-laranja" : ""}`}
                    >
                      {textoDaPalavra(item, legenda)}
                    </button>
                  );
                })}
              </p>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
