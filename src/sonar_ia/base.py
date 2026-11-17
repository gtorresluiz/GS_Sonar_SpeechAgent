"""Base de conhecimento do Sonar: coleta, limpeza, divisão em trechos e leitura.

Usado pelo notebook 01 (coleta e chunking) e pelos demais componentes
(`carregar_trechos`). Cada trecho tem os metadados:
id, fonte, url, formato, licenca, data_coleta, texto.
"""
from __future__ import annotations

import io
import json
import re
import unicodedata
from datetime import date
from pathlib import Path
from urllib.parse import urljoin

import pdfplumber
import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

RAIZ = Path(__file__).resolve().parents[2]
CAMINHO_TRECHOS = RAIZ / "base" / "trechos.jsonl"
CAMINHO_FONTES = RAIZ / "base" / "fontes.md"
DIR_BRUTOS = RAIZ / "base" / "brutos"

CAMPOS = ("id", "fonte", "url", "formato", "licenca", "data_coleta", "texto")
CABECALHOS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
              "Accept-Language": "pt-BR,pt;q=0.9"}

MIN_PALAVRAS, MAX_PALAVRAS, SOBREPOSICAO = 250, 380, 40

# Como extrair o texto de cada fonte. Sem entrada = HTML genérico (corpo sem menu/rodapé).
CONFIG_FONTES: dict[str, dict] = {
    "lbi": {"modo": "artigos", "artigos": range(46, 53)},
    "lei_caoguia": {"modo": "artigos"},
    "metro_elev": {"modo": "tabela_metro"},
    "dec_caoguia": {"modo": "artigos"},
    "smped_guia": {"seletor": "#main-content", "corte_inicio": "Guia de Serviços - Transporte e Mobilidade",
                   "corte_fim": "collections"},
    "metro_pref": {"seletor": "main"},
    "cptm_acess": {"seletor": "main"},
}

# ---------------------------------------------------------------- fontes.md


def ler_fontes(caminho: Path = CAMINHO_FONTES) -> list[dict]:
    """Lê a tabela de fontes.md (uma fonte por linha)."""
    fontes = []
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        if not linha.startswith("|"):
            continue
        celulas = [c.strip() for c in linha.strip().strip("|").split("|")]
        if len(celulas) != 7 or celulas[0] in ("ID",) or set(celulas[0]) <= {"-"}:
            continue
        fonte = dict(zip(["id", "titulo", "url", "formato", "licenca", "responde_a", "n_trechos"], celulas))
        fonte["descartada"] = fonte["responde_a"].lower().startswith("descartada")
        fontes.append(fonte)
    return fontes


def atualizar_contagem_fontes(contagens: dict[str, int], caminho: Path = CAMINHO_FONTES) -> None:
    """Preenche a coluna "Nº de trechos" de fontes.md (linhas sem contagem ficam como estão)."""
    saida = []
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        if linha.startswith("|"):
            celulas = [c.strip() for c in linha.strip().strip("|").split("|")]
            if len(celulas) == 7 and celulas[0] in contagens:
                celulas[6] = str(contagens[celulas[0]])
                linha = "| " + " | ".join(celulas) + " |"
        saida.append(linha)
    caminho.write_text("\n".join(saida) + "\n", encoding="utf-8")


# ----------------------------------------------------------------- download


def _achar_pdf_de_redirecionamento(html: bytes, url_base: str) -> str | None:
    """Páginas de redirecionamento (ex.: metro_elev) só apontam para um PDF."""
    sopa = BeautifulSoup(_decodificar(html), "html.parser")
    miolo = sopa.select_one("main") or sopa
    if "redirecion" not in miolo.get_text(" ").lower() and len(miolo.get_text(" ").split()) > 80:
        return None
    for a in miolo.find_all("a", href=True):
        if a["href"].lower().split("?")[0].endswith(".pdf"):
            return urljoin(url_base, a["href"])
    achado = re.search(r"""url=([^"'\s>]+\.pdf)""", _decodificar(html), re.I)
    if achado:
        return urljoin(url_base, achado.group(1))
    texto = miolo.get_text(" ")
    achado = re.search(r"(\S+\.pdf)", texto, re.I)
    return urljoin(url_base, achado.group(1)) if achado else None


