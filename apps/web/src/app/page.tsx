import {
  ArrowRight,
  BrainCircuit,
  Check,
  Clapperboard,
  LayoutGrid,
  Mic,
  ScanFace,
  Share2,
  Smartphone,
  Sparkles,
  SquarePlay,
  Video,
} from "lucide-react";
import Link from "next/link";

import { Logo } from "@/componentes/Logo";

const FLUXO = [
  { icone: Video, texto: "Grave" },
  { icone: BrainCircuit, texto: "IA seleciona" },
  { icone: SquarePlay, texto: "Edita" },
  { icone: Smartphone, texto: "Compartilha" },
];

const MODULOS = [
  { icone: Sparkles, nome: "HolyStories", texto: "Stories prontos em segundos.", cor: "var(--hc-yellow)" },
  { icone: Clapperboard, nome: "HolyReels", texto: "Reels que conectam.", cor: "var(--hc-violet)" },
  { icone: Mic, nome: "HolySermon", texto: "Pregações em cortes impactantes.", cor: "#5B8CFF" },
  { icone: ScanFace, nome: "HolyMoments", texto: "Os melhores momentos do culto, automaticamente.", cor: "var(--hc-cyan)" },
  { icone: LayoutGrid, nome: "Sua Identidade", texto: "Filtros, fontes e estilos da sua igreja.", cor: "var(--hc-magenta)" },
];

const RECURSOS = [
  "Edição automática com IA",
  "Músicas livres de direitos",
  "Legendas e textos dinâmicos",
  "Filtros e correção de cor",
  "Templates exclusivos para igrejas",
];

function CelularStory() {
  return (
    <div className="relative mx-auto w-[260px] sm:w-[300px]" aria-hidden>
      <div className="relative aspect-[9/19] overflow-hidden rounded-[2.75rem] border-[6px] border-[#1c1f29] bg-ink shadow-[0_30px_80px_rgba(0,0,0,.6)]">
        {/* Luzes de palco simuladas */}
        <div
          className="absolute inset-0"
          style={{
            background:
              "radial-gradient(ellipse at 50% 18%, rgba(120,170,255,.55), transparent 45%)," +
              "radial-gradient(ellipse at 20% 40%, rgba(123,97,255,.45), transparent 40%)," +
              "radial-gradient(ellipse at 85% 35%, rgba(240,91,255,.30), transparent 40%)," +
              "linear-gradient(180deg, #0c1224 0%, #08090F 75%)",
          }}
        />
        <div className="absolute left-1/2 top-[12%] h-[34%] w-[3px] -translate-x-1/2 bg-white/50 blur-[1px]" />
        <div className="absolute left-1/2 top-[20%] h-[3px] w-[22%] -translate-x-1/2 bg-white/50 blur-[1px]" />
        <div className="absolute inset-x-0 bottom-0 h-[45%] bg-gradient-to-t from-ink via-ink/80 to-transparent" />

        <div className="absolute inset-x-4 top-4 h-[3px] rounded-full bg-white/25">
          <div className="h-full w-2/3 rounded-full bg-white/80" />
        </div>
        <div className="absolute left-4 top-8 flex items-center gap-2">
          <Logo variante="simbolo" altura={26} />
          <span className="text-xs font-medium text-white/90">nossaigreja</span>
          <span className="text-xs text-white/50">2h</span>
        </div>

        <div className="absolute inset-x-0 top-[52%] flex flex-col items-center">
          <span className="font-display text-sm font-semibold tracking-[0.3em] text-white/90">ELE É</span>
          <span className="font-script text-6xl leading-none text-white drop-shadow-[0_2px_12px_rgba(0,0,0,.6)]">
            Digno
          </span>
          <span className="mt-3 text-2xl font-light text-white/80">✝</span>
        </div>

        <div className="absolute inset-x-4 bottom-5 flex items-center gap-2">
          <div className="flex-1 rounded-full border border-white/30 px-4 py-2 text-xs text-white/60">
            Enviar mensagem
          </div>
          <Share2 className="size-5 text-white/70" />
        </div>
      </div>
      <p className="absolute -right-6 top-24 hidden rotate-[-8deg] font-script text-3xl leading-tight text-white/90 lg:block lg:-right-44">
        Mesmo conteúdo.
        <br />
        Muito mais
        <br />
        alcance.
        <span className="mt-1 block h-1 w-36 rounded-full" style={{ backgroundImage: "var(--hc-gradient-marca)" }} />
      </p>
    </div>
  );
}

