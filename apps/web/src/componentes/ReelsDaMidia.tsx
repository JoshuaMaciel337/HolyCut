"use client";

import { ChevronRight, Clapperboard, Sparkles } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { chamarApi, ErroApi } from "@/lib/api";
import { formatarTempo } from "@/lib/formatar";
import type { Midia, Projeto } from "@/lib/tipos";

/** Reels feitos a partir de uma gravação, e o botão para começar outro. */
export function ReelsDaMidia({ midia, tempoAtual = 0 }: { midia: Midia; tempoAtual?: number }) {
  const router = useRouter();
  const [projetos, setProjetos] = useState<Projeto[] | null>(null);
  const [criando, setCriando] = useState(false);
  const [erro, setErro] = useState("");
  const podeCriar = midia.status === "pronta" && midia.video !== null;

  useEffect(() => {
    let cancelado = false;
    chamarApi<Projeto[]>(`/projetos?midia_id=${midia.id}`)
      .then((lista) => {
        if (!cancelado) setProjetos(lista);
      })
      .catch(() => undefined);
    return () => {
      cancelado = true;
    };
  }, [midia.id]);

  async function criar() {
    setCriando(true);
    setErro("");
    try {
      const projeto = await chamarApi<Projeto>("/projetos", { metodo: "POST", corpo: { midia_id: midia.id } });
      router.push(`/app/projetos/${projeto.id}`);
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível criar o Reel.");
      setCriando(false);
    }
  }

  return (
    <section className="cartao p-6" aria-labelledby="titulo-reels">
      <h2 id="titulo-reels" className="font-display text-lg font-bold">
        Reels e Stories desta gravação
      </h2>
      {projetos && projetos.length > 0 ? (
        <ul className="mt-3 flex flex-col">
          {projetos.map((projeto) => (
            <li key={projeto.id} className="border-b border-borda last:border-0">
              <Link href={`/app/projetos/${projeto.id}`} className="flex items-center justify-between gap-3 py-2.5 text-sm hover:text-laranja">
                <span className="min-w-0">
                  <span className="block truncate font-medium">{projeto.nome}</span>
                  <span className="text-xs text-suave">
                    {projeto.tipo === "story" ? "Story" : "Reel"} · {projeto.proporcao} ·{" "}
                    {formatarTempo(projeto.trecho.fim - projeto.trecho.inicio)} escolhidos
                  </span>
                </span>
                <ChevronRight className="size-4 shrink-0" aria-hidden />
              </Link>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-sm text-suave">
          {podeCriar
            ? "Escolha o trecho, enquadre em 9:16 e exporte com o corte de silêncios."
            : "Para criar um Reel, a gravação precisa estar pronta e ter vídeo."}
        </p>
      )}
      {erro ? <p className="mt-3 text-sm text-vermelho">{erro}</p> : null}
      <div className="mt-4 flex flex-col gap-2">
        <button type="button" onClick={criar} disabled={!podeCriar || criando} className="botao-cta w-full">
          <Clapperboard className="size-4" aria-hidden /> {criando ? "Criando..." : "Criar um Reel"}
        </button>
        {podeCriar ? (
          <Link href={`/app/midias/${midia.id}/story?inicio=${Math.floor(tempoAtual)}`} className="botao-contorno w-full">
            <Sparkles className="size-4 text-amarelo" aria-hidden /> Criar um Story a partir de {formatarTempo(tempoAtual)}
          </Link>
        ) : null}
      </div>
    </section>
  );
}