def _arquivo_manual(id_fonte: str, dir_brutos: Path) -> Path | None:
    for ext in ("html", "pdf"):
        p = dir_brutos / f"{id_fonte}.{ext}"
        if p.exists():
            return p
    return None


def _coleta_anterior(id_fonte: str) -> dict | None:
    """url e data_coleta gravados em trechos.jsonl para a fonte (None se ainda não houver)."""
    if not CAMINHO_TRECHOS.exists():
        return None
    for t in carregar_trechos():
        if t["fonte"] == id_fonte:
            return {"url": t["url"], "data_coleta": t["data_coleta"]}
    return None


def obter_bruto(fonte: dict, dir_brutos: Path = DIR_BRUTOS, forcar: bool = False) -> dict:
    """Usa o original versionado em base/brutos/<id>.<ext>; se não existir (ou `forcar`), baixa e salva.

    Se o download falhar, usa o arquivo salvo à mão. Retorna {caminho, url, formato, data_coleta, aviso};
    `caminho` é None se não houver nada. Reaproveitar o original mantém a base reproduzível: as páginas mudam.
    """
    dir_brutos.mkdir(parents=True, exist_ok=True)
    id_fonte, url = fonte["id"], fonte["url"]
    existente = None if forcar else _arquivo_manual(id_fonte, dir_brutos)
    anterior = _coleta_anterior(id_fonte)
    if existente and anterior:
        return {"caminho": existente, "url": anterior["url"], "formato": existente.suffix[1:].upper(),
                "data_coleta": anterior["data_coleta"], "aviso": None}
    formato = fonte["formato"].lower()
    try:
        r = requests.get(url, headers=CABECALHOS, timeout=60)
        r.raise_for_status()
        conteudo = r.content
        if conteudo[:5] == b"%PDF-":
            formato = "pdf"
        else:
            formato = "html"
            pdf = _achar_pdf_de_redirecionamento(conteudo, url)
            if pdf:
                r2 = requests.get(pdf, headers=CABECALHOS, timeout=90)
                r2.raise_for_status()
                conteudo, url, formato = r2.content, pdf, "pdf"
        caminho = dir_brutos / f"{id_fonte}.{formato}"
        caminho.write_bytes(conteudo)
        return {"caminho": caminho, "url": url, "formato": formato.upper(),
                "data_coleta": date.today().isoformat(), "aviso": None}
    except requests.RequestException as erro:
        manual = _arquivo_manual(id_fonte, dir_brutos)
        if manual is None:
            return {"caminho": None, "url": url, "formato": fonte["formato"], "data_coleta": None,
                    "aviso": f"FALHOU ({erro}) e não há arquivo manual em base/brutos/{id_fonte}.html"}
        data = date.fromtimestamp(manual.stat().st_mtime).isoformat()
        return {"caminho": manual, "url": url, "formato": manual.suffix[1:].upper(), "data_coleta": data,
                "aviso": f"download falhou ({erro}); usou o arquivo salvo manualmente {manual.name}"}


# ------------------------------------------------------------ extração de texto

_RUIDO = re.compile(
    r"^(Z\d_[A-Z0-9]+|\{\}|×|Topo e base|Mensagem de veto|"
    r"\((Redação dada|Incluíd[oa]|Revogad[oa]|Vigência|Vide|Regulamento|Vetado|Produção de efeito|"
    r"Texto compilado|Mensagem de veto)[^)]*\))\s*$",
    re.I,
)
_CABECALHO_LEI = re.compile(r"^(CAP[ÍI]TULO|T[ÍI]TULO|SE[ÇC][ÃA]O|SUBSE[ÇC][ÃA]O|LIVRO|PARTE)\b", re.I)


def _limpar_linhas(texto: str) -> list[str]:
    texto = unicodedata.normalize("NFC", texto).replace("\xa0", " ").replace("​", "").replace("\xad", "")
    linhas = (re.sub(r"\s+", " ", l).strip() for l in texto.splitlines())
    return [l for l in linhas if l and not _RUIDO.match(l)]


