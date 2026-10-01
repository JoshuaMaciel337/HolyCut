"use client";

import { AudioLines } from "lucide-react";

import type { Limpeza } from "@/lib/tipos";

type Props = {
  ligada: boolean;
  pronta: boolean;
  temAudio: boolean;
  estado: Limpeza | null;
  aoMudar: (ligada: boolean) => void;
  aoTentarDeNovo: () => void;
};

export function PainelAudio({ ligada, pronta, temAudio, estado, aoMudar, aoTentarDeNovo }: Props) {
  const andando = ligada && !pronta && (estado?.status === "pendente" || estado?.status === "executando");
  const falhou = ligada && !pronta && estado?.status === "erro";

  return (
    <section className="cartao p-6" aria-labelledby="titulo-audio">
      <h2 id="titulo-audio" className="flex items-center gap-2 font-display text-lg font-bold">
        <AudioLines className="size-5 text-ciano" aria-hidden /> Limpar o áudio
      </h2>
      <p className="mt-2 text-sm text-suave">
        Tira o ruído do ar-condicionado e o eco da nave. A fala continua a mesma, e o texto não muda.
      </p>
      <label className="mt-4 flex items-start gap-3 text-sm">
        <input
          type="checkbox"
          className="mt-1 size-4 accent-ciano"
          checked={ligada}
          disabled={!temAudio}
          onChange={(evento) => aoMudar(evento.target.checked)}
        />
        <span>
          Usar o áudio limpo neste vídeo
          <span className="mt-1 block text-suave">
            {!temAudio
              ? "Esta gravação não tem áudio."
              : pronta && ligada
                ? "A prévia e a exportação usam o áudio limpo. Desligar volta ao original."
                : "Desligada, a exportação usa o áudio original. A limpeza, se já começou, termina em segundo plano."}
          </span>
        </span>
      </label>
      {andando ? (
        <p className="mt-3 text-sm text-suave" role="status">
          {estado?.mensagem || "Na fila"} · {estado?.progresso ?? 0}%
        </p>
      ) : null}
      {falhou ? (
        <p className="mt-3 text-sm text-vermelho" role="alert">
          {estado?.erro || "Não foi possível limpar o áudio."}{" "}
          <button type="button" onClick={aoTentarDeNovo} className="font-semibold underline">
            Tentar de novo
          </button>
        </p>
      ) : null}
    </section>
  );
}
