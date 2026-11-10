#!/usr/bin/env python3
"""Módulo Recorte territorial do Radar ENEM.

Autor: Vinícius Joacir dos Anjos. Regras registradas em docs/decisoes (DL-04).

Pergunta do módulo: a mesma nota ocupa a mesma posição no estado, na região
e no Brasil? Para uma nota e a UF informadas, o módulo calcula três cenários
(Plano de Trabalho, "Recorte territorial"):

  1. Posição entre os participantes que fizeram a prova na mesma UF.
  2. Posição entre os participantes da mesma região (IBGE).
  3. Posição na referência nacional da edição.

E compara as distribuições: diferença de posição entre UF e Brasil,
probabilidade de superioridade da UF contra o restante do país e a mediana
das 27 UFs, para situar o estado.

O arquivo tem três partes, como o módulo de equidade:

  - Regras de negócio: UFs, regiões, códigos de grupo, validação da entrada.
  - Agregação offline: lê a TRUSTED e grava data/analytics/dist_territorial.parquet
    (CDF exata por edição, área e grupo), conferida por três caminhos antes
    de publicar.
  - Comparação: aplica o motor estatístico v1 (scripts/estatistica.py).

Nenhuma função daqui devolve registro individual. O artefato contém
frequências por nota e fica restrito ao backend, como o dist_exata.parquet
(ADR-001).

Uso (depois de scripts/etl.py ter gerado a TRUSTED):
  ./.venv/bin/python scripts/territorial.py
"""

from __future__ import annotations

import json
import math
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from numbers import Real
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from colunas import PISO_GRUPO  # noqa: E402
from estatistica import (  # noqa: E402
    construir_acumulada,
    dobro_posicao,
    formatar_percentil,
    percentil_exato_acumulado,
    prob_superioridade,
    quantil,
    resumo,
    texto_da_posicao,
    z_score,
)

RAIZ = Path(__file__).resolve().parent.parent
TRUSTED = RAIZ / "data" / "trusted" / "enem"
ANALYTICS = RAIZ / "data" / "analytics"
DIST_TERRITORIAL = ANALYTICS / "dist_territorial.parquet"
MANIFESTO_TERRITORIAL = ANALYTICS / "_manifesto_territorial.json"

RECORTE = "territorial"
AREAS = {
    "cn": "Ciências da Natureza",
    "ch": "Ciências Humanas",
    "lc": "Linguagens e Códigos",
    "mt": "Matemática",
    "redacao": "Redação",
}

# ============================================================ REGRAS (DL-04)

# Regiões do IBGE. A ordem das UFs segue o código IBGE dentro da região.
REGIOES: dict[str, tuple[str, tuple[str, ...]]] = {
    "N": ("Norte", ("RO", "AC", "AM", "RR", "PA", "AP", "TO")),
    "NE": ("Nordeste", ("MA", "PI", "CE", "RN", "PB", "PE", "AL", "SE", "BA")),
    "SE": ("Sudeste", ("MG", "ES", "RJ", "SP")),
    "S": ("Sul", ("PR", "SC", "RS")),
    "CO": ("Centro-Oeste", ("MS", "MT", "GO", "DF")),
}

NOMES_UF = {
    "RO": "Rondônia", "AC": "Acre", "AM": "Amazonas", "RR": "Roraima", "PA": "Pará",
    "AP": "Amapá", "TO": "Tocantins", "MA": "Maranhão", "PI": "Piauí", "CE": "Ceará",
    "RN": "Rio Grande do Norte", "PB": "Paraíba", "PE": "Pernambuco", "AL": "Alagoas",
    "SE": "Sergipe", "BA": "Bahia", "MG": "Minas Gerais", "ES": "Espírito Santo",
    "RJ": "Rio de Janeiro", "SP": "São Paulo", "PR": "Paraná", "SC": "Santa Catarina",
    "RS": "Rio Grande do Sul", "MS": "Mato Grosso do Sul", "MT": "Mato Grosso",
    "GO": "Goiás", "DF": "Distrito Federal",
}

REGIAO_DA_UF = {uf: regiao for regiao, (_, ufs) in REGIOES.items() for uf in ufs}
UFS = tuple(sorted(REGIAO_DA_UF))

# Códigos de grupo com prefixo: "SE" é Sergipe e também a sigla do Sudeste,
# então sigla solta seria ambígua no artefato.
BRASIL = "BR"


def grupo_uf(uf: str) -> str:
    return f"UF-{uf}"