def _decodificar(html: bytes) -> str:
    """UTF-8 se for válido; senão Windows-1252 (o Planalto usa ISO-8859-1 e o autodetector erra)."""
    try:
        return html.decode("utf-8")
    except UnicodeDecodeError:
        return html.decode("cp1252", errors="replace")


def html_para_texto(html: bytes, seletor: str | None = None, corte_inicio: str | None = None,
                    corte_fim: str | None = None) -> str:
    """Texto limpo de um HTML: sem menu, rodapé, scripts e trechos riscados (texto revogado)."""
    sopa = BeautifulSoup(_decodificar(html), "html.parser")
    raiz = sopa.select_one(seletor) if seletor else None
    raiz = raiz or sopa.body or sopa
    for tag in raiz(["script", "style", "nav", "footer", "header", "aside", "form", "noscript", "svg",
                     "iframe", "button", "strike", "s", "del"]):
        tag.decompose()
    linhas = _limpar_linhas(raiz.get_text("\n"))
    if corte_inicio and corte_inicio in linhas:
        linhas = linhas[linhas.index(corte_inicio):]
    if corte_fim and corte_fim in linhas:
        linhas = linhas[:linhas.index(corte_fim)]
    return "\n".join(linhas)


def pdf_para_texto(conteudo: bytes) -> str:
    """Texto de um PDF (pypdf), com hifenização de fim de linha desfeita e quebras viradas em espaço."""
    leitor = PdfReader(io.BytesIO(conteudo))
    texto = "\n".join((p.extract_text() or "") for p in leitor.pages)
    texto = unicodedata.normalize("NFC", texto).replace("\xad", "").replace("\xa0", " ")
    texto = re.sub(r"(\w)-\n(?=[a-zà-ú])", r"\1", texto)
    return re.sub(r"\s+", " ", texto).strip()


def extrair_texto(id_fonte: str, caminho: Path) -> str:
    """Escolhe o extrator pelo formato do arquivo, usando CONFIG_FONTES."""
    cfg = CONFIG_FONTES.get(id_fonte, {})
    conteudo = caminho.read_bytes()
    if cfg.get("modo") == "tabela_metro":
        return texto_metro_elev(conteudo)
    if caminho.suffix.lower() == ".pdf":
        return pdf_para_texto(conteudo)
    return html_para_texto(conteudo, cfg.get("seletor"), cfg.get("corte_inicio"), cfg.get("corte_fim"))


# ------------------------------------- tabela de acessos do Metrô (metro_elev)

# Fronteiras em x (pontos PDF) entre as 4 colunas: ESTAÇÃO | LOCAL | ACESSO À ESTAÇÃO | ACESSO À PLATAFORMA
_FRONTEIRAS_X = (124.0, 259.5, 417.0)
_COLUNAS_X = ((0, 124.0), (124.0, 259.5), (259.5, 417.0), (417.0, 700.0))


def _coluna(x_centro: float) -> int:
    return sum(x_centro > f for f in _FRONTEIRAS_X)


def _intervalos(bordas: list[float], coluna: int, margem: float = 1.5) -> list[tuple[float, float]]:
    """Intervalos verticais (células) delimitados pelas bordas horizontais que cruzam a coluna."""
    ys: list[float] = []
    for y in sorted(bordas):
        if not ys or y - ys[-1] > margem:
            ys.append(y)
    return list(zip(ys[:-1], ys[1:]))


_SUPER = {"¹": "1", "²": "2", "³": "3", "⁴": "4"}


def _marcar_notas(palavras: list[dict]) -> list[dict]:
    """Troca o número sobrescrito de nota de rodapé (ex.: "Elevador²") por um marcador ⟦n⟧ colado à palavra."""
    saida: list[dict] = []
    for w in palavras:
        w = dict(w)
        col = _coluna((w["x0"] + w["x1"]) / 2)
        if col >= 2 and w["text"].isdigit() and w["size"] < 10:
            centro = (w["top"] + w["bottom"]) / 2
            for ant in reversed(saida):
                if abs((ant["top"] + ant["bottom"]) / 2 - centro) < 8 and -2 <= w["x0"] - ant["x1"] < 4:
                    ant["text"] += f"⟦{w['text']}⟧"
                    ant["x1"] = w["x1"]
                    break
            else:
                w["text"] = f"⟦{w['text']}⟧"
                saida.append(w)
            continue
        if col >= 2 and w["text"][-1:] in _SUPER:
            w["text"] = w["text"][:-1] + f"⟦{_SUPER[w['text'][-1]]}⟧"
        saida.append(w)
    return saida

