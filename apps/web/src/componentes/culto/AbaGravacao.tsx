"use client";

import { Download, ImagePlus } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { BlocosDoCulto } from "@/componentes/culto/BlocosDoCulto";
import { PainelPregacao } from "@/componentes/culto/PainelPregacao";
import { FaixaDeMiniaturas } from "@/componentes/FaixaDeMiniaturas";
import { FormaDeOnda } from "@/componentes/FormaDeOnda";
import { type OpcaoCorte, PainelSilencios } from "@/componentes/PainelSilencios";
import { ReelsDaMidia } from "@/componentes/ReelsDaMidia";
import { chamarApi, ErroApi } from "@/lib/api";
import { formatarBytes, formatarData, formatarTempo } from "@/lib/formatar";
import type { FormaDeOnda as DadosFormaDeOnda, Midia, Silencios } from "@/lib/tipos";
import { useBlocos } from "@/lib/useBlocos";

function Informacao({ rotulo, valor }: { rotulo: string; valor: string }) {
  return (
    <div className="flex justify-between gap-4 border-b border-borda py-2.5 text-sm last:border-0">
      <dt className="text-suave">{rotulo}</dt>
      <dd className="text-right font-medium">{valor}</dd>
    </div>
  );
}

/** A gravação inteira: player, forma de onda, miniaturas, blocos do culto, pregação, silêncios e detalhes técnicos. */
export function AbaGravacao({ midia, aoMudar }: { midia: Midia; aoMudar: (midia: Midia) => void }) {
  const [forma, setForma] = useState<DadosFormaDeOnda | null>(null);
  const [tempo, setTempo] = useState(0);
  const [opcaoCorte, setOpcaoCorte] = useState<OpcaoCorte>("media");
  const [silencios, setSilencios] = useState<Silencios | null>(null);
  const [pularSilencios, setPularSilencios] = useState(true);
  const [erroSilencios, setErroSilencios] = useState("");
  const [avisoCapa, setAvisoCapa] = useState("");
  const [rascunhoPregacao, setRascunhoPregacao] = useState<[number, number] | null>(null);
  const player = useRef<HTMLVideoElement & HTMLAudioElement>(null);
  // Lidos a cada quadro da prévia, sem recriar o acompanhamento do player
  const cortesAtivos = useRef<[number, number][]>([]);
  const id = midia.id;
  // Os blocos podem marcar a pregação: a gravação é recarregada quando o job termina
  const recarregar = useCallback(() => {
    chamarApi<Midia>(`/midias/${id}`).then(aoMudar).catch(() => undefined);
  }, [id, aoMudar]);
  const blocos = useBlocos(id, recarregar);

  const temForma = midia.arquivos.includes("forma_de_onda.json");
  useEffect(() => {
    if (!temForma) return;
    let cancelado = false;
    fetch(`/api/midias/${id}/arquivos/forma_de_onda.json`, { credentials: "same-origin" })
      .then((resposta) => (resposta.ok ? resposta.json() : null))
      .then((dados) => {
        if (!cancelado && dados) setForma(dados);
      })
      .catch(() => undefined);
    return () => {
      cancelado = true;
    };
  }, [id, temForma]);

  useEffect(() => {
    if (opcaoCorte === "desligado") return;
    let cancelado = false;
    chamarApi<Silencios>(`/midias/${id}/silencios?intensidade=${opcaoCorte}`)
      .then((dados) => {
        if (!cancelado) setSilencios(dados);
      })
      .catch((e) => {
        if (!cancelado) setErroSilencios(e instanceof ErroApi ? e.message : "Não foi possível analisar os silêncios.");
      });
    return () => {
      cancelado = true;
    };
  }, [id, opcaoCorte]);

  const cortes = opcaoCorte !== "desligado" && silencios?.intensidade === opcaoCorte ? silencios.silencios : null;
  useEffect(() => {
    cortesAtivos.current = cortes && pularSilencios ? cortes : [];
  }, [cortes, pularSilencios]);

  // Enquanto toca, acompanha o tempo a cada quadro para a forma de onda andar sem saltos
  useEffect(() => {
    const elemento = player.current;
    if (!elemento) return;
    let quadro = 0;
    const acompanhar = () => {
      // Prévia do corte: ao entrar num silêncio, pula para o fim dele
      const corte = cortesAtivos.current.find(([inicio, fim]) => elemento.currentTime >= inicio && elemento.currentTime < fim - 0.05);
      if (corte) elemento.currentTime = corte[1];
      setTempo(elemento.currentTime);
      if (!elemento.paused) quadro = requestAnimationFrame(acompanhar);
    };
    const tocar = () => {
      cancelAnimationFrame(quadro);
      quadro = requestAnimationFrame(acompanhar);
    };
    const atualizar = () => setTempo(elemento.currentTime);
    elemento.addEventListener("play", tocar);
    elemento.addEventListener("seeked", atualizar);
    elemento.addEventListener("pause", atualizar);
    return () => {
      cancelAnimationFrame(quadro);
      elemento.removeEventListener("play", tocar);
      elemento.removeEventListener("seeked", atualizar);
      elemento.removeEventListener("pause", atualizar);
    };
  }, [id]);

  function buscar(segundos: number) {
    if (player.current) player.current.currentTime = segundos;
    setTempo(segundos);
  }

  async function usarNaCapa() {
    setAvisoCapa("");
    try {
      aoMudar(await chamarApi<Midia>(`/midias/${id}/capa`, { metodo: "POST", corpo: { instante: Math.round(tempo * 100) / 100 } }));
      setAvisoCapa(`O quadro de ${formatarTempo(tempo)} vai para a capa. Leva alguns segundos.`);
    } catch (e) {
      setAvisoCapa(e instanceof ErroApi ? e.message : "Não foi possível trocar a capa.");
    }
  }

  const video = midia.video;
  const emPe = video ? video.altura > video.largura : false;
  const base = `/api/midias/${id}/arquivos`;

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
      <div className="flex min-w-0 flex-col gap-6">
        <section className="cartao flex min-w-0 flex-col gap-4 p-4 sm:p-6" aria-label="Prévia">
          {video ? (
            <video
              ref={player}
              src={`${base}/proxy.mp4`}
              poster={midia.arquivos.includes("capa.jpg") ? `${base}/capa.jpg` : undefined}
              controls
              playsInline
              preload="metadata"
              className={`mx-auto w-full rounded-xl bg-black ${emPe ? "max-h-[70vh] w-auto" : ""}`}
              style={{ aspectRatio: `${video.largura} / ${video.altura}` }}
            />
          ) : (
            <audio ref={player} src={`${base}/proxy.m4a`} controls preload="metadata" className="w-full" />
          )}
          {forma && midia.duracao ? (
            <div>
              <FormaDeOnda
                picos={forma.picos}
                duracao={midia.duracao}
                tempo={tempo}
                aoBuscar={buscar}
                cortes={cortes ?? []}
                faixa={rascunhoPregacao ?? undefined}
                aoMudarFaixa={rascunhoPregacao ? setRascunhoPregacao : undefined}
              />
              <p className="mt-2 text-right text-xs tabular-nums text-suave">
                {formatarTempo(tempo)} / {formatarTempo(midia.duracao)}
              </p>
            </div>
          ) : null}
          {midia.miniaturas && midia.arquivos.includes("miniaturas.jpg") ? (
            <FaixaDeMiniaturas midiaId={midia.id} miniaturas={midia.miniaturas} tempo={tempo} aoBuscar={buscar} />
          ) : null}
          {video ? (
            <div className="flex flex-wrap items-center gap-3">
              <button type="button" onClick={usarNaCapa} className="botao-contorno px-3 py-2 text-sm">
                <ImagePlus className="size-4" aria-hidden /> Usar este quadro na capa
              </button>
              {avisoCapa ? <p className="text-sm text-suave">{avisoCapa}</p> : null}
            </div>
          ) : null}
        </section>
        {midia.duracao ? (
          <BlocosDoCulto
            dados={blocos.dados}
            erro={blocos.erro}
            andando={blocos.andando}
            pedir={blocos.pedir}
            duracao={midia.duracao}
            tempo={tempo}
            aoBuscar={buscar}
          />
        ) : null}
      </div>
      <aside className="flex flex-col gap-6">
        {midia.duracao ? (
          <PainelPregacao
            midia={midia}
            tempo={tempo}
            rascunho={rascunhoPregacao}
            aoMudarRascunho={setRascunhoPregacao}
            sugestao={blocos.dados?.status === "pronta" ? blocos.dados.pregacao : null}
            aoBuscar={buscar}
            aoMudar={aoMudar}
          />
        ) : null}
        {midia.arquivos.includes("forma_de_onda.json") && midia.duracao ? (
          <PainelSilencios
            opcao={opcaoCorte}
            aoMudar={setOpcaoCorte}
            dados={cortes ? silencios : null}
            carregando={opcaoCorte !== "desligado" && !cortes}
            duracao={midia.duracao}
            pular={pularSilencios}
            aoMudarPular={setPularSilencios}
            erro={erroSilencios}
          />
        ) : null}
        <ReelsDaMidia midia={midia} tempoAtual={tempo} />
        <section className="cartao p-6" aria-labelledby="titulo-info">
          <h2 id="titulo-info" className="font-display text-lg font-bold">
            Detalhes
          </h2>
          <dl className="mt-3">
            <Informacao rotulo="Duração" valor={formatarTempo(midia.duracao)} />
            {video ? (
              <>
                <Informacao rotulo="Resolução" valor={`${video.largura} × ${video.altura}`} />
                <Informacao rotulo="Quadros por segundo" valor={video.fps ? String(Math.round(video.fps * 100) / 100) : "—"} />
              </>
            ) : null}
            {midia.audio ? (
              <Informacao rotulo="Áudio" valor={`${midia.audio.canais === 1 ? "Mono" : "Estéreo"} · ${Math.round(midia.audio.taxa / 1000)} kHz`} />
            ) : null}
            <Informacao rotulo="Tamanho" valor={formatarBytes(midia.tamanho_total)} />
            <Informacao rotulo="Enviada em" valor={midia.enviado_em ? formatarData(midia.enviado_em) : "—"} />
            <Informacao rotulo="Arquivo" valor={midia.nome_original} />
            {midia.importacao ? (
              <Informacao rotulo="Importada do" valor={midia.importacao.origem === "youtube" ? "YouTube" : "Google Drive"} />
            ) : null}
          </dl>
          {midia.status === "pronta" ? (
            <a href={`/api/midias/${id}/original`} download className="mt-4 inline-flex items-center gap-1.5 text-sm text-suave hover:text-texto">
              <Download className="size-4" aria-hidden /> Baixar a gravação original
            </a>
          ) : null}
        </section>
      </aside>
    </div>
  );
}
