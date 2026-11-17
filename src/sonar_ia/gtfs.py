"""Ferramenta determinística sobre o GTFS da SPTrans (usada pelo agente, config 3).

Responde "qual linha vai de A até B?" listando linhas DIRETAS (sem baldeação)
que passam por uma parada perto de A e, depois, por uma parada perto de B.
"""
from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

RAIO_METROS = 300  # paradas a até 300 m do local citado contam como "o mesmo lugar"

TIPO_ROTA = {0: "VLT", 1: "Metrô", 2: "Trem (CPTM)", 3: "Ônibus"}

_STOPWORDS = {"de", "da", "do", "das", "dos", "e", "estacao", "metro", "term", "terminal", "plat", "lado"}


def normalizar(texto: str) -> str:
    """Minúsculas, sem acento e sem pontuação."""
    texto = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9 ]", " ", texto.lower()).strip()


def _tokens(texto: str) -> set[str]:
    return {t for t in normalizar(texto).split() if t not in _STOPWORDS and len(t) > 1}


def _haversine_m(lat1, lon1, lat2, lon2):
    r = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


@dataclass
class LinhaDireta:
    linha: str
    nome: str
    tipo: str
    sentido: str
    parada_embarque: str
    parada_desembarque: str
    paradas_no_trajeto: int

    def para_dict(self) -> dict:
        return self.__dict__.copy()