def _texto_celula(palavras: list[dict], a: float, b: float, col: int) -> str:
    sel = [w for w in palavras if _coluna((w["x0"] + w["x1"]) / 2) == col and a <= (w["top"] + w["bottom"]) / 2 < b]
    sel.sort(key=lambda w: (round(w["top"] / 3), w["x0"]))
    texto = " ".join(w["text"] for w in sel)
    texto = re.sub(r"(?<=-) ", "", texto)  # "PAULO- AYRTON" -> "PAULO-AYRTON"
    return re.sub(r"\s+(?=⟦)", "", texto).strip()


def _separar_rodape(palavras: list[dict]) -> tuple[list[dict], list[dict]]:
    """Separa as notas de rodapé ("¹ Equipamento sob ...") do resto: linha que começa com marcador
    de nota (¹ ² ³ ou dígito pequeno à esquerda) e as linhas pequenas logo abaixo dela."""
    linhas: dict[int, list[dict]] = {}
    for w in palavras:
        linhas.setdefault(round(w["top"] / 3), []).append(w)
    rodape_ids: set[int] = set()
    ultima = None
    for k in sorted(linhas):
        ws = sorted(linhas[k], key=lambda w: w["x0"])
        topo = min(w["top"] for w in ws)
        primeiro = ws[0]
        inicia = primeiro["x0"] < 40 and primeiro["size"] < 10 and (
            primeiro["text"][:1] in _SUPER or primeiro["text"].isdigit())
        continua = (ultima is not None and topo - ultima <= 16 and primeiro["x0"] < 40
                    and all(w["size"] < 10 for w in ws))
        if inicia or continua:
            rodape_ids.add(k)
            ultima = topo
        else:
            ultima = None
    rodape = [w for k in rodape_ids for w in linhas[k]]
    ids = {id(w) for w in rodape}
    return [w for w in palavras if id(w) not in ids], rodape


def _notas_de_rodape(rodape: list[dict]) -> dict[str, str]:
    """Texto do rodapé -> {"1": "Equipamento sob responsabilidade do ..."}."""
    linhas = sorted(rodape, key=lambda w: (round(w["top"] / 3), w["x0"]))
    texto = " ".join(w["text"] for w in linhas)
    for s, n in _SUPER.items():
        texto = texto.replace(s, n)
    partes = re.split(r"(?:^|\s)(\d)\s+(?=[A-Za-zÀ-ú])", texto)
    return {partes[k]: partes[k + 1].strip() for k in range(1, len(partes) - 1, 2)}

