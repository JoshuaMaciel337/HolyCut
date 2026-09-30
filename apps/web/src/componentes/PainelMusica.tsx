"use client";

import { Music } from "lucide-react";
import Link from "next/link";

import { formatarTempo } from "@/lib/formatar";
import type { Musica, MusicaProjeto } from "@/lib/tipos";

/** Música de fundo do vídeo: a faixa da biblioteca, o volume e se ela abaixa quando alguém fala. */
export function PainelMusica({
  musica,
  musicas,
  aoMudar,
}: {
  musica: MusicaProjeto;
  musicas: Musica[] | null;
  aoMudar: (musica: MusicaProjeto) => void;
}) {
  const escolhida = musicas?.find((item) => item.id === musica.id) ?? null;
  const inicioMaximo = Math.max((escolhida?.duracao ?? 0) - 1, 0);
  return (
    <section className="cartao p-6" aria-labelledby="titulo-musica">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id="titulo-musica" className="font-display text-lg font-bold">
          Música
        </h2>
        <Link href="/app/musicas" className="inline-flex items-center gap-1.5 text-sm text-suave hover:text-texto">
          <Music className="size-4" aria-hidden /> Biblioteca
        </Link>
      </div>
      {musicas !== null && musicas.length === 0 ? (
        <p className="mt-3 text-sm text-suave">
          A biblioteca da igreja ainda não tem músicas.{" "}
          <Link href="/app/musicas" className="text-laranja hover:underline">
            Adicionar uma música
          </Link>
        </p>
      ) : (
        <select
          value={escolhida ? escolhida.id : ""}
          onChange={(evento) => aoMudar({ ...musica, id: evento.target.value || null, inicio: 0 })}
          aria-label="Música de fundo"
          className="mt-4 w-full rounded-xl border border-borda bg-ink px-3 py-2 outline-none focus:border-violeta"
        >
          <option value="">Sem música</option>
          {(musicas ?? []).map((item) => (
            <option key={item.id} value={item.id} disabled={item.status !== "pronta"}>
              {[item.titulo, item.artista].filter(Boolean).join(" · ")}
              {item.status === "pronta" ? "" : item.status === "erro" ? " (com erro)" : " (preparando)"}
            </option>
          ))}
        </select>
      )}

      {escolhida ? (
        <div className="mt-4 flex flex-col gap-4">
          <label className="flex items-center gap-3 text-sm">
            <span className="w-24 shrink-0 text-suave">Volume</span>
            <input
              type="range"
              min={0.05}
              max={1}
              step={0.05}
              value={musica.volume}
              onChange={(evento) => aoMudar({ ...musica, volume: Number(evento.target.value) })}
              className="w-full accent-[var(--hc-orange)]"
            />
            <span className="w-12 text-right tabular-nums">{Math.round(musica.volume * 100)}%</span>
          </label>
          <label className="flex items-center gap-3 text-sm">
            <span className="w-24 shrink-0 text-suave">Começa em</span>
            <input
              type="range"
              min={0}
              max={inicioMaximo}
              step={0.5}
              value={Math.min(musica.inicio, inicioMaximo)}
              onChange={(evento) => aoMudar({ ...musica, inicio: Number(evento.target.value) })}
              className="w-full accent-[var(--hc-orange)]"
            />
            <span className="w-12 text-right tabular-nums">{formatarTempo(musica.inicio)}</span>
          </label>
          <label className="flex cursor-pointer items-start gap-3 text-sm">
            <input
              type="checkbox"
              checked={musica.abaixar_na_fala}
              onChange={(evento) => aoMudar({ ...musica, abaixar_na_fala: evento.target.checked })}
              className="mt-0.5 size-4 accent-[var(--hc-orange)]"
            />
            <span>
              Abaixar a música quando alguém fala
              <span className="block text-xs text-suave">Na prévia o efeito é aproximado; no vídeo exportado ele acompanha a voz.</span>
            </span>
          </label>
          {escolhida.licenca === "cc_by" ? (
            <p className="rounded-xl border border-amarelo/40 bg-amarelo/10 px-4 py-3 text-sm">
              Esta licença pede crédito. Coloque na legenda do post: <strong>{escolhida.atribuicao}</strong>
            </p>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
