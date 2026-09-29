// Copia logos, ícones e tokens de /brand para dentro do app.
// Roda sozinho antes de "npm run dev" e "npm run build". A fonte da verdade é /brand.
import { copyFileSync, existsSync, mkdirSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const web = join(dirname(fileURLToPath(import.meta.url)), "..");
const brand = join(web, "..", "..", "brand");

if (!existsSync(brand)) {
  console.error(`[brand] Pasta não encontrada: ${brand}`);
  process.exit(1);
}

function copiar(origem, destino) {
  mkdirSync(dirname(join(web, destino)), { recursive: true });
  copyFileSync(join(brand, origem), join(web, destino));
}

for (const arquivo of readdirSync(join(brand, "logo")).filter((nome) => nome.endsWith(".svg"))) {
  copiar(join("logo", arquivo), join("public", "brand", "logo", arquivo));
}
for (const arquivo of ["icone-maskable-192.png", "icone-maskable-512.png", "icone-escuro-192.png", "icone-escuro-512.png"]) {
  copiar(join("app-icon", arquivo), join("public", "brand", "app-icon", arquivo));
}
copiar(join("app-icon", "favicon.ico"), join("src", "app", "favicon.ico"));
copiar(join("app-icon", "favicon.svg"), join("src", "app", "icon.svg"));
copiar(join("app-icon", "apple-touch-icon.png"), join("src", "app", "apple-icon.png"));
copiar(join("tokens", "design-tokens.css"), join("src", "estilos", "design-tokens.css"));

console.log("[brand] Logos, ícones e tokens copiados.");
