import { Clapperboard, Play } from "lucide-react";
import Image from "next/image";
import Link from "next/link";

import { dataDoCulto, urlBanner } from "@/lib/acervo";
import { formatarTempo } from "@/lib/formatar";
import type { CultoResumo } from "@/lib/tipos";

/** O banner grande do topo do acervo: o culto mais recente, com assistir e ver os cortes. */
export function DestaqueCulto({ culto }: { culto: CultoResumo }) {
  const detalhes = [culto.pregador, dataDoCulto(culto.data), culto.duracao ? formatarTempo(culto.duracao) : ""].filter(Boolean);
  const temBanner = Boolean(culto.capa_versao);
  return (
    <section aria-labelledby="titulo-destaque" className="overflow-hidden rounded-3xl border border-borda bg-surface">
      <div className="relative aspect-[16/9] w-full">
        {temBanner ? (
          <Image src={urlBanner(culto.id, culto.capa_versao)} alt="" fill unoptimized priority sizes="(min-width: 1152px) 1152px, 100vw" className="object-cover" />
        ) : (
          <div className="absolute inset-0 flex items-end bg-gradient-to-br from-violeta/40 via-ink to-laranja/20 p-6 sm:p-10">
            <span aria-hidden className="font-display text-3xl font-bold sm:text-5xl">
              {culto.titulo}
            </span>
          </div>
        )}
      </div>
      <div className="flex flex-wrap items-center justify-between gap-4 px-5 py-4 sm:px-8">
        <div className="min-w-0">
          {/* O título já está desenhado no banner; aqui ele fica para leitores de tela */}
          <h2 id="titulo-destaque" className="sr-only">
            {culto.titulo}
          </h2>
          <p className="text-xs font-semibold uppercase tracking-wider text-laranja">{culto.serie ? `Série: ${culto.serie}` : "Mais recente"}</p>
          <p className="mt-0.5 text-sm text-suave">{detalhes.join(" · ")}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href={`/app/midias/${culto.id}?aba=gravacao`} className="botao-cta">
            <Play className="size-4" aria-hidden /> Assistir
          </Link>
          <Link href={`/app/midias/${culto.id}?aba=cortes`} className="botao-contorno">
            <Clapperboard className="size-4" aria-hidden /> {culto.cortes > 0 ? `Ver os ${culto.cortes} cortes` : "Criar cortes"}
          </Link>
        </div>
      </div>
    </section>
  );
}
