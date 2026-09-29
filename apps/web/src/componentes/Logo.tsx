import Image from "next/image";

// Proporções dos SVGs gerados em brand/logo
const VARIANTES = {
  horizontal: { arquivo: "holycut-horizontal.svg", proporcao: 2119.1 / 591.4 },
  slogan: { arquivo: "holycut-horizontal-slogan.svg", proporcao: 2119.1 / 725.0 },
  simbolo: { arquivo: "holycut-simbolo.svg", proporcao: 1 },
} as const;

type Props = {
  variante?: keyof typeof VARIANTES;
  altura?: number;
  className?: string;
  prioridade?: boolean;
};

export function Logo({ variante = "horizontal", altura = 36, className, prioridade = false }: Props) {
  const { arquivo, proporcao } = VARIANTES[variante];
  return (
    <Image
      src={`/brand/logo/${arquivo}`}
      alt="HolyCut"
      width={Math.round(altura * proporcao)}
      height={altura}
      className={className}
      priority={prioridade}
      unoptimized
    />
  );
}
