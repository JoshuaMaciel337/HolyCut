"use client";

import { ImageUp, RotateCcw } from "lucide-react";
import Image from "next/image";
import { useRef, useState } from "react";

import { urlPoster } from "@/lib/acervo";
import { ErroApi, chamarApi } from "@/lib/api";
import type { Midia } from "@/lib/tipos";

/** O pôster do culto e o fundo dele: um quadro da gravação ou uma imagem enviada. */
export function CapaDoCulto({ midia, aoMudar }: { midia: Midia; aoMudar: (midia: Midia) => void }) {
  const entrada = useRef<HTMLInputElement>(null);
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);

  async function enviar(arquivo: File | undefined) {
    if (!arquivo) return;
    setErro("");
    setEnviando(true);
    try {
      const resposta = await fetch(`/api/midias/${midia.id}/capa/imagem`, {
        method: "PUT",
        body: arquivo,
        headers: { "Content-Type": arquivo.type || "application/octet-stream" },
        credentials: "same-origin",
      });
      const dados = await resposta.json();
      if (!resposta.ok) throw new ErroApi(resposta.status, dados?.detail ?? "Não foi possível enviar a imagem.");
      aoMudar(dados);
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível enviar a imagem.");
    } finally {
      setEnviando(false);
      if (entrada.current) entrada.current.value = "";
    }
  }

  async function voltarAoQuadro() {
    try {
      aoMudar(await chamarApi<Midia>(`/midias/${midia.id}/capa/imagem`, { metodo: "DELETE" }));
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível voltar ao quadro do vídeo.");
    }
  }

  return (
    <section className="cartao p-6" aria-labelledby="titulo-capa">
      <h2 id="titulo-capa" className="font-display text-lg font-bold">
        Capa no acervo
      </h2>
      <div className="mt-4 flex gap-4">
        <span className="relative block aspect-[2/3] w-32 shrink-0 overflow-hidden rounded-xl bg-surface-2 ring-1 ring-borda">
          {midia.capa_versao ? <Image src={urlPoster(midia.id, midia.capa_versao)} alt="Pôster do culto" fill unoptimized sizes="128px" className="object-cover" /> : null}
        </span>
        <div className="flex min-w-0 flex-col gap-2 text-sm">
          <p className="text-suave">
            {midia.capa_personalizada
              ? "O fundo é a imagem que você enviou."
              : midia.video
                ? "O fundo é um quadro da gravação. Na aba Gravação, pause no quadro que quiser e toque em Usar na capa."
                : "Sem vídeo, o fundo leva a cor da igreja. Você pode enviar uma imagem."}
          </p>
          <button type="button" onClick={() => entrada.current?.click()} disabled={enviando} className="botao-contorno self-start px-3 py-2 text-sm">
            <ImageUp className="size-4" aria-hidden /> {enviando ? "Enviando..." : "Enviar uma imagem"}
          </button>
          {midia.capa_personalizada ? (
            <button type="button" onClick={voltarAoQuadro} className="inline-flex items-center gap-1.5 self-start text-xs text-suave hover:text-texto">
              <RotateCcw className="size-3.5" aria-hidden /> Voltar ao quadro do vídeo
            </button>
          ) : null}
          <input ref={entrada} type="file" accept="image/png,image/jpeg,image/webp" className="sr-only" onChange={(evento) => enviar(evento.target.files?.[0])} />
          {erro ? <p className="text-xs text-vermelho">{erro}</p> : null}
        </div>
      </div>
    </section>
  );
}
