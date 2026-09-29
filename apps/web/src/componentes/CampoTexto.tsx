import type { InputHTMLAttributes } from "react";

type Props = InputHTMLAttributes<HTMLInputElement> & {
  rotulo: string;
  dica?: string;
};

export function CampoTexto({ rotulo, dica, id, className, ...resto }: Props) {
  const campoId = id ?? resto.name;
  return (
    <label htmlFor={campoId} className="flex flex-col gap-2">
      <span className="text-sm font-medium text-texto">{rotulo}</span>
      <input
        id={campoId}
        className={`rounded-xl border border-borda bg-ink px-4 py-3 text-texto placeholder:text-suave/60 outline-none transition focus:border-violeta focus:ring-2 focus:ring-violeta/30 ${className ?? ""}`}
        {...resto}
      />
      {dica ? <span className="text-xs text-suave">{dica}</span> : null}
    </label>
  );
}
