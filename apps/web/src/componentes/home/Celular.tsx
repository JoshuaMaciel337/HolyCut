import { Ellipsis, Maximize, Play, X } from "lucide-react";
import Image from "next/image";

import { Logo } from "@/componentes/Logo";

type Props = {
  /** Foto da tela, em /public/marketing. */
  imagem?: string;
  /** "cheia" cobre a tela toda; "topo" ocupa a parte de cima e escurece até embaixo, onde fica o texto. */
  enquadramento?: "cheia" | "topo";
  posicao?: string;
  cabecalho?: boolean;
  controles?: boolean;
  className?: string;
  children?: React.ReactNode;
};

/**
 * Um celular com um Story, desenhado em HTML: a foto embaixo e o texto de verdade por cima,
 * nas fontes da marca. As fotos são pequenas, então a tela nunca depende de detalhe fino delas.
 */
export function Celular({ imagem, enquadramento = "cheia", posicao = "center", cabecalho = true, controles = false, className = "", children }: Props) {
  return (
    <div
      className={`relative aspect-[9/19] rounded-[2.4rem] border border-white/10 bg-[#141418] p-[5px] shadow-[0_40px_100px_rgba(0,0,0,.7)] ${className}`}
      aria-hidden
    >
      <div className="relative h-full w-full overflow-hidden rounded-[2.1rem] bg-[#060608]">
        {imagem ? (
          <div
            className={`absolute inset-x-0 top-0 ${enquadramento === "topo" ? "h-[70%]" : "h-full"}`}
            style={enquadramento === "topo" ? { maskImage: "linear-gradient(to bottom, black 55%, transparent 100%)" } : undefined}
          >
            <Image src={imagem} alt="" fill sizes="(min-width: 1024px) 320px, 60vw" className="object-cover" style={{ objectPosition: posicao }} />
          </div>
        ) : null}
        <div
          className="absolute inset-0"
          style={{
            background:
              enquadramento === "topo"
                ? "linear-gradient(180deg, rgba(0,0,0,.35) 0%, transparent 18%, transparent 38%, rgba(6,6,8,.55) 58%, rgba(6,6,8,.9) 74%)"
                : "linear-gradient(180deg, rgba(0,0,0,.45) 0%, transparent 22%, transparent 45%, rgba(6,6,8,.9) 100%)",
          }}
        />
        {cabecalho ? (
          <div className="absolute inset-x-4 top-4">
            <div className="flex gap-1">
              <span className="h-[3px] flex-1 rounded-full bg-white/85" />
              <span className="h-[3px] flex-1 rounded-full bg-white/25" />
            </div>
            <div className="mt-3 flex items-center gap-2 text-[11px]">
              <Logo fundo="escuro" variante="simbolo" altura={18} />
              <span className="font-semibold text-white/95">HolyCut</span>
              <span className="text-white/55">2h</span>
              <Ellipsis className="ml-auto size-4 text-white/70" />
              <X className="size-4 text-white/85" />
            </div>
          </div>
        ) : null}
        <div className="absolute inset-0">{children}</div>
        {controles ? (
          <div className="absolute inset-x-4 bottom-5">
            <div className="flex items-center gap-2 text-[10px] tabular-nums text-white/75">
              <Play className="size-3 fill-white/80 text-white/80" />
              0:12 / 0:18
              <Maximize className="ml-auto size-3.5" />
            </div>
            <div className="relative mt-2 h-[3px] rounded-full bg-white/20">
              <div className="h-full w-2/3 rounded-full bg-white/80" />
              <span className="absolute left-2/3 top-1/2 size-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-white" />
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}

/** A cruz fina e luminosa dos Stories. */
export function Cruz({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 34" className={className} fill="none" stroke="currentColor" strokeWidth={1.4} strokeLinecap="round" aria-hidden>
      <path d="M12 2v30M5 11h14" />
    </svg>
  );
}

/** O Story "Ele é Digno", no preset Digno: a palavra em Caveat. */
const TAMANHOS_DIGNO = {
  grande: { topo: "top-[56%]", rotulo: "text-xs", palavra: "text-[64px]", cruz: "mt-3 h-6" },
  pequeno: { topo: "top-[58%]", rotulo: "text-[8px]", palavra: "text-[34px]", cruz: "mt-1.5 h-3.5" },
  // No leque da seção "Como funciona", o celular do meio é estreito na tela do celular
  responsivo: { topo: "top-[56%]", rotulo: "text-[8px] sm:text-xs", palavra: "text-[36px] sm:text-[60px]", cruz: "mt-1.5 h-4 sm:mt-3 sm:h-6" },
};

export function StoryDigno({ tamanho = "grande" }: { tamanho?: keyof typeof TAMANHOS_DIGNO }) {
  const medidas = TAMANHOS_DIGNO[tamanho];
  return (
    <div className={`absolute inset-x-0 flex flex-col items-center text-white ${medidas.topo}`}>
      <span className={`font-display font-semibold tracking-[0.35em] text-white/90 ${medidas.rotulo}`}>ELE É</span>
      <span className={`font-script leading-none drop-shadow-[0_2px_14px_rgba(0,0,0,.7)] ${medidas.palavra}`}>Digno</span>
      <Cruz className={`text-white/85 ${medidas.cruz}`} />
    </div>
  );
}

/** Uma frase grande no alto do Story, como no modelo de texto. */
export function StoryFrase({ frase, referencia, tamanho = "text-[22px]" }: { frase: string; referencia?: string; tamanho?: string }) {
  return (
    <>
      <div className="absolute inset-x-0 top-0 h-[55%] bg-gradient-to-b from-black/80 via-black/50 to-transparent" />
      <div className="absolute inset-x-5 top-[16%] text-white">
        <p className={`font-display font-bold leading-[1.15] drop-shadow-[0_2px_10px_rgba(0,0,0,.6)] ${tamanho}`}>{frase}</p>
        {referencia ? <p className="mt-2 text-[10px] uppercase tracking-[0.2em] text-laranja">{referencia}</p> : null}
      </div>
    </>
  );
}
