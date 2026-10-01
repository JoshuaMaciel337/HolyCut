import { CloudUpload, FolderKanban, House, Library, Settings } from "lucide-react";
import Image from "next/image";

import { Logo } from "@/componentes/Logo";

const MOMENTOS = [
  { imagem: "/marketing/louvor-maos.jpg", tempo: "12:40" },
  { imagem: "/marketing/cruz-banda.jpg", tempo: "18:05" },
  { imagem: "/marketing/pregador-palco.jpg", tempo: "41:22" },
  { imagem: "/marketing/louvor-palco.jpg", tempo: "1:02:10" },
];

const CORTES = [
  { imagem: "/marketing/pregador-retrato.jpg", duracao: "0:42" },
  { imagem: "/marketing/story-cruz.jpg", duracao: "0:18" },
  { imagem: "/marketing/pregador-costas.jpg", duracao: "0:55" },
  { imagem: "/marketing/camera.jpg", duracao: "0:31" },
];

const MENU = [
  { icone: House, rotulo: "Início", ativo: true },
  { icone: FolderKanban, rotulo: "Projetos" },
  { icone: Library, rotulo: "Acervo" },
  { icone: Settings, rotulo: "Ajustes" },
];

function Miniatura({ imagem, selo, proporcao }: { imagem: string; selo: string; proporcao: string }) {
  return (
    <div className={`relative overflow-hidden rounded-lg border border-white/10 ${proporcao}`}>
      <Image src={imagem} alt="" fill sizes="120px" className="object-cover" />
      <span className="absolute bottom-1 right-1 rounded bg-black/70 px-1 text-[9px] tabular-nums text-white/90">{selo}</span>
    </div>
  );
}

/** O app numa janela: o envio do culto, os momentos que a IA achou e os cortes prontos. É um desenho, não um print. */
export function PainelDoApp() {
  return (
    <div className="grid grid-cols-[110px_1fr] overflow-hidden rounded-2xl border border-white/10 bg-[#0e0e12] text-left shadow-[0_40px_120px_rgba(0,0,0,.7)]" aria-hidden>
      <aside className="flex flex-col gap-1 border-r border-white/5 p-3">
        <Logo fundo="escuro" altura={18} className="mb-4" />
        {MENU.map(({ icone: Icone, rotulo, ativo }) => (
          <span
            key={rotulo}
            className={`flex items-center gap-2 rounded-lg px-2 py-1.5 text-[11px] ${ativo ? "bg-white/8 text-white" : "text-white/50"}`}
          >
            <Icone className="size-3.5" /> {rotulo}
          </span>
        ))}
      </aside>
      <div className="flex min-w-0 flex-col gap-4 p-4 lg:pr-14">
        <p className="font-display text-sm font-semibold text-white">Novo projeto</p>
        <div className="flex flex-col items-center gap-1 rounded-xl border border-dashed border-white/15 bg-white/[0.02] px-4 py-5 text-center">
          <CloudUpload className="size-5 text-violeta" />
          <p className="text-[11px] font-medium text-white/85">Envie o vídeo do culto</p>
          <p className="text-[10px] text-white/45">Arraste e solte, ou clique para escolher</p>
        </div>
        <div>
          <p className="mb-2 text-[11px] font-medium text-white/70">Momentos encontrados</p>
          <div className="grid grid-cols-4 gap-2">
            {MOMENTOS.map((item) => (
              <Miniatura key={item.imagem} imagem={item.imagem} selo={item.tempo} proporcao="aspect-[4/3]" />
            ))}
          </div>
        </div>
        <div>
          <p className="mb-2 text-[11px] font-medium text-white/70">Cortes prontos</p>
          <div className="grid grid-cols-4 gap-2">
            {CORTES.map((item) => (
              <Miniatura key={item.imagem} imagem={item.imagem} selo={item.duracao} proporcao="aspect-[3/4]" />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
