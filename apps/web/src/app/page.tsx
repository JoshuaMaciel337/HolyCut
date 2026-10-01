import {
  ArrowRight,
  BadgeDollarSign,
  BookOpen,
  BrainCircuit,
  CheckCheck,
  CirclePlay,
  Clapperboard,
  FileArchive,
  FolderDown,
  Heart,
  Library,
  Mic,
  MonitorSmartphone,
  MousePointerClick,
  Palette,
  Plus,
  Quote,
  Radio,
  ScanFace,
  Server,
  Sparkles,
} from "lucide-react";
import Image from "next/image";
import Link from "next/link";

import { Celular, Cruz, StoryDigno, StoryFrase } from "@/componentes/home/Celular";
import { EditorNoNotebook } from "@/componentes/home/EditorNoNotebook";
import { PainelDoApp } from "@/componentes/home/PainelDoApp";
import { Logo } from "@/componentes/Logo";

const NAVEGACAO = [
  { href: "#recursos", rotulo: "Recursos" },
  { href: "#como-funciona", rotulo: "Como funciona" },
  { href: "#por-que", rotulo: "Por que o HolyCut" },
  { href: "#perguntas", rotulo: "Perguntas" },
];

const GARANTIAS = [
  { icone: BadgeDollarSign, texto: "Sem custo por uso" },
  { icone: BrainCircuit, texto: "Modelos abertos" },
  { icone: Server, texto: "Roda na sua máquina" },
  { icone: Palette, texto: "A identidade da sua igreja" },
];

const MODULOS = [
  { icone: Sparkles, nome: "HolyStories", texto: "Stories prontos em segundos.", cor: "var(--hc-violet)" },
  { icone: Clapperboard, nome: "HolyReels", texto: "Reels que conectam.", cor: "var(--hc-orange)" },
  { icone: Mic, nome: "HolySermon", texto: "A pregação em cortes que tocam.", cor: "#5B8CFF" },
  { icone: ScanFace, nome: "HolyMoments", texto: "Os melhores momentos do culto, sozinhos.", cor: "var(--hc-cyan)" },
];

const EXTRAS = [
  { icone: Library, nome: "Acervo da igreja", texto: "Cada culto com capa, cortes, versículos e estudo, como num streaming." },
  { icone: BookOpen, nome: "HolyStudy", texto: "Resumo e guia para células com as palavras do próprio pregador." },
  { icone: CheckCheck, nome: "Aprovação pelo celular", texto: "O pastor aprova o corte por um link, sem criar conta." },
  { icone: Radio, nome: "Chega sozinho", texto: "Do OBS ou da live do YouTube, a gravação entra sem ninguém abrir o site." },
  { icone: FileArchive, nome: "DaVinci e Premiere", texto: "Os cortes e a legenda num pacote, para quem edita no profissional." },
];

const MOTIVOS = [
  { icone: Quote, nome: "Fiel ao que foi pregado", texto: "A IA não inventa: títulos, resumos e legendas saem das palavras do pregador." },
  { icone: BrainCircuit, nome: "IA aberta", texto: "Modelos abertos, sem travas e sem custo por minuto." },
  { icone: Server, nome: "Roda na sua máquina", texto: "Mais privacidade e controle, sem depender de terceiros." },
  { icone: Palette, nome: "A cara da sua igreja", texto: "Logo, cor e fontes em todos os conteúdos." },
  { icone: MousePointerClick, nome: "Fácil de usar", texto: "Feito para a rotina da mídia. Dá para cortar apagando palavras do texto." },
  { icone: FolderDown, nome: "Tudo é da igreja", texto: "Baixe em MP4, SRT, TXT e PDF, quando quiser." },
];

const PASSOS = [
  { nome: "Envie", texto: "A gravação do culto, ou deixe o OBS e a live do YouTube chegarem sozinhos." },
  { nome: "A IA edita", texto: "Transcreve, acha a pregação, corta, legenda e aplica a identidade da igreja." },
  { nome: "Publique", texto: "Revise, peça a aprovação do pastor pelo celular e poste." },
];

