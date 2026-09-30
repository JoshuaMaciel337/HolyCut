"use client";

import {
  ArrowLeft,
  BookmarkPlus,
  Check,
  ChevronLeft,
  ChevronRight,
  CircleAlert,
  Clapperboard,
  ImageIcon,
  LoaderCircle,
  Pause,
  Play,
  Plus,
  RotateCcw,
  Scissors,
  Trash2,
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { CamadaSobreposta } from "@/componentes/CamadaSobreposta";
import { FormaDeOnda } from "@/componentes/FormaDeOnda";
import { LinhaDoTempo } from "@/componentes/LinhaDoTempo";
import { ListaExportacoes } from "@/componentes/ListaExportacoes";
import { MusicaNaPrevia } from "@/componentes/MusicaNaPrevia";
import { PainelCor } from "@/componentes/PainelCor";
import { PainelFundo } from "@/componentes/PainelFundo";
import { PainelMarca } from "@/componentes/PainelMarca";
import { PainelMusica } from "@/componentes/PainelMusica";
import { type OpcaoCorte, PainelSilencios } from "@/componentes/PainelSilencios";
import { PainelTextos } from "@/componentes/PainelTextos";
import { PreviaEnquadrada } from "@/componentes/PreviaEnquadrada";
import { chamarApi, ErroApi } from "@/lib/api";
import { cssDoFiltro, FiltroSvg, useFiltros } from "@/lib/filtros";
import { formatarTempo } from "@/lib/formatar";
import {
  cortesNaParte,
  DURACAO_MINIMA_PARTE,
  duracaoDasPartes,
  duracaoFinalDaParte,
  instanteNaParte,
  MAXIMO_PARTES,
  mover,
  novoIdDeParte,
  posicaoNaParte,
} from "@/lib/partes";
import { PROPORCOES, ZOOM_MAXIMO } from "@/lib/recorte";
import type { Exportacao, FormaDeOnda as DadosFormaDeOnda, Identidade, Midia, Musica, Parte, Projeto, Proporcao, Silencios } from "@/lib/tipos";

const ESPERA_SALVAR_MS = 700;
// Pico da forma de onda (em % da escala cheia) a partir do qual a prévia considera que há voz
const PICO_DE_FALA = 4;
type Edicao = Pick<Projeto, "nome" | "proporcao" | "partes" | "silencios" | "enquadramento" | "marca" | "textos" | "fundo" | "cor" | "musica">;
type EstadoSalvar = "salvo" | "salvando" | "erro";

export default function PaginaProjeto() {
  const { id } = useParams<{ id: string }>();
  const [projeto, setProjeto] = useState<Projeto | null>(null);
  const [edicao, setEdicao] = useState<Edicao | null>(null);
  const [midia, setMidia] = useState<Midia | null>(null);
  const [identidade, setIdentidade] = useState<Identidade | null>(null);
  const [musicas, setMusicas] = useState<Musica[] | null>(null);
  const [forma, setForma] = useState<DadosFormaDeOnda | null>(null);
  const [silencios, setSilencios] = useState<Silencios | null>(null);
  const [erro, setErro] = useState("");
  const [estadoSalvar, setEstadoSalvar] = useState<EstadoSalvar>("salvo");
  const [tempo, setTempo] = useState(0);
  const [tocando, setTocando] = useState(false);
  const [exportando, setExportando] = useState(false);
  const [ultimaExportacao, setUltimaExportacao] = useState<Exportacao | null>(null);
  const [aviso, setAviso] = useState("");
  const [avisoParte, setAvisoParte] = useState("");
  // Parte em que a prévia está (a que as alças e os botões da linha do tempo editam)
  const [indiceAtual, setIndiceAtual] = useState(0);
  const indiceRef = useRef(0);
  const player = useRef<HTMLVideoElement>(null);
  const filtros = useFiltros();

  // Salvamento: em fila, um de cada vez, sempre com a versão mais nova que o servidor devolveu
  const versao = useRef(0);
  const fila = useRef<Promise<boolean>>(Promise.resolve(true));
  const espera = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const edicaoAtual = useRef<Edicao | null>(null);

  useEffect(() => {
    let cancelado = false;
    (async () => {
      try {
        const carregado = await chamarApi<Projeto>(`/projetos/${id}`);
        const gravacao = await chamarApi<Midia>(`/midias/${carregado.midia_id}`);
        if (cancelado) return;
        versao.current = carregado.versao;
        const inicial: Edicao = {
          nome: carregado.nome,
          proporcao: carregado.proporcao,
          partes: carregado.partes,
          silencios: carregado.silencios,
          enquadramento: carregado.enquadramento,
          marca: carregado.marca,
          fundo: carregado.fundo,
          cor: carregado.cor,
          musica: carregado.musica,
          textos: carregado.textos,
        };
        edicaoAtual.current = inicial;
        setProjeto(carregado);
        setEdicao(inicial);
        setMidia(gravacao);
        chamarApi<Identidade>("/identidade")
          .then((dados) => {
            if (!cancelado) setIdentidade(dados);
          })
          .catch(() => undefined);
        chamarApi<Musica[]>("/musicas")
          .then((dados) => {
            if (!cancelado) setMusicas(dados);
          })
          .catch(() => undefined);
        if (gravacao.arquivos.includes("forma_de_onda.json")) {
          const resposta = await fetch(`/api/midias/${gravacao.id}/arquivos/forma_de_onda.json`, { credentials: "same-origin" });
          if (resposta.ok && !cancelado) setForma(await resposta.json());
        }
      } catch (e) {
        if (!cancelado) setErro(e instanceof ErroApi ? e.message : "Não foi possível abrir o projeto.");
      }
    })();
    return () => {
      cancelado = true;
    };
  }, [id]);

  const intensidade = edicao?.silencios.intensidade ?? null;
  useEffect(() => {
    if (!midia || !intensidade) return;
    let cancelado = false;
    chamarApi<Silencios>(`/midias/${midia.id}/silencios?intensidade=${intensidade}`)
      .then((dados) => {
        if (!cancelado) setSilencios(dados);
      })
      .catch(() => undefined);
    return () => {
      cancelado = true;
    };
  }, [midia, intensidade]);

  /** Coloca um salvamento na fila. A promessa diz se deu certo. */
  const salvar = useCallback(
    (dados: Edicao): Promise<boolean> => {
      fila.current = fila.current.then(async () => {
        try {
          const salvo = await chamarApi<Projeto>(`/projetos/${id}`, { metodo: "PATCH", corpo: { versao: versao.current, ...dados } });
          versao.current = salvo.versao;
          setProjeto(salvo);
          setEstadoSalvar("salvo");
          return true;
        } catch (e) {
          setEstadoSalvar("erro");
          setErro(e instanceof ErroApi ? e.message : "Não foi possível salvar.");
          return false;
        }
      });
      return fila.current;
    },
    [id],
  );

  const editar = useCallback(
    (mudanca: Partial<Edicao>) => {
      const atual = edicaoAtual.current;
      if (!atual) return;
      const nova = { ...atual, ...mudanca };
      edicaoAtual.current = nova;
      setEdicao(nova);
      setEstadoSalvar("salvando");
      clearTimeout(espera.current);
      espera.current = setTimeout(() => void salvar(nova), ESPERA_SALVAR_MS);
    },
    [salvar],
  );

  const partes = useMemo(() => edicao?.partes ?? [], [edicao]);
  const indice = Math.min(indiceAtual, Math.max(partes.length - 1, 0));
  const parteAtual = partes[indice];
  // Cortes de silêncio de cada parte, e quanto cada uma dura no vídeo final
  const cortesPorParte = useMemo(() => {
    const ativos = intensidade && silencios?.intensidade === intensidade ? silencios.silencios : [];
    return partes.map((parte) => cortesNaParte(ativos, parte));
  }, [partes, intensidade, silencios]);
  const duracoes = partes.map((parte, i) => duracaoFinalDaParte(parte, cortesPorParte[i] ?? []));
  const duracaoFinal = duracoes.reduce((soma, duracao) => soma + duracao, 0);
  // Onde a prévia está no vídeo final: as partes anteriores inteiras mais o ponto dentro da atual
  const posicaoFinal = parteAtual
    ? duracoes.slice(0, indice).reduce((soma, duracao) => soma + duracao, 0) +
      posicaoNaParte(parteAtual, cortesPorParte[indice] ?? [], tempo)
    : 0;

  const irParaParte = useCallback((novo: number) => {
    indiceRef.current = novo;
    setIndiceAtual(novo);
  }, []);

  // A prévia toca as partes na ordem, pulando os cortes, como vai ficar no vídeo final
  const regras = useRef({ partes: [] as Parte[], cortes: [] as [number, number][][] });
  useEffect(() => {
    regras.current = { partes, cortes: cortesPorParte };
  }, [partes, cortesPorParte]);

  useEffect(() => {
    const elemento = player.current;
    if (!elemento) return;
    let quadro = 0;
    /** Fim da parte: segue para a próxima, ou para no fim do vídeo e volta ao começo. */
    const avancar = () => {
      const { partes: lista } = regras.current;
      const atual = Math.min(indiceRef.current, lista.length - 1);
      const proxima = atual + 1 < lista.length ? atual + 1 : 0;
      indiceRef.current = proxima;
      setIndiceAtual(proxima);
      elemento.currentTime = lista[proxima].inicio;
      return proxima;
    };
    const acompanhar = () => {
      const { partes: lista, cortes: porParte } = regras.current;
      const atual = Math.min(indiceRef.current, lista.length - 1);
      const parte = lista[atual];
      if (parte) {
        const corte = (porParte[atual] ?? []).find(([a, b]) => elemento.currentTime >= a && elemento.currentTime < b - 0.05);
        if (corte) elemento.currentTime = corte[1];
        if (elemento.currentTime >= parte.fim && avancar() === 0) elemento.pause();
      }
      setTempo(elemento.currentTime);
      if (!elemento.paused) quadro = requestAnimationFrame(acompanhar);
    };
    // A gravação acabou antes do fim da parte (a última parte vai até o fim do arquivo)
    const aoTerminar = () => {
      if (avancar() !== 0) void elemento.play();
    };
    const aoTocar = () => {
      setTocando(true);
      cancelAnimationFrame(quadro);
      quadro = requestAnimationFrame(acompanhar);
    };
    const aoPausar = () => {
      setTocando(false);
      setTempo(elemento.currentTime);
    };
    // Os saltos da própria prévia (início do trecho, silêncios pulados) também disparam "seeked":
    // só atualizam o tempo, sem mexer no botão de tocar.
    const aoSaltar = () => setTempo(elemento.currentTime);
    elemento.addEventListener("play", aoTocar);
    elemento.addEventListener("pause", aoPausar);
    elemento.addEventListener("seeked", aoSaltar);
    elemento.addEventListener("ended", aoTerminar);
    return () => {
      cancelAnimationFrame(quadro);
      elemento.removeEventListener("ended", aoTerminar);
      elemento.removeEventListener("play", aoTocar);
      elemento.removeEventListener("pause", aoPausar);
      elemento.removeEventListener("seeked", aoSaltar);
    };
  }, [midia]);

  function alternarReproducao() {
    const elemento = player.current;
    if (!elemento || !edicao) return;
    if (!elemento.paused) {
      elemento.pause();
      return;
    }
    const lista = edicao.partes;
    const atual = Math.min(indiceRef.current, lista.length - 1);
    if (elemento.currentTime >= lista[atual].fim - 0.1) {
      const proxima = atual + 1 < lista.length ? atual + 1 : 0;
      irParaParte(proxima);
      elemento.currentTime = lista[proxima].inicio;
    } else if (elemento.currentTime < lista[atual].inicio) {
      elemento.currentTime = lista[atual].inicio;
    }
    void elemento.play();
  }

  function levarPreviaPara(segundos: number) {
    if (player.current) player.current.currentTime = segundos;
    setTempo(segundos);
  }

  /** Clique na forma de onda da gravação. Se cair em outra parte, ela passa a ser a atual. */
  function buscar(segundos: number) {
    const lista = edicaoAtual.current?.partes ?? [];
    const dentro = (parte: Parte) => segundos >= parte.inicio && segundos <= parte.fim;
    const atual = lista[indiceRef.current];
    if (!atual || !dentro(atual)) {
      const achada = lista.findIndex(dentro);
      if (achada >= 0) irParaParte(achada);
    }
    levarPreviaPara(segundos);
  }

  /** Clique num bloco da linha do tempo: vai para aquele ponto do vídeo final. */
  function buscarNaLinhaDoTempo(novo: number, posicao: number) {
    const parte = partes[novo];
    if (!parte) return;
    irParaParte(novo);
    levarPreviaPara(instanteNaParte(parte, cortesPorParte[novo] ?? [], posicao));
  }

  function trocarParte(novaParte: Parte) {
    if (!edicao) return;
    editar({ partes: edicao.partes.map((parte, i) => (i === indice ? novaParte : parte)) });
  }

  function marcar(lado: "inicio" | "fim") {
    if (!parteAtual) return;
    const agora = Math.round(tempo * 100) / 100;
    const { inicio, fim } = parteAtual;
    trocarParte(lado === "inicio" ? { ...parteAtual, inicio: Math.min(agora, fim - 1) } : { ...parteAtual, fim: Math.max(agora, inicio + 1) });
  }

  function dividir() {
    if (!edicao || !parteAtual) return;
    const ponto = Math.round(tempo * 100) / 100;
    if (ponto - parteAtual.inicio < DURACAO_MINIMA_PARTE || parteAtual.fim - ponto < DURACAO_MINIMA_PARTE) {
      setAvisoParte("Para dividir, leve a prévia até um ponto da parte com pelo menos 1 segundo de cada lado.");
      return;
    }
    if (edicao.partes.length >= MAXIMO_PARTES) {
      setAvisoParte(`O vídeo pode ter até ${MAXIMO_PARTES} partes.`);
      return;
    }
    setAvisoParte("");
    const segunda = { id: novoIdDeParte(edicao.partes), inicio: ponto, fim: parteAtual.fim };
    editar({ partes: [...edicao.partes.slice(0, indice), { ...parteAtual, fim: ponto }, segunda, ...edicao.partes.slice(indice + 1)] });
    irParaParte(indice + 1);
  }

  function novaParte() {
    if (!edicao || !midia?.duracao) return;
    if (edicao.partes.length >= MAXIMO_PARTES) {
      setAvisoParte(`O vídeo pode ter até ${MAXIMO_PARTES} partes.`);
      return;
    }
    setAvisoParte("");
    const duracao = Math.floor(midia.duracao * 100) / 100;
    const inicio = Math.min(Math.round(tempo * 100) / 100, duracao - DURACAO_MINIMA_PARTE);
    const parte = { id: novoIdDeParte(edicao.partes), inicio, fim: Math.min(inicio + 10, duracao) };
    editar({ partes: [...edicao.partes.slice(0, indice + 1), parte, ...edicao.partes.slice(indice + 1)] });
    irParaParte(indice + 1);
    levarPreviaPara(inicio);
  }

  function reordenar(de: number, para: number) {
    if (!edicao || para < 0 || para >= edicao.partes.length) return;
    const idAtual = edicao.partes[indice]?.id;
    const novas = mover(edicao.partes, de, para);
    editar({ partes: novas });
    irParaParte(Math.max(novas.findIndex((parte) => parte.id === idAtual), 0));
  }

  function apagarParte() {
    if (!edicao || edicao.partes.length < 2) return;
    const restantes = edicao.partes.filter((_, i) => i !== indice);
    const novo = Math.min(indice, restantes.length - 1);
    editar({ partes: restantes });
    irParaParte(novo);
    levarPreviaPara(restantes[novo].inicio);
  }

  async function exportar(formato: "video" | "imagem") {
    const atual = edicaoAtual.current;
    if (!atual) return;
    setExportando(true);
    setErro("");
    try {
      // Garante que o vídeo sai com a última edição: salva e espera a fila terminar
      clearTimeout(espera.current);
      if (!(await salvar(atual))) return;
      const corpo = { formato, instante: Math.round(posicaoFinal * 100) / 100 };
      setUltimaExportacao(await chamarApi<Exportacao>(`/projetos/${id}/exportar`, { metodo: "POST", corpo }));
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível exportar.");
    } finally {
      setExportando(false);
    }
  }

  async function salvarComoModelo() {
    const atual = edicaoAtual.current;
    const nome = window.prompt("Nome do modelo (ex.: Culto de domingo)", atual?.nome.replace(/^(Story|Reel) · /, "") ?? "");
    if (!atual || !nome?.trim()) return;
    clearTimeout(espera.current);
    if (!(await salvar(atual))) return;
    try {
      await chamarApi("/modelos", { metodo: "POST", corpo: { nome: nome.trim().slice(0, 60), projeto_id: id } });
      setAviso(`Modelo "${nome.trim()}" salvo. Ele aparece quando você criar um Story.`);
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível salvar o modelo.");
    }
  }

  const voltar = midia ? (
    <Link href={`/app/midias/${midia.id}`} className="inline-flex items-center gap-2 text-sm text-suave hover:text-texto">
      <ArrowLeft className="size-4" aria-hidden /> {midia.nome}
    </Link>
  ) : (
    <Link href="/app" className="inline-flex items-center gap-2 text-sm text-suave hover:text-texto">
      <ArrowLeft className="size-4" aria-hidden /> Início
    </Link>
  );

  if (!projeto || !edicao || !parteAtual || !midia || !midia.video || !midia.duracao) {
    return (
      <main className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
        {voltar}
        <p className="mt-6 text-suave">{erro || "Carregando o editor..."}</p>
      </main>
    );
  }

  const base = `/api/midias/${midia.id}/arquivos`;
  const opcaoCorte: OpcaoCorte = intensidade ?? "desligado";
  const alvo = PROPORCOES[edicao.proporcao];
  const filtroEscolhido = filtros.find((filtro) => filtro.id === edicao.cor.filtro);
  const musicaEscolhida = musicas?.find((item) => item.id === edicao.musica.id && item.status === "pronta" && item.duracao);
  const indicePico = forma ? Math.floor(tempo * forma.picos_por_segundo) : -1;
  const falando = forma ? Math.max(...forma.picos.slice(Math.max(indicePico - 1, 0), indicePico + 2), 0) >= PICO_DE_FALA : false;

  return (
    <main className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
      {voltar}
      <div className="mt-4 flex flex-wrap items-center justify-between gap-4">
        <input
          value={edicao.nome}
          onChange={(evento) => editar({ nome: evento.target.value.slice(0, 120) })}
          aria-label="Nome do projeto"
          className="min-w-0 flex-1 rounded-xl border border-transparent bg-transparent px-2 py-1 font-display text-2xl font-bold outline-none hover:border-borda focus:border-violeta sm:text-3xl"
        />
        <span className="inline-flex items-center gap-1.5 text-sm text-suave" aria-live="polite">
          {estadoSalvar === "salvando" ? (
            <>
              <LoaderCircle className="size-4 animate-spin" aria-hidden /> Salvando
            </>
          ) : estadoSalvar === "erro" ? (
            <>
              <CircleAlert className="size-4 text-vermelho" aria-hidden /> Não salvou
            </>
          ) : (
            <>
              <Check className="size-4 text-ciano" aria-hidden /> Salvo
            </>
          )}
        </span>
      </div>
      {erro ? (
        <p role="alert" className="mt-4 rounded-xl border border-vermelho/40 bg-vermelho/10 px-4 py-3 text-sm text-vermelho">
          {erro}
        </p>
      ) : null}

      <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,380px)_1fr]">
        <section className="flex flex-col items-center gap-4" aria-label="Prévia">
          <FiltroSvg id="cor-previa" filtro={filtroEscolhido} intensidade={edicao.cor.intensidade} />
          <PreviaEnquadrada
            player={player}
            src={`${base}/proxy.mp4`}
            poster={midia.arquivos.includes("capa.jpg") ? `${base}/capa.jpg` : undefined}
            largura={midia.video.largura}
            altura={midia.video.altura}
            proporcao={edicao.proporcao}
            enquadramento={edicao.enquadramento}
            aoMudar={(enquadramento) => editar({ enquadramento })}
            fundo={edicao.fundo}
            filtroCor={cssDoFiltro("cor-previa", filtroEscolhido, edicao.cor.intensidade)}
          >
            {identidade?.logo && edicao.marca.logo ? (
              <CamadaSobreposta pedido={{ largura: alvo.largura, altura: alvo.altura, tipo: "logo", marca: edicao.marca }} />
            ) : null}
            {edicao.textos
              .filter((texto) => texto.texto.trim())
              .map((texto) => (
                <CamadaSobreposta
                  key={texto.id}
                  pedido={{ largura: alvo.largura, altura: alvo.altura, tipo: "texto", texto }}
                  visivel={posicaoFinal >= texto.inicio && (texto.fim === null || posicaoFinal < texto.fim)}
                />
              ))}
          </PreviaEnquadrada>
          {musicaEscolhida ? (
            <MusicaNaPrevia
              src={`/api/musicas/${musicaEscolhida.id}/arquivo`}
              duracao={musicaEscolhida.duracao ?? 0}
              musica={edicao.musica}
              posicaoFinal={posicaoFinal}
              tocando={tocando}
              falando={falando}
            />
          ) : null}
          <div className="flex items-center gap-3">
            <button type="button" onClick={alternarReproducao} className="botao-cta size-12 p-0" aria-label={tocando ? "Pausar" : "Tocar o trecho"}>
              {tocando ? <Pause className="size-5" aria-hidden /> : <Play className="size-5" aria-hidden />}
            </button>
            <p className="text-sm tabular-nums text-suave">
              {formatarTempo(posicaoFinal)} de <strong className="text-texto">{formatarTempo(duracaoFinal)}</strong> no vídeo final
            </p>
          </div>
        </section>

        <div className="flex min-w-0 flex-col gap-6">
          <section className="cartao p-6" aria-labelledby="titulo-formato">
            <h2 id="titulo-formato" className="font-display text-lg font-bold">
              Formato
            </h2>
            <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4" role="radiogroup" aria-label="Proporção">
              {(Object.keys(PROPORCOES) as Proporcao[]).map((valor) => {
                const escolhido = edicao.proporcao === valor;
                return (
                  <button
                    key={valor}
                    type="button"
                    role="radio"
                    aria-checked={escolhido}
                    onClick={() => editar({ proporcao: valor })}
                    className={`flex flex-col items-center gap-1 rounded-2xl border px-3 py-3 transition ${
                      escolhido ? "border-laranja bg-laranja/10" : "border-borda hover:border-suave"
                    }`}
                  >
                    <span className="font-display font-bold">{valor}</span>
                    <span className="text-xs text-suave">{PROPORCOES[valor].rotulo}</span>
                  </button>
                );
              })}
            </div>
            <label className="mt-5 flex items-center gap-4 text-sm">
              <span className="shrink-0 text-suave">Zoom</span>
              <input
                type="range"
                min={1}
                max={ZOOM_MAXIMO}
                step={0.05}
                value={edicao.enquadramento.zoom}
                onChange={(evento) => editar({ enquadramento: { ...edicao.enquadramento, zoom: Number(evento.target.value) } })}
                className="w-full accent-[var(--hc-orange)]"
              />
              <span className="w-12 text-right tabular-nums">{edicao.enquadramento.zoom.toFixed(2)}x</span>
            </label>
            <button
              type="button"
              onClick={() => editar({ enquadramento: { x: 0.5, y: 0.5, zoom: 1 } })}
              className="mt-3 inline-flex items-center gap-1.5 text-sm text-suave hover:text-texto"
            >
              <RotateCcw className="size-4" aria-hidden /> Centralizar
            </button>
          </section>

          <section className="cartao p-6" aria-labelledby="titulo-trecho">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h2 id="titulo-trecho" className="font-display text-lg font-bold">
                Linha do tempo
              </h2>
              <p className="text-sm tabular-nums text-suave">
                {partes.length} {partes.length === 1 ? "parte" : "partes"} · {formatarTempo(duracaoFinal)} no vídeo
              </p>
            </div>
            <p className="mt-1 text-sm text-suave">Divida no ponto da prévia e arraste as partes para mudar a ordem. A mesma parte da gravação pode entrar mais de uma vez.</p>
            <div className="mt-4">
              <LinhaDoTempo
                partes={partes}
                duracoes={duracoes}
                indiceAtual={indice}
                posicaoFinal={posicaoFinal}
                aoBuscar={buscarNaLinhaDoTempo}
                aoReordenar={reordenar}
              />
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              <button type="button" onClick={dividir} className="botao-contorno px-4 py-2 text-sm">
                <Scissors className="size-4" aria-hidden /> Dividir aqui
              </button>
              <button type="button" onClick={novaParte} className="botao-contorno px-4 py-2 text-sm">
                <Plus className="size-4" aria-hidden /> Nova parte aqui
              </button>
              <button
                type="button"
                onClick={() => reordenar(indice, indice - 1)}
                disabled={indice === 0}
                className="botao-contorno px-3 py-2 text-sm disabled:opacity-40"
                aria-label="Mover a parte para antes"
              >
                <ChevronLeft className="size-4" aria-hidden />
              </button>
              <button
                type="button"
                onClick={() => reordenar(indice, indice + 1)}
                disabled={indice >= partes.length - 1}
                className="botao-contorno px-3 py-2 text-sm disabled:opacity-40"
                aria-label="Mover a parte para depois"
              >
                <ChevronRight className="size-4" aria-hidden />
              </button>
              <button type="button" onClick={apagarParte} disabled={partes.length < 2} className="botao-contorno px-4 py-2 text-sm disabled:opacity-40">
                <Trash2 className="size-4" aria-hidden /> Apagar parte
              </button>
            </div>
            {avisoParte ? <p className="mt-2 text-sm text-amarelo">{avisoParte}</p> : null}

            <h3 className="mt-6 text-sm font-semibold">
              Parte {indice + 1} na gravação <span className="font-normal text-suave">· arraste as alças laranja ou marque pelo ponto da prévia</span>
            </h3>
            {forma ? (
              <div className="mt-2">
                <FormaDeOnda
                  picos={forma.picos}
                  duracao={midia.duracao}
                  tempo={tempo}
                  aoBuscar={buscar}
                  cortes={cortesPorParte.flat()}
                  faixa={[parteAtual.inicio, parteAtual.fim]}
                  aoMudarFaixa={([inicio, fim]) => trocarParte({ ...parteAtual, inicio: Math.round(inicio * 100) / 100, fim: Math.round(fim * 100) / 100 })}
                  outrasFaixas={partes.filter((_, i) => i !== indice).map((parte) => [parte.inicio, parte.fim] as [number, number])}
                />
              </div>
            ) : null}
            <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm">
              <div className="flex flex-wrap gap-2">
                <button type="button" onClick={() => marcar("inicio")} className="botao-contorno px-4 py-2 text-sm">
                  Início aqui
                </button>
                <button type="button" onClick={() => marcar("fim")} className="botao-contorno px-4 py-2 text-sm">
                  Fim aqui
                </button>
              </div>
              <p className="tabular-nums text-suave">
                {formatarTempo(parteAtual.inicio)} até {formatarTempo(parteAtual.fim)} · {formatarTempo(parteAtual.fim - parteAtual.inicio)}
              </p>
            </div>
          </section>

          <PainelSilencios
            opcao={opcaoCorte}
            aoMudar={(opcao) => editar({ silencios: { intensidade: opcao === "desligado" ? null : opcao } })}
            dados={
              silencios && intensidade && silencios.intensidade === intensidade
                ? { ...silencios, silencios: cortesPorParte.flat(), tempo_cortado: duracaoDasPartes(partes) - duracaoFinal, duracao_final: duracaoFinal }
                : null
            }
            carregando={Boolean(intensidade) && silencios?.intensidade !== intensidade}
            duracao={duracaoDasPartes(partes)}
            pular
            aoMudarPular={() => undefined}
            semOpcaoPular
          />

          <PainelTextos
            textos={edicao.textos}
            aoMudar={(textos) => editar({ textos })}
            duracaoFinal={duracaoFinal}
            posicaoFinal={posicaoFinal}
          />

          <PainelMusica musica={edicao.musica} musicas={musicas} aoMudar={(musica) => editar({ musica })} />

          <PainelCor
            cor={edicao.cor}
            aoMudar={(cor) => editar({ cor })}
            capa={midia.arquivos.includes("capa.jpg") ? `${base}/capa.jpg` : undefined}
          />

          <PainelFundo fundo={edicao.fundo} aoMudar={(fundo) => editar({ fundo })} />

          <PainelMarca marca={edicao.marca} temLogo={Boolean(identidade?.logo)} aoMudar={(marca) => editar({ marca })} />

          <section className="cartao p-6" aria-labelledby="titulo-exportar">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <h2 id="titulo-exportar" className="font-display text-lg font-bold">
                  Exportar
                </h2>
                <p className="mt-1 text-sm text-suave">
                  {PROPORCOES[edicao.proporcao].largura}×{PROPORCOES[edicao.proporcao].altura}. O vídeo sai com o áudio no volume das
                  redes (-14 LUFS); a imagem é o quadro em que a prévia está ({formatarTempo(posicaoFinal)}).
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <button type="button" onClick={() => exportar("video")} disabled={exportando} className="botao-cta">
                  <Clapperboard className="size-4" aria-hidden /> {exportando ? "Enviando para a fila..." : "Exportar vídeo"}
                </button>
                <button type="button" onClick={() => exportar("imagem")} disabled={exportando} className="botao-contorno">
                  <ImageIcon className="size-4" aria-hidden /> Exportar imagem
                </button>
              </div>
            </div>
            <button type="button" onClick={salvarComoModelo} className="mt-4 inline-flex items-center gap-1.5 text-sm text-suave hover:text-texto">
              <BookmarkPlus className="size-4" aria-hidden /> Salvar o visual como modelo
            </button>
            {aviso ? <p className="mt-2 text-sm text-ciano">{aviso}</p> : null}
            <div className="mt-5">
              <ListaExportacoes projetoId={projeto.id} nova={ultimaExportacao} />
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}
