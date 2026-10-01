import Image from "next/image";

// Proporções dos SVGs gerados em brand/logo. "claro" é a versão para fundo claro.
const VARIANTES = {
  horizontal: { escuro: "holycut-horizontal.svg", claro: "holycut-horizontal-fundo-claro.svg", proporcao: 2119.1 / 591.4 },
  slogan: { escuro: "holycut-horizontal-slogan.svg", claro: "holycut-horizontal-slogan-fundo-claro.svg", proporcao: 2119.1 / 725.0 },
  simbolo: { escuro: "holycut-simbolo.svg", claro: "holycut-simbolo-fundo-claro.svg", proporcao: 1 },
} as const;

type Props = {
  variante?: keyof typeof VARIANTES;
  altura?: number;
  className?: string;
  prioridade?: boolean;
  /** "escuro" fixa a versão para fundo escuro, como dentro dos celulares desenhados na home. */
  fundo?: "tema" | "escuro";
};

/** O logo acompanha o tema: as duas versões vão no HTML e o CSS mostra a certa, sem piscar. */
export function Logo({ variante = "horizontal", altura = 36, className = "", prioridade = false, fundo = "tema" }: Props) {
  const { escuro, claro, proporcao } = VARIANTES[variante];
  const largura = Math.round(altura * proporcao);
  const imagem = (arquivo: string, classe: string) => (
    <Image
      src={`/brand/logo/${arquivo}`}
      alt="HolyCut"
      width={largura}
      height={altura}
      className={`${classe} ${className}`}
      priority={prioridade}
      unoptimized
    />
  );
  if (fundo === "escuro") return imagem(escuro, "");
  return (
    <>
      {imagem(escuro, "so-escuro")}
      {imagem(claro, "so-claro")}
    </>
  );
}