def grupo_regiao(regiao: str) -> str:
    return f"RG-{regiao}"


GRUPOS = (BRASIL,) + tuple(grupo_regiao(r) for r in REGIOES) + tuple(grupo_uf(u) for u in UFS)


def rotulo_grupo(grupo: str) -> str:
    if grupo == BRASIL:
        return "Brasil"
    tipo, _, sigla = grupo.partition("-")
    if tipo == "RG" and sigla in REGIOES:
        return f"Região {REGIOES[sigla][0]}"
    if tipo == "UF" and sigla in NOMES_UF:
        return NOMES_UF[sigla]
    raise ValueError(f"grupo territorial desconhecido: {grupo!r}")


class EntradaInvalida(ValueError):
    """Entrada do usuário fora das regras. A mensagem é exibida na interface."""


def normalizar_uf(uf: object) -> str:
    """Sigla da UF em maiúsculas. Aceita espaços e minúsculas (" sc " vira "SC")."""
    if not isinstance(uf, str) or not uf.strip():
        raise EntradaInvalida("Informe a UF onde você fez a prova.")
    sigla = uf.strip().upper()
    if sigla not in REGIAO_DA_UF:
        raise EntradaInvalida(f"UF '{uf}' não existe. Use a sigla de uma das 27 unidades federativas.")
    return sigla


@dataclass(frozen=True)
class Entrada:
    ano: int
    area: str
    nota: float
    uf: str
    regiao: str


def validar_entrada(ano: object, area: object, nota: object, uf: object, anos_disponiveis) -> Entrada:
    """Confere a entrada do usuário e devolve a versão normalizada.

    Regras de nota iguais às do produto: número finito entre 0 e 1000; nas
    provas objetivas no máximo uma casa decimal; na redação, múltipla de 20.
    """
    if isinstance(ano, bool) or not isinstance(ano, int) or ano not in set(anos_disponiveis):
        raise EntradaInvalida(f"Edição {ano!r} indisponível para comparação.")
    if area not in AREAS:
        raise EntradaInvalida(f"Área {area!r} inválida.")
    if nota is None:
        raise EntradaInvalida(f"Informe a nota de {AREAS[area]}.")
    if isinstance(nota, bool) or not isinstance(nota, Real):
        raise EntradaInvalida(f"A nota de {AREAS[area]} precisa ser um número.")
    nota = float(nota)
    if not math.isfinite(nota):
        raise EntradaInvalida(f"A nota de {AREAS[area]} precisa ser um número finito.")
    if not 0 <= nota <= 1000:
        raise EntradaInvalida(f"A nota de {AREAS[area]} deve estar entre 0 e 1000.")
    if area == "redacao":
        if abs(nota / 20 - round(nota / 20)) > 1e-9:
            raise EntradaInvalida("A nota da redação é sempre múltipla de 20 (ex.: 620, 640).")
    elif abs(nota * 10 - round(nota * 10)) > 1e-6:
        raise EntradaInvalida(f"A nota de {AREAS[area]} tem no máximo uma casa decimal.")
    sigla = normalizar_uf(uf)
    return Entrada(ano, area, round(nota, 1), sigla, REGIAO_DA_UF[sigla])


# ====================================================== AGREGAÇÃO OFFLINE


def _caso_regiao() -> str:
    return "CASE uf " + " ".join(f"WHEN '{uf}' THEN '{r}'" for uf, r in REGIAO_DA_UF.items()) + " END"


def sql_contagens(fonte: str, area: str) -> str:
    """SELECT (ano, grupo, nota, n) da área para Brasil, regiões e UFs.

    Cada participante elegível com nota na área entra em três grupos: o
    Brasil, a região e a UF da prova. UF fora das 27 siglas não entra em
    nenhum grupo, nem no Brasil, para os três níveis somarem igual (DL-04,
    item 5); a contagem fica no manifesto.
    """
    validas = ", ".join(f"'{u}'" for u in UFS)
    return f"""
        WITH base AS (
            SELECT ano, nota_{area} AS nota, upper(trim(uf_prova)) AS uf
            FROM {fonte}
            WHERE elegivel AND nota_{area} IS NOT NULL
        ), valida AS (
            SELECT ano, nota, uf, {_caso_regiao()} AS regiao FROM base WHERE uf IN ({validas})
        )
        SELECT ano, '{BRASIL}' AS grupo, nota, count(*) AS n FROM valida GROUP BY 1, 2, 3
        UNION ALL
        SELECT ano, 'RG-' || regiao AS grupo, nota, count(*) AS n FROM valida GROUP BY 1, 2, 3
        UNION ALL
        SELECT ano, 'UF-' || uf AS grupo, nota, count(*) AS n FROM valida GROUP BY 1, 2, 3
        ORDER BY 1, 2, 3
    """


