import Image from "next/image";

// A forma de onda do desenho: alturas fixas, para o servidor e o navegador desenharem igual
const ONDA = [30, 55, 40, 70, 48, 85, 60, 35, 75, 50, 90, 62, 38, 70, 45, 80, 58, 33, 66, 52, 88, 47, 72, 40, 60, 82, 54, 36, 68, 50];

const QUADROS = ["/marketing/louvor-maos.jpg", "/marketing/cruz-banda.jpg", "/marketing/pregador-palco.jpg", "/marketing/story-cruz.jpg",
  "/marketing/louvor-palco.jpg", "/marketing/pregador-costas.jpg", "/marketing/camera.jpg", "/marketing/biblia.jpg"];

/** O editor do HolyCut na tela de um notebook: a prévia 9:16, a fala ao lado e a linha do tempo. É um desenho, não um print. */
export function EditorNoNotebook() {
  return (
    <div className="relative" aria-hidden>
      <div className="rounded-t-2xl border border-white/10 bg-[#141418] p-2.5 shadow-[0_40px_120px_rgba(0,0,0,.7)]">
        <div className="grid aspect-[16/10] grid-cols-[1fr_1.4fr] grid-rows-[1fr_auto] gap-2.5 overflow-hidden rounded-lg bg-[#0b0b0f] p-2.5">
          <div className="relative overflow-hidden rounded-md">
            <Image src="/marketing/cruz-banda.jpg" alt="" fill sizes="200px" className="object-cover" />
            <span className="absolute inset-x-0 bottom-[18%] text-center font-script text-2xl text-white drop-shadow">Digno</span>
          </div>
          <div className="flex flex-col gap-1.5 rounded-md bg-white/[0.03] p-2.5">
            <span className="h-1.5 w-1/3 rounded-full bg-violeta/70" />
            {[92, 78, 85, 64, 88, 70, 80, 58].map((largura, indice) => (
              <span key={indice} className="h-1.5 rounded-full bg-white/15" style={{ width: `${largura}%` }} />
            ))}
            <span className="mt-1 h-1.5 w-1/4 rounded-full bg-laranja/70" />
            {[86, 74, 90].map((largura, indice) => (
              <span key={indice} className="h-1.5 rounded-full bg-white/15" style={{ width: `${largura}%` }} />
            ))}
          </div>
          <div className="col-span-2 flex flex-col gap-1.5">
            <div className="flex h-7 gap-0.5 overflow-hidden rounded">
              {QUADROS.map((quadro) => (
                <div key={quadro} className="relative flex-1">
                  <Image src={quadro} alt="" fill sizes="60px" className="object-cover" />
                </div>
              ))}
            </div>
            <div className="flex h-6 items-center gap-[3px] rounded bg-white/[0.03] px-1.5">
              {ONDA.map((altura, indice) => (
                <span
                  key={indice}
                  className={`flex-1 rounded-full ${indice > 8 && indice < 20 ? "bg-violeta" : "bg-white/25"}`}
                  style={{ height: `${altura}%` }}
                />
              ))}
            </div>
            <div className="flex h-2 gap-1">
              <span className="w-[22%] rounded-full bg-violeta/80" />
              <span className="w-[30%] rounded-full bg-laranja/80" />
              <span className="w-[18%] rounded-full bg-violeta/50" />
            </div>
          </div>
        </div>
      </div>
      {/* A base do notebook */}
      <div className="mx-auto h-3 w-[108%] -translate-x-[3.7%] rounded-b-2xl bg-gradient-to-b from-[#26262c] to-[#141418]" />
    </div>
  );
}
