import Link from "next/link";

import { Logo } from "@/componentes/Logo";

export default function LayoutConta({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <div
      className="flex min-h-dvh flex-col items-center justify-center px-4 py-12"
      style={{
        background:
          "radial-gradient(circle at 20% 15%, rgba(168,85,247,.16), transparent 40%)," +
          "radial-gradient(circle at 80% 85%, rgba(255,138,0,.10), transparent 40%)",
      }}
    >
      <Link href="/" aria-label="Voltar para a página inicial">
        <Logo variante="slogan" altura={96} prioridade />
      </Link>
      <main className="cartao mt-10 w-full max-w-md p-6 sm:p-8">{children}</main>
    </div>
  );
}