def sql_artefato(fonte: str, piso: int = PISO_GRUPO) -> str:
    """SELECT do artefato: CDF exata por (ano, área, grupo), já com o piso."""
    partes = []
    for area in AREAS:
        partes.append(f"""
            SELECT ano, '{area}' AS area, '{RECORTE}' AS recorte, grupo, nota, n,
                   CAST(sum(n) OVER (PARTITION BY ano, grupo ORDER BY nota) - n AS BIGINT) AS abaixo,
                   CAST(sum(n) OVER (PARTITION BY ano, grupo) AS BIGINT) AS total
            FROM ({sql_contagens(fonte, area)})""")
    return f"""SELECT ano, area, recorte, grupo, CAST(nota AS DOUBLE) AS nota, CAST(n AS BIGINT) AS n,
                      abaixo, total
               FROM ({" UNION ALL ".join(partes)})
               WHERE total >= {piso}
               ORDER BY ano, area, grupo, nota"""


def calcular_cdfs(con, fonte: str, piso: int = PISO_GRUPO) -> tuple[dict, dict, dict]:
    """Mesmas CDFs do artefato, montadas em Python com construir_acumulada.

    Segundo caminho de cálculo: o artefato SQL só é publicado se coincidir com
    este. Devolve (cdfs, funil, contagens_brutas); as contagens brutas servem
    à conferência de soma entre níveis e não saem desta função para disco.
    """
    por_grupo: dict[tuple[int, str, str], list[tuple[float, int]]] = {}
    for area in AREAS:
        for ano, grupo, nota, n in con.execute(sql_contagens(fonte, area)).fetchall():
            por_grupo.setdefault((int(ano), area, grupo), []).append((float(nota), int(n)))

    cdfs, suprimidos, publicados = {}, [], {}
    for (ano, area, grupo), contagens in sorted(por_grupo.items()):
        total = sum(n for _, n in contagens)
        if total < piso:
            suprimidos.append(f"{ano}/{area}/{grupo}")
            continue
        cdfs[(ano, area, grupo)] = construir_acumulada(contagens)
        publicados[f"{ano}/{area}/{grupo}"] = total
    return cdfs, {"publicados": publicados, "suprimidos_abaixo_do_piso": suprimidos}, por_grupo


def conferir_somas(por_grupo: dict) -> None:
    """Terceira conferência: UFs somam a região e regiões somam o Brasil, nota a nota.

    Feita nas contagens antes do piso. Levanta AssertionError se algum
    participante tiver sido contado em nível errado ou perdido.
    """
    chaves = {(ano, area) for ano, area, _ in por_grupo}
    for ano, area in sorted(chaves):
        def contagem(grupo):
            return dict(por_grupo.get((ano, area, grupo), []))

        def somar(grupos):
            soma: dict[float, int] = {}
            for g in grupos:
                for nota, n in contagem(g).items():
                    soma[nota] = soma.get(nota, 0) + n
            return soma

        for regiao, (_, ufs) in REGIOES.items():
            if contagem(grupo_regiao(regiao)) != somar(grupo_uf(u) for u in ufs):
                raise AssertionError(f"{ano}/{area}: UFs não somam a região {regiao}")
        if contagem(BRASIL) != somar(grupo_regiao(r) for r in REGIOES):
            raise AssertionError(f"{ano}/{area}: regiões não somam o Brasil")


def auditar_uf(con, fonte: str) -> dict:
    """Elegíveis por situação da UF da prova, por edição (só para o manifesto local)."""
    validas = ", ".join(f"'{u}'" for u in UFS)
    saida = {}
    for ano, total, ausente, invalida, distintas in con.execute(
        f"""SELECT ano, count(*),
                   count(*) FILTER (uf_prova IS NULL OR trim(uf_prova) = ''),
                   count(*) FILTER (trim(uf_prova) <> '' AND upper(trim(uf_prova)) NOT IN ({validas})),
                   count(DISTINCT upper(trim(uf_prova))) FILTER (upper(trim(uf_prova)) IN ({validas}))
            FROM {fonte} WHERE elegivel GROUP BY 1 ORDER BY 1"""
    ).fetchall():
        saida[str(ano)] = {"elegiveis": total, "uf_ausente": ausente, "uf_invalida": invalida,
                           "ufs_presentes": distintas}
    return saida


