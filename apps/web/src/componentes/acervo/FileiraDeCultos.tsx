"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { useRef } from "react";

import { CartazCulto } from "@/componentes/acervo/CartazCulto";
import type { CultoResumo } from "@/lib/tipos";

/** Uma fileira horizontal de cartazes, com setas no computador e o dedo no celular. */
export function FileiraDeCultos({ titulo, cultos }: { titulo: string; cultos: CultoResumo[] }) {
  const trilho = useRef<HTMLDivElement>(null);
  const idTitulo = `fileira-${titulo.replace(/\W+/g, "-").toLowerCase()}`;

  function rolar(sentido: 1 | -1) {
    const elemento = trilho.current;
    if (elemento) elemento.scrollBy({ left: sentido * elemento.clientWidth * 0.85, behavior: "smooth" });
  }

  if (cultos.length === 0) return null;
  return (
    <section aria-labelledby={idTitulo} className="group/fileira relative">
      <h2 id={idTitulo} className="font-display text-lg font-bold">
        {titulo}
      </h2>
      <div className="relative mt-3">
        <div ref={trilho} className="-mx-4 flex snap-x gap-3 overflow-x-auto px-4 pb-2 [scrollbar-width:none] sm:-mx-6 sm:px-6 [&::-webkit-scrollbar]:hidden">
          {cultos.map((culto) => (
            <CartazCulto key={culto.id} culto={culto} />
          ))}
        </div>
        {cultos.length > 4 ? (
          <>
            <button
              type="button"
              onClick={() => rolar(-1)}
              aria-label={`Voltar em ${titulo}`}
              className="absolute -left-3 top-[40%] hidden size-10 -translate-y-1/2 items-center justify-center rounded-full border border-borda bg-ink/90 opacity-0 shadow-lg transition group-hover/fileira:opacity-100 sm:flex"
            >
              <ChevronLeft className="size-5" aria-hidden />
            </button>
            <button
              type="button"
              onClick={() => rolar(1)}
              aria-label={`Avançar em ${titulo}`}
              className="absolute -right-3 top-[40%] hidden size-10 -translate-y-1/2 items-center justify-center rounded-full border border-borda bg-ink/90 opacity-0 shadow-lg transition group-hover/fileira:opacity-100 sm:flex"
            >
              <ChevronRight className="size-5" aria-hidden />
            </button>
          </>
        ) : null}
      </div>
    </section>
  );
}
