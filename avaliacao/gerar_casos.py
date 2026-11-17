"""Gera avaliacao/casos_teste.jsonl. Rode da raiz do repositório: python avaliacao/gerar_casos.py

trechos_esperados NÃO são digitados: saem de âncoras (os trechos que contêm o texto), então continuam
certos se o chunking mudar. Nas rotas o gabarito é verificado à mão e a ferramenta GTFS só serve de evidência."""
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
from sonar_ia.base import carregar_trechos  # noqa: E402
from sonar_ia.gtfs import GTFS  # noqa: E402

T = carregar_trechos()
NAO_CONSTA = "Não consta na base de conhecimento."


def achar(ancoras: list[str]) -> list[str]:
    ids = []
    for a in ancoras:
        achados = [t["id"] for t in T if re.sub(r"\s+", " ", a) in re.sub(r"\s+", " ", t["texto"])]
        assert achados, f"âncora sem trecho: {a!r}"
        ids += [i for i in achados if i not in ids]
    return ids


# (pergunta, resposta_esperada, palavras_chave, âncoras)
# palavras_chave: cada item é um termo OBRIGATÓRIO; "a|b" = qualquer uma das variantes (sem acento/caixa)
TEXTO = [
    # --- 8 elevador/rampa no Metrô (metro_elev)
    ("oi, a estaçao tucuruvi tem elevador?",
     "Sim. Na Estação Tucuruvi (Linha 1-Azul) o acesso à estação, na Av. Dr. Antônio Maria de Laet, é por rampa e o acesso à plataforma é por elevador.",
     ["elevador"], ["Estação Tucuruvi (Linha 1-Azul)"]),
    ("a estação paraíso tem elevador nas duas linhas, a azul e a verde?",
     "Sim. Na Estação Paraíso, tanto na Linha 1-Azul quanto na 2-Verde, os dois locais (Rua Vergueiro, perto da Catedral Ortodoxa, e Viaduto Santa Generosa, lado da praça) têm elevador para a estação e para a plataforma.",
     ["elevador", "azul|linha 1", "verde|linha 2"],
     ["Estação Paraíso (Linha 1-Azul)", "Estação Paraíso (Linha 2-Verde)"]),
    ("como eu entro na estaçao ana rosa pelo terminal urbano, tem elevador?",
     "Na Estação Ana Rosa, local Terminal Urbano, o acesso à estação não é por elevador: é por plataforma de elevação inclinada (nas Linhas 1-Azul e 2-Verde). O acesso à plataforma é por elevador.",
     ["plataforma de elevação|elevacao inclinada|elevação inclinada"],
     ["Estação Ana Rosa (Linha 1-Azul)", "Estação Ana Rosa (Linha 2-Verde)"]),
    ("na estação armenia, pelo terminal urbano sul, é elevador ou rampa?",
     "Na Estação Armênia, local Terminal Urbano Sul, o acesso à estação é em nível (sem elevador nem rampa); o acesso à plataforma é por elevador.",
     ["nível|nivel"], ["Estação Armênia (Linha 1-Azul)"]),
    ("o elevador do terminal da EMTU lá na jabaquara é do metrô?",
     "Na Estação Jabaquara, o acesso pelo Terminal EMTU é por elevador, e o equipamento é de responsabilidade da EMTU (não do Metrô).",
     ["emtu"], ["Estação Jabaquara (Linha 1-Azul), local Terminal EMTU"]),
    ("pra ir da estação consolação pra linha 4 amarela, tem rampa ou escada rolante?",
     "Na Estação Consolação (Linha 2-Verde), a conexão com a Linha 4-Amarela é por rampa ou esteira rolante, tanto para a estação quanto para a plataforma.",
     ["rampa", "esteira|escada rolante"],
     ["Estação Consolação (Linha 2-Verde), local Conexão Linha 4-Amarela"]),
    ("a estação brigadeiro tem elevador pra quem sai na paulista?",
     "Sim. Na Estação Brigadeiro (Linha 2-Verde), local Av. Paulista, lado ímpar, entre as ruas Maria Figueiredo e Teixeira da Silva, o acesso à estação e à plataforma é por elevador.",
     ["elevador"], ["Estação Brigadeiro (Linha 2-Verde)"]),
    ("na estação sapopemba da linha prata, o acesso é por rampa ou elevador?",
     "Na Estação Sapopemba (Linha 15-Prata), local Av. Sapopemba, o acesso à estação é por rampa ou elevador, e o acesso à plataforma é por elevador.",
     ["rampa", "elevador"],
     ["Estação Sapopemba (Linha 15-Prata), local Av. Sapopemba, lado par",
      "Estação Sapopemba (Linha 15-Prata), local Av. Sapopemba, lado impar"]),
    # --- 6 cão-guia
    ("posso entrar no onibus com meu cao guia?",
     "Sim. A pessoa com deficiência visual acompanhada de cão-guia tem o direito de ingressar e permanecer com o animal em todos os meios de transporte.",
     ["sim|pode|direito"],
     ["É assegurado à pessoa com deficiência visual acompanhada de cão-guia o direito de ingressar e de permanecer com o animal em todos os meios de transporte",
      "A pessoa com deficiência visual usuária de cão-guia tem o direito de ingressar e permanecer com o animal em todos os locais públicos ou privados de uso coletivo",
      "A Lei Federal nº 11.126/2005 garante às pessoas com deficiência visual o direito de ingressar e de permanecer com o cão-guia em todos os meios de transporte",
      "Pessoas com deficiência visual acompanhadas de cão-guia A lei garante que esse usuário embarque e viaje nos veículos de transporte coletivo normalmente"]),
    ("o cachorro guia precisa usar focinheira no transporte?",
     "Não. É vedada a exigência de focinheira nos cães-guia como condição para entrar e permanecer nos locais de uso coletivo.",
     ["focinheira", "não|nao|vedad|proib"],
     ["É vedada a exigência do uso de focinheira"]),
    ("o motorista ou o metrô pode cobrar a mais por causa do meu cão-guia?",
     "Não. É vedada a cobrança de valores, tarifas ou acréscimos ligados à presença do cão-guia; quem cobrar sofre as sanções do decreto.",
     ["não|nao|vedad|proib"],
     ["É vedada a cobrança de valores, tarifas ou acréscimos vinculados"]),
    ("quais documentos o cao guia tem que ter pra andar de transporte?",
     "Carteira de identificação e plaqueta de identificação (do centro de treinamento ou instrutor), carteira de vacinação atualizada (vacina múltipla e antirrábica) e equipamento com coleira, guia e arreio com alça.",
     ["vacina", "identifica"],
     ["II - carteira de vacinação", "É importante lembrar que o cão-guia deve estar sempre acompanhado de"]),
    ("qual a multa se o motorista nao deixar meu cão guia entrar?",
     "Multa de R$ 1.000,00 a R$ 30.000,00 para quem impedir ou dificultar o ingresso e a permanência com o cão-guia; na reincidência, interdição por trinta dias e multa de até R$ 50.000,00.",
     ["1.000|mil reais"],
     ["máximo de R$ 30.000,00 (trinta mil reais)",
      "Negar o acesso do cão-guia aos espaços pode render ao infrator multas"]),
    ("onde meu cachorro guia fica sentado dentro do onibus ou do metrô?",
     "No transporte público a pessoa com deficiência visual acompanhada de cão-guia ocupa, preferencialmente, o assento mais amplo, com maior espaço livre à sua volta ou próximo de uma passagem.",
     ["assento"],
     ["ocupará, preferencialmente, o assento mais amplo"]),
    # --- 5 conduta do motorista e do ônibus (sptrans_manual)
    ("se o motorista ver uma pessoa cega no ponto, ele é obrigado a parar?",
     "Sim. O manual da SPTrans orienta que, sempre que identificar uma pessoa cega no ponto, o motorista pare e informe qual é a linha que está operando.",
     ["pare|parar|parada", "linha"],
     ["Sempre que identificar uma pessoa cega no ponto, pare e informe qual a linha que está operando"]),
    ("como o motorista tem que me avisar a hora de descer?",
     "Quem está sem acompanhante deve ficar na frente do ônibus, no banco reservado (ou atrás dele), para ter contato com o motorista, que avisa gentilmente quando chegar o ponto de desembarque. O motorista também deve perguntar onde a pessoa vai descer.",
     ["avis"],
     ["Dessa forma, o operador poderá, gentilmente, avisar quando chegar o ponto de desembarque",
      "pergunte onde ela vai descer para facilitar o desembarque"]),
    ("por que o motorista só pode parar nos pontos quando tem passageiro cego?",
     "Porque a pessoa com deficiência visual é treinada para ter o ponto como referência e pode se perder se o ônibus parar fora dele.",
     ["referência|referencia|perder"],
     ["A pessoa com deficiência visual é treinada para ter o ponto como referência"]),
    ("como o motorista deve ajudar uma pessoa cega que ta com dificuldade de entrar no ônibus?",
     "Aproximar a mão da pessoa do balaústre para ajudar a subir ou descer, colocar a mão dela no encosto do banco para que sente sozinha e perguntar onde vai descer.",
     ["balaústre|balaustre|encosto"],
     ["aproxime a mão dela do balaústre"]),
    ("quando eu for guiado por alguem, em que braço devo segurar?",
     "O acompanhante deve oferecer o braço oposto ao da bengala para a pessoa com deficiência visual segurar, o que dá um trajeto menos acidentado.",
     ["braço|braco", "oposto|contrário|contrario|outro braço"],
     ["Acompanhe a pessoa com deficiência visual oferecendo o braço oposto à bengala"]),
    # --- 4 Bilhete Único Especial e Atende+
    ("como eu faço pra pedir o bilhete unico especial de pessoa com deficiência?",
     "Pelo site da SPTrans: fazer o cadastro e gerar o relatório médico, que o médico de sua escolha preenche e assina; depois ir a um Posto de Atendimento da SPTrans com os documentos (relatório médico, comprovante de endereço com CEP, documento com foto, laudo se necessário).",
     ["site", "médico|medico|posto"],
     ["Para fazer a solicitação do “Bilhete Único Especial - Pessoa com Deficiência”",
      "Informamos que o Bilhete Único Especial da Pessoa com Deficiência deverá ser solicitado"]),
    ("o que fazem quando eu entrego os documentos do bilhete especial no posto?",
     "No ato da entrega o solicitante assina o termo de compromisso e ciência, a foto é capturada para a impressão do bilhete e as dúvidas podem ser tiradas.",
     ["foto", "termo"],
     ["No ato da entrega, o solicitante deverá assinar o termo de compromisso"]),
    ("quem pode usar o atende mais, aquele transporte porta a porta?",
     "O Atende+ é exclusivo para pessoas com surdocegueira, com deficiência física e mobilidade reduzida com comprometimento severo, e pessoas com Transtorno do Espectro Autista (TEA).",
     ["surdocegueira"],
     ["O Serviço Atende+ destina-se, exclusivamente, às pessoas com surdocegueira"]),
    ("quais documentos eu preciso levar pra me cadastrar no atende+?",
     "CPF (original e cópia), RG ou certidão de nascimento (original e cópia) e comprovante de endereço com CEP (original e cópia), além da Ficha de Avaliação Médica preenchida pelo médico.",
     ["cpf", "comprovante"],
     ["Os documentos necessários são: CPF (original e cópia)"]),
    # --- 4 direitos no transporte (lbi)
    ("o taxista pode cobrar mais caro de uma pessoa com deficiência?",
     "Não. A Lei Brasileira de Inclusão proíbe a cobrança diferenciada de tarifas ou de valores adicionais pelo serviço de táxi prestado à pessoa com deficiência.",
     ["não|nao|proib"],
     ["É proibida a cobrança diferenciada de tarifas ou de valores adicionais pelo serviço de táxi"]),
    ("quantos por cento dos taxis tem que ser acessíveis?",
     "As frotas de empresas de táxi devem reservar 10% de seus veículos acessíveis à pessoa com deficiência.",
     ["10%|10 %|dez por cento"],
     ["As frotas de empresas de táxi devem reservar 10%"]),
    ("tenho prioridade pra embarcar e desembarcar no transporte coletivo?",
     "Sim. A LBI assegura à pessoa com deficiência prioridade e segurança nos procedimentos de embarque e desembarque nos veículos de transporte coletivo, de acordo com as normas técnicas.",
     ["prioridade"],
     ["São asseguradas à pessoa com deficiência prioridade e segurança nos procedimentos de embarque e de desembarque"]),
    ("os ônibus e terminais precisam avisar todos os pontos do trajeto de um jeito acessível?",
     "Sim. Os veículos e as estruturas de transporte devem dispor de sistema de comunicação acessível que disponibilize informações sobre todos os pontos do itinerário.",
     ["itinerário|itinerario|trajeto|pontos"],
     ["sistema de comunicação acessível que disponibilize informações sobre todos os pontos do itinerário"]),
    # --- 3 Metrô e CPTM
    ("na estaçao belem do metrô tem embarque preferencial? que horas?",
     "Sim. Na Estação Belém (Linha 3-Vermelha) o embarque preferencial é das 7h às 9h, no sentido Palmeiras-Barra Funda.",
     ["7h|7 h|sete", "9h|9 h|nove"],
     ["BELÉM Das 7h às 9h Palmeiras-Barra Funda"]),
    ("quantas estações da cptm são acessiveis?",
     "Das 41 estações da CPTM, 35 já possuem condições de acesso às pessoas com deficiência ou restrição de mobilidade.",
     ["35"],
     ["Das 41 estações, 35 já possuem condições de acesso"]),
    ("uma pessoa cega pode usar o táxi acessivel da cptm?",
     "Não. O Táxi Acessível da CPTM é um serviço gratuito e exclusivo para pessoas com deficiência físico-motora.",
     ["motora", "não|nao|exclusiv"],
     ["É um serviço gratuito e exclusivo para pessoas com deficiência físico-motora"]),
]

