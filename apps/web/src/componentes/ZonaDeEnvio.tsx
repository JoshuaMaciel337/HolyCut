"use client";

import { UploadCloud } from "lucide-react";
import { useRef, useState } from "react";

import { ACEITAR_ARQUIVOS, useEnvios } from "@/lib/envios";

export function ZonaDeEnvio() {
  const { iniciar } = useEnvios();
  const entrada = useRef<HTMLInputElement>(null);
  const [arrastando, setArrastando] = useState(false);

  function receber(lista: FileList | null) {
    if (lista && lista.length > 0) iniciar(Array.from(lista));
  }

  return (
    <section
      aria-labelledby="titulo-envio"
      onDragOver={(evento) => {
        evento.preventDefault();
        setArrastando(true);
      }}
      onDragLeave={() => setArrastando(false)}
      onDrop={(evento) => {
        evento.preventDefault();
        setArrastando(false);
        receber(evento.dataTransfer.files);
      }}
      className={`flex flex-col items-start gap-5 rounded-[22px] border-2 border-dashed p-6 transition sm:flex-row sm:items-center sm:p-8 ${
        arrastando ? "border-laranja bg-laranja/10" : "border-borda bg-surface"
      }`}
    >
      <span
        className="flex size-16 shrink-0 items-center justify-center rounded-2xl"
        style={{ backgroundImage: "var(--hc-gradient-cta)", boxShadow: "var(--hc-shadow-glow-violet)" }}
      >
        <UploadCloud className="size-8 text-white" aria-hidden />
      </span>
      <div className="flex-1">
        <h2 id="titulo-envio" className="font-display text-xl font-bold">
          Envie a gravação do culto
        </h2>
        <p className="mt-1 max-w-xl text-sm text-suave">
          Arraste o arquivo para cá ou escolha no computador ou no celular. Pode ser grande: se a internet cair, o envio
          continua de onde parou.
        </p>
        <p className="mt-2 text-xs text-suave">Vídeo (MP4, MOV, MKV e outros) ou áudio (MP3, WAV, M4A).</p>
      </div>
      <button type="button" className="botao-cta w-full sm:w-auto" onClick={() => entrada.current?.click()}>
        Escolher arquivo
      </button>
      <input
        ref={entrada}
        type="file"
        multiple
        accept={ACEITAR_ARQUIVOS}
        className="sr-only"
        tabIndex={-1}
        aria-hidden
        onChange={(evento) => {
          receber(evento.target.files);
          evento.target.value = "";
        }}
      />
    </section>
  );
}