const PERGUNTAS = [
  {
    pergunta: "O que é o HolyCut?",
    resposta:
      "Uma plataforma que transforma a gravação do culto em Stories, Reels e cortes da pregação, com a identidade visual da sua igreja. Cada culto vira uma página no acervo, com os cortes, os versículos citados e um guia de estudo.",
  },
  {
    pergunta: "Preciso saber editar vídeo?",
    resposta:
      "Não. A IA sugere os cortes, e o editor é simples: dá para cortar apagando palavras do texto da pregação. Quem já edita pode levar os cortes para o DaVinci ou o Premiere.",
  },
  {
    pergunta: "A IA pode colocar palavras na boca do pastor?",
    resposta:
      "Não. Títulos, resumos, perguntas de estudo e legendas saem do que ele disse. Quando a IA não tem certeza, ela deixa de fora, e todo texto automático vem marcado para alguém revisar.",
  },
  {
    pergunta: "Funciona com vídeo gravado no celular?",
    resposta:
      "Funciona. O HolyCut aceita MP4, MOV, MKV e outros formatos comuns, do celular, da câmera ou do OBS. Também importa a live pelo link do canal da igreja no YouTube.",
  },
  {
    pergunta: "Tem custo por uso ou limite de vídeos?",
    resposta:
      "Não há cobrança por minuto: o HolyCut roda em máquina própria, com modelos abertos. Cada gravação pode ter até 20 GB, e o limite é o espaço do servidor.",
  },
  {
    pergunta: "Os vídeos da igreja ficam com quem?",
    resposta: "Com a igreja. Cada igreja só vê o que é dela, e tudo pode ser baixado em formatos abertos.",
  },
];

function Rotulo({ children }: { children: React.ReactNode }) {
  return <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-suave">{children}</p>;
}

/** A frase manuscrita com o traço laranja embaixo, como nos materiais da marca. */
function Manuscrito({ linhas, className = "" }: { linhas: string[]; className?: string }) {
  return (
    <p className={`rotate-[-8deg] font-script text-3xl leading-[1.1] text-white/90 ${className}`} aria-hidden>
      {linhas.map((linha) => (
        <span key={linha} className="block">
          {linha}
        </span>
      ))}
      <span className="mt-2 block h-[3px] w-40 rounded-full" style={{ backgroundImage: "var(--hc-gradient-marca)" }} />
    </p>
  );
}

function Cabecalho() {
  return (
    <header className="sticky top-0 z-30 border-b border-white/5 bg-ink/75 backdrop-blur-md">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-4 sm:px-6">
        <Link href="/" aria-label="HolyCut, início">
          <Logo altura={30} prioridade />
        </Link>
        <nav className="hidden items-center gap-8 text-sm text-suave md:flex" aria-label="Seções">
          {NAVEGACAO.map((item) => (
            <a key={item.href} href={item.href} className="transition hover:text-texto">
              {item.rotulo}
            </a>
          ))}
        </nav>
        <div className="flex items-center gap-2">
          <Link href="/entrar" className="botao-contorno px-4 py-2 text-sm">
            Entrar
          </Link>
          <Link href="/cadastro" className="botao-cta hidden px-4 py-2 text-sm sm:inline-flex">
            Comece agora
          </Link>
        </div>
      </div>
    </header>
  );
}