def tabela_metro_elev(conteudo: bytes) -> list[dict]:
    """Lê a tabela do PDF de acessos do Metrô e devolve uma linha por LOCAL de cada estação.

    Colunas do PDF: ESTAÇÃO, LOCAL, ACESSO À ESTAÇÃO, ACESSO À PLATAFORMA. As células mescladas
    (ex.: um único "Elevador" para dois locais) são repetidas em cada local que elas cobrem, e as
    notas de rodapé (¹ ² ³) são anexadas ao texto da célula.
    Cada item: linha, estacao, local, acesso_estacao, acesso_plataforma, pagina, bbox (a, b), bloco (topo, fim)
    — os dois últimos servem para conferir contra o PDF original.
    """
    saida: list[dict] = []
    linha_atual: str | None = None
    estacao_atual: str | None = None
    with pdfplumber.open(io.BytesIO(conteudo)) as pdf:
        for num, pg in enumerate(pdf.pages, start=1):
            palavras = _marcar_notas([w for w in pg.extract_words(extra_attrs=["size"]) if w["top"] < 795])
            # cabeçalhos "LINHA n-COR" e a faixa com os títulos das colunas, que não é conteúdo
            marcas, faixas = [], []
            for w in palavras:
                if w["text"] != "LINHA":
                    continue
                resto = next((p["text"] for p in palavras if abs(p["top"] - w["top"]) < 2 and p["x0"] > w["x0"]), "")
                if re.match(r"\d+-", resto):
                    marcas.append((w["top"], resto))
                    titulos = [p for p in palavras if p["text"] == "ESTAÇÃO" and p["top"] > w["top"]]
                    faixas.append((w["top"] - 3, min((p["bottom"] for p in titulos), default=w["bottom"]) + 4))
            marcas.sort()
            livres = [w for w in palavras if not any(a <= w["top"] <= b for a, b in faixas)]
            horizontais = [e for e in pg.edges if e["orientation"] == "h" and e["x1"] - e["x0"] > 20
                           and e["top"] < 795]

            def bordas(col: int) -> list[float]:
                x0, x1 = _COLUNAS_X[col]
                ys = [e["top"] for e in horizontais if e["x0"] < x1 - 5 and e["x1"] > x0 + 5]
                # página que continua a tabela da anterior não tem borda no topo: cria uma
                topo = min((w["top"] for w in livres), default=None)
                if topo is not None and ys and min(ys) - topo > 8 and not any(t < topo for t, _ in marcas):
                    ys.append(topo - 3)
                return ys

            ints = [_intervalos(bordas(c), c) for c in (1, 2, 3)]
            corpo, rodape = _separar_rodape(livres)
            notas = _notas_de_rodape(rodape)

            def com_notas(texto: str) -> str:
                return re.sub(r"⟦(\d)⟧", lambda m: f" ({notas.get(m.group(1), 'nota ' + m.group(1))})", texto)

            def linha_em(y: float) -> str | None:
                anterior = [nome for top, nome in marcas if top < y]
                return f"Linha {anterior[-1]}" if anterior else linha_atual

            # estações = grupos de linhas consecutivas na coluna 0
            nomes0 = sorted((w for w in corpo if _coluna((w["x0"] + w["x1"]) / 2) == 0), key=lambda w: w["top"])
            grupos: list[list[dict]] = []
            for w in nomes0:
                if grupos and w["top"] - grupos[-1][-1]["top"] <= 22:
                    grupos[-1].append(w)
                else:
                    grupos.append([w])
            estacoes = [(g[0]["top"], _texto_celula(g, 0, 1e9, 0)) for g in grupos]
            for (a, b) in ints[0]:
                centro = (a + b) / 2
                local = _texto_celula(corpo, a, b, 1)
                if not local:
                    continue
                antes = [nome for top, nome in estacoes if top - 6 <= centro]
                if antes:
                    estacao_atual = antes[-1]
                linha_atual = linha_em(centro)
                if linha_atual is None or estacao_atual is None:
                    continue
                valores = []
                for col in (1, 2):
                    partes = []
                    for (c, d) in ints[col]:
                        if min(b, d) - max(a, c) > 3:
                            t = re.sub(r"\s*/\s*", " / ", com_notas(_texto_celula(corpo, c, d, col + 1)))
                            if t and t not in partes:
                                partes.append(t)
                    valores.append(" / ".join(partes))
                saida.append({"linha": linha_atual, "estacao": estacao_atual, "local": local,
                              "acesso_estacao": valores[0], "acesso_plataforma": valores[1],
                              "pagina": num, "bbox": (a, b)})
    return saida

def _nome_estacao(nome: str) -> str:
    """CAIXA ALTA do PDF -> 'Title Case' com preposições em minúscula; siglas curtas ficam em caixa alta."""
    pequenas = {"de", "da", "do", "das", "dos", "e"}
    palavras = []
    for i, p in enumerate(nome.split()):
        partes = []
        for k, parte in enumerate(p.split("-")):
            baixa = parte.lower()
            if baixa in pequenas and (i > 0 or k > 0):
                partes.append(baixa)
            elif parte in _SIGLAS:
                partes.append(parte)
            else:
                partes.append(baixa.capitalize())
        palavras.append("-".join(partes))
    return " ".join(palavras)


_SIGLAS = {"USP", "AACD", "SESC", "FEI", "CPTM", "ABC", "UNIFESP", "FMU", "SENAC", "II", "III", "MASP"}


