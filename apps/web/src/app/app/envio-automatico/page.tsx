"use client";

import { ArrowLeft, Check, Copy, Download, KeyRound, Trash2 } from "lucide-react";
import Link from "next/link";
import { useEffect, useState, useSyncExternalStore } from "react";

import { CampoTexto } from "@/componentes/CampoTexto";
import { chamarApi, ErroApi } from "@/lib/api";
import { formatarData } from "@/lib/formatar";
import type { ChaveEnvio, ChaveEnvioCriada } from "@/lib/tipos";

const nuncaMuda = () => () => undefined;

export default function PaginaEnvioAutomatico() {
  const [chaves, setChaves] = useState<ChaveEnvio[] | null>(null);
  const [nome, setNome] = useState("PC da mídia");
  const [criada, setCriada] = useState<ChaveEnvioCriada | null>(null);
  const [copiada, setCopiada] = useState(false);
  const [erro, setErro] = useState("");

  // O endereço do site vai dentro do agente baixado, para ninguém precisar digitar
  const endereco = useSyncExternalStore(nuncaMuda, () => window.location.origin, () => "");

  useEffect(() => {
    chamarApi<ChaveEnvio[]>("/chaves-envio")
      .then(setChaves)
      .catch((e) => setErro(e instanceof ErroApi ? e.message : "Não foi possível carregar as chaves."));
  }, []);

  async function criar(evento: React.FormEvent) {
    evento.preventDefault();
    setErro("");
    setCopiada(false);
    try {
      const nova = await chamarApi<ChaveEnvioCriada>("/chaves-envio", { metodo: "POST", corpo: { nome: nome.trim() } });
      setCriada(nova);
      setChaves((atuais) => [nova, ...(atuais ?? [])]);
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível criar a chave.");
    }
  }

  async function copiar() {
    if (!criada) return;
    try {
      await navigator.clipboard.writeText(criada.chave);
      setCopiada(true);
    } catch {
      setErro("Não foi possível copiar. Selecione a chave e copie com Ctrl+C.");
    }
  }

  async function revogar(chave: ChaveEnvio) {
    if (!window.confirm(`Revogar a chave "${chave.nome}"? O agente que usa esta chave para de enviar.`)) return;
    try {
      await chamarApi(`/chaves-envio/${chave.id}`, { metodo: "DELETE" });
      setChaves((atuais) => (atuais ?? []).filter((item) => item.id !== chave.id));
      if (criada?.id === chave.id) setCriada(null);
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível revogar a chave.");
    }
  }

  const linkDoAgente = `/api/chaves-envio/agente.zip${endereco ? `?servidor=${encodeURIComponent(endereco)}` : ""}`;

  return (
    <main className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
      <Link href="/app" className="inline-flex items-center gap-2 text-sm text-suave hover:text-texto">
        <ArrowLeft className="size-4" aria-hidden /> Início
      </Link>
      <h1 className="mt-4 font-display text-3xl font-bold">Envio automático do OBS</h1>
      <p className="mt-1 max-w-2xl text-suave">
        Um programa pequeno no computador da mídia envia a gravação sozinho quando o OBS para de gravar. Quando o culto acaba, a
        gravação já está chegando no HolyCut, sem ninguém abrir o site.
      </p>
      {erro ? (
        <p role="alert" className="mt-6 rounded-xl border border-vermelho/40 bg-vermelho/10 px-4 py-3 text-sm text-vermelho">
          {erro}
        </p>
      ) : null}

      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        <section className="cartao flex flex-col gap-4 p-6" aria-labelledby="titulo-chave">
          <h2 id="titulo-chave" className="font-display text-lg font-bold">
            1. Crie uma chave
          </h2>
          <p className="text-sm text-suave">A chave deixa o agente enviar gravações em nome da igreja. Ela não dá acesso ao resto do site.</p>
          <form onSubmit={criar} className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <div className="flex-1">
              <CampoTexto rotulo="Onde vai ser usada" name="nome" value={nome} maxLength={60} required onChange={(evento) => setNome(evento.target.value)} />
            </div>
            <button type="submit" disabled={!nome.trim()} className="botao-cta">
              <KeyRound className="size-4" aria-hidden /> Criar chave
            </button>
          </form>
          {criada ? (
            <div className="rounded-xl border border-amarelo/40 bg-amarelo/10 p-4 text-sm">
              <p className="font-semibold">Copie agora: esta chave não aparece de novo.</p>
              <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-center">
                <code className="min-w-0 flex-1 break-all rounded-lg bg-ink px-3 py-2 font-mono text-xs" data-chave-criada>
                  {criada.chave}
                </code>
                <button type="button" onClick={copiar} className="botao-contorno px-4 py-2 text-sm">
                  {copiada ? <Check className="size-4" aria-hidden /> : <Copy className="size-4" aria-hidden />} {copiada ? "Copiada" : "Copiar"}
                </button>
              </div>
            </div>
          ) : null}
        </section>

        <section className="cartao flex flex-col gap-4 p-6" aria-labelledby="titulo-agente">
          <h2 id="titulo-agente" className="font-display text-lg font-bold">
            2. Instale o agente no PC da mídia
          </h2>
          <a href={linkDoAgente} download className="botao-cta self-start">
            <Download className="size-4" aria-hidden /> Baixar o agente (.zip)
          </a>
          <ol className="list-decimal space-y-2 pl-5 text-sm text-suave">
            <li>
              Instale o Python em <span className="text-texto">python.org/downloads</span> e marque <span className="text-texto">“Add python.exe to PATH”</span>.
            </li>
            <li>Descompacte o .zip e dê dois cliques em <span className="text-texto">iniciar_agente.bat</span>.</li>
            <li>Cole a chave e informe a pasta onde o OBS salva as gravações (no OBS: Configurações › Saída › Caminho da gravação).</li>
            <li>
              Para iniciar com o Windows: crie um atalho do <span className="text-texto">iniciar_agente.bat</span> na pasta{" "}
              <span className="text-texto">shell:startup</span> e acrescente <span className="text-texto">--automatico</span> no destino.
            </li>
          </ol>
          <p className="text-xs text-suave">
            O agente envia só as gravações novas, em pedaços. Se a internet cair, ele continua de onde parou. O .zip traz as instruções completas.
          </p>
        </section>
      </div>

      <section className="mt-8" aria-labelledby="titulo-chaves">
        <h2 id="titulo-chaves" className="font-display text-lg font-bold">
          Chaves ativas
        </h2>
        {chaves === null ? (
          <p className="mt-4 text-suave">Carregando...</p>
        ) : chaves.length === 0 ? (
          <p className="mt-4 text-suave">Nenhuma chave ainda.</p>
        ) : (
          <ul className="mt-4 flex flex-col gap-2">
            {chaves.map((chave) => (
              <li key={chave.id} className="cartao flex items-center justify-between gap-3 px-4 py-3 text-sm">
                <div className="min-w-0">
                  <p className="font-semibold">{chave.nome}</p>
                  <p className="text-suave">
                    <code className="font-mono">{chave.inicio}…</code> · criada em {formatarData(chave.criado_em)} ·{" "}
                    {chave.ultimo_uso_em ? `último envio em ${formatarData(chave.ultimo_uso_em)}` : "ainda não usada"}
                  </p>
                </div>
                <button type="button" onClick={() => revogar(chave)} className="shrink-0 text-suave hover:text-vermelho" aria-label={`Revogar ${chave.nome}`}>
                  <Trash2 className="size-4" aria-hidden />
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
