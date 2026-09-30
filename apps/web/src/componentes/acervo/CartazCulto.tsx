import { Clapperboard } from "lucide-react";
import Image from "next/image";
import Link from "next/link";

import { dataDoCulto, urlPoster } from "@/lib/acervo";
import type { CultoResumo } from "@/lib/tipos";

/** O pôster 2:3 de um culto, como a capa de um filme numa fileira de streaming. */
export function CartazCulto({ culto }: { culto: CultoResumo }) {
  return (
    <Link
      href={`/app/midias/${culto.id}`}
      className="group block w-36 shrink-0 snap-start focus-visible:outline-none sm:w-44"
      aria-label={`${culto.titulo}${culto.pregador ? `, ${culto.pregador}` : ""}, ${dataDoCulto(culto.data)}`}
      data-cartaz={culto.id}
    >
      <span className="relative block aspect-[2/3] overflow-hidden rounded-xl bg-surface-2 ring-1 ring-borda transition duration-200 group-hover:scale-[1.03] group-hover:ring-laranja group-focus-visible:ring-2 group-focus-visible:ring-laranja">
        {culto.capa_versao ? (
          <Image src={urlPoster(culto.id, culto.capa_versao)} alt="" fill unoptimized sizes="176px" className="object-cover" />
        ) : (
          // Capa ainda não desenhada (gravação antiga ou worker ocupado): o título sobre a cor da marca
          <span className="absolute inset-0 flex items-end bg-gradient-to-br from-violeta/40 to-ink p-3">
            <span className="font-display text-base font-bold leading-tight">{culto.titulo}</span>
          </span>
        )}
        {culto.cortes > 0 ? (
          <span className="absolute right-2 top-2 inline-flex items-center gap-1 rounded-full bg-ink/80 px-2 py-0.5 text-[11px] font-semibold backdrop-blur">
            <Clapperboard className="size-3 text-laranja" aria-hidden /> {culto.cortes}
          </span>
        ) : null}
      </span>
      <span className="mt-1.5 block truncate text-xs text-suave">
        {culto.pregador ? `${culto.pregador} · ` : ""}
        {dataDoCulto(culto.data)}
      </span>
    </Link>
  );
}