# --- rota. Gabarito verificado à mão (a ferramenta NÃO é a fonte, para não ficar circular):
# (pergunta, origem, destino, esperadas, incorretas, palavras_chave, resposta)
# esperadas=None -> usa o que o GTFS devolve (casos já conferidos); incorretas = falsos positivos da ferramenta.
SEM_LINHA = ["não há|nao ha|nenhuma|não encontr|nao encontr|sem linha direta"]
ROTAS = [
    ("qual linha do metrô vai do tucuruvi ate o jabaquara?", "Tucuruvi", "Jabaquara", None, [], ["L1|linha 1|azul"], None),
    ("como chego da vila madalena ate o paraiso de metro?", "Vila Madalena", "Paraíso", None, [], ["L2|linha 2|verde"], None),
    ("tem trem ou metrô direto do corinthians itaquera pra palmeiras barra funda?", "Corinthians-Itaquera",
     "Palmeiras-Barra Funda", None, [], ["L3|linha 3|vermelha|L11|linha 11|coral"], None),
    ("o que vai do brás ate o tatuapé?", "Brás", "Tatuapé", ["CPTM L11", "CPTM L12", "METRÔ L3"],
     ["2582-10", "2769-10"], ["L3|L11|L12|linha 3|linha 11|linha 12"], None),
    ("qual trem da cptm vai do brás pra luz?", "Brás", "Luz", ["CPTM L11", "CPTM L10"],
     ["5013-31", "546L-10", "5013-10", "4491-10", "5129-10", "N634-11"],
     ["L10|L11|linha 10|linha 11|turquesa|coral"], None),
    ("tem trem direto da lapa pro terminal pirituba?", "Terminal Lapa", "Terminal Pirituba",
     ["CPTM L07", "N103-11", "8100-10", "8200-10", "8002-10"], ["9188-42", "8010-10"],
     ["L07|L7|linha 7|rubi|N103|8100|8200|8002"], None),  # 847P-10 fica fora das duas listas (duvidosa)
    ("tem alguma linha de trem do pinheiros pro santo amaro?", "Pinheiros", "Santo Amaro",
     ["CPTM L09", "637P-10", "709M-10"],
     ["776M-10", "N633-11", "637J-10", "637G-10", "856R-10", "637G-51", "N603-11"],
     ["L09|L9|linha 9|esmeralda|637P|709M"], None),
    # gabarito corrigido após a C1b: stop_times confirma 476A-10 de "Terminal Sacoma" a "Terminal Sto. Amaro, 1"
    # (a sequência de paradas é impressa como evidência); as outras duas continuam falsos positivos de rua.
    ("qual onibus vai do terminal sacomã ate o terminal santo amaro?", "Terminal Sacomã", "Terminal Santo Amaro",
     ["476A-10"], ["477A-10", "477P-10"], None, None),
    ("preciso ir do terminal capelinha pro terminal santo amaro, qual onibus pego?", "Terminal Capelinha",
     "Terminal Santo Amaro", None, [], None, None),
    ("que onibus vai do terminal bandeira ate o terminal princesa isabel?", "Terminal Bandeira",
     "Terminal Princesa Isabel", [], "TODAS", SEM_LINHA, "Não há linha direta confirmada."),
    ("qual onibus liga o terminal vila nova cachoeirinha ao terminal lapa?", "Terminal Vila Nova Cachoeirinha",
     "Terminal Lapa", None, [], None, None),
    ("tem onibus direto do terminal santo amaro pro terminal lapa?", "Terminal Santo Amaro", "Terminal Lapa",
     [], "TODAS", SEM_LINHA, "Não há linha direta confirmada."),
    ("tem alguma linha direta do tucuruvi ate o corinthians itaquera?", "Tucuruvi", "Corinthians-Itaquera",
     [], [], SEM_LINHA, "Sem linha direta."),
    ("tem trem direto da luz ate osasco?", "Luz", "Osasco", [], [], SEM_LINHA, "Sem linha direta."),
    ("qual metro vai da estação atlantida ate a luz?", "Estação Atlântida", "Luz", [], [], SEM_LINHA,
     "Local não encontrado."),
    # novos: route_long_name "Term. A - Term. B", embarque e desembarque nos próprios terminais
    ("qual onibus vai do terminal sacoma ate o terminal mercado?", "Terminal Sacomã", "Terminal Mercado",
     ["5105-10"], [], ["5105"], None),
    ("tem onibus direto do terminal cidade tiradentes pro terminal dom pedro?", "Terminal Cidade Tiradentes",
     "Terminal Parque Dom Pedro II", ["4313-10", "4210-10"], [], ["4313|4210"], None),
    ("que linha vai do terminal grajau pro terminal agua espraiada?", "Terminal Grajaú", "Terminal Água Espraiada",
     ["607M-10"], [], ["607M"], None),
]
# --- 15 nao_consta: (pergunta, termos que NÃO podem aparecer na base)
NAO = [
    ("a estação faria lima da linha 4 amarela tem elevador?", ["Faria Lima"]),
    ("tem elevador na estação adolfo pinheiro da linha 5 lilás?", ["Adolfo Pinheiro"]),
    ("a estaçao carapicuiba da linha 8 diamante é acessivel pra cego?", ["Carapicu"]),
    ("o que tem de acessibilidade na estação interlagos da linha 9?", ["Interlagos"]),
    ("o elevador da estaçao sé ta funcionando agora?", ["funcionando", "agora"]),
    ("hoje tem elevador quebrado na estação tatuapé?", ["quebrad", "hoje"]),
    ("quanto custa uma corrida de uber do terminal santo amaro até a paulista?", ["corrida", r"\buber\b", r"\b99 ?(pop|táxi|taxi)"]),
    ("que horas começa o show hoje no allianz parque?", ["Allianz", "show"]),
    ("a estação carioca do metrô do rio de janeiro tem elevador?", ["Carioca"]),
    ("quanto custa a passagem de onibus em são paulo?", [r"R\$ ?\d+,\d\d.*passagem", "custa"]),
    ("que horas passa o proximo onibus 477P no terminal santo amaro?", ["próximo ônibus", "previsão"]),
    ("como faço pra conseguir um cão guia, quanto custa?", ["custa", "adoção", "adotar"]),
    ("o metrô tem piso tatil pra me guiar da catraca até a plataforma?", ["piso tátil", "pisos táteis", "piso podotátil"]),
    ("tem embarque preferencial na estação tucuruvi?", ["TUCURUVI Das"]),
    ("qual o telefone da central de atendimento do metrô?", ["0800", "Central de Atendimento"]),
]