def _nome_linha(linha: str) -> str:
    """"Linha 3-VERMELHA" -> "Linha 3-Vermelha"."""
    return re.sub(r"(\d+)-(\w+)", lambda m: f"{m.group(1)}-{m.group(2).capitalize()}", linha)


def frase_metro_elev(e: dict) -> str:
    """Frase de uma linha da tabela, usando exatamente as colunas do PDF."""
    partes = []
    if e["acesso_estacao"]:
        partes.append(f"acesso à estação: {e['acesso_estacao']}")
    if e["acesso_plataforma"]:
        partes.append(f"acesso à plataforma: {e['acesso_plataforma']}")
    return (f"Estação {_nome_estacao(e['estacao'])} ({_nome_linha(e['linha'])}), local {e['local']}: "
            f"{'; '.join(partes) or 'sem informação de acesso'}.")


def texto_metro_elev(conteudo: bytes) -> str:
    """Texto do PDF do Metrô como uma frase por local, em blocos '## Linha ...' (um bloco por linha)."""
    por_linha: dict[str, list[str]] = {}
    for e in tabela_metro_elev(conteudo):
        por_linha.setdefault(_nome_linha(e["linha"]), []).append(frase_metro_elev(e))
    return "\n".join(f"## {linha}\n" + "\n".join(frases) for linha, frases in por_linha.items())


def original_da_entrada(conteudo: bytes, e: dict) -> str:
    """Texto cru da faixa da tabela original (todas as colunas) para conferir uma frase gerada."""
    with pdfplumber.open(io.BytesIO(conteudo)) as pdf:
        pg = pdf.pages[e["pagina"] - 1]
        a, b = e["bbox"]
        faixa = pg.crop((0, max(a - 1, 0), pg.width, min(b + 1, pg.height)))
        return re.sub(r"\s*\n\s*", " | ", faixa.extract_text() or "")

# -------------------------------------------------------------- chunking

_ABREV = {"art", "arts", "nº", "n", "no", "dr", "dra", "av", "sr", "sra", "prof", "ex", "inc", "par", "cf",
          "etc", "pág", "tel", "ltda", "sp", "ss", "al", "vol", "fig", "min", "máx"}


def dividir_sentencas(linha: str) -> list[str]:
    """Divide uma linha em frases sem cortar abreviações (Art., nº, Av. ...)."""
    partes, ini = [], 0
    for m in re.finditer(r"[.!?…]+[\"”')\]]*\s+", linha):
        antes = re.findall(r"[\wº°ª§]+", linha[ini:m.start()])
        token = antes[-1].lower() if antes else ""
        proximo = linha[m.end():m.end() + 1]
        if not proximo or proximo.islower() or token in _ABREV or len(token) == 1:
            continue
        partes.append(linha[ini:m.end()].strip())
        ini = m.end()
    resto = linha[ini:].strip()
    if resto:
        partes.append(resto)
    return partes


def _unidades(texto: str, maximo: int) -> list[tuple[str, str]]:
    """Lista de (frase, separador antes dela). Frases maiores que `maximo` são quebradas por palavras."""
    unidades: list[tuple[str, str]] = []
    for linha in texto.splitlines():
        for i, frase in enumerate(dividir_sentencas(linha.strip())):
            palavras = frase.split()
            for k in range(0, len(palavras), maximo):
                pedaco = " ".join(palavras[k:k + maximo])
                sep = "\n" if (i == 0 and k == 0) else " "
                unidades.append((pedaco, sep))
    return unidades


def _montar(unidades: list[tuple[str, str]], idx: list[int]) -> str:
    return "".join((unidades[j][1] if n else "") + unidades[j][0] for n, j in enumerate(idx)).strip()


