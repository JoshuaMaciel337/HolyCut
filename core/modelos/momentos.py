# -----------------------------------------------
# HolyCut — momentos de energia e troca de cena
# A nota visual, quando existe, vem de um assunto fechado: pregador, plateia, luz ou outro.
# -----------------------------------------------

ASSUNTOS = {"pregador", "plateia", "luz", "outro"}


def picos_de_energia(niveis: list[int], por_segundo: int = 100,
                     janela: float = 2.0) -> list[tuple[float, float, float]]:
    """Trechos em que a voz sobe. Cada item é (início, fim, energia de 0 a 1)."""
    if por_segundo <= 0 or len(niveis) < int(por_segundo * janela):
        return []
    tamanho = int(por_segundo * janela)
    medias = []
    for inicio in range(0, len(niveis) - tamanho, tamanho // 2):
        bloco = niveis[inicio:inicio + tamanho]
        medias.append((inicio / por_segundo, sum(bloco) / len(bloco)))
    if not medias:
        return []
    ordenadas = sorted(valor for _, valor in medias)
    limiar = max(ordenadas[int(len(ordenadas) * 0.85)], -22)
    picos = []
    for instante, media in medias:
        if media < limiar:
            continue
        energia = min(max((media - limiar) / 20 + 0.5, 0.0), 1.0)
        if picos and instante - picos[-1][1] <= 1.0:
            anterior = picos[-1]
            picos[-1] = (anterior[0], round(instante + janela, 2), round(max(anterior[2], energia), 2))
        else:
            picos.append((round(instante, 2), round(instante + janela, 2), round(energia, 2)))
    return picos


def montar_momentos(picos: list[tuple[float, float, float]], cenas: list[float],
                    notas: dict[float, dict] | None = None) -> list[dict]:
    """Junta energia, cenas próximas e, se houver, a nota do quadro."""
    notas = notas or {}
    momentos = []
    for inicio, fim, energia in picos:
        nota_visual = next((notas[cena] for cena in notas if inicio - 1 <= cena <= fim + 1), None)
        item = {"inicio": inicio, "fim": fim, "energia": energia, "nota": round(energia * 10, 1)}
        if nota_visual and nota_visual.get("assunto") in ASSUNTOS:
            item["assunto"] = nota_visual["assunto"]
            item["nota"] = round(float(nota_visual.get("nota") or item["nota"]), 1)
        cenas_aqui = [cena for cena in cenas if inicio - 0.5 <= cena <= fim + 0.5]
        if cenas_aqui:
            item["cena"] = round(cenas_aqui[0], 2)
        momentos.append(item)
    return momentos[:40]
