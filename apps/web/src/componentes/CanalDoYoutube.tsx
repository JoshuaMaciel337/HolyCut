"use client";

import { Radio, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";

import { CampoTexto } from "@/componentes/CampoTexto";
import { chamarApi, ErroApi } from "@/lib/api";
import { formatarData } from "@/lib/formatar";
import type { CanalYoutube } from "@/lib/tipos";

/** O canal da igreja no YouTube: libera a importação pelo link e, com o monitor ligado, traz cada live que terminar. */
export function CanalDoYoutube() {
  const [canal, setCanal] = useState<CanalYoutube | null>(null);
  const [texto, setTexto] = useState("");
  const [monitorar, setMonitorar] = useState(false);
  const [erro, setErro] = useState("");
  const [aviso, setAviso] = useState("");

  useEffect(() => {
    chamarApi<CanalYoutube>("/canal-youtube")
      .then((dados) => {
        setCanal(dados);
        setTexto(dados.canal);
        setMonitorar(dados.monitorar);
      })
      .catch((e) => setErro(e instanceof ErroApi ? e.message : "Não foi possível carregar o canal."));
  }, []);

  async function salvar(evento: React.FormEvent) {
    evento.preventDefault();
    setErro("");
    setAviso("");
    try {
      const dados = await chamarApi<CanalYoutube>("/canal-youtube", { metodo: "PUT", corpo: { canal: texto, monitorar } });
      setCanal(dados);
      setAviso(
        dados.monitorar
          ? "Pronto. A partir de agora, cada live que terminar no canal chega sozinha ao HolyCut."
          : "Canal salvo. Já dá para importar as lives dele pelo link.",
      );
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível salvar o canal.");
    }
  }

  async function remover() {
    if (!window.confirm("Remover o canal? O HolyCut para de olhar as lives e a importação pelo link do YouTube fica bloqueada.")) return;
    setErro("");
    setAviso("");
    try {
      await chamarApi(`/canal-youtube`, { metodo: "DELETE" });
      setCanal({ configurado: false, canal: "", id: null, handle: null, monitorar: false, ultima_verificacao: null, ultimo_erro: null });
      setTexto("");
      setMonitorar(false);
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível remover o canal.");
    }
  }

  return (
    <section className="cartao mt-8 flex flex-col gap-4 p-6" aria-labelledby="titulo-canal">
      <h2 id="titulo-canal" className="flex items-center gap-2 font-display text-lg font-bold">
        <Radio className="size-5 text-vermelho" aria-hidden /> Canal do YouTube
      </h2>
      <p className="max-w-2xl text-sm text-suave">
        Com o canal da igreja cadastrado, dá para importar as lives pelo link. Ligue o monitor e o HolyCut importa sozinho cada live que
        terminar. Ele lê o feed público do canal a cada 10 minutos, sem senha do Google e sem custo.
      </p>
      <form onSubmit={salvar} className="flex max-w-xl flex-col gap-3">
        <CampoTexto
          rotulo="Canal"
          name="canal"
          value={texto}
          maxLength={200}
          placeholder="@suaigreja"
          dica="O @ do canal ou o endereço dele no YouTube."
          onChange={(evento) => setTexto(evento.target.value)}
        />
        <label className="flex items-start gap-2 text-sm">
          <input type="checkbox" checked={monitorar} onChange={(evento) => setMonitorar(evento.target.checked)} className="mt-0.5" />
          Importar sozinho cada live que terminar (vídeos com menos de 20 minutos ficam de fora)
        </label>
        <div className="flex flex-wrap gap-2">
          <button type="submit" disabled={!texto.trim()} className="botao-cta">
            Salvar
          </button>
          {canal?.configurado ? (
            <button type="button" onClick={remover} className="botao-contorno px-4 py-2 text-sm">
              <Trash2 className="size-4" aria-hidden /> Remover canal
            </button>
          ) : null}
        </div>
      </form>
      {aviso ? <p className="text-sm text-ciano">{aviso}</p> : null}
      {canal?.configurado && canal.monitorar ? (
        <p className="text-xs text-suave">
          {canal.ultima_verificacao
            ? `Última olhada no canal: ${formatarData(canal.ultima_verificacao)}.`
            : "A primeira olhada no canal acontece em até 1 minuto."}
        </p>
      ) : null}
      {canal?.ultimo_erro ? (
        <p role="alert" className="text-sm text-vermelho">
          Na última olhada: {canal.ultimo_erro}
        </p>
      ) : null}
      {erro ? (
        <p role="alert" className="text-sm text-vermelho">
          {erro}
        </p>
      ) : null}
    </section>
  );
}
