"use client";

import { ImageIcon, Search, Trash2, Video } from "lucide-react";
import { useState } from "react";

import { chamarApi, ErroApi } from "@/lib/api";
import { formatarTempo } from "@/lib/formatar";
import type { ApoioProjeto, ResultadoBanco, SugestaoBanco } from "@/lib/tipos";

type Props = {
  frase: string;
  posicaoFinal: number;
  apoios: ApoioProjeto[];
  aoMudar: (apoios: ApoioProjeto[]) => void;
  usando: boolean;
  aoUsar: (tipo: "imagem" | "video", pixabayId: number) => void;
  aoFalhar: (mensagem: string) => void;
};

/** Busca foto e vídeo na Pixabay a partir da frase que está sendo dita. */
export function PainelBanco({ frase, posicaoFinal, apoios, aoMudar, usando, aoUsar, aoFalhar }: Props) {
  const [consulta, setConsulta] = useState("");
  const [tipo, setTipo] = useState<"imagem" | "video">("imagem");
  const [resultados, setResultados] = useState<ResultadoBanco[]>([]);
  const [buscando, setBuscando] = useState(false);
  const [sugerindo, setSugerindo] = useState(false);

  const buscar = async (texto: string, qual: "imagem" | "video") => {
    const q = texto.trim();
    if (q.length < 2) {
      aoFalhar("Escreva pelo menos duas letras para buscar.");
      return;
    }
    setBuscando(true);
    aoFalhar("");
    try {
      setResultados(await chamarApi<ResultadoBanco[]>(`/banco/buscar?q=${encodeURIComponent(q)}&tipo=${qual}`));
    } catch (e) {
      setResultados([]);
      aoFalhar(e instanceof ErroApi ? e.message : "Não foi possível buscar na Pixabay.");
    } finally {
      setBuscando(false);
    }
  };

  const sugerir = async () => {
    if (frase.trim().length < 2) {
      aoFalhar("Avance o vídeo até uma frase da pregação para sugerir a busca.");
      return;
    }
    setSugerindo(true);
    aoFalhar("");
    try {
      const sugestao = await chamarApi<SugestaoBanco>("/banco/sugerir", { metodo: "POST", corpo: { frase } });
      if (!sugestao.usar || sugestao.consulta.length < 2) {
        aoFalhar("Essa frase não sugere uma imagem. Escreva a busca você mesmo.");
        return;
      }
      setConsulta(sugestao.consulta);
      setTipo(sugestao.tipo);
      await buscar(sugestao.consulta, sugestao.tipo);
    } catch (e) {
      aoFalhar(e instanceof ErroApi ? e.message : "Não foi possível sugerir a busca.");
    } finally {
      setSugerindo(false);
    }
  };

  return (
    <section className="cartao p-6" aria-labelledby="titulo-banco">
      <h2 id="titulo-banco" className="font-display text-lg font-bold">
        Banco de imagens
      </h2>
      <p className="mt-1 text-sm text-suave">
        A foto entra em Figura. O vídeo cobre o quadro nesta parte, e o som continua o da pregação. Pixabay, uso dentro do vídeo.
      </p>
      {frase ? (
        <p className="mt-3 text-sm">
          <span className="text-suave">Frase neste ponto: </span>
          {frase}
        </p>
      ) : null}
      <div className="mt-4 flex flex-col gap-2">
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setTipo("imagem")}
            className={tipo === "imagem" ? "botao-cta px-3 py-1.5 text-xs" : "botao-contorno px-3 py-1.5 text-xs"}
          >
            <ImageIcon className="size-3.5" aria-hidden /> Foto
          </button>
          <button
            type="button"
            onClick={() => setTipo("video")}
            className={tipo === "video" ? "botao-cta px-3 py-1.5 text-xs" : "botao-contorno px-3 py-1.5 text-xs"}
          >
            <Video className="size-3.5" aria-hidden /> Vídeo
          </button>
        </div>
        <label className="flex gap-2">
          <span className="sr-only">Busca</span>
          <input
            value={consulta}
            onChange={(evento) => setConsulta(evento.target.value)}
            onKeyDown={(evento) => {
              if (evento.key === "Enter") void buscar(consulta, tipo);
            }}
            maxLength={100}
            placeholder="luz, igreja, céu"
            className="w-full rounded-xl border border-borda bg-ink px-3 py-2 text-sm outline-none focus:border-violeta"
          />
          <button type="button" disabled={buscando} onClick={() => void buscar(consulta, tipo)} className="botao-cta px-3" aria-label="Buscar">
            <Search className="size-4" aria-hidden />
          </button>
        </label>
        <button type="button" disabled={sugerindo || buscando} onClick={() => void sugerir()} className="botao-contorno px-3 py-1.5 text-xs">
          {sugerindo ? "Sugerindo…" : "Sugerir pela frase"}
        </button>
      </div>
      {buscando ? <p className="mt-3 text-sm text-suave">Buscando na Pixabay…</p> : null}
      {resultados.length > 0 ? (
        <ul className="mt-4 grid grid-cols-2 gap-3">
          {resultados.map((item) => (
            <li key={`${item.tipo}-${item.id}`} className="flex flex-col gap-2">
              {/* A miniatura é temporária, só para escolher. O arquivo usado fica no armazenamento da igreja. */}
              <img src={item.miniatura} alt={item.nome} className="aspect-video w-full rounded-xl object-cover" />
              <p className="truncate text-xs text-suave">Pixabay · {item.autor || "autor"}</p>
              <button
                type="button"
                disabled={usando}
                onClick={() => aoUsar(item.tipo, item.id)}
                className="botao-contorno px-3 py-1.5 text-xs"
              >
                {usando ? "Baixando…" : `Usar em ${formatarTempo(posicaoFinal)}`}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
      {apoios.length > 0 ? (
        <ul className="mt-4 flex flex-col gap-3">
          {apoios.map((apoio) => (
            <li key={apoio.id} className="rounded-2xl border border-borda bg-surface-2/50 p-4">
              <div className="flex items-center justify-between gap-2">
                <span className="truncate text-sm font-semibold">{apoio.nome}</span>
                <button
                  type="button"
                  onClick={() => aoMudar(apoios.filter((item) => item.id !== apoio.id))}
                  aria-label={`Remover ${apoio.nome}`}
                  className="text-suave hover:text-texto"
                >
                  <Trash2 className="size-4" aria-hidden />
                </button>
              </div>
              {apoio.credito ? <p className="mt-1 text-xs text-suave">{apoio.credito}</p> : null}
              <p className="mt-1 text-xs text-suave">
                {formatarTempo(apoio.inicio)}
                {apoio.fim !== null ? ` – ${formatarTempo(apoio.fim)}` : ""}
              </p>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