class GTFS:
    """Consulta determinística sobre o GTFS da SPTrans.

    `modo="v1"` (padrão, o original, usado pelo agente oficial): casa o nome em stop_name + stop_desc e
    acrescenta as paradas num raio de 300 m. `modo="v2"` (correção C1 da etapa 6): casa só stop_name e
    escolhe o GRUPO de paradas mais denso, com preferência por nome igual ao pedido (ver `_paradas_v2`).
    """

    def __init__(self, pasta: str | Path, modo: str = "v1"):
        if modo not in ("v1", "v2"):
            raise ValueError(f"modo desconhecido: {modo!r}")
        self.modo = modo
        pasta = Path(pasta)
        self.stops = pd.read_csv(pasta / "stops.txt", dtype={"stop_id": str})
        self.routes = pd.read_csv(pasta / "routes.txt", dtype={"route_id": str})
        self.trips = pd.read_csv(pasta / "trips.txt", dtype={"route_id": str, "trip_id": str})
        self.stop_times = pd.read_csv(
            pasta / "stop_times.txt",
            dtype={"trip_id": str, "stop_id": str},
            usecols=["trip_id", "stop_id", "stop_sequence"],
        )
        self.stops["_tokens"] = (self.stops["stop_name"].fillna("") + " " + self.stops["stop_desc"].fillna("")).map(_tokens)
        self.stops["_tokens_nome"] = self.stops["stop_name"].fillna("").map(_tokens)

    def _paradas_v2(self, local: str) -> pd.DataFrame:
        """C1: casa só stop_name; agrupa as paradas casadas por proximidade (<= RAIO_METROS, encadeando) e fica
        com o grupo com mais paradas. Ordem de escolha: (1) se a pergunta tem "terminal" ou "estação", grupos cujos
        nomes têm essa palavra; (2) grupo com nome igual ao pedido; (3) mais paradas."""
        alvo = _tokens(local)
        if not alvo:
            return self.stops.iloc[0:0]
        casadas = self.stops[self.stops["_tokens_nome"].map(lambda t: alvo <= t)]
        if casadas.empty:
            return casadas
        lat, lon = casadas["stop_lat"].to_numpy(), casadas["stop_lon"].to_numpy()
        n = len(casadas)
        grupo = [-1] * n
        for i in range(n):  # componentes conexas (ligação simples) com distância <= RAIO_METROS
            if grupo[i] != -1:
                continue
            grupo[i], fila = i, [i]
            while fila:
                a = fila.pop()
                for b in range(n):
                    if grupo[b] == -1 and _haversine_m(lat[a], lon[a], lat[b], lon[b]) <= RAIO_METROS:
                        grupo[b] = i
                        fila.append(b)
        norm = normalizar(local)
        palavras = [p for p in ("terminal", "estacao") if p in norm.split()]
        nomes = casadas["stop_name"].map(normalizar).tolist()

        exato = casadas["_tokens_nome"].map(lambda t: t == alvo).tolist()

        def chave(g: int) -> tuple[int, int, int]:
            membros = [k for k in range(n) if grupo[k] == g]
            prioridade = int(any(p in nomes[k].split() for k in membros for p in palavras)) if palavras else 0
            # só "mais paradas" escolhia a avenida em vez da estação (o teste Tucuruvi -> Jabaquara quebrou);
            # por isso um grupo com nome IGUAL ao pedido ("Jabaquara") vem antes de grupos de rua ("Av. Jabaquara, 79")
            return prioridade, int(any(exato[k] for k in membros)), len(membros)

        melhor = max(set(grupo), key=chave)
        return casadas.iloc[[k for k in range(n) if grupo[k] == melhor]]

    def encontrar_paradas(self, local: str) -> pd.DataFrame:
        """Paradas cujo nome contém todas as palavras do local + paradas num raio de RAIO_METROS (modo v1)."""
        if self.modo == "v2":
            return self._paradas_v2(local)
        alvo = _tokens(local)
        if not alvo:
            return self.stops.iloc[0:0]
        casadas = self.stops[self.stops["_tokens"].map(lambda t: alvo <= t)]
        if casadas.empty:
            return casadas
        lat, lon = casadas["stop_lat"].mean(), casadas["stop_lon"].mean()
        dist = self.stops.apply(lambda r: _haversine_m(lat, lon, r.stop_lat, r.stop_lon), axis=1)
        return self.stops[(dist <= RAIO_METROS) | self.stops.index.isin(casadas.index)]

    def linhas_diretas(self, origem: str, destino: str, limite: int = 10) -> dict:
        p_orig = self.encontrar_paradas(origem)
        p_dest = self.encontrar_paradas(destino)
        if p_orig.empty or p_dest.empty:
            faltou = [n for n, p in ((origem, p_orig), (destino, p_dest)) if p.empty]
            return {"encontrado": False, "motivo": f"local não encontrado no GTFS: {', '.join(faltou)}", "linhas": []}

        st = self.stop_times
        o = st[st.stop_id.isin(p_orig.stop_id)].rename(columns={"stop_id": "o_id", "stop_sequence": "o_seq"})
        d = st[st.stop_id.isin(p_dest.stop_id)].rename(columns={"stop_id": "d_id", "stop_sequence": "d_seq"})
        pares = o.merge(d, on="trip_id")
        pares = pares[pares.o_seq < pares.d_seq]
        if pares.empty:
            return {"encontrado": False, "motivo": "nenhuma linha direta entre os dois locais", "linhas": []}

        pares = pares.assign(n=pares.d_seq - pares.o_seq).sort_values("n").drop_duplicates("trip_id")
        pares = pares.merge(self.trips, on="trip_id").merge(self.routes, on="route_id")
        nomes = self.stops.set_index("stop_id")["stop_name"]
        linhas = [
            LinhaDireta(
                linha=r.route_short_name,
                nome=r.route_long_name,
                tipo=TIPO_ROTA.get(int(r.route_type), "Outro"),
                sentido=str(r.trip_headsign),
                parada_embarque=nomes.get(r.o_id, r.o_id),
                parada_desembarque=nomes.get(r.d_id, r.d_id),
                paradas_no_trajeto=int(r.n),
            ).para_dict()
            for r in pares.drop_duplicates("route_id").head(limite).itertuples()
        ]
        return {"encontrado": True, "fonte": "gtfs_sptrans", "linhas": linhas}
