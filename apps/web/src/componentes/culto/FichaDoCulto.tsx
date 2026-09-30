"use client";

import { Check } from "lucide-react";
import { type FormEvent, useEffect, useState } from "react";

import { chamarApi, ErroApi } from "@/lib/api";
import type { Acervo, Midia } from "@/lib/tipos";

const CAMPO = "rounded-xl border border-borda bg-ink px-3 py-2.5 text-sm outline-none focus:border-violeta";

/** Título, data, pregador, série e descrição do culto. Salvar redesenha as capas. */
export function FichaDoCulto({ midia, aoSalvar }: { midia: Midia; aoSalvar: (midia: Midia) => void }) {
  const [salvando, setSalvando] = useState(false);
  const [salvo, setSalvo] = useState(false);
  const [erro, setErro] = useState("");
  const [sugestoes, setSugestoes] = useState<{ series: string[]; pregadores: string[] }>({ series: [], pregadores: [] });

  // Séries e pregadores já usados, para completar enquanto digita
  useEffect(() => {
    chamarApi<Acervo>("/acervo")
      .then((acervo) => setSugestoes({ series: acervo.series, pregadores: acervo.pregadores }))
      .catch(() => undefined);
  }, []);

  async function salvar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    const dados = new FormData(evento.currentTarget);
    const texto = (nome: string) => String(dados.get(nome) ?? "").trim();
    setSalvando(true);
    setSalvo(false);
    setErro("");
    try {
      const atualizada = await chamarApi<Midia>(`/midias/${midia.id}`, {
        metodo: "PATCH",
        corpo: {
          nome: texto("titulo") || midia.nome,
          ficha: { data: texto("data") || null, pregador: texto("pregador"), serie: texto("serie"), descricao: texto("descricao") },
        },
      });
      aoSalvar(atualizada);
      setSalvo(true);
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível salvar a ficha.");
    } finally {
      setSalvando(false);
    }
  }

  return (
    <section className="cartao p-6" aria-labelledby="titulo-ficha">
      <h2 id="titulo-ficha" className="font-display text-lg font-bold">
        Ficha do culto
      </h2>
      <form onSubmit={salvar} className="mt-4 grid gap-4 sm:grid-cols-2" onChange={() => setSalvo(false)}>
        <label className="flex flex-col gap-1.5 sm:col-span-2">
          <span className="text-sm font-medium">Título</span>
          <input name="titulo" defaultValue={midia.nome} maxLength={120} required className={CAMPO} />
        </label>
        <label className="flex flex-col gap-1.5">
          <span className="text-sm font-medium">Data do culto</span>
          <input name="data" type="date" defaultValue={midia.ficha.data} className={CAMPO} />
        </label>
        <label className="flex flex-col gap-1.5">
          <span className="text-sm font-medium">Pregador</span>
          <input name="pregador" defaultValue={midia.ficha.pregador} maxLength={80} list="pregadores-da-igreja" placeholder="Ex.: Pr. João" className={CAMPO} />
          <datalist id="pregadores-da-igreja">
            {sugestoes.pregadores.map((nome) => (
              <option key={nome} value={nome} />
            ))}
          </datalist>
        </label>
        <label className="flex flex-col gap-1.5 sm:col-span-2">
          <span className="text-sm font-medium">Série</span>
          <input name="serie" defaultValue={midia.ficha.serie} maxLength={80} list="series-da-igreja" placeholder="Opcional. Ex.: Romanos, Família" className={CAMPO} />
          <datalist id="series-da-igreja">
            {sugestoes.series.map((nome) => (
              <option key={nome} value={nome} />
            ))}
          </datalist>
        </label>
        <label className="flex flex-col gap-1.5 sm:col-span-2">
          <span className="text-sm font-medium">Descrição</span>
          <textarea name="descricao" defaultValue={midia.ficha.descricao} maxLength={500} rows={3} placeholder="Opcional. Do que tratou a mensagem" className={CAMPO} />
        </label>
        <div className="flex flex-wrap items-center gap-3 sm:col-span-2">
          <button type="submit" disabled={salvando} className="botao-cta">
            {salvando ? "Salvando..." : "Salvar a ficha"}
          </button>
          {salvo ? (
            <span className="inline-flex items-center gap-1.5 text-sm text-ciano">
              <Check className="size-4" aria-hidden /> Salva. As capas estão sendo redesenhadas.
            </span>
          ) : null}
          {erro ? <span className="text-sm text-vermelho">{erro}</span> : null}
        </div>
      </form>
    </section>
  );
}
