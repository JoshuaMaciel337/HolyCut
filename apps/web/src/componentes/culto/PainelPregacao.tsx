"use client";

import { Clapperboard, Mic } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { chamarApi, ErroApi } from "@/lib/api";
import { formatarTempo } from "@/lib/formatar";
import type { Midia, Projeto } from "@/lib/tipos";

const MINIMO_SEGUNDOS = 30;

type Props = {
  midia: Midia;
  tempo: number;
  /** A marcação sendo ajustada, que aparece com alças na forma de onda. Nula fora do ajuste. */
  rascunho: [number, number] | null;
  aoMudarRascunho: (faixa: [number, number] | null) => void;
  /** A pregação que a análise dos blocos encontrou, para voltar a ela depois de mexer. */
  sugestao: { inicio: number; fim: number } | null;
  aoBuscar: (segundos: number) => void;
  aoMudar: (midia: Midia) => void;
};

function duracaoEmMinutos(segundos: number): string {
  const minutos = Math.round(segundos / 60);
  return minutos >= 1 ? `${minutos} min` : `${Math.round(segundos)} s`;
}

/** Onde a mensagem começa e termina, e o vídeo 16:9 só dela, sem louvor nem avisos. */
export function PainelPregacao({ midia, tempo, rascunho, aoMudarRascunho, sugestao, aoBuscar, aoMudar }: Props) {
  const router = useRouter();
  const [erro, setErro] = useState("");
  const [salvando, setSalvando] = useState(false);
  const duracao = midia.duracao ?? 0;
  const marcada = midia.pregacao;

  async function enviar(acao: () => Promise<void>) {
    setErro("");
    setSalvando(true);
    try {
      await acao();
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível salvar a pregação.");
    } finally {
      setSalvando(false);
    }
  }

  const salvar = () =>
    enviar(async () => {
      if (!rascunho) return;
      const [inicio, fim] = rascunho.map((s) => Math.round(s * 100) / 100);
      aoMudar(await chamarApi<Midia>(`/midias/${midia.id}/pregacao`, { metodo: "PUT", corpo: { inicio, fim } }));
      aoMudarRascunho(null);
    });

  const desmarcar = () =>
    enviar(async () => {
      aoMudar(await chamarApi<Midia>(`/midias/${midia.id}/pregacao`, { metodo: "DELETE" }));
    });

  const criarVideo = () =>
    enviar(async () => {
      const projeto = await chamarApi<Projeto>(`/midias/${midia.id}/pregacao/projeto`, { metodo: "POST" });
      router.push(`/app/projetos/${projeto.id}`);
    });

  function comecarAjuste() {
    if (marcada) aoMudarRascunho([marcada.inicio, marcada.fim]);
    else if (sugestao) aoMudarRascunho([sugestao.inicio, sugestao.fim]);
    else aoMudarRascunho([tempo, Math.min(tempo + 40 * 60, duracao)]);   // uma pregação típica, a ajustar
  }

  const curta = rascunho ? rascunho[1] - rascunho[0] < MINIMO_SEGUNDOS : false;
  const sugestaoDiferente =
    sugestao && rascunho && (Math.abs(sugestao.inicio - rascunho[0]) > 0.5 || Math.abs(sugestao.fim - rascunho[1]) > 0.5);

  return (
    <section className="cartao p-6" aria-labelledby="titulo-pregacao">
      <h2 id="titulo-pregacao" className="flex items-center gap-2 font-display text-lg font-bold">
        <Mic className="size-5 text-magenta" aria-hidden /> Pregação
      </h2>
      <p className="mt-1 text-sm text-suave">Marque onde a mensagem começa e termina para exportar só ela em 16:9, sem louvor nem avisos.</p>

      {rascunho ? (
        <div className="mt-4 flex flex-col gap-3">
          <p className="text-sm tabular-nums">
            {formatarTempo(rascunho[0])} → {formatarTempo(rascunho[1])}{" "}
            <span className="text-suave">· {duracaoEmMinutos(rascunho[1] - rascunho[0])}</span>
          </p>
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => aoMudarRascunho([Math.min(tempo, rascunho[1] - 1), rascunho[1]])}
              className="botao-contorno px-3 py-2 text-sm"
            >
              Começa aqui
            </button>
            <button
              type="button"
              onClick={() => aoMudarRascunho([rascunho[0], Math.max(tempo, rascunho[0] + 1)])}
              className="botao-contorno px-3 py-2 text-sm"
            >
              Termina aqui
            </button>
          </div>
          <p className="text-xs text-suave">
            Os botões usam o ponto do player ({formatarTempo(tempo)}). Também dá para arrastar as bordas laranja na forma de onda.
          </p>
          {sugestao && sugestaoDiferente ? (
            <button type="button" onClick={() => aoMudarRascunho([sugestao.inicio, sugestao.fim])} className="self-start text-sm text-laranja hover:underline">
              Voltar para a que a IA encontrou ({formatarTempo(sugestao.inicio)} → {formatarTempo(sugestao.fim)})
            </button>
          ) : null}
          {curta ? <p className="text-sm text-vermelho">A pregação precisa ter pelo menos 30 segundos.</p> : null}
          <div className="flex flex-wrap gap-2">
            <button type="button" onClick={salvar} disabled={salvando || curta} className="botao-cta">
              Salvar a marcação
            </button>
            <button type="button" onClick={() => aoMudarRascunho(null)} className="botao-contorno px-4 py-2 text-sm">
              Cancelar
            </button>
          </div>
        </div>
      ) : marcada ? (
        <div className="mt-4 flex flex-col gap-3">
          <p className="text-sm tabular-nums">
            {formatarTempo(marcada.inicio)} → {formatarTempo(marcada.fim)}{" "}
            <span className="text-suave">· {duracaoEmMinutos(marcada.fim - marcada.inicio)}</span>
          </p>
          <p className="text-xs text-suave">
            {marcada.origem === "ia" ? "Encontrada pela IA. Ouça o começo e o fim antes de exportar." : "Marcada por você."}
          </p>
          <div className="flex flex-wrap gap-2">
            <button type="button" onClick={() => aoBuscar(marcada.inicio)} className="botao-contorno px-3 py-2 text-sm">
              Ouvir o começo
            </button>
            <button type="button" onClick={() => aoBuscar(Math.max(marcada.fim - 15, marcada.inicio))} className="botao-contorno px-3 py-2 text-sm">
              Ouvir o fim
            </button>
            <button type="button" onClick={comecarAjuste} className="botao-contorno px-3 py-2 text-sm">
              Ajustar
            </button>
          </div>
          {midia.video ? (
            <button type="button" onClick={criarVideo} disabled={salvando} className="botao-cta">
              <Clapperboard className="size-4" aria-hidden /> Criar o vídeo 16:9 da mensagem
            </button>
          ) : null}
          <button type="button" onClick={desmarcar} disabled={salvando} className="self-start text-xs text-suave hover:text-vermelho">
            Tirar a marcação
          </button>
        </div>
      ) : (
        <div className="mt-4">
          <button type="button" onClick={comecarAjuste} disabled={!duracao} className="botao-contorno px-4 py-2 text-sm">
            {sugestao ? "Conferir a que a IA encontrou" : "Marcar a pregação"}
          </button>
        </div>
      )}
      {erro ? (
        <p className="mt-3 text-sm text-vermelho" role="alert">
          {erro}
        </p>
      ) : null}
    </section>
  );
}
