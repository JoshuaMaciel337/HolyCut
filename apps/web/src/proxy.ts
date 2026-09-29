import { NextResponse, type NextRequest } from "next/server";

// Só confere se o cookie existe. Quem valida a sessão de verdade é a API:
// se ela responder 401, a tela apaga o cookie e manda para /entrar.
const COOKIE_SESSAO = "holycut_sessao";

export function proxy(request: NextRequest) {
  const temSessao = request.cookies.has(COOKIE_SESSAO);
  const { pathname, search } = request.nextUrl;

  if (pathname.startsWith("/app") && !temSessao) {
    const destino = new URL("/entrar", request.url);
    destino.searchParams.set("proximo", `${pathname}${search}`);
    return NextResponse.redirect(destino);
  }
  if ((pathname === "/entrar" || pathname === "/cadastro") && temSessao) {
    return NextResponse.redirect(new URL("/app", request.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/app/:path*", "/entrar", "/cadastro"],
};