export default function PaginaInicial() {
  return (
    <div className="relative overflow-hidden">
      {/* Brilhos de fundo */}
      <div
        className="pointer-events-none absolute inset-0 -z-10"
        style={{
          background:
            "radial-gradient(circle at 15% 10%, rgba(123,97,255,.18), transparent 35%)," +
            "radial-gradient(circle at 85% 25%, rgba(255,138,0,.12), transparent 35%)",
        }}
      />

      <header className="mx-auto flex max-w-6xl items-center justify-between px-4 py-5 sm:px-6">
        <Logo altura={34} prioridade />
        <nav className="flex items-center gap-2 sm:gap-4">
          <Link href="/entrar" className="rounded-full px-4 py-2 text-sm font-medium text-suave hover:text-texto">
            Entrar
          </Link>
          <Link href="/cadastro" className="botao-cta px-5 py-2 text-sm">
            Comece agora
          </Link>
        </nav>
      </header>

      <main>
        <section className="mx-auto grid max-w-6xl items-center gap-14 px-4 pb-20 pt-10 sm:px-6 lg:grid-cols-[1.1fr_1fr] lg:pt-16">
          <div>
            <span className="inline-flex items-center gap-2 rounded-full border border-violeta/40 bg-violeta/10 px-3 py-1 text-xs font-medium text-violeta">
              <Sparkles className="size-3.5" aria-hidden />
              IA para a mídia da sua igreja
            </span>
            <h1 className="mt-6 font-display text-4xl font-bold leading-[1.1] sm:text-5xl lg:text-6xl">
              Transforme momentos em <span className="texto-gradiente">histórias.</span>
            </h1>
            <p className="mt-6 max-w-xl text-lg text-suave">
              Envie a gravação do culto e receba Stories, Reels e cortes da pregação prontos para postar, com a
              identidade visual da sua igreja.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link href="/cadastro" className="botao-cta">
                Comece agora <ArrowRight className="size-4" aria-hidden />
              </Link>
              <a href="#como-funciona" className="botao-contorno">
                Como funciona
              </a>
            </div>

            <ol id="como-funciona" className="mt-12 flex flex-wrap items-center gap-x-2.5 gap-y-4">
              {FLUXO.map(({ icone: Icone, texto }, indice) => (
                <li key={texto} className="flex items-center gap-2.5">
                  <span className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.14em]">
                    <Icone className="size-5 text-texto" aria-hidden />
                    {texto}
                  </span>
                  {indice < FLUXO.length - 1 ? <ArrowRight className="size-4 text-magenta" aria-hidden /> : null}
                </li>
              ))}
            </ol>
          </div>
          <CelularStory />
        </section>

        <section className="border-y border-borda bg-surface/60" aria-label="Módulos do HolyCut">
          <ul className="mx-auto grid max-w-6xl gap-8 px-4 py-14 sm:grid-cols-2 sm:px-6 lg:grid-cols-5">
            {MODULOS.map(({ icone: Icone, nome, texto, cor }) => (
              <li key={nome} className="flex flex-col items-center text-center">
                <span
                  className="flex size-14 items-center justify-center rounded-2xl border-2"
                  style={{ borderColor: cor, boxShadow: `0 0 24px color-mix(in srgb, ${cor} 35%, transparent)` }}
                >
                  <Icone className="size-7" style={{ color: cor }} aria-hidden />
                </span>
                <h2 className="mt-4 font-display text-lg font-bold">{nome}</h2>
                <p className="mt-1 text-sm text-suave">{texto}</p>
              </li>
            ))}
          </ul>
        </section>

        <section className="mx-auto grid max-w-6xl gap-10 px-4 py-20 sm:px-6 lg:grid-cols-2">
          <div>
            <h2 className="font-display text-3xl font-bold text-violeta">IA + Criatividade</h2>
            <p className="mt-2 text-2xl font-medium">O melhor dos dois mundos.</p>
            <p className="mt-5 max-w-lg text-suave">
              Envie seus vídeos e deixe o HolyCut transformar os melhores momentos do seu culto em conteúdos prontos
              para o Instagram, o TikTok e o YouTube.
            </p>
            <Link href="/cadastro" className="botao-cta mt-8">
              Comece agora <ArrowRight className="size-4" aria-hidden />
            </Link>
          </div>
          <ul className="cartao flex flex-col gap-4 p-8">
            {RECURSOS.map((recurso) => (
              <li key={recurso} className="flex items-center gap-3">
                <Check className="size-5 shrink-0 text-magenta" aria-hidden />
                {recurso}
              </li>
            ))}
          </ul>
        </section>
      </main>

      <footer className="border-t border-borda">
        <div className="mx-auto flex max-w-6xl flex-col items-start gap-6 px-4 py-10 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <Logo altura={30} />
          <p className="rotulo-espacado leading-6">
            Mais que vídeos.
            <br />É o evangelho em movimento.
          </p>
          <p className="text-xs text-suave">© {new Date().getFullYear()} HolyCut</p>
        </div>
      </footer>
    </div>
  );
}
