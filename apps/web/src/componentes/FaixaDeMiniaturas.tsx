"use client";

import { formatarTempo } from "@/lib/formatar";
import type { Miniaturas } from "@/lib/tipos";

const LARGURA_EXIBIDA = 128;

/** Miniaturas recortadas da imagem única gerada na ingestão. Clicar leva o player até aquele ponto. */
export function FaixaDeMiniaturas({
  midiaId,
  miniaturas,
  tempo,
  aoBuscar,
}: {
  midiaId: string;
  miniaturas: Miniaturas;
  tempo: number;
  aoBuscar: (segundos: number) => void;
}) {
  const alturaExibida = Math.round((LARGURA_EXIBIDA * miniaturas.altura) / miniaturas.largura);
  const imagem = `url(/api/midias/${midiaId}/arquivos/miniaturas.jpg)`;
  const atual = Math.min(Math.floor(tempo / miniaturas.intervalo), miniaturas.total - 1);

  return (
    <ol className="flex gap-2 overflow-x-auto pb-2" aria-label="Miniaturas da gravação">
      {Array.from({ length: miniaturas.total }, (_, indice) => {
        const coluna = indice % miniaturas.colunas;
        const linha = Math.floor(indice / miniaturas.colunas);
        const instante = indice * miniaturas.intervalo;
        return (
          <li key={indice} className="shrink-0">
            <button
              type="button"
              onClick={() => aoBuscar(instante)}
              title={formatarTempo(instante)}
              aria-label={`Ir para ${formatarTempo(instante)}`}
              className={`block overflow-hidden rounded-lg border-2 transition ${
                indice === atual ? "border-laranja" : "border-transparent opacity-70 hover:opacity-100"
              }`}
              style={{
                width: LARGURA_EXIBIDA,
                height: alturaExibida,
                backgroundImage: imagem,
                backgroundSize: `${miniaturas.colunas * LARGURA_EXIBIDA}px auto`,
                backgroundPosition: `-${coluna * LARGURA_EXIBIDA}px -${linha * alturaExibida}px`,
              }}
            />
          </li>
        );
      })}
    </ol>
  );
}
