"use client";

import { ArrowLeft, Sparkles, Trash2 } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { CamadaSobreposta } from "@/componentes/CamadaSobreposta";
import { chamarApi, ErroApi } from "@/lib/api";
import { cssDoFiltro, FiltroSvg, useFiltros } from "@/lib/filtros";
import { formatarTempo } from "@/lib/formatar";
import type { Identidade, Midia, Modelo, Projeto, TextoProjeto } from "@/lib/tipos";

const LARGURA_FINAL = 1080;
const ALTURA_FINAL = 1920;

/** Mesma troca que a API faz: {igreja} e {instagram} viram os dados de Sua Identidade. */
function preencher(textos: TextoProjeto[], identidade: Identidade | null): TextoProjeto[] {
  return textos
    .map((texto) => ({
      ...texto,
      texto: texto.texto.replaceAll("{igreja}", identidade?.nome_exibicao ?? "").replaceAll("{instagram}", identidade?.instagram ?? ""),
    }))
    .filter((texto) => texto.texto.trim());
}

function CartaoModelo({
  modelo,
  midia,
  identidade,
  aoEscolher,
  aoApagar,
  ocupado,
}: {
  modelo: Modelo;
  midia: Midia;
  identidade: Identidade | null;
  aoEscolher: () => void;
  aoApagar?: () => void;
  ocupado: boolean;
}) {
  const temCapa = midia.arquivos.includes("capa.jpg");
  const comLogo = modelo.marca.logo && identidade?.logo;
  const filtros = useFiltros();
  const filtro = filtros.find((f) => f.id === modelo.cor.filtro);
  const idFiltro = `modelo-cor-${modelo.id}`;
  const desfoque = modelo.fundo.desfoque ? `blur(${(modelo.fundo.desfoque * 176) / LARGURA_FINAL}px)` : "";
  return (
    <li className="cartao flex flex-col overflow-hidden">
      <FiltroSvg id={idFiltro} filtro={filtro} intensidade={modelo.cor.intensidade} />
      <button
        type="button"
        onClick={aoEscolher}
        disabled={ocupado}
        className="group relative mx-auto mt-5 aspect-[9/16] w-44 overflow-hidden rounded-2xl bg-black ring-2 ring-transparent transition hover:ring-laranja disabled:cursor-wait"
        aria-label={`Usar o modelo ${modelo.nome}`}
      >
        {temCapa ? (
          <Image
            src={`/api/midias/${midia.id}/arquivos/capa.jpg`}
            alt=""
            fill
            unoptimized
            sizes="176px"
            className="object-cover"
            style={{ filter: [cssDoFiltro(idFiltro, filtro, modelo.cor.intensidade), desfoque].filter(Boolean).join(" ") || undefined }}
          />
        ) : null}
        {modelo.fundo.escurecer ? <div className="absolute inset-0 bg-black" style={{ opacity: modelo.fundo.escurecer }} /> : null}
        {comLogo ? <CamadaSobreposta pedido={{ largura: LARGURA_FINAL, altura: ALTURA_FINAL, tipo: "logo", marca: modelo.marca }} /> : null}
        {preencher(modelo.textos, identidade).map((texto) => (
          <CamadaSobreposta key={texto.id} pedido={{ largura: LARGURA_FINAL, altura: ALTURA_FINAL, tipo: "texto", texto }} />
        ))}
      </button>
      <div className="flex flex-1 flex-col gap-1 p-5">
        <div className="flex items-start justify-between gap-2">
          <h2 className="font-display text-lg font-bold">{modelo.nome}</h2>
          {aoApagar ? (
            <button type="button" onClick={aoApagar} aria-label={`Apagar o modelo ${modelo.nome}`} className="text-suave hover:text-texto">
              <Trash2 className="size-4" aria-hidden />
            </button>
          ) : null}
        </div>
        <p className="text-sm text-suave">{modelo.descricao}</p>
        <span className="mt-2 text-xs font-medium text-suave">{modelo.pronto ? "Vem com o HolyCut" : "Da sua igreja"}</span>
      </div>
    </li>
  );
}

function EscolherModelo() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  // useSearchParams, e não window.location: numa navegação dentro do site, o Next desenha a página
  // nova antes de atualizar a URL do navegador
  const inicio = Number(useSearchParams().get("inicio")) || 0;
  const [midia, setMidia] = useState<Midia | null>(null);
  const [modelos, setModelos] = useState<Modelo[] | null>(null);
  const [identidade, setIdentidade] = useState<Identidade | null>(null);
  const [criando, setCriando] = useState(false);
  const [erro, setErro] = useState("");

  useEffect(() => {
    Promise.all([chamarApi<Midia>(`/midias/${id}`), chamarApi<Modelo[]>("/modelos"), chamarApi<Identidade>("/identidade")])
      .then(([gravacao, lista, dados]) => {
        setMidia(gravacao);
        setModelos(lista);
        setIdentidade(dados);
      })
      .catch((e) => setErro(e instanceof ErroApi ? e.message : "Não foi possível carregar os modelos."));
  }, [id]);

  async function escolher(modelo: Modelo) {
    setCriando(true);
    setErro("");
    try {
      const projeto = await chamarApi<Projeto>("/projetos", {
        metodo: "POST",
        corpo: { midia_id: id, tipo: "story", modelo_id: modelo.id, inicio },
      });
      router.push(`/app/projetos/${projeto.id}`);
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível criar o Story.");
      setCriando(false);
    }
  }

  async function apagar(modelo: Modelo) {
    if (!window.confirm(`Apagar o modelo "${modelo.nome}"? Os Stories já feitos com ele não mudam.`)) return;
    try {
      await chamarApi(`/modelos/${modelo.id}`, { metodo: "DELETE" });
      setModelos((lista) => lista?.filter((m) => m.id !== modelo.id) ?? lista);
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível apagar o modelo.");
    }
  }

  return (
    <main className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
      <Link href={`/app/midias/${id}`} className="inline-flex items-center gap-2 text-sm text-suave hover:text-texto">
        <ArrowLeft className="size-4" aria-hidden /> {midia?.nome ?? "Gravação"}
      </Link>
      <h1 className="mt-4 flex items-center gap-2 font-display text-3xl font-bold">
        <Sparkles className="size-7 text-amarelo" aria-hidden /> Novo Story
      </h1>
      <p className="mt-1 text-suave">
        Escolha um modelo. O Story começa em {formatarTempo(inicio)} da gravação, tem 15 segundos, e tudo pode ser ajustado no editor.
      </p>
      {erro ? (
        <p role="alert" className="mt-6 rounded-xl border border-vermelho/40 bg-vermelho/10 px-4 py-3 text-sm text-vermelho">
          {erro}
        </p>
      ) : null}
      {!midia || !modelos ? (
        <p className="mt-8 text-suave">{erro ? "" : "Carregando os modelos..."}</p>
      ) : (
        <ul className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {modelos.map((modelo) => (
            <CartaoModelo
              key={modelo.id}
              modelo={modelo}
              midia={midia}
              identidade={identidade}
              ocupado={criando}
              aoEscolher={() => escolher(modelo)}
              aoApagar={modelo.pronto ? undefined : () => apagar(modelo)}
            />
          ))}
        </ul>
      )}
    </main>
  );
}

export default function PaginaNovoStory() {
  return (
    <Suspense fallback={<main className="mx-auto max-w-6xl px-4 py-10 text-suave sm:px-6">Carregando os modelos...</main>}>
      <EscolherModelo />
    </Suspense>
  );
}
