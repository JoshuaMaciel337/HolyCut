import type { LucideIcon } from "lucide-react";

/**
 * Lugar reservado para o que a IA vai tirar do culto (versículos, estudo, transcrição, resumo).
 * A estrutura já existe; o conteúdo chega quando a transcrição rodar no servidor com GPU.
 */
export function EmBreveComIA({
  idSecao,
  icone: Icone,
  titulo,
  descricao,
  itens,
}: {
  idSecao: string;
  icone: LucideIcon;
  titulo: string;
  descricao: string;
  itens: string[];
}) {
  return (
    <section className="cartao p-6" aria-labelledby={`em-breve-${idSecao}`}>
      <div className="flex items-start gap-3">
        <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-violeta/15">
          <Icone className="size-5 text-violeta" aria-hidden />
        </span>
        <div className="min-w-0">
          <h2 id={`em-breve-${idSecao}`} className="font-display text-lg font-bold">
            {titulo}
          </h2>
          <p className="mt-1 text-sm text-suave">{descricao}</p>
        </div>
      </div>
      <ul className="mt-4 flex flex-col gap-2" aria-label="O que vai aparecer aqui">
        {itens.map((item) => (
          <li key={item} className="flex items-center gap-3 rounded-xl border border-dashed border-borda px-4 py-3 text-sm text-suave">
            <span className="size-2 shrink-0 rounded-full bg-violeta/60" aria-hidden />
            {item}
          </li>
        ))}
      </ul>
      <p className="mt-4 text-xs text-suave">
        Chega com a transcrição, quando a IA estiver ligada no servidor. Tudo sai da própria pregação: a IA organiza o que foi
        dito, não inventa.
      </p>
    </section>
  );
}