def _filtro_grupo(grupo: str) -> str:
    validas = ", ".join(f"'{u}'" for u in UFS)
    if grupo == BRASIL:
        return f"upper(trim(uf_prova)) IN ({validas})"
    tipo, _, sigla = grupo.partition("-")
    ufs = REGIOES[sigla][1] if tipo == "RG" else (sigla,)
    return f"upper(trim(uf_prova)) IN ({', '.join(repr(u) for u in ufs)})"


def percentil_direto(con, fonte: str, ano: int, area: str, grupo: str, nota: float) -> float:
    """Percentil por contagem direta na TRUSTED, sem passar pela CDF."""
    total, abaixo, iguais = con.execute(
        f"""SELECT count(*), count(*) FILTER (nota_{area} < ?), count(*) FILTER (nota_{area} = ?)
            FROM {fonte} WHERE ano = ? AND elegivel AND nota_{area} IS NOT NULL AND {_filtro_grupo(grupo)}""",
        [nota, nota, ano],
    ).fetchone()
    return (abaixo + iguais / 2) / total * 100


def etapa_territorial(trusted: Path = TRUSTED, destino: Path = DIST_TERRITORIAL,
                      manifesto: Path = MANIFESTO_TERRITORIAL, piso: int = PISO_GRUPO) -> dict:
    """TRUSTED -> dist_territorial.parquet, conferido por três caminhos.

    1. CDF em SQL (janela) igual à CDF em Python (construir_acumulada).
    2. UFs somam a região e regiões somam o Brasil, nota a nota.
    3. Percentil da CDF igual à contagem direta na TRUSTED.

    Grava num temporário e só troca o arquivo final depois das conferências.
    """
    import duckdb

    con = duckdb.connect()
    inicio = time.perf_counter()
    try:
        notas = ", ".join(f"nota_{a}" for a in AREAS)
        con.execute(
            f"""CREATE TEMP TABLE base_territorial AS
                SELECT ano, elegivel, uf_prova, {notas}
                FROM read_parquet('{trusted}/*/*.parquet', hive_partitioning=true)
                WHERE elegivel"""
        )
        fonte = "base_territorial"
        esperadas, funil, brutas = calcular_cdfs(con, fonte, piso)
        if not esperadas:
            raise ValueError("nenhum grupo territorial atingiu o piso; publicação abortada")
        conferir_somas(brutas)
        del brutas
        destino.parent.mkdir(parents=True, exist_ok=True)
        temporario = destino.with_name(f".{destino.name}.tmp")
        try:
            con.execute(f"COPY ({sql_artefato(fonte, piso)}) TO '{temporario}' (FORMAT parquet, COMPRESSION zstd)")
            cdfs = carregar(temporario)
            if cdfs != esperadas:
                diferentes = sorted(set(cdfs) ^ set(esperadas)) or [
                    k for k in cdfs if cdfs[k] != esperadas[k]]
                raise AssertionError(f"artefato SQL difere do cálculo em Python: {diferentes[:5]}")
            maior = 0.0
            for (ano, area, grupo), cdf in cdfs.items():
                lista = [item[0] for item in cdf]
                for nota in {lista[0], lista[-1], lista[len(lista) // 2], lista[0] - 1, lista[-1] + 1,
                             400.0, 500.0, 650.0}:
                    divergencia = abs(percentil_exato_acumulado(cdf, nota)
                                      - percentil_direto(con, fonte, ano, area, grupo, nota))
                    if divergencia > 1e-9:
                        raise AssertionError(f"{ano}/{area}/{grupo} nota {nota}: divergência {divergencia}")
                    maior = max(maior, divergencia)
            temporario.replace(destino)
        finally:
            temporario.unlink(missing_ok=True)
        resultado = {
            "gerado_em_utc": datetime.now(timezone.utc).isoformat(),
            "regras": "docs/decisoes/README.md#dl-04",
            "piso": piso,
            "grupos": funil,
            "uf_prova": auditar_uf(con, fonte),
            "verificacao": {
                "metodo": "CDF em SQL = CDF em Python; UFs somam regiao e regioes somam Brasil; "
                          "percentil da CDF x contagem direta",
                "maior_divergencia_pp": maior,
            },
            "linhas": sum(len(c) for c in cdfs.values()),
            "bytes": destino.stat().st_size,
            "tempo_segundos": round(time.perf_counter() - inicio, 3),
        }
        manifesto.write_text(json.dumps(resultado, indent=2, ensure_ascii=False), encoding="utf-8")
        return resultado
    finally:
        con.close()


def carregar(arquivo: Path = DIST_TERRITORIAL) -> dict[tuple[int, str, str], list[tuple[float, int, int]]]:
    """CDFs por (ano, área, grupo), só em memória do backend."""
    import duckdb

    saida: dict[tuple[int, str, str], list[tuple[float, int, int]]] = {}
    for ano, area, grupo, nota, n, abaixo in duckdb.sql(
        f"SELECT ano, area, grupo, nota, n, abaixo FROM read_parquet('{arquivo}') "
        f"WHERE recorte = '{RECORTE}' ORDER BY ano, area, grupo, nota"
    ).fetchall():
        saida.setdefault((int(ano), area, grupo), []).append((float(nota), int(n), int(abaixo)))
    return saida


# ============================================================= COMPARAÇÃO


def restante(dist_total: list[tuple[float, int, int]],
             dist_parte: list[tuple[float, int, int]]) -> list[tuple[float, int, int]]:
    """CDF do total sem a parte (ex.: Brasil sem a UF), nota a nota.

    A parte precisa estar contida no total: toda nota da parte existe no total
    com frequência maior ou igual. Caso contrário, ValueError.
    """
    da_parte = {nota: n for nota, n, _ in dist_parte}
    contagens = []
    for nota, n, _ in dist_total:
        sobra = n - da_parte.pop(nota, 0)
        if sobra < 0:
            raise ValueError(f"parte maior que o total na nota {nota}")
        if sobra:
            contagens.append((nota, sobra))
    if da_parte:
        raise ValueError("parte tem notas que não existem no total")
    if not contagens:
        raise ValueError("restante vazio")
    return construir_acumulada(contagens)


@dataclass(frozen=True)
class Cenario:
    grupo: str
    rotulo: str
    disponivel: bool
    motivo: str = ""
    n: int = 0
    percentil: float = 0.0  # exato, só backend
    media: float = 0.0
    mediana: float = 0.0
    desvio: float = 0.0
    z: float | None = None
    texto_percentil: str = ""  # o que a interface mostra
    em_limite: bool = False


@dataclass(frozen=True)
class Comparacao:
    entrada: Entrada
    uf: Cenario
    regiao: Cenario
    brasil: Cenario
    diferenca_pp: float | None = None  # percentil na UF - no Brasil; None se a UF está em limite
    prob_superioridade: float | None = None  # P(UF > restante do Brasil) + 0,5 P(=)
    posicao_mediana: int | None = None  # 1 = maior mediana entre as UFs publicadas
    ufs_comparadas: int = 0
    avisos: list[str] = field(default_factory=list)
    superioridade_regiao: float | None = None  # P(região > restante do Brasil) + 0,5 P(=)
    mediana_empatada_com: int = 0  # outras UFs com a mesma mediana (dividem a posição)


def _cenario(cdfs, ano: int, area: str, grupo: str, nota: float) -> Cenario:
    rotulo = rotulo_grupo(grupo)
    cdf = cdfs.get((ano, area, grupo))
    if not cdf:
        return Cenario(grupo, rotulo, False,
                       f"grupo insuficiente: menos de {PISO_GRUPO} participantes nesta edição e área")
    medidas = resumo(cdf)
    try:
        z = z_score(cdf, nota)
    except ValueError:  # desvio zero
        z = None
    # Uma busca só: percentil exato, texto e em_limite saem do mesmo
    # (2 · abaixo + iguais, N), e a diferença UF − Brasil usa a mesma posição
    # que decidiu o limite.
    dobro, total = dobro_posicao(cdf, nota)
    percentil = dobro * 100 / (2 * total)
    if grupo == BRASIL:  # Brasil segue exato (ADR-001; DL-04, 8.6)
        texto, em_limite = formatar_percentil(percentil), False
    else:
        texto, em_limite = texto_da_posicao(dobro, total)
    return Cenario(grupo, rotulo, True, n=medidas["N"], percentil=percentil,
                   media=medidas["media"], mediana=medidas["mediana"], desvio=medidas["desvio"], z=z,
                   texto_percentil=texto, em_limite=em_limite)


def medianas_ufs(cdfs, ano: int, area: str) -> list[tuple[str, float, int]]:
    """[(UF, mediana, N)] das UFs publicadas, da maior para a menor mediana.

    A ordem entre UFs de mesma mediana (sigla) é só de listagem; a posição
    exibida é compartilhada (posicao_da_mediana).
    """
    linhas = []
    for uf in UFS:
        cdf = cdfs.get((ano, area, grupo_uf(uf)))
        if cdf:
            linhas.append((uf, quantil(cdf, 0.5), cdf[-1][1] + cdf[-1][2]))
    return sorted(linhas, key=lambda linha: (-linha[1], linha[0]))


def posicao_da_mediana(ranking: list[tuple[str, float, int]], uf: str) -> tuple[int, int]:
    """(posição, outras UFs com a mesma mediana). Empatadas dividem a posição.

    Posição = 1 + número de UFs com mediana estritamente maior ("1, 2, 2, 4").
    """
    mediana = next(m for sigla, m, _ in ranking if sigla == uf)
    maiores = sum(m > mediana for _, m, _ in ranking)
    empatadas = sum(m == mediana for sigla, m, _ in ranking if sigla != uf)
    return 1 + maiores, empatadas


def comparar(cdfs, entrada: Entrada) -> Comparacao:
    """Os três cenários do módulo para uma entrada já validada.

    Nunca levanta exceção por falta de grupo: o cenário sem dados volta com
    disponivel=False e as medidas entre grupos ficam None.
    """
    ano, area, nota = entrada.ano, entrada.area, entrada.nota
    uf = _cenario(cdfs, ano, area, grupo_uf(entrada.uf), nota)
    regiao = _cenario(cdfs, ano, area, grupo_regiao(entrada.regiao), nota)
    brasil = _cenario(cdfs, ano, area, BRASIL, nota)
    avisos = []
    if any(c.disponivel and c.z is None for c in (uf, regiao, brasil)):
        avisos.append("Z-Score indefinido em grupo com todas as notas iguais.")
    diferenca = superioridade = posicao = None
    if uf.disponivel and brasil.disponivel:
        # Em limite, a diferença somada ao Brasil exato devolveria o valor
        # escondido (DL-04, 8.7).
        diferenca = None if uf.em_limite else uf.percentil - brasil.percentil
        dist_uf, dist_br = cdfs[(ano, area, grupo_uf(entrada.uf))], cdfs[(ano, area, BRASIL)]
        try:
            superioridade = prob_superioridade(dist_uf, restante(dist_br, dist_uf))
        except ValueError:  # UF é o país inteiro (artefato de uma UF só)
            avisos.append("Sem participantes fora da UF para comparar com o restante do país.")
    superioridade_regiao = None
    if regiao.disponivel and brasil.disponivel:
        dist_rg = cdfs[(ano, area, grupo_regiao(entrada.regiao))]
        try:
            superioridade_regiao = prob_superioridade(dist_rg, restante(cdfs[(ano, area, BRASIL)], dist_rg))
        except ValueError:  # região é o país inteiro
            avisos.append("Sem participantes fora da região para comparar com o restante do país.")
    ranking = medianas_ufs(cdfs, ano, area)
    empatadas = 0
    if uf.disponivel:
        posicao, empatadas = posicao_da_mediana(ranking, entrada.uf)
    if ranking and len(ranking) < len(UFS):
        avisos.append(f"{len(UFS) - len(ranking)} UF(s) sem grupo publicado nesta edição e área.")
    return Comparacao(entrada, uf, regiao, brasil, diferenca, superioridade, posicao, len(ranking), avisos,
                      superioridade_regiao, empatadas)


# ======================================================= EXIBIÇÃO (DL-01)


def formatar_nota(nota: float) -> str:
    return f"{nota:.1f}".replace(".", ",")


def formatar_z(z: float | None) -> str:
    return "indefinido" if z is None else f"{z:+.2f}".replace(".", ",")


def formatar_inteiro(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def main() -> int:
    if not TRUSTED.exists():
        print(f"TRUSTED não encontrada em {TRUSTED}. Rode antes: scripts/etl.py", file=sys.stderr)
        return 1
    r = etapa_territorial()
    print(f"[territorial] {len(r['grupos']['publicados'])} grupos publicados, "
          f"{len(r['grupos']['suprimidos_abaixo_do_piso'])} suprimidos pelo piso, "
          f"{r['linhas']} linhas, {r['bytes']} bytes, {r['tempo_segundos']}s")
    print(f"[territorial] maior divergência CDF x contagem direta: {r['verificacao']['maior_divergencia_pp']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
