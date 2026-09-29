"use client";

import { Clapperboard, FolderOpen, LogOut, Mic, Plus, ScanFace, Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { CartaoJob } from "@/componentes/CartaoJob";
import { Logo } from "@/componentes/Logo";
import { PainelSistema } from "@/componentes/PainelSistema";
import { chamarApi, ErroApi } from "@/lib/api";
import type { Job, Sessao, Sistema } from "@/lib/tipos";
import { useJobsAoVivo } from "@/lib/useJobsAoVivo";

const INTERVALO_SISTEMA_MS = 15_000;

const MODULOS = [
  { icone: Sparkles, nome: "HolyStories", cor: "var(--hc-yellow)" },
  { icone: Clapperboard, nome: "HolyReels", cor: "var(--hc-violet)" },
  { icone: Mic, nome: "HolySermon", cor: "#5B8CFF" },
  { icone: ScanFace, nome: "HolyMoments", cor: "var(--hc-cyan)" },
];

export default function PaginaInicio() {
  const router = useRouter();
  const [sessao, setSessao] = useState<Sessao | null>(null);
  const [sistema, setSistema] = useState<Sistema | null>(null);
  const [erroGeral, setErroGeral] = useState("");
  const [criando, setCriando] = useState(false);
  const { jobs, conexao, adicionar } = useJobsAoVivo(sessao !== null);

  // Sessão: se a API recusar, apaga o cookie e volta para o login
  useEffect(() => {
    chamarApi<Sessao>("/auth/eu")
      .then(setSessao)
      .catch(async (e) => {
        if (e instanceof ErroApi && e.status === 401) {
          await chamarApi("/auth/sair", { metodo: "POST" }).catch(() => undefined);
          router.replace("/entrar?proximo=/app");
          return;
        }
        setErroGeral(e instanceof ErroApi ? e.message : "Não foi possível carregar o painel.");
      });
  }, [router]);

  // Workers online, atualizado a cada 15 s
  useEffect(() => {
    if (!sessao) return;
    const atualizar = () => chamarApi<Sistema>("/sistema").then(setSistema).catch(() => setSistema(null));
    atualizar();
    const intervalo = setInterval(atualizar, INTERVALO_SISTEMA_MS);
    return () => clearInterval(intervalo);
  }, [sessao]);

  async function criarJob(corpo: { tipo: string; duracao?: number; falhar?: boolean }) {
    setCriando(true);
    setErroGeral("");
    try {
      adicionar(await chamarApi<Job>("/jobs", { metodo: "POST", corpo }));
    } catch (e) {
      setErroGeral(e instanceof ErroApi ? e.message : "Não foi possível criar o job.");
    } finally {
      setCriando(false);
    }
  }

  async function sair() {
    await chamarApi("/auth/sair", { metodo: "POST" }).catch(() => undefined);
    router.replace("/entrar");
  }

  if (!sessao) {
    return (
      <div className="flex min-h-dvh items-center justify-center px-4 text-center text-suave">
        {erroGeral || "Carregando..."}
      </div>
    );
  }

  const primeiroNome = sessao.usuario.nome.split(" ")[0];
  const gpuOnline = sistema?.workers.some((w) => w.recursos.includes("gpu")) ?? false;

  return (
    <div className="min-h-dvh">
      <header className="border-b border-borda bg-surface/70 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-4 sm:px-6">
          <Logo altura={30} prioridade />
          <div className="flex items-center gap-3">
            <div className="hidden text-right sm:block">
              <p className="text-sm font-medium">{sessao.organizacao.nome}</p>
              <p className="text-xs text-suave">{sessao.usuario.nome}</p>
            </div>
            <button type="button" onClick={sair} className="botao-contorno px-4 py-2 text-sm">
              <LogOut className="size-4" aria-hidden /> Sair
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
        <h1 className="font-display text-3xl font-bold">Olá, {primeiroNome}!</h1>
        <p className="mt-1 text-suave">O que vamos criar para a {sessao.organizacao.nome} hoje?</p>

        {erroGeral ? (
          <p role="alert" className="mt-6 rounded-xl border border-vermelho/40 bg-vermelho/10 px-4 py-3 text-sm text-vermelho">
            {erroGeral}
          </p>
        ) : null}

        <section className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-5" aria-label="Criar conteúdo">
          <div className="cartao flex flex-col justify-between gap-4 p-5 lg:col-span-1" style={{ backgroundImage: "var(--hc-gradient-cta)" }}>
            <Plus className="size-7" aria-hidden />
            <div>
              <p className="font-display text-lg font-bold">Criar agora</p>
              <p className="text-sm text-white/80">Upload de vídeo chega na Fase 1.</p>
            </div>
          </div>
          {MODULOS.map(({ icone: Icone, nome, cor }) => (
            <div key={nome} className="cartao flex flex-col justify-between gap-4 p-5 opacity-80">
              <Icone className="size-7" style={{ color: cor }} aria-hidden />
              <div>
                <p className="font-display text-lg font-bold">{nome}</p>
                <p className="text-sm text-suave">Em breve</p>
              </div>
            </div>
          ))}
        </section>

        <div className="mt-8 grid gap-6 lg:grid-cols-[1fr_320px]">
          <section className="cartao p-6" aria-labelledby="titulo-teste">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <h2 id="titulo-teste" className="font-display text-lg font-bold">
                  Teste do pipeline
                </h2>
                <p className="mt-1 max-w-xl text-sm text-suave">
                  Cria um job na fila. O worker pega, processa e o progresso aparece aqui ao vivo.
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <button type="button" className="botao-cta px-4 py-2 text-sm" disabled={criando} onClick={() => criarJob({ tipo: "teste", duracao: 10 })}>
                  Rodar job de teste
                </button>
                <button type="button" className="botao-contorno px-4 py-2 text-sm" disabled={criando} onClick={() => criarJob({ tipo: "teste", duracao: 6, falhar: true })}>
                  Simular falha
                </button>
                <button type="button" className="botao-contorno px-4 py-2 text-sm" disabled={criando} onClick={() => criarJob({ tipo: "diagnostico_gpu" })}>
                  Testar GPU
                </button>
              </div>
            </div>

            {jobs.length === 0 ? (
              <div className="mt-8 flex flex-col items-center gap-2 rounded-2xl border border-dashed border-borda py-10 text-center text-suave">
                <FolderOpen className="size-8" aria-hidden />
                <p>Nenhum job ainda. Rode o job de teste para ver a fila funcionando.</p>
              </div>
            ) : (
              <ul className="mt-6 flex flex-col gap-3">
                {jobs.map((job) => (
                  <CartaoJob key={job.id} job={job} gpuOnline={gpuOnline} />
                ))}
              </ul>
            )}
          </section>

          <PainelSistema sistema={sistema} conexao={conexao} />
        </div>
      </main>
    </div>
  );
}
