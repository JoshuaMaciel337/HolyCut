"use client";

import { ArrowLeft, BookmarkPlus, Check, CircleAlert, Clapperboard, ImageIcon, LoaderCircle, Pause, Play, RotateCcw } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { CamadaSobreposta } from "@/componentes/CamadaSobreposta";
import { FormaDeOnda } from "@/componentes/FormaDeOnda";
import { ListaExportacoes } from "@/componentes/ListaExportacoes";
import { PainelCor } from "@/componentes/PainelCor";
import { PainelFundo } from "@/componentes/PainelFundo";
import { PainelMarca } from "@/componentes/PainelMarca";
import { type OpcaoCorte, PainelSilencios } from "@/componentes/PainelSilencios";
import { PainelTextos } from "@/componentes/PainelTextos";
import { PreviaEnquadrada } from "@/componentes/PreviaEnquadrada";
import { chamarApi, ErroApi } from "@/lib/api";
import { cssDoFiltro, FiltroSvg, useFiltros } from "@/lib/filtros";
import { formatarTempo } from "@/lib/formatar";
import { PROPORCOES, ZOOM_MAXIMO } from "@/lib/recorte";
import type { Exportacao, FormaDeOnda as DadosFormaDeOnda, Identidade, Midia, Projeto, Proporcao, Silencios } from "@/lib/tipos";

const ESPERA_SALVAR_MS = 700;
type Edicao = Pick<Projeto, "nome" | "proporcao" | "trecho" | "silencios" | "enquadramento" | "marca" | "textos" | "fundo" | "cor">;
type EstadoSalvar = "salvo" | "salvando" | "erro";

/** Cortes de silêncio que caem dentro do trecho, recortados nas bordas dele. */
function cortesNoTrecho(cortes: [number, number][], inicio: number, fim: number): [number, number][] {
  return cortes
    .filter(([a, b]) => b > inicio && a < fim)
    .map(([a, b]) => [Math.max(a, inicio), Math.min(b, fim)] as [number, number]);
}

export default function PaginaProjeto() {
  const { id } = useParams<{ id: string }>();
  const [projeto, setProjeto] = useState<Projeto | null>(null);
  const [edicao, setEdicao] = useState<Edicao | null>(null);
  const [midia, setMidia] = useState<Midia | null>(null);
  const [identidade, setIdentidade] = useState<Identidade | null>(null);
  const [forma, setForma] = useState<DadosFormaDeOnda | null>(null);
  const [silencios, setSilencios] = useState<Silencios | null>(null);
  const [erro, setErro] = useState("");
  const [estadoSalvar, setEstadoSalvar] = useState<EstadoSalvar>("salvo");
  const [tempo, setTempo] = useState(0);
  const [tocando, setTocando] = useState(false);
  const [exportando, setExportando] = useState(false);
  const [ultimaExportacao, setUltimaExportacao] = useState<Exportacao | null>(null);
  const [aviso, setAviso] = useState("");
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
          trecho: carregado.trecho,
          silencios: carregado.silencios,
          enquadramento: carregado.enquadramento,
          marca: carregado.marca,
          fundo: carregado.fundo,
          cor: carregado.cor,
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

  const cortes = useMemo(() => {
    if (!edicao || !intensidade || silencios?.intensidade !== intensidade) return [];
    return cortesNoTrecho(silencios.silencios, edicao.trecho.inicio, edicao.trecho.fim);
  }, [edicao, intensidade, silencios]);
  const duracaoFinal = edicao
    ? edicao.trecho.fim - edicao.trecho.inicio - cortes.reduce((soma, [a, b]) => soma + (b - a), 0)
    : 0;
  // Onde a prévia está na linha do tempo do vídeo final (já sem o que foi cortado)
  const posicaoFinal = edicao
    ? Math.max(
        0,
        Math.min(tempo, edicao.trecho.fim) -
          edicao.trecho.inicio -
          cortes.reduce((soma, [a, b]) => soma + Math.max(0, Math.min(b, tempo) - a), 0),
      )
    : 0;

  // A prévia toca só o trecho, pulando os cortes, como vai ficar no vídeo final
  const regras = useRef({ inicio: 0, fim: 0, cortes: [] as [number, number][] });
  useEffect(() => {
    if (edicao) regras.current = { inicio: edicao.trecho.inicio, fim: edicao.trecho.fim, cortes };
  }, [edicao, cortes]);

  useEffect(() => {
    const elemento = player.current;
    if (!elemento) return;
    let quadro = 0;
    const acompanhar = () => {
      const { inicio, fim, cortes: ativos } = regras.current;
      const corte = ativos.find(([a, b]) => elemento.currentTime >= a && elemento.currentTime < b - 0.05);
      if (corte) elemento.currentTime = corte[1];
      if (elemento.currentTime >= fim) {
        elemento.pause();
        elemento.currentTime = inicio;
      }
      setTempo(elemento.currentTime);
      if (!elemento.paused) quadro = requestAnimationFrame(acompanhar);
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
    return () => {
      cancelAnimationFrame(quadro);
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
    if (elemento.currentTime < edicao.trecho.inicio || elemento.currentTime >= edicao.trecho.fim - 0.1) {
      elemento.currentTime = edicao.trecho.inicio;
    }
    void elemento.play();
  }

  function buscar(segundos: number) {
    if (player.current) player.current.currentTime = segundos;
    setTempo(segundos);
  }

  function marcar(lado: "inicio" | "fim") {
    if (!edicao || !midia?.duracao) return;
    const agora = Math.round(tempo * 100) / 100;
    const { inicio, fim } = edicao.trecho;
    const trecho = lado === "inicio" ? { inicio: Math.min(agora, fim - 1), fim } : { inicio, fim: Math.max(agora, inicio + 1) };
    editar({ trecho });
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

  if (!projeto || !edicao || !midia || !midia.video || !midia.duracao) {
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
            <h2 id="titulo-trecho" className="font-display text-lg font-bold">
              Trecho
            </h2>
            <p className="mt-1 text-sm text-suave">Arraste as alças laranja ou marque pelo ponto em que a prévia está.</p>
            {forma ? (
              <div className="mt-4">
                <FormaDeOnda
                  picos={forma.picos}
                  duracao={midia.duracao}
                  tempo={tempo}
                  aoBuscar={buscar}
                  cortes={cortes}
                  faixa={[edicao.trecho.inicio, edicao.trecho.fim]}
                  aoMudarFaixa={([inicio, fim]) => editar({ trecho: { inicio: Math.round(inicio * 100) / 100, fim: Math.round(fim * 100) / 100 } })}
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
                {formatarTempo(edicao.trecho.inicio)} até {formatarTempo(edicao.trecho.fim)} · {formatarTempo(edicao.trecho.fim - edicao.trecho.inicio)}
              </p>
            </div>
          </section>

          <PainelSilencios
            opcao={opcaoCorte}
            aoMudar={(opcao) => editar({ silencios: { intensidade: opcao === "desligado" ? null : opcao } })}
            dados={
              silencios && intensidade && silencios.intensidade === intensidade
                ? { ...silencios, silencios: cortes, tempo_cortado: edicao.trecho.fim - edicao.trecho.inicio - duracaoFinal, duracao_final: duracaoFinal }
                : null
            }
            carregando={Boolean(intensidade) && silencios?.intensidade !== intensidade}
            duracao={edicao.trecho.fim - edicao.trecho.inicio}
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