def evidencia_sequencia(g: GTFS, linha: str, origem: str, destino: str) -> None:
    """Imprime a sequência de paradas (stop_times) de uma viagem da linha entre os dois nomes de parada."""
    nomes = g.stops.set_index("stop_id")["stop_name"]
    rotas = g.routes[g.routes.route_short_name == linha].route_id
    for trip in g.trips[g.trips.route_id.isin(rotas)].trip_id:
        st = g.stop_times[g.stop_times.trip_id == trip].sort_values("stop_sequence")
        seq = [(int(s.stop_sequence), nomes.get(s.stop_id, s.stop_id)) for s in st.itertuples()]
        pos_o = [i for i, (_, n) in enumerate(seq) if n == origem]
        pos_d = [i for i, (_, n) in enumerate(seq) if n == destino]
        if pos_o and pos_d and pos_o[0] < pos_d[0]:
            o, d = pos_o[0], pos_d[0]
            print(f"\nEVIDÊNCIA stop_times: linha {linha}, viagem {trip} ({len(seq)} paradas)")
            print(f"  embarque  : seq {seq[o][0]:>3} {seq[o][1]}")
            for n, nome in seq[o + 1:d]:
                print(f"              seq {n:>3} {nome}")
            print(f"  desembarque: seq {seq[d][0]:>3} {seq[d][1]}   ({d - o} paradas depois do embarque)")
            return
    print(f"\nEVIDÊNCIA: nenhuma viagem de {linha} com {origem!r} antes de {destino!r}")