function Hero() {
  return (
    <section className="relative isolate overflow-hidden" aria-labelledby="titulo-hero">
      {/* O palco ao fundo, desfocado: a foto é pequena, e o desfoque é o que a deixa bonita grande */}
      <div
        className="absolute inset-y-0 right-0 -z-10 w-full lg:w-[62%]"
        style={{ maskImage: "linear-gradient(to left, black 35%, transparent 95%)" }}
        aria-hidden
      >
        <Image src="/marketing/louvor-maos.jpg" alt="" fill priority sizes="62vw" className="object-cover opacity-45 blur-xl" />
        <div className="absolute inset-0 bg-gradient-to-t from-ink via-ink/40 to-ink/70" />
      </div>
      <div
        className="absolute inset-0 -z-10"
        style={{
          background:
            "radial-gradient(circle at 12% 18%, rgba(168,85,247,.16), transparent 38%)," +
            "radial-gradient(circle at 78% 30%, rgba(255,138,0,.14), transparent 40%)",
        }}
        aria-hidden
      />

      <div className="mx-auto grid max-w-6xl items-center gap-14 px-4 pb-20 pt-12 sm:px-6 lg:grid-cols-[1.05fr_1fr] lg:pb-28 lg:pt-20">
        <div>
          <Rotulo>IA para igrejas</Rotulo>
          <h1 id="titulo-hero" className="mt-5 font-display text-[42px] font-bold leading-[1.05] tracking-tight sm:text-6xl lg:text-[68px]">
            Transforme momentos em <span className="texto-gradiente">histórias.</span>
          </h1>
          <p className="mt-6 max-w-xl text-lg leading-relaxed text-suave">
            O HolyCut transforma a gravação do culto em Stories, Reels e cortes da pregação prontos para postar, com a identidade
            visual da sua igreja. A IA roda em máquina própria, com modelos abertos e sem custo por uso.
          </p>
          <div className="mt-9 flex flex-wrap gap-3">
            <Link href="/cadastro" className="botao-cta">
              Comece agora <ArrowRight className="size-4" aria-hidden />
            </Link>
            <a href="#como-funciona" className="botao-contorno">
              <CirclePlay className="size-4" aria-hidden /> Como funciona
            </a>
          </div>
          <ul className="mt-12 grid max-w-xl grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-4">
            {GARANTIAS.map(({ icone: Icone, texto }) => (
              <li key={texto} className="flex items-start gap-2.5 text-[13px] leading-snug text-suave">
                <Icone className="mt-0.5 size-5 shrink-0 text-texto/80" aria-hidden />
                {texto}
              </li>
            ))}
          </ul>
        </div>

        <div className="relative mx-auto w-[270px] sm:w-[300px]">
          <div className="absolute -inset-10 -z-10 rounded-full bg-violeta/20 blur-3xl" aria-hidden />
          <Celular imagem="/marketing/story-cruz.jpg" enquadramento="topo" posicao="60% center" controles>
            <StoryDigno />
          </Celular>
          <Manuscrito
            linhas={["Mesmo conteúdo.", "Muito mais", "alcance."]}
            className="absolute -right-48 top-28 hidden xl:block"
          />
        </div>
      </div>
    </section>
  );
}

