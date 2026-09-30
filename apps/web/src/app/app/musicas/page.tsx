"use client";

import { ArrowLeft, CircleAlert, LoaderCircle, Music, Trash2, Upload } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { BarraProgresso } from "@/componentes/BarraProgresso";
import { CampoTexto } from "@/componentes/CampoTexto";
import { chamarApi, ErroApi } from "@/lib/api";
import { useEventosJobs } from "@/lib/eventos";
import { formatarTempo } from "@/lib/formatar";
import type { LicencaMusica, Musica } from "@/lib/tipos";

const TAMANHO_MAXIMO = 40 * 1024 * 1024;
const LICENCAS: { id: LicencaMusica; nome: string; dica: string }[] = [
  { id: "propria", nome: "Própria da igreja", dica: "Gravação ou composição do ministério de louvor" },
  { id: "dominio_publico", nome: "Domínio público ou CC0", dica: "Hinos antigos, faixas sem direitos autorais" },
  { id: "cc_by", nome: "Creative Commons (CC BY)", dica: "Pode usar dando o crédito ao autor" },
  { id: "licenciada", nome: "Licenciada", dica: "Temos permissão por escrito ou uma assinatura" },
];
const FORMULARIO_VAZIO = { titulo: "", artista: "", licenca: "" as LicencaMusica | "", atribuicao: "", fonte: "" };

/** Envia o arquivo com XMLHttpRequest, que informa o progresso (o fetch não informa). */
function enviarArquivo(musicaId: string, arquivo: File, aoProgredir: (valor: number) => void): Promise<Musica> {
  return new Promise((resolver, rejeitar) => {
    const pedido = new XMLHttpRequest();
    pedido.open("PUT", `/api/musicas/${musicaId}/arquivo?nome=${encodeURIComponent(arquivo.name)}`);
    pedido.setRequestHeader("Content-Type", "application/octet-stream");
    pedido.withCredentials = true;
    pedido.upload.onprogress = (evento) => {
      if (evento.lengthComputable) aoProgredir(Math.round((evento.loaded / evento.total) * 100));
    };
    pedido.onload = () => {
      const dados = JSON.parse(pedido.responseText || "null");
      if (pedido.status >= 200 && pedido.status < 300) resolver(dados as Musica);
      else rejeitar(new ErroApi(pedido.status, dados?.detail ?? "Não foi possível enviar a música."));
    };
    pedido.onerror = () => rejeitar(new ErroApi(0, "Sem conexão com o servidor. Verifique sua internet."));
    pedido.send(arquivo);
  });
}

