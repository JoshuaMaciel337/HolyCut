"use client";

import { ArrowLeft, Check, ImageUp, Trash2 } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { CampoTexto } from "@/componentes/CampoTexto";
import { chamarApi, ErroApi } from "@/lib/api";
import type { Identidade } from "@/lib/tipos";
import { useCamada } from "@/lib/useCamada";

// Cores da marca HolyCut como ponto de partida; a igreja pode digitar a sua
const SUGESTOES_COR = ["#FF8A00", "#FFD24D", "#FF5A5F", "#F05BFF", "#7B61FF", "#5B8CFF", "#22D3EE", "#00C853"];

export default function PaginaIdentidade() {
  const [identidade, setIdentidade] = useState<Identidade | null>(null);
  const [rascunho, setRascunho] = useState({ nome_exibicao: "", instagram: "", cor_destaque: "#FF8A00" });
  const [versaoLogo, setVersaoLogo] = useState(0);
  const [estado, setEstado] = useState<"" | "salvando" | "salvo">("");
  const [erro, setErro] = useState("");
  const entrada = useRef<HTMLInputElement>(null);

  useEffect(() => {
    chamarApi<Identidade>("/identidade")
      .then((dados) => {
        setIdentidade(dados);
        setRascunho({ nome_exibicao: dados.nome_exibicao, instagram: dados.instagram, cor_destaque: dados.cor_destaque });
      })
      .catch((e) => setErro(e instanceof ErroApi ? e.message : "Não foi possível carregar a identidade."));
  }, []);

  // Exemplo com a cor escolhida, desenhado pelo mesmo código que desenha o vídeo
  const exemplo = useCamada(
    identidade && identidade.cor_destaque === rascunho.cor_destaque
      ? { largura: 540, altura: 960, tipo: "texto", texto: { id: "exemplo", tipo: "titulo", texto: "Culto de hoje", referencia: "", estilo: "destaque", posicao: "centro", inicio: 0, fim: null } }
      : null,
  );

  async function salvar() {
    setEstado("salvando");
    setErro("");
    try {
      const dados = await chamarApi<Identidade>("/identidade", { metodo: "PATCH", corpo: rascunho });
      setIdentidade(dados);
      setRascunho({ nome_exibicao: dados.nome_exibicao, instagram: dados.instagram, cor_destaque: dados.cor_destaque });
      setEstado("salvo");
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível salvar.");
      setEstado("");
    }
  }

  async function enviarLogo(arquivo: File | undefined) {
    if (!arquivo) return;
    setErro("");
    try {
      const resposta = await fetch("/api/identidade/logo", {
        method: "PUT",
        body: arquivo,
        headers: { "Content-Type": arquivo.type || "application/octet-stream" },
        credentials: "same-origin",
      });
      const dados = await resposta.json();
      if (!resposta.ok) throw new ErroApi(resposta.status, dados?.detail ?? "Não foi possível enviar o logo.");
      setIdentidade(dados);
      setVersaoLogo((valor) => valor + 1);
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível enviar o logo.");
    }
  }

  async function removerLogo() {
    if (!window.confirm("Remover o logo? Os próximos vídeos saem sem ele.")) return;
    try {
      setIdentidade(await chamarApi<Identidade>("/identidade/logo", { metodo: "DELETE" }));
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível remover o logo.");
    }
  }

  const alterado =
    identidade !== null &&
    (rascunho.nome_exibicao !== identidade.nome_exibicao ||
      rascunho.instagram !== identidade.instagram ||
      rascunho.cor_destaque.toUpperCase() !== identidade.cor_destaque);
  const corValida = /^#[0-9A-Fa-f]{6}$/.test(rascunho.cor_destaque);

  return (
    <main className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
      <Link href="/app" className="inline-flex items-center gap-2 text-sm text-suave hover:text-texto">
        <ArrowLeft className="size-4" aria-hidden /> Início
      </Link>
      <h1 className="mt-4 font-display text-3xl font-bold">Sua Identidade</h1>
      <p className="mt-1 text-suave">O logo e a cor da igreja entram sozinhos em todo Reel e Story.</p>
      {erro ? (
        <p role="alert" className="mt-6 rounded-xl border border-vermelho/40 bg-vermelho/10 px-4 py-3 text-sm text-vermelho">
          {erro}
        </p>
      ) : null}

      {!identidade ? (
        <p className="mt-8 text-suave">Carregando...</p>
      ) : (
        <div className="mt-8 grid gap-6 lg:grid-cols-2">
          <section className="cartao p-6" aria-labelledby="titulo-logo">
            <h2 id="titulo-logo" className="font-display text-lg font-bold">
              Logo
            </h2>
            <p className="mt-1 text-sm text-suave">PNG com fundo transparente fica melhor. JPG e WEBP também servem. Até 5 MB.</p>
            <div className="mt-4 grid grid-cols-2 gap-3">
              {["bg-ink", "bg-white"].map((fundo) => (
                <div key={fundo} className={`relative flex aspect-video items-center justify-center overflow-hidden rounded-2xl border border-borda ${fundo}`}>
                  {identidade.logo ? (
                    <Image
                      src={`/api/identidade/logo?v=${versaoLogo}`}
                      alt="Logo da igreja"
                      fill
                      unoptimized
                      sizes="240px"
                      className="object-contain p-4"
                    />
                  ) : (
                    <span className={`text-sm ${fundo === "bg-white" ? "text-neutral-500" : "text-suave"}`}>Sem logo</span>
                  )}
                </div>
              ))}
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <button type="button" onClick={() => entrada.current?.click()} className="botao-cta px-4 py-2 text-sm">
                <ImageUp className="size-4" aria-hidden /> {identidade.logo ? "Trocar o logo" : "Enviar o logo"}
              </button>
              {identidade.logo ? (
                <button type="button" onClick={removerLogo} className="botao-contorno px-4 py-2 text-sm">
                  <Trash2 className="size-4" aria-hidden /> Remover
                </button>
              ) : null}
            </div>
            <input
              ref={entrada}
              type="file"
              accept="image/png,image/jpeg,image/webp"
              className="sr-only"
              tabIndex={-1}
              aria-hidden
              onChange={(evento) => {
                void enviarLogo(evento.target.files?.[0]);
                evento.target.value = "";
              }}
            />
          </section>

          <section className="cartao flex flex-col gap-4 p-6" aria-labelledby="titulo-dados">
            <h2 id="titulo-dados" className="font-display text-lg font-bold">
              Nome, @ e cor
            </h2>
            <CampoTexto
              rotulo="Nome que aparece nos vídeos"
              name="nome_exibicao"
              value={rascunho.nome_exibicao}
              maxLength={80}
              onChange={(evento) => setRascunho({ ...rascunho, nome_exibicao: evento.target.value })}
            />
            <CampoTexto
              rotulo="Instagram"
              name="instagram"
              placeholder="@suaigreja"
              value={rascunho.instagram}
              maxLength={80}
              onChange={(evento) => setRascunho({ ...rascunho, instagram: evento.target.value })}
            />
            <div className="flex flex-col gap-2">
              <span className="text-sm font-medium">Cor de destaque</span>
              <div className="flex flex-wrap items-center gap-2">
                {SUGESTOES_COR.map((cor) => (
                  <button
                    key={cor}
                    type="button"
                    onClick={() => setRascunho({ ...rascunho, cor_destaque: cor })}
                    aria-label={`Usar a cor ${cor}`}
                    className={`size-8 rounded-full border-2 ${rascunho.cor_destaque.toUpperCase() === cor ? "border-white" : "border-transparent"}`}
                    style={{ backgroundColor: cor }}
                  />
                ))}
                <input
                  type="color"
                  value={corValida ? rascunho.cor_destaque : "#FF8A00"}
                  onChange={(evento) => setRascunho({ ...rascunho, cor_destaque: evento.target.value.toUpperCase() })}
                  aria-label="Escolher outra cor"
                  className="size-8 cursor-pointer rounded-full border border-borda bg-transparent"
                />
                <input
                  value={rascunho.cor_destaque}
                  onChange={(evento) => setRascunho({ ...rascunho, cor_destaque: evento.target.value })}
                  aria-label="Código da cor"
                  maxLength={7}
                  className="w-24 rounded-xl border border-borda bg-ink px-3 py-1.5 font-mono text-sm uppercase outline-none focus:border-violeta"
                />
              </div>
              {!corValida ? <span className="text-xs text-vermelho">Use o formato #RRGGBB, por exemplo #FF8A00.</span> : null}
            </div>
            <div className="mt-auto flex items-center gap-3">
              <button type="button" onClick={salvar} disabled={!alterado || !corValida || estado === "salvando"} className="botao-cta px-5 py-2 text-sm">
                {estado === "salvando" ? "Salvando..." : "Salvar"}
              </button>
              {estado === "salvo" && !alterado ? (
                <span className="inline-flex items-center gap-1.5 text-sm text-suave">
                  <Check className="size-4 text-ciano" aria-hidden /> Salvo
                </span>
              ) : null}
            </div>
          </section>

          <section className="cartao p-6 lg:col-span-2" aria-labelledby="titulo-exemplo">
            <h2 id="titulo-exemplo" className="font-display text-lg font-bold">
              Como fica no vídeo
            </h2>
            <p className="mt-1 text-sm text-suave">Salve para ver a cor nova aqui.</p>
            <div
              className="relative mx-auto mt-4 aspect-[9/16] w-48 overflow-hidden rounded-2xl"
              style={{ background: "linear-gradient(180deg, #1b2240, #3a2a6b 60%, #08090F)" }}
            >
              {exemplo ? (
                <Image src={exemplo} alt="Exemplo de texto com a cor da igreja" fill unoptimized sizes="192px" />
              ) : null}
              {identidade.logo ? (
                <Image
                  src={`/api/identidade/logo?v=${versaoLogo}`}
                  alt=""
                  width={48}
                  height={48}
                  unoptimized
                  className="absolute right-2 top-2 h-auto w-8 object-contain"
                />
              ) : null}
            </div>
          </section>
        </div>
      )}
    </main>
  );
}