def dividir_em_trechos(texto: str, minimo: int = MIN_PALAVRAS, maximo: int = MAX_PALAVRAS,
                       sobreposicao: int = SOBREPOSICAO) -> list[str]:
    """Janelas de `minimo` a `maximo` palavras, cortadas em fim de frase, com ~`sobreposicao` palavras
    repetidas entre trechos vizinhos (frases inteiras do final do trecho anterior)."""
    un = _unidades(texto, maximo)
    pal = [len(u[0].split()) for u in un]
    n = len(un)
    janelas: list[list[int]] = []
    i = 0
    while i < n:
        atual, total, j = [], 0, i
        while j < n and total + pal[j] <= maximo:
            atual.append(j)
            total += pal[j]
            j += 1
        janelas.append(atual)
        if j >= n:
            break
        k, acumulado = j, 0
        while k > atual[0] + 1 and acumulado < sobreposicao and acumulado + pal[k - 1] <= 3 * sobreposicao:
            k -= 1
            acumulado += pal[k]
        i = k
    # cauda curta: tenta anexar ao trecho anterior se couber
    if len(janelas) > 1 and sum(pal[j] for j in janelas[-1]) < minimo:
        novos = [j for j in janelas[-1] if j > janelas[-2][-1]]
        if sum(pal[j] for j in janelas[-2] + novos) <= maximo:
            janelas[-2] += novos
            janelas.pop()
    return [_montar(un, w) for w in janelas if w]


def dividir_por_artigo(texto: str, artigos: range | None = None, maximo: int = MAX_PALAVRAS) -> list[str]:
    """Um artigo = um trecho. Artigos com mais de `maximo` palavras viram vários (com sobreposição).

    `artigos` filtra pelos números desejados (ex.: range(46, 53) para a LBI).
    """
    linhas = texto.splitlines()
    inicios = [(i, int(m.group(1))) for i, l in enumerate(linhas)
               if (m := re.match(r"^Art\.\s*(\d+)(?:-[A-Z])?(?!\d)", l))]
    vistos: set[int] = set()
    trechos: list[str] = []
    for pos, (i, numero) in enumerate(inicios):
        if numero in vistos or (artigos is not None and numero not in artigos):
            continue
        vistos.add(numero)
        fim = inicios[pos + 1][0] if pos + 1 < len(inicios) else len(linhas)
        corpo = []
        for l in linhas[i:fim]:
            if _CABECALHO_LEI.match(l) or re.match(r"^Brasília,", l):
                break  # cabeçalho do próximo capítulo ou assinatura da lei
            corpo.append(l)
        artigo = "\n".join(corpo)
        if len(artigo.split()) < 8:
            continue  # artigo vetado/revogado: só o número, sem texto
        if len(artigo.split()) > maximo:
            trechos += dividir_em_trechos(artigo, maximo=maximo)
        else:
            trechos.append(artigo)
    return trechos


# --------------------------------------------------------- montagem e leitura


def gerar_trechos(fonte: dict, texto: str, url: str, formato: str, data_coleta: str) -> list[dict]:
    """Aplica o chunking certo à fonte e devolve os trechos com metadados."""
    cfg = CONFIG_FONTES.get(fonte["id"], {})
    if cfg.get("modo") == "artigos":
        textos = dividir_por_artigo(texto, cfg.get("artigos"))
    elif cfg.get("modo") == "tabela_metro":
        textos = []
        for bloco in re.split(r"(?m)^## .*\n", texto):
            if bloco.strip():
                textos += dividir_em_trechos(bloco.strip())
    else:
        textos = dividir_em_trechos(texto)
    return [{"id": f"{fonte['id']}_{n:03d}", "fonte": fonte["id"], "url": url, "formato": formato,
             "licenca": fonte["licenca"], "data_coleta": data_coleta, "texto": t}
            for n, t in enumerate(textos, start=1)]


def salvar_trechos(trechos: list[dict], caminho: Path = CAMINHO_TRECHOS) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8", newline="\n") as f:
        for t in trechos:
            f.write(json.dumps({c: t[c] for c in CAMPOS}, ensure_ascii=False) + "\n")


def carregar_trechos(caminho: Path = CAMINHO_TRECHOS) -> list[dict]:
    """Lê base/trechos.jsonl e confere que todo trecho tem os 7 metadados."""
    trechos = []
    with Path(caminho).open(encoding="utf-8") as f:
        for n, linha in enumerate(f, start=1):
            if not linha.strip():
                continue
            t = json.loads(linha)
            faltando = [c for c in CAMPOS if not t.get(c)]
            if faltando:
                raise ValueError(f"linha {n} de {caminho}: campos ausentes {faltando}")
            trechos.append(t)
    return trechos