export default function PaginaMusicas() {
  const [musicas, setMusicas] = useState<Musica[] | null>(null);
  const [formulario, setFormulario] = useState(FORMULARIO_VAZIO);
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [progresso, setProgresso] = useState<number | null>(null);
  const [erro, setErro] = useState("");
  const entrada = useRef<HTMLInputElement>(null);

  const carregar = useCallback(() => {
    chamarApi<Musica[]>("/musicas")
      .then(setMusicas)
      .catch((e) => setErro(e instanceof ErroApi ? e.message : "Não foi possível carregar as músicas."));
  }, []);
  useEffect(carregar, [carregar]);

  // Quando o worker termina de preparar uma faixa, a lista se atualiza sozinha
  useEventosJobs((job) => {
    if (job.tipo === "preparar_musica" && (job.status === "concluido" || job.status === "erro")) carregar();
  });

  function escolherArquivo(escolhido: File | undefined) {
    setErro("");
    if (!escolhido) return;
    if (escolhido.size > TAMANHO_MAXIMO) {
      setErro("A música pode ter no máximo 40 MB.");
      return;
    }
    setArquivo(escolhido);
    if (!formulario.titulo.trim()) setFormulario((atual) => ({ ...atual, titulo: escolhido.name.replace(/\.[^.]+$/, "").slice(0, 120) }));
  }

  async function adicionar(evento: React.FormEvent) {
    evento.preventDefault();
    if (!arquivo || !formulario.licenca) return;
    setErro("");
    setProgresso(0);
    let criada: Musica | null = null;
    try {
      criada = await chamarApi<Musica>("/musicas", { metodo: "POST", corpo: formulario });
      const enviada = await enviarArquivo(criada.id, arquivo, setProgresso);
      setMusicas((atuais) => [enviada, ...(atuais ?? []).filter((m) => m.id !== enviada.id)]);
      setFormulario(FORMULARIO_VAZIO);
      setArquivo(null);
      if (entrada.current) entrada.current.value = "";
    } catch (e) {
      // Sem o arquivo, o cadastro não serve para nada: apaga para não ficar uma faixa vazia na lista
      if (criada) await chamarApi(`/musicas/${criada.id}`, { metodo: "DELETE" }).catch(() => undefined);
      setErro(e instanceof ErroApi ? e.message : "Não foi possível enviar a música.");
    } finally {
      setProgresso(null);
    }
  }

  async function apagar(musica: Musica) {
    if (!window.confirm(`Apagar "${musica.titulo}"? Os projetos que usam esta música ficam sem ela.`)) return;
    try {
      await chamarApi(`/musicas/${musica.id}`, { metodo: "DELETE" });
      setMusicas((atuais) => (atuais ?? []).filter((m) => m.id !== musica.id));
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível apagar a música.");
    }
  }

  const precisaAtribuicao = formulario.licenca === "cc_by";
  const podeEnviar =
    Boolean(arquivo) && Boolean(formulario.titulo.trim()) && Boolean(formulario.licenca) && (!precisaAtribuicao || Boolean(formulario.atribuicao.trim()));

  return (
    <main className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
      <Link href="/app" className="inline-flex items-center gap-2 text-sm text-suave hover:text-texto">
        <ArrowLeft className="size-4" aria-hidden /> Início
      </Link>
      <h1 className="mt-4 font-display text-3xl font-bold">Músicas</h1>
      <p className="mt-1 max-w-2xl text-suave">
        Trilhas para tocar por baixo da pregação. Envie só músicas que a igreja pode usar: música comercial sem licença faz o
        Instagram tirar o som ou o vídeo do ar.
      </p>
      {erro ? (
        <p role="alert" className="mt-6 rounded-xl border border-vermelho/40 bg-vermelho/10 px-4 py-3 text-sm text-vermelho">
          {erro}
        </p>
      ) : null}

      <div className="mt-8 grid gap-6 lg:grid-cols-[minmax(0,420px)_1fr]">
        <form onSubmit={adicionar} className="cartao flex flex-col gap-5 p-6" aria-labelledby="titulo-nova">
          <h2 id="titulo-nova" className="font-display text-lg font-bold">
            Adicionar música
          </h2>
          <label className="flex cursor-pointer flex-col items-center gap-2 rounded-2xl border border-dashed border-borda px-4 py-6 text-center transition hover:border-suave">
            <Upload className="size-6 text-laranja" aria-hidden />
            <span className="text-sm font-medium">{arquivo ? arquivo.name : "Escolher o arquivo"}</span>
            <span className="text-xs text-suave">MP3, M4A, WAV, OGG ou FLAC, até 40 MB</span>
            <input
              ref={entrada}
              type="file"
              accept=".mp3,.m4a,.aac,.wav,.ogg,.flac,audio/*"
              className="sr-only"
              onChange={(evento) => escolherArquivo(evento.target.files?.[0])}
            />
          </label>
          <CampoTexto
            rotulo="Título"
            name="titulo"
            value={formulario.titulo}
            maxLength={120}
            required
            onChange={(evento) => setFormulario({ ...formulario, titulo: evento.target.value })}
          />
          <CampoTexto
            rotulo="Artista"
            name="artista"
            value={formulario.artista}
            maxLength={120}
            onChange={(evento) => setFormulario({ ...formulario, artista: evento.target.value })}
          />
          <fieldset className="flex flex-col gap-2">
            <legend className="mb-2 text-sm font-medium">Licença</legend>
            {LICENCAS.map((licenca) => (
              <label
                key={licenca.id}
                className={`flex cursor-pointer items-start gap-3 rounded-xl border px-4 py-3 transition ${
                  formulario.licenca === licenca.id ? "border-laranja bg-laranja/10" : "border-borda hover:border-suave"
                }`}
              >
                <input
                  type="radio"
                  name="licenca"
                  value={licenca.id}
                  checked={formulario.licenca === licenca.id}
                  onChange={() => setFormulario({ ...formulario, licenca: licenca.id })}
                  className="mt-1 accent-[var(--hc-orange)]"
                />
                <span>
                  <span className="block text-sm font-semibold">{licenca.nome}</span>
                  <span className="block text-xs text-suave">{licenca.dica}</span>
                </span>
              </label>
            ))}
          </fieldset>
          {precisaAtribuicao ? (
            <CampoTexto
              rotulo="Crédito (atribuição)"
              name="atribuicao"
              value={formulario.atribuicao}
              maxLength={300}
              required
              placeholder='Ex.: "Nome da música" por Autor, CC BY 4.0'
              dica="Do jeito que a licença pede. O HolyCut lembra você de pôr na legenda do post."
              onChange={(evento) => setFormulario({ ...formulario, atribuicao: evento.target.value })}
            />
          ) : null}
          <CampoTexto
            rotulo="De onde veio"
            name="fonte"
            value={formulario.fonte}
            maxLength={300}
            placeholder="Link ou descrição (opcional)"
            onChange={(evento) => setFormulario({ ...formulario, fonte: evento.target.value })}
          />
          {progresso !== null ? <BarraProgresso valor={progresso} rotulo="Enviando a música" /> : null}
          <button type="submit" disabled={!podeEnviar || progresso !== null} className="botao-cta">
            <Music className="size-4" aria-hidden /> {progresso !== null ? `Enviando ${progresso}%` : "Adicionar à biblioteca"}
          </button>
        </form>

        <section aria-labelledby="titulo-biblioteca">
          <h2 id="titulo-biblioteca" className="font-display text-lg font-bold">
            Biblioteca da igreja
          </h2>
          {musicas === null ? (
            <p className="mt-4 text-suave">Carregando...</p>
          ) : musicas.length === 0 ? (
            <p className="mt-4 text-suave">Nenhuma música ainda. A primeira que você enviar aparece aqui.</p>
          ) : (
            <ul className="mt-4 flex flex-col gap-3">
              {musicas.map((musica) => (
                <li key={musica.id} className="cartao flex flex-col gap-3 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate font-semibold">{musica.titulo}</p>
                      <p className="text-sm text-suave">
                        {[musica.artista, musica.licenca_nome, musica.duracao ? formatarTempo(musica.duracao) : ""].filter(Boolean).join(" · ")}
                      </p>
                      {musica.atribuicao ? <p className="mt-1 text-xs text-suave">Crédito: {musica.atribuicao}</p> : null}
                    </div>
                    <button type="button" onClick={() => apagar(musica)} className="shrink-0 text-suave hover:text-vermelho" aria-label={`Apagar ${musica.titulo}`}>
                      <Trash2 className="size-4" aria-hidden />
                    </button>
                  </div>
                  {musica.status === "pronta" ? (
                    <audio controls preload="none" src={`/api/musicas/${musica.id}/arquivo`} className="w-full" />
                  ) : musica.status === "erro" ? (
                    <p className="inline-flex items-center gap-1.5 text-sm text-vermelho">
                      <CircleAlert className="size-4" aria-hidden /> {musica.erro ?? "Não foi possível preparar a música."}
                    </p>
                  ) : (
                    <p className="inline-flex items-center gap-1.5 text-sm text-suave">
                      <LoaderCircle className="size-4 animate-spin" aria-hidden /> Preparando a música
                    </p>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </main>
  );
}