function Recursos() {
  return (
    <section id="recursos" className="scroll-mt-20 border-t border-white/5 bg-gradient-to-b from-surface/40 to-ink" aria-labelledby="titulo-recursos">
      <div className="mx-auto grid max-w-6xl items-center gap-14 px-4 py-20 sm:px-6 lg:grid-cols-[1fr_1.1fr] lg:py-28">
        <div>
          <Rotulo>Principais recursos</Rotulo>
          <h2 id="titulo-recursos" className="mt-4 font-display text-3xl font-bold leading-tight sm:text-4xl">
            Do culto ao seu feed, em poucos cliques.
          </h2>
          <p className="mt-4 max-w-lg text-suave">
            O HolyCut assiste à gravação, encontra os melhores momentos da pregação e cria conteúdos prontos para postar, com
            qualidade profissional e a identidade da sua igreja.
          </p>
          <ul className="mt-10 grid grid-cols-2 gap-3">
            {MODULOS.map(({ icone: Icone, nome, texto, cor }) => (
              <li key={nome} className="cartao flex flex-col gap-3 p-4">
                <span
                  className="flex size-11 items-center justify-center rounded-xl border"
                  style={{ borderColor: cor, boxShadow: `0 0 22px color-mix(in srgb, ${cor} 30%, transparent)` }}
                >
                  <Icone className="size-5" style={{ color: cor }} aria-hidden />
                </span>
                <h3 className="font-display text-sm font-bold">{nome}</h3>
                <p className="text-xs leading-relaxed text-suave">{texto}</p>
              </li>
            ))}
          </ul>
        </div>

        <div className="relative">
          <div className="absolute -inset-8 -z-10 rounded-[40px] bg-violeta/10 blur-3xl" aria-hidden />
          <div className="lg:mr-16">
            <PainelDoApp />
          </div>
          <div className="absolute -top-10 right-0 hidden w-[118px] lg:block">
            <Celular imagem="/marketing/cruz-banda.jpg" cabecalho={false}>
              <StoryDigno tamanho="pequeno" />
            </Celular>
          </div>
          <div className="absolute -bottom-14 -right-6 hidden w-[118px] lg:block">
            <Celular imagem="/marketing/louvor-maos.jpg" cabecalho={false}>
              <StoryFrase frase="Deus cuida de todos os detalhes." tamanho="text-[13px]" />
            </Celular>
          </div>
        </div>
      </div>

      <div className="mx-auto max-w-6xl px-4 pb-20 sm:px-6 lg:pb-28">
        <h3 className="font-display text-lg font-bold">E também</h3>
        <ul className="mt-5 grid gap-px overflow-hidden rounded-[22px] border border-borda bg-borda sm:grid-cols-2 lg:grid-cols-5">
          {EXTRAS.map(({ icone: Icone, nome, texto }) => (
            <li key={nome} className="flex flex-col gap-2 bg-surface p-5">
              <Icone className="size-5 text-laranja" aria-hidden />
              <p className="text-sm font-semibold">{nome}</p>
              <p className="text-[13px] leading-relaxed text-suave">{texto}</p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

function PorQue() {
  return (
    <section id="por-que" className="scroll-mt-20 border-t border-white/5" aria-labelledby="titulo-por-que">
      <div className="mx-auto grid max-w-6xl items-center gap-16 px-4 py-20 sm:px-6 lg:grid-cols-[1fr_1.1fr] lg:py-28">
        <div className="relative order-2 lg:order-1">
          <div className="absolute -inset-10 -z-10 rounded-full bg-laranja/10 blur-3xl" aria-hidden />
          <div className="relative">
            <div className="mr-14 sm:mr-20">
              <EditorNoNotebook />
            </div>
            <div className="absolute -bottom-16 right-0 w-[104px] sm:w-[128px]">
              <Celular imagem="/marketing/story-cruz.jpg" enquadramento="topo" posicao="60% center" cabecalho={false}>
                <StoryDigno tamanho="pequeno" />
              </Celular>
            </div>
          </div>
          <p className="mt-10 pr-32 font-display text-2xl font-semibold leading-snug sm:mt-14 sm:text-3xl">
            Tecnologia a serviço
            <br />
            do Reino.
          </p>
        </div>

        <div className="order-1 lg:order-2">
          <Rotulo>Por que o HolyCut</Rotulo>
          <h2 id="titulo-por-que" className="mt-4 font-display text-3xl font-bold leading-tight sm:text-4xl">
            Mais que uma ferramenta, uma aliada da sua igreja.
          </h2>
          <ul className="mt-10 grid gap-x-8 gap-y-8 sm:grid-cols-2 lg:grid-cols-3">
            {MOTIVOS.map(({ icone: Icone, nome, texto }) => (
              <li key={nome} className="border-t border-borda pt-5">
                <span className="flex size-10 items-center justify-center rounded-full border border-borda bg-surface">
                  <Icone className="size-4.5 text-texto" aria-hidden />
                </span>
                <h3 className="mt-4 text-sm font-semibold">{nome}</h3>
                <p className="mt-1.5 text-[13px] leading-relaxed text-suave">{texto}</p>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}

function ComoFunciona() {
  return (
    <section id="como-funciona" className="scroll-mt-20 border-t border-white/5 bg-gradient-to-b from-ink via-surface/40 to-ink" aria-labelledby="titulo-como">
      <div className="mx-auto grid max-w-6xl items-center gap-16 px-4 py-20 sm:px-6 lg:grid-cols-[1fr_1.15fr] lg:py-28">
        <div>
          <Rotulo>Como funciona</Rotulo>
          <h2 id="titulo-como" className="mt-4 font-display text-3xl font-bold leading-tight sm:text-4xl">
            Simples, rápido
            <br />e poderoso.
          </h2>
          <p className="mt-4 max-w-md text-suave">Em poucos passos, os conteúdos ficam prontos para todas as redes da igreja.</p>
          <ol className="mt-10 grid gap-8 sm:grid-cols-3">
            {PASSOS.map(({ nome, texto }, indice) => (
              <li key={nome} className="sm:border-l sm:border-borda sm:pl-5 sm:first:border-0 sm:first:pl-0">
                <span className="flex size-10 items-center justify-center rounded-full border border-white/25 font-display font-bold">
                  {indice + 1}
                </span>
                <h3 className="mt-4 font-semibold">{nome}</h3>
                <p className="mt-1.5 text-[13px] leading-relaxed text-suave">{texto}</p>
              </li>
            ))}
          </ol>
        </div>

        {/* Os Stories em leque, como saem do HolyCut */}
        <div className="relative mx-auto h-[440px] w-full max-w-[520px] sm:h-[500px]" aria-hidden>
          <div className="absolute left-[2%] top-[14%] w-[30%] -rotate-[8deg] opacity-90">
            <Celular imagem="/marketing/pregador-retrato.jpg" cabecalho={false}>
              <span className="absolute bottom-[10%] left-3 text-[9px] font-semibold uppercase tracking-[0.2em] text-white/80">
                Corte da pregação
              </span>
            </Celular>
          </div>
          <div className="absolute right-[2%] top-[14%] w-[30%] rotate-[8deg] opacity-90">
            <Celular imagem="/marketing/louvor-maos.jpg" cabecalho={false}>
              <StoryFrase frase="Deus cuida de todos os detalhes." tamanho="text-[11px] sm:text-[15px]" />
            </Celular>
          </div>
          <div className="absolute left-1/2 top-0 z-10 w-[40%] -translate-x-1/2">
            <Celular imagem="/marketing/story-cruz.jpg" enquadramento="topo" posicao="60% center" controles>
              <StoryDigno tamanho="responsivo" />
            </Celular>
          </div>
          <Manuscrito
            linhas={["Mais que vídeos.", "É o evangelho", "em movimento."]}
            className="absolute -bottom-2 right-0 z-20 hidden text-2xl sm:block"
          />
        </div>
      </div>
    </section>
  );
}

function Chamada() {
  return (
    <section className="mx-auto max-w-6xl px-4 py-20 sm:px-6" aria-labelledby="titulo-chamada">
      {/* A borda em degradê: o fundo do cartão por cima do degradê, com 1 px de folga */}
      <div className="rounded-[26px] p-px" style={{ backgroundImage: "linear-gradient(120deg, rgba(168,85,247,.8), rgba(255,138,0,.6))" }}>
        <div className="relative grid gap-10 overflow-hidden rounded-[25px] bg-[#0f0f13] px-6 py-12 sm:px-12 lg:grid-cols-[1.2fr_1fr_auto] lg:items-center">
          <div
            className="absolute inset-0"
            style={{ background: "radial-gradient(circle at 85% 50%, rgba(255,138,0,.12), transparent 45%), radial-gradient(circle at 10% 0%, rgba(168,85,247,.14), transparent 40%)" }}
            aria-hidden
          />
          <div className="relative">
            <Rotulo>Comece agora</Rotulo>
            <h2 id="titulo-chamada" className="mt-4 font-display text-3xl font-bold leading-tight sm:text-4xl">
              Seu culto, muito mais longe.
            </h2>
            <p className="mt-4 max-w-md text-suave">
              Sem custo por uso e sem complicação. Só o que a sua igreja precisa para alcançar mais pessoas.
            </p>
          </div>
          <div className="relative flex flex-col items-start gap-4">
            <Link href="/cadastro" className="botao-cta">
              Criar a conta da igreja <ArrowRight className="size-4" aria-hidden />
            </Link>
            <Link href="/entrar" className="inline-flex items-center gap-1.5 text-sm text-suave hover:text-texto">
              Já tenho conta <ArrowRight className="size-3.5" aria-hidden />
            </Link>
          </div>
          <div className="relative hidden flex-col items-center gap-3 border-l border-borda pl-10 text-center text-sm text-suave lg:flex">
            <Cruz className="h-10 text-white/80" />
            <p>
              Juntos, levando
              <br />o evangelho mais longe.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

function Perguntas() {
  return (
    <section id="perguntas" className="scroll-mt-20 border-t border-white/5" aria-labelledby="titulo-perguntas">
      <div className="mx-auto grid max-w-6xl gap-12 px-4 py-20 sm:px-6 lg:grid-cols-[1fr_1.6fr]">
        <div>
          <Rotulo>Perguntas</Rotulo>
          <h2 id="titulo-perguntas" className="mt-4 font-display text-3xl font-bold leading-tight">
            Perguntas frequentes
          </h2>
          <span className="mt-6 block h-[3px] w-14 rounded-full" style={{ backgroundImage: "var(--hc-gradient-marca)" }} aria-hidden />
          <div className="cartao mt-10 flex items-start gap-4 p-5">
            <span className="flex size-11 shrink-0 items-center justify-center rounded-xl border border-borda">
              <MonitorSmartphone className="size-5 text-laranja" aria-hidden />
            </span>
            <div>
              <p className="text-sm font-semibold">Quer ver na prática?</p>
              <p className="mt-1 text-[13px] text-suave">Crie a conta da igreja e envie a gravação do último culto.</p>
              <Link href="/cadastro" className="mt-2 inline-flex items-center gap-1 text-[13px] text-laranja hover:underline">
                Começar agora <ArrowRight className="size-3.5" aria-hidden />
              </Link>
            </div>
          </div>
        </div>
        <div className="divide-y divide-borda border-y border-borda">
          {PERGUNTAS.map(({ pergunta, resposta }) => (
            <details key={pergunta} className="group py-1">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4 rounded-lg py-4 text-[15px] font-medium focus-visible:outline-2 focus-visible:outline-violeta [&::-webkit-details-marker]:hidden">
                {pergunta}
                <Plus className="size-4 shrink-0 text-suave transition group-open:rotate-45" aria-hidden />
              </summary>
              <p className="pb-5 pr-8 text-sm leading-relaxed text-suave">{resposta}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}

function Rodape() {
  return (
    <footer className="relative overflow-hidden border-t border-white/5">
      {/* As linhas de luz da marca, em SVG para ficarem nítidas em qualquer tamanho */}
      <svg className="pointer-events-none absolute -bottom-10 left-0 h-56 w-full opacity-60" viewBox="0 0 1200 220" preserveAspectRatio="none" aria-hidden>
        <defs>
          <linearGradient id="linha-laranja" x1="0" x2="1">
            <stop offset="0" stopColor="#FF8A00" stopOpacity="0" />
            <stop offset=".6" stopColor="#FF8A00" />
            <stop offset="1" stopColor="#FFD24D" stopOpacity="0" />
          </linearGradient>
          <linearGradient id="linha-roxa" x1="0" x2="1">
            <stop offset="0" stopColor="#A855F7" stopOpacity="0" />
            <stop offset=".4" stopColor="#A855F7" />
            <stop offset="1" stopColor="#F05BFF" stopOpacity="0" />
          </linearGradient>
          <filter id="brilho">
            <feGaussianBlur stdDeviation="3" />
          </filter>
        </defs>
        <path d="M0 200 C 300 120, 520 210, 760 150 S 1100 60, 1200 110" stroke="url(#linha-roxa)" strokeWidth="2" fill="none" filter="url(#brilho)" />
        <path d="M0 200 C 300 120, 520 210, 760 150 S 1100 60, 1200 110" stroke="url(#linha-roxa)" strokeWidth="1" fill="none" />
        <path d="M200 220 C 480 150, 700 190, 900 120 S 1150 70, 1200 60" stroke="url(#linha-laranja)" strokeWidth="2" fill="none" filter="url(#brilho)" />
        <path d="M200 220 C 480 150, 700 190, 900 120 S 1150 70, 1200 60" stroke="url(#linha-laranja)" strokeWidth="1" fill="none" />
      </svg>
      <div className="relative mx-auto grid max-w-6xl gap-10 px-4 pb-16 pt-14 sm:px-6 md:grid-cols-[1.4fr_1fr_1fr_auto]">
        <div>
          <Logo altura={30} />
          <p className="mt-5 text-[11px] font-medium uppercase leading-6 tracking-[0.35em] text-suave">
            Mais que vídeos.
            <br />É o evangelho em movimento.
          </p>
        </div>
        <nav aria-label="Produto">
          <p className="text-sm font-semibold">Produto</p>
          <ul className="mt-3 flex flex-col gap-2 text-sm text-suave">
            {NAVEGACAO.map((item) => (
              <li key={item.href}>
                <a href={item.href} className="hover:text-texto">
                  {item.rotulo}
                </a>
              </li>
            ))}
          </ul>
        </nav>
        <nav aria-label="Acesso">
          <p className="text-sm font-semibold">Acesso</p>
          <ul className="mt-3 flex flex-col gap-2 text-sm text-suave">
            <li>
              <Link href="/entrar" className="hover:text-texto">
                Entrar
              </Link>
            </li>
            <li>
              <Link href="/cadastro" className="hover:text-texto">
                Criar a conta da igreja
              </Link>
            </li>
          </ul>
        </nav>
        <div className="flex flex-col gap-2 text-xs text-suave md:items-end">
          <p>© {new Date().getFullYear()} HolyCut</p>
          <p className="inline-flex items-center gap-1.5">
            <Heart className="size-3.5 text-laranja" aria-hidden /> Feito com propósito.
          </p>
        </div>
      </div>
    </footer>
  );
}

export default function PaginaInicial() {
  return (
    <div className="relative bg-ink">
      <Cabecalho />
      <main>
        <Hero />
        <Recursos />
        <PorQue />
        <ComoFunciona />
        <Chamada />
        <Perguntas />
      </main>
      <Rodape />
    </div>
  );
}
