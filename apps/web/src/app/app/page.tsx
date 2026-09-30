"use client";

import { CircleAlert, Clapperboard, Film, Mic, ScanFace, Sparkles, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { CartaoMidia } from "@/componentes/CartaoMidia";
import { PainelSistema } from "@/componentes/PainelSistema";
import { ZonaDeEnvio } from "@/componentes/ZonaDeEnvio";
import { chamarApi, ErroApi } from "@/lib/api";
import { useEnvios } from "@/lib/envios";
import { useEventosJobs } from "@/lib/eventos";
import { useSessao } from "@/lib/sessao";
import type { Midia } from "@/lib/tipos";
import { useSistema } from "@/lib/useSistema";

const LIMITE_MIDIAS = 30;

const MODULOS = [
  { icone: Sparkles, nome: "HolyStories", cor: "var(--hc-yellow)" },
  { icone: Clapperboard, nome: "HolyReels", cor: "var(--hc-violet)" },
  { icone: Mic, nome: "HolySermon", cor: "#5B8CFF" },
  { icone: ScanFace, nome: "HolyMoments", cor: "var(--hc-cyan)" },
];

export default function PaginaInicio() {
  const { sessao } = useSessao();
  const sistema = useSistema();
  const { envios, versao, cancelar, dispensar } = useEnvios();
  const [midias, setMidias] = useState<Midia[] | null>(null);
  const [erro, setErro] = useState("");

  const carregar = useCallback(() => {
    chamarApi<Midia[]>(`/midias?limite=${LIMITE_MIDIAS}`)
      .then(setMidias)
      .catch((e) => setErro(e instanceof ErroApi ? e.message : "Não foi possível carregar as gravações."));
  }, []);

  // Recarrega quando um envio cria uma mídia ou termina
  useEffect(() => {
    carregar();
  }, [carregar, versao]);

  const atualizarMidia = useCallback((id: string) => {
    chamarApi<Midia>(`/midias/${id}`)
      .then((nova) => setMidias((lista) => lista?.map((m) => (m.id === id ? nova : m)) ?? lista))
      .catch(() => undefined);
  }, []);

  useEventosJobs((job) => {
    const midiaId = job.entrada?.midia_id;
    if (job.tipo !== "ingestao" || typeof midiaId !== "string") return;
    setMidias(
      (lista) =>
        lista?.map((m) =>
          m.id === midiaId && m.status === "processando"
            ? { ...m, processamento: { status: job.status, progresso: job.progresso, mensagem: job.mensagem } }
            : m,
        ) ?? lista,
    );
    if (job.status === "concluido" || job.status === "erro") atualizarMidia(midiaId);
  });

  async function excluir(midia: Midia) {
    if (!window.confirm(`Excluir "${midia.nome}"? A gravação e tudo o que foi gerado a partir dela serão apagados.`)) return;
    const envio = envios.find((item) => item.midiaId === midia.id);
    if (envio) cancelar(envio.chave);
    try {
      await chamarApi(`/midias/${midia.id}`, { metodo: "DELETE" });
      setMidias((lista) => lista?.filter((m) => m.id !== midia.id) ?? lista);
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível excluir.");
    }
  }

  const envioPorMidia = useMemo(
    () => new Map(envios.filter((envio) => envio.midiaId).map((envio) => [envio.midiaId as string, envio])),
    [envios],
  );
  // Envios que ainda não viraram mídia: começando ou recusados antes de começar
  const enviosSemMidia = envios.filter((envio) => !envio.midiaId);
  const primeiroNome = sessao.usuario.nome.split(" ")[0];

  return (
    <main className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
      <h1 className="font-display text-3xl font-bold">Olá, {primeiroNome}!</h1>
      <p className="mt-1 text-suave">O que vamos criar para a {sessao.organizacao.nome} hoje?</p>

      {erro ? (
        <p role="alert" className="mt-6 rounded-xl border border-vermelho/40 bg-vermelho/10 px-4 py-3 text-sm text-vermelho">
          {erro}
        </p>
      ) : null}

      <div className="mt-8 grid gap-6 lg:grid-cols-[1fr_320px]">
        <div className="flex min-w-0 flex-col gap-8">
          <ZonaDeEnvio />

          {enviosSemMidia.length > 0 ? (
            <ul className="flex flex-col gap-2" aria-label="Envios começando">
              {enviosSemMidia.map((envio) => (
                <li key={envio.chave} className="flex items-center justify-between gap-3 rounded-2xl border border-borda bg-surface px-4 py-3 text-sm">
                  <span className="flex min-w-0 items-center gap-2">
                    {envio.estado === "erro" ? (
                      <CircleAlert className="size-4 shrink-0 text-vermelho" aria-hidden />
                    ) : (
                      <Film className="size-4 shrink-0 text-suave" aria-hidden />
                    )}
                    <span className="truncate font-medium">{envio.nome}</span>
                    <span className={envio.estado === "erro" ? "text-vermelho" : "text-suave"}>
                      {envio.estado === "erro" ? envio.erro : "Começando o envio..."}
                    </span>
                  </span>
                  <button
                    type="button"
                    aria-label="Dispensar"
                    onClick={() => (envio.estado === "erro" ? dispensar(envio.chave) : cancelar(envio.chave))}
                    className="text-suave hover:text-texto"
                  >
                    <X className="size-4" aria-hidden />
                  </button>
                </li>
              ))}
            </ul>
          ) : null}

          <section aria-labelledby="titulo-midias">
            <h2 id="titulo-midias" className="font-display text-xl font-bold">
              Suas gravações
            </h2>
            {midias === null ? (
              <p className="mt-4 text-suave">Carregando...</p>
            ) : midias.length === 0 ? (
              <p className="mt-4 rounded-2xl border border-dashed border-borda px-6 py-10 text-center text-suave">
                Nenhuma gravação ainda. Envie a gravação de um culto para começar.
              </p>
            ) : (
              <ul className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                {midias.map((midia) => (
                  <CartaoMidia key={midia.id} midia={midia} envio={envioPorMidia.get(midia.id)} aoExcluir={excluir} />
                ))}
              </ul>
            )}
          </section>

          <section aria-labelledby="titulo-modulos">
            <h2 id="titulo-modulos" className="font-display text-xl font-bold">
              Em breve
            </h2>
            <ul className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
              {MODULOS.map(({ icone: Icone, nome, cor }) => (
                <li key={nome} className="cartao flex items-center gap-3 p-4 opacity-80">
                  <Icone className="size-6 shrink-0" style={{ color: cor }} aria-hidden />
                  <span className="font-display font-bold">{nome}</span>
                </li>
              ))}
            </ul>
          </section>
        </div>

        <aside className="flex flex-col gap-6">
          <PainelSistema sistema={sistema} comLinkDiagnostico />
        </aside>
      </div>
    </main>
  );
}
