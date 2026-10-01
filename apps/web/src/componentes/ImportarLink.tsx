"use client";

import { Link2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { chamarApi, ErroApi } from "@/lib/api";
import type { Midia } from "@/lib/tipos";

const LINK_DO_DRIVE = /(drive|docs)\.google\.com/i;

/** A gravação pelo link: do YouTube, só do canal da igreja; do Google Drive, com a confirmação de que é da igreja. */
export function ImportarLink({ aoImportar }: { aoImportar: (midia: Midia) => void }) {
  const [url, setUrl] = useState("");
  const [confirmo, setConfirmo] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState("");
  const doDrive = LINK_DO_DRIVE.test(url);

  async function importar(evento: React.FormEvent) {
    evento.preventDefault();
    setErro("");
    setEnviando(true);
    try {
      const midia = await chamarApi<Midia>("/midias/importar", {
        metodo: "POST",
        corpo: { url: url.trim(), confirmo_que_e_da_igreja: doDrive && confirmo },
      });
      setUrl("");
      setConfirmo(false);
      aoImportar(midia);
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível importar o vídeo.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form onSubmit={importar} className="cartao flex flex-col gap-3 p-4 sm:p-5" aria-labelledby="titulo-importar">
      <h2 id="titulo-importar" className="flex items-center gap-2 text-sm font-semibold">
        <Link2 className="size-4 text-violeta" aria-hidden /> Ou importe pelo link
      </h2>
      <div className="flex flex-col gap-2 sm:flex-row">
        <input
          type="text"
          inputMode="url"
          value={url}
          onChange={(evento) => setUrl(evento.target.value)}
          placeholder="Link da live no YouTube ou do vídeo no Google Drive"
          aria-label="Link do vídeo"
          maxLength={500}
          className="min-w-0 flex-1 rounded-xl border border-borda bg-ink px-4 py-2.5 text-sm text-texto outline-none transition placeholder:text-suave/60 focus:border-violeta focus:ring-2 focus:ring-violeta/30"
        />
        <button type="submit" disabled={enviando || !url.trim() || (doDrive && !confirmo)} className="botao-cta">
          {enviando ? "Importando..." : "Importar"}
        </button>
      </div>
      {doDrive ? (
        <label className="flex items-start gap-2 text-sm">
          <input type="checkbox" checked={confirmo} onChange={(evento) => setConfirmo(evento.target.checked)} className="mt-0.5" />
          Confirmo que este vídeo é da nossa igreja.
        </label>
      ) : null}
      <p className="text-xs text-suave">
        Do YouTube, só vídeos do canal da igreja,{" "}
        <Link href="/app/envio-automatico" className="text-laranja hover:underline">
          cadastrado em Envio automático
        </Link>
        . Se a live ainda estiver no ar, o HolyCut espera ela terminar.
      </p>
      {erro ? (
        <p role="alert" className="text-sm text-vermelho">
          {erro}
        </p>
      ) : null}
    </form>
  );
}
