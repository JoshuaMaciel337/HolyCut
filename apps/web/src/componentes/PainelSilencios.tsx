"use client";

import { Scissors } from "lucide-react";

import { formatarTempo } from "@/lib/formatar";
import type { Intensidade, Silencios } from "@/lib/tipos";

export type OpcaoCorte = Intensidade | "desligado";

const OPCOES: { valor: OpcaoCorte; rotulo: string; dica: string }[] = [
  { valor: "desligado", rotulo: "Sem corte", dica: "Mantém a gravação inteira." },
  { valor: "leve", rotulo: "Leve", dica: "Só pausas longas, de 1 s ou mais, quase sem som." },
  { valor: "media", rotulo: "Médio", dica: "Pausas a partir de 0,6 s. Bom para a maioria das pregações." },
  { valor: "forte", rotulo: "Forte", dica: "Pausas a partir de 0,35 s. Ritmo de Reels, mais dinâmico." },
];

type Props = {
  opcao: OpcaoCorte;
  aoMudar: (opcao: OpcaoCorte) => void;
  dados: Silencios | null;
  carregando: boolean;
  duracao: number;
  pular: boolean;
  aoMudarPular: (pular: boolean) => void;
  erro?: string;
};

export function PainelSilencios({ opcao, aoMudar, dados, carregando, duracao, pular, aoMudarPular, erro }: Props) {
  const ativo = opcao !== "desligado" && dados !== null;
  const dica = OPCOES.find((item) => item.valor === opcao)?.dica;

  return (
    <section className="cartao p-6" aria-labelledby="titulo-silencios">
      <h2 id="titulo-silencios" className="flex items-center gap-2 font-display text-lg font-bold">
        <Scissors className="size-5 text-laranja" aria-hidden /> Cortar silêncios
      </h2>
      <div role="radiogroup" aria-label="Intensidade do corte" className="mt-4 grid grid-cols-4 gap-1 rounded-full border border-borda bg-ink p-1">
        {OPCOES.map((item) => (
          <button
            key={item.valor}
            type="button"
            role="radio"
            aria-checked={opcao === item.valor}
            onClick={() => aoMudar(item.valor)}
            className={`whitespace-nowrap rounded-full px-1 py-1.5 text-xs font-semibold transition ${
              opcao === item.valor ? "text-white" : "text-suave hover:text-texto"
            }`}
            style={opcao === item.valor ? { backgroundImage: "var(--hc-gradient-cta)" } : undefined}
          >
            {item.rotulo}
          </button>
        ))}
      </div>
      <p className="mt-3 text-sm text-suave">{dica}</p>

      <div className="mt-4 rounded-2xl bg-ink px-4 py-3" aria-live="polite">
        {opcao === "desligado" ? (
          <p className="text-sm text-suave">Duração: {formatarTempo(duracao)}</p>
        ) : erro && !dados ? (
          <p className="text-sm text-vermelho">{erro}</p>
        ) : carregando || !dados ? (
          <p className="text-sm text-suave">Procurando os silêncios...</p>
        ) : (
          <>
            <p className="text-sm">
              Sai <strong>{formatarTempo(dados.tempo_cortado)}</strong> em {dados.silencios.length}{" "}
              {dados.silencios.length === 1 ? "trecho" : "trechos"}
            </p>
            <p className="text-sm text-suave">
              O vídeo fica com <strong className="text-texto">{formatarTempo(dados.duracao_final)}</strong> de{" "}
              {formatarTempo(duracao)}
            </p>
          </>
        )}
      </div>

      <label className={`mt-4 flex items-center gap-3 text-sm ${ativo ? "" : "opacity-50"}`}>
        <input
          type="checkbox"
          checked={pular}
          disabled={!ativo}
          onChange={(evento) => aoMudarPular(evento.target.checked)}
          className="size-4 accent-[var(--hc-orange)]"
        />
        Pular os silêncios ao tocar a prévia
      </label>
    </section>
  );
}