def main() -> None:
    g = GTFS(RAIZ / "base" / "gtfs")
    anterior = RAIZ / "avaliacao" / "casos_teste.jsonl"
    antes = {}
    if anterior.exists():
        antes = {c["id"]: c["trechos_esperados"] for c in map(json.loads, anterior.read_text(encoding="utf-8").splitlines())}
    casos = []
    for i, (p, r, kw, anc) in enumerate(TEXTO, 1):
        casos.append({"id": f"texto_{i:02d}", "pergunta": p, "tipo": "texto", "resposta_esperada": r,
                      "palavras_chave": kw, "trechos_esperados": achar(anc), "linhas_esperadas": [],
                      "linhas_incorretas": []})
    print("\nEVIDÊNCIA DAS ROTAS (linha | route_long_name | embarque -> desembarque)")
    for i, (p, o, d, esp, inc, kw, resp) in enumerate(ROTAS, 1):
        res = g.linhas_diretas(o, d)
        devolvidas = [l["linha"] for l in res["linhas"]]
        if esp is None:
            esp = devolvidas  # caso conferido: a ferramenta acertou tudo
        if inc == "TODAS":
            inc = list(devolvidas)
        # a ferramenta não pode ter mudado: tudo que ela devolve está classificado (ou é a "duvidosa" 847P-10)
        fora = [x for x in devolvidas if x not in esp and x not in inc and x != "847P-10"]
        assert not fora, f"rota_{i:02d}: linhas devolvidas sem classificação: {fora}"
        assert all(x in devolvidas for x in esp), f"rota_{i:02d}: esperada que a ferramenta não devolve"
        print(f"\nrota_{i:02d}  {o} -> {d}   [{res.get('motivo', 'ok')}]")
        for l in res["linhas"]:
            marca = "ESPERADA " if l["linha"] in esp else "INCORRETA" if l["linha"] in inc else "duvidosa "
            print(f"   {marca} {l['linha']:<9} | {l['nome']:<42} | {l['parada_embarque']} -> {l['parada_desembarque']}")
        if kw is None:
            kw = ["|".join(sorted({x.split("-")[0] for x in esp}))]
        if resp is None:
            resp = ("Linhas diretas (GTFS SPTrans): "
                    + "; ".join(f"{l['linha']} ({l['tipo']}, {l['nome']})" for l in res["linhas"] if l["linha"] in esp))
        casos.append({"id": f"rota_{i:02d}", "pergunta": p, "tipo": "rota", "resposta_esperada": resp,
                      "palavras_chave": kw, "trechos_esperados": [], "linhas_esperadas": esp,
                      "linhas_incorretas": inc, "origem": o, "destino": d})
    for i, (p, ausentes) in enumerate(NAO, 1):
        for a in ausentes:
            quem = [t["id"] for t in T if re.search(a, t["texto"].replace("\n", " "), re.I)]
            assert not quem, f"nao_consta {i}: {a!r} aparece em {quem}"
        casos.append({"id": f"nao_consta_{i:02d}", "pergunta": p, "tipo": "nao_consta",
                      "resposta_esperada": NAO_CONSTA, "palavras_chave": [], "trechos_esperados": [],
                      "linhas_esperadas": [], "linhas_incorretas": []})
    saida = RAIZ / "avaliacao" / "casos_teste.jsonl"
    saida.parent.mkdir(exist_ok=True)
    with saida.open("w", encoding="utf-8", newline="\n") as f:
        for c in casos:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    evidencia_sequencia(g, "476A-10", "Terminal Sacoma", "Terminal Sto. Amaro, 1")
    print("\n", len(casos), "casos ->", saida)
    print("\nTRECHOS ESPERADOS DOS CASOS DE ELEVADOR (antes -> depois)")
    for c in casos:
        ant = antes.get(c["id"], [])
        if c["tipo"] == "texto" and any(i.startswith("metro_elev") for i in ant + c["trechos_esperados"]):
            print(f"  {c['id']}: {ant} -> {c['trechos_esperados']}")


main()