#!/usr/bin/env python3
"""Módulo Capital escolar familiar do Radar ENEM.

Autor: Guilherme da Silva Anselmo. Regras registradas em docs/decisoes (DL-05).

Pergunta do módulo: a mesma nota ocupa a mesma posição entre participantes
cujos responsáveis têm escolaridades diferentes? Para uma nota e as respostas
de Q001 (pai ou responsável) e Q002 (mãe ou responsável), o módulo calcula:

  1. Posição entre participantes do mesmo nível de escolaridade (o maior
     nível entre pai e mãe, DL-05 item 2).
  2. Posição na referência nacional da edição.
  3. Opcional: posição entre participantes do nível vizinho (o imediatamente
     acima; para o nível G, o imediatamente abaixo), com a diferença de
     posição e a probabilidade de superioridade entre os dois níveis.

O arquivo tem três partes, como os módulos de equidade e territorial:

  - Regras de negócio: níveis, rótulos, validação da entrada.
  - Agregação offline: lê a TRUSTED e grava data/analytics/dist_capital.parquet
    (CDF exata por edição, área e nível), conferida por três caminhos antes
    de publicar.
  - Comparação: aplica o motor estatístico v1 (scripts/estatistica.py).

Nenhuma função daqui devolve registro individual. O artefato contém
frequências por nota e fica restrito ao backend, como o dist_exata.parquet
(ADR-001).

Uso (depois de scripts/etl.py ter gerado a TRUSTED):
  ./.venv/bin/python scripts/capital_escolar.py
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
    exibir_percentil,
    formatar_percentil,
    percentil_exato_acumulado,
    prob_superioridade,
    resumo,
    z_score,
)

RAIZ = Path(__file__).resolve().parent.parent
TRUSTED = RAIZ / "data" / "trusted" / "enem"
ANALYTICS = RAIZ / "data" / "analytics"
DIST_CAPITAL = ANALYTICS / "dist_capital.parquet"
MANIFESTO_CAPITAL = ANALYTICS / "_manifesto_capital.json"
DICIONARIO = RAIZ / "docs" / "dicionario"

RECORTE = "capital"
AREAS = {
    "cn": "Ciências da Natureza",
    "ch": "Ciências Humanas",
    "lc": "Linguagens e Códigos",
    "mt": "Matemática",
    "redacao": "Redação",
}

# ============================================================ REGRAS (DL-05)

# Alternativas de Q001 e Q002 (iguais nas quatro edições, conferido em
# docs/dicionario). A a G são níveis; H é "Não sei", resposta válida que não
# informa nível (DL-05, item 3).
ALTERNATIVAS = tuple("ABCDEFGH")
NAO_SEI = "H"

# Seis níveis em ordem crescente de escolaridade (DL-05, item 4). B e C são
# juntados: ambos significam "não terminou o Fundamental".
NIVEIS = ("A", "BC", "D", "E", "F", "G")
LETRAS_DO_NIVEL = {"A": ("A",), "BC": ("B", "C"), "D": ("D",), "E": ("E",), "F": ("F",), "G": ("G",)}
NIVEL_DA_LETRA = {letra: nivel for nivel, letras in LETRAS_DO_NIVEL.items() for letra in letras}
POSICAO_DO_NIVEL = {nivel: i for i, nivel in enumerate(NIVEIS, start=1)}  # A = 1 ... G = 6

ROTULOS = {
    "A": "Nunca estudou",
    "BC": "Ensino Fundamental incompleto",
    "D": "Ensino Fundamental completo",
    "E": "Ensino Médio completo",
    "F": "Ensino Superior completo",
    "G": "Pós-graduação completa",
}

# "BR" é a referência nacional: todos os elegíveis com nota na área, inclusive
# quem não tem nível (DL-05, itens 3 e 8). Os códigos de nível levam prefixo
# para não se confundirem com alternativas da pergunta ("A" é alternativa e nível).
BRASIL = "BR"


def grupo_nivel(nivel: str) -> str:
    return f"NV-{nivel}"


GRUPOS = (BRASIL,) + tuple(grupo_nivel(n) for n in NIVEIS)


def rotulo_grupo(grupo: str) -> str:
    if grupo == BRASIL:
        return "Brasil"
    tipo, _, nivel = grupo.partition("-")
    if tipo == "NV" and nivel in ROTULOS:
        return f"Responsáveis com {ROTULOS[nivel].lower()}"
    raise ValueError(f"grupo de capital escolar desconhecido: {grupo!r}")


class EntradaInvalida(ValueError):
    """Entrada do usuário fora das regras. A mensagem é exibida na interface."""


def _alternativa(valor: object, rotulo: str) -> str:
    """Letra de Q001/Q002 em maiúscula (" e " vira "E"). Levanta se faltar ou não existir."""
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        raise EntradaInvalida(f"Informe a escolaridade de {rotulo} (pode responder \"Não sei\").")
    if not isinstance(valor, str):
        raise EntradaInvalida(f"A escolaridade de {rotulo} deve ser uma alternativa de A a H.")
    letra = valor.strip().upper()
    if letra not in ALTERNATIVAS:
        raise EntradaInvalida(f"Alternativa '{valor}' não existe para a escolaridade de {rotulo} (A a H).")
    return letra


def nivel_do_participante(pai: object, mae: object) -> str | None:
    """Nível do participante: o maior entre pai e mãe, ou None sem nível (DL-05).

    Regras, na ordem:
      - campo fora de A–H (código inexistente) tira o registro dos níveis, mesmo
        que o outro campo seja válido (itens 8 e 9);
      - H ou vazio num campo: vale o outro (item 2);
      - H ou vazio nos dois: sem nível (item 3).
    Referência em Python puro; o ETL calcula o mesmo em SQL e os testes conferem
    os dois caminhos.
    """
    letras = []
    for valor in (pai, mae):
        if valor is None:
            continue
        if not isinstance(valor, str):
            return None
        letra = valor.strip().upper()
        if not letra:
            continue
        if letra not in ALTERNATIVAS:
            return None
        letras.append(letra)
    niveis = [NIVEL_DA_LETRA[x] for x in letras if x != NAO_SEI]
    if not niveis:
        return None
    return max(niveis, key=POSICAO_DO_NIVEL.__getitem__)


def nivel_de_comparacao(nivel: str) -> tuple[str, str]:
    """(nível vizinho, "acima" ou "abaixo"): o imediatamente acima; para G, o F (itens 6 e 7).

    O módulo não pula níveis: se o vizinho não tiver grupo publicado, a
    comparação não é exibida em vez de trocar de nível sem o usuário escolher.
    """
    posicao = POSICAO_DO_NIVEL[nivel]
    if posicao == len(NIVEIS):
        return NIVEIS[posicao - 2], "abaixo"
    return NIVEIS[posicao], "acima"


@dataclass(frozen=True)
class Entrada:
    ano: int
    area: str
    nota: float
    pai: str
    mae: str
    nivel: str | None  # None quando pai e mãe são "Não sei" (só posição nacional)


def validar_entrada(ano: object, area: object, nota: object, pai: object, mae: object,
                    anos_disponiveis) -> Entrada:
    """Confere a entrada do usuário e devolve a versão normalizada.

    Regras de nota iguais às do produto: número finito entre 0 e 1000; nas
    provas objetivas no máximo uma casa decimal; na redação, múltipla de 20.
    Pai e mãe: alternativa de A a H, obrigatória nos dois campos.
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
    letra_pai = _alternativa(pai, "seu pai ou responsável")
    letra_mae = _alternativa(mae, "sua mãe ou responsável")
    return Entrada(ano, area, round(nota, 1), letra_pai, letra_mae, nivel_do_participante(letra_pai, letra_mae))


def opcoes_escolaridade(ano: int, variavel: str, dicionario: Path = DICIONARIO) -> list[tuple[str, str]]:
    """Alternativas de Q001 ou Q002 com o texto oficial da edição: [(letra, texto)].

    O texto vem do dicionário do INEP versionado em docs/dicionario, então a
    pessoa escolhe a mesma frase que leu no questionário.
    """
    arquivo = dicionario / f"dicionario_{ano}.json"
    if not arquivo.exists():
        raise EntradaInvalida(f"Edição {ano} sem dicionário de {variavel}.")
    categorias = _procurar_variavel(json.loads(arquivo.read_text(encoding="utf-8")), variavel)
    if categorias is None:
        raise EntradaInvalida(f"Dicionário {ano} sem a variável {variavel}.")
    faltando = set(ALTERNATIVAS) - set(categorias)
    if faltando:
        raise EntradaInvalida(f"Dicionário {ano} sem as alternativas {sorted(faltando)} de {variavel}.")
    return [(letra, categorias[letra].strip().rstrip(".")) for letra in ALTERNATIVAS]


def _procurar_variavel(no, nome: str) -> dict | None:
    if isinstance(no, dict):
        if no.get("variavel") == nome and isinstance(no.get("categorias"), dict):
            return no["categorias"]
        filhos = no.values()
    elif isinstance(no, list):
        filhos = no
    else:
        return None
    for filho in filhos:
        achado = _procurar_variavel(filho, nome)
        if achado is not None:
            return achado
    return None


# ====================================================== AGREGAÇÃO OFFLINE


def _sql_posicao(coluna: str) -> str:
    """Posição do nível de um campo: A=1, B/C=2, D=3, E=4, F=5, G=6; 0 = H ou vazio; -1 = inválido."""
    casos = " ".join(f"WHEN '{letra}' THEN {POSICAO_DO_NIVEL[nivel]}" for letra, nivel in NIVEL_DA_LETRA.items())
    return (f"CASE upper(trim({coluna})) {casos} WHEN '{NAO_SEI}' THEN 0 WHEN '' THEN 0 "
            f"ELSE CASE WHEN {coluna} IS NULL THEN 0 ELSE -1 END END")


def _sql_nivel() -> str:
    """Posição do nível do participante (1 a 6) ou NULL, sobre as colunas `rp` e `rm`."""
    return ("CASE WHEN rp < 0 OR rm < 0 THEN NULL WHEN greatest(rp, rm) = 0 THEN NULL "
            "ELSE greatest(rp, rm) END")


def _sql_grupo_do_nivel() -> str:
    casos = " ".join(f"WHEN {POSICAO_DO_NIVEL[n]} THEN '{grupo_nivel(n)}'" for n in NIVEIS)
    return f"CASE posicao {casos} END"


def sql_contagens(fonte: str, area: str) -> str:
    """SELECT (ano, grupo, nota, n) da área para o Brasil e os seis níveis.

    Todo participante elegível com nota na área entra no Brasil. Só quem tem
    nível entra também num grupo de nível. Sem nível: pai e mãe "Não sei" ou
    vazios, ou um campo inválido (DL-05, itens 3, 8 e 9). As contagens dessas
    exclusões vão para o manifesto (auditar_escolaridade).
    """
    return f"""
        WITH base AS (
            SELECT ano, nota_{area} AS nota,
                   {_sql_posicao("escolaridade_pai")} AS rp,
                   {_sql_posicao("escolaridade_mae")} AS rm
            FROM {fonte}
            WHERE elegivel AND nota_{area} IS NOT NULL
        ), nivel AS (
            SELECT ano, nota, {_sql_nivel()} AS posicao FROM base
        )
        SELECT ano, '{BRASIL}' AS grupo, nota, count(*) AS n FROM nivel GROUP BY 1, 2, 3
        UNION ALL
        SELECT ano, {_sql_grupo_do_nivel()} AS grupo, nota, count(*) AS n
        FROM nivel WHERE posicao IS NOT NULL GROUP BY 1, 2, 3
        ORDER BY 1, 2, 3
    """


def sql_artefato(fonte: str, piso: int = PISO_GRUPO) -> str:
    """SELECT do artefato: CDF exata por (ano, área, grupo), já com o piso (DL-05, item 14)."""
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
    à conferência de soma e não saem desta função para disco.
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
    """Terceira conferência: os níveis nunca somam mais que o Brasil, nota a nota.

    Cada participante entra no Brasil uma vez e em no máximo um nível. Se a
    soma dos níveis passar do Brasil em alguma nota, alguém foi contado em
    dois níveis (ou perdido do Brasil). Feita nas contagens antes do piso.
    Levanta AssertionError.
    """
    for ano, area in sorted({(a, ar) for a, ar, _ in por_grupo}):
        brasil = dict(por_grupo.get((ano, area, BRASIL), []))
        soma: dict[float, int] = {}
        for nivel in NIVEIS:
            for nota, n in por_grupo.get((ano, area, grupo_nivel(nivel)), []):
                soma[nota] = soma.get(nota, 0) + n
        for nota, n in soma.items():
            if n > brasil.get(nota, 0):
                raise AssertionError(f"{ano}/{area}: níveis somam {n} na nota {nota}, Brasil tem {brasil.get(nota, 0)}")


def auditar_escolaridade(con, fonte: str) -> dict:
    """Elegíveis por situação de Q001 e Q002, por edição (só para o manifesto local, DL-05 itens 3, 8 e 9)."""
    saida = {}
    consulta = f"""
        WITH base AS (
            SELECT ano, {_sql_posicao("escolaridade_pai")} AS rp, {_sql_posicao("escolaridade_mae")} AS rm,
                   upper(trim(escolaridade_pai)) AS p, upper(trim(escolaridade_mae)) AS m
            FROM {fonte} WHERE elegivel
        )
        SELECT ano, count(*),
               count(*) FILTER (rp >= 0 AND rm >= 0 AND greatest(rp, rm) > 0),
               count(*) FILTER (rp >= 0 AND rm >= 0 AND greatest(rp, rm) = 0),
               count(*) FILTER (rp < 0 OR rm < 0),
               count(*) FILTER (p = '{NAO_SEI}'), count(*) FILTER (m = '{NAO_SEI}')
        FROM base GROUP BY 1 ORDER BY 1"""
    for ano, total, com_nivel, sem_informacao, invalido, pai_h, mae_h in con.execute(consulta).fetchall():
        saida[str(ano)] = {"elegiveis": total, "com_nivel": com_nivel,
                           "sem_nivel_nao_sei_ou_vazio": sem_informacao,
                           "campo_invalido": invalido, "pai_nao_sei": pai_h, "mae_nao_sei": mae_h}
    return saida


def _filtro_grupo(grupo: str) -> str:
    """Filtro SQL do grupo escrito por letras (não por posições), independente do caminho principal.

    Nível X = os dois campos em A–H ou vazios, ao menos um campo numa letra de X
    e nenhum numa letra de nível maior.
    """
    if grupo == BRASIL:
        return "TRUE"
    tipo, _, nivel = grupo.partition("-")
    if tipo != "NV" or nivel not in LETRAS_DO_NIVEL:
        raise ValueError(f"grupo de capital escolar desconhecido: {grupo!r}")
    pai = "coalesce(upper(trim(escolaridade_pai)), '')"
    mae = "coalesce(upper(trim(escolaridade_mae)), '')"

    def lista(letras):
        return ", ".join(f"'{x}'" for x in letras)

    validas = lista(ALTERNATIVAS + ("",))
    proprias = lista(LETRAS_DO_NIVEL[nivel])
    maiores = [letra for n in NIVEIS if POSICAO_DO_NIVEL[n] > POSICAO_DO_NIVEL[nivel] for letra in LETRAS_DO_NIVEL[n]]
    filtro = (f"{pai} IN ({validas}) AND {mae} IN ({validas}) AND ({pai} IN ({proprias}) OR {mae} IN ({proprias}))")
    if maiores:
        filtro += f" AND {pai} NOT IN ({lista(maiores)}) AND {mae} NOT IN ({lista(maiores)})"
    return filtro


def percentil_direto(con, fonte: str, ano: int, area: str, grupo: str, nota: float) -> float:
    """Percentil por contagem direta na TRUSTED, sem passar pela CDF."""
    total, abaixo, iguais = con.execute(
        f"""SELECT count(*), count(*) FILTER (nota_{area} < ?), count(*) FILTER (nota_{area} = ?)
            FROM {fonte} WHERE ano = ? AND elegivel AND nota_{area} IS NOT NULL AND {_filtro_grupo(grupo)}""",
        [nota, nota, ano],
    ).fetchone()
    return (abaixo + iguais / 2) / total * 100


def etapa_capital(trusted: Path = TRUSTED, destino: Path = DIST_CAPITAL,
                  manifesto: Path = MANIFESTO_CAPITAL, piso: int = PISO_GRUPO) -> dict:
    """TRUSTED -> dist_capital.parquet, conferido por três caminhos.

    1. CDF em SQL (janela) igual à CDF em Python (construir_acumulada).
    2. Os níveis nunca somam mais que o Brasil, nota a nota.
    3. Percentil da CDF igual à contagem direta na TRUSTED (filtro por letras).

    Grava num temporário e só troca o arquivo final depois das conferências.
    """
    import duckdb

    con = duckdb.connect()
    inicio = time.perf_counter()
    try:
        notas = ", ".join(f"nota_{a}" for a in AREAS)
        con.execute(
            f"""CREATE TEMP TABLE base_capital AS
                SELECT ano, elegivel, escolaridade_pai, escolaridade_mae, {notas}
                FROM read_parquet('{trusted}/*/*.parquet', hive_partitioning=true)
                WHERE elegivel"""
        )
        fonte = "base_capital"
        esperadas, funil, brutas = calcular_cdfs(con, fonte, piso)
        if not esperadas:
            raise ValueError("nenhum grupo de capital escolar atingiu o piso; publicação abortada")
        conferir_somas(brutas)
        del brutas
        destino.parent.mkdir(parents=True, exist_ok=True)
        temporario = destino.with_name(f".{destino.name}.tmp")
        try:
            con.execute(f"COPY ({sql_artefato(fonte, piso)}) TO '{temporario}' (FORMAT parquet, COMPRESSION zstd)")
            cdfs = carregar(temporario)
            if cdfs != esperadas:
                diferentes = sorted(set(cdfs) ^ set(esperadas)) or [k for k in cdfs if cdfs[k] != esperadas[k]]
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
            "regras": "docs/decisoes/README.md#dl-05",
            "piso": piso,
            "grupos": funil,
            "escolaridade": auditar_escolaridade(con, fonte),
            "verificacao": {
                "metodo": "CDF em SQL = CDF em Python; niveis nunca somam mais que o Brasil; "
                          "percentil da CDF x contagem direta (filtro por letras)",
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


def carregar(arquivo: Path = DIST_CAPITAL) -> dict[tuple[int, str, str], list[tuple[float, int, int]]]:
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
    proprio: Cenario | None  # None: pai e mãe "Não sei"; só a posição nacional
    brasil: Cenario
    vizinho: Cenario | None = None  # só quando o usuário pediu a comparação (DL-05, item 5)
    sentido_vizinho: str = ""  # "acima" ou "abaixo"
    diferenca_pp: float | None = None  # percentil no próprio nível - no vizinho; None se algum está em limite
    prob_superioridade: float | None = None  # P(próprio > vizinho) + 0,5 P(=)
    avisos: list[str] = field(default_factory=list)


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
    percentil = percentil_exato_acumulado(cdf, nota)
    if grupo == BRASIL:  # referência nacional segue exata (ADR-001; DL-04, 8.6)
        texto, em_limite = formatar_percentil(percentil), False
    else:
        texto, em_limite = exibir_percentil(cdf, nota)  # função compartilhada (DL-05, item 13)
    return Cenario(grupo, rotulo, True, n=medidas["N"], percentil=percentil,
                   media=medidas["media"], mediana=medidas["mediana"], desvio=medidas["desvio"], z=z,
                   texto_percentil=texto, em_limite=em_limite)


def comparar(cdfs, entrada: Entrada, comparar_outro_nivel: bool = False) -> Comparacao:
    """Cenários do módulo para uma entrada já validada.

    Por padrão: a posição no próprio nível e a posição nacional. Com
    `comparar_outro_nivel`, também o nível vizinho, a diferença de posição e a
    probabilidade de superioridade (DL-05, itens 5 a 7 e 12).

    Nunca levanta exceção por falta de grupo: o cenário sem dados volta com
    disponivel=False e as medidas entre grupos ficam None. Se um dos dois
    níveis estiver em limite, a diferença de posição não é calculada (item 13):
    somada ao percentil exato do outro, ela devolveria o valor escondido. A
    probabilidade de superioridade continua, pois compara os níveis inteiros.
    """
    ano, area, nota = entrada.ano, entrada.area, entrada.nota
    brasil = _cenario(cdfs, ano, area, BRASIL, nota)
    avisos: list[str] = []
    if entrada.nivel is None:
        avisos.append("Você respondeu \"Não sei\" para os dois responsáveis: não há nível de escolaridade "
                      "para comparar, então só a posição nacional é mostrada.")
        return Comparacao(entrada, None, brasil, avisos=avisos)
    if NAO_SEI in (entrada.pai, entrada.mae):
        avisos.append("Um dos responsáveis ficou como \"Não sei\", então vale a escolaridade do outro. Se o "
                      "que ficou como \"Não sei\" tiver escolaridade maior, o seu grupo real seria outro.")
    proprio = _cenario(cdfs, ano, area, grupo_nivel(entrada.nivel), nota)
    vizinho, sentido, diferenca, superioridade = None, "", None, None
    if comparar_outro_nivel:
        nivel_vizinho, sentido = nivel_de_comparacao(entrada.nivel)
        vizinho = _cenario(cdfs, ano, area, grupo_nivel(nivel_vizinho), nota)
        if proprio.disponivel and vizinho.disponivel:
            if not (proprio.em_limite or vizinho.em_limite):
                diferenca = proprio.percentil - vizinho.percentil
            superioridade = prob_superioridade(cdfs[(ano, area, grupo_nivel(entrada.nivel))],
                                               cdfs[(ano, area, grupo_nivel(nivel_vizinho))])
    cenarios = [c for c in (proprio, vizinho, brasil) if c is not None and c.disponivel]
    if any(c.z is None for c in cenarios):
        avisos.append("Z-Score indefinido em grupo com todas as notas iguais.")
    if proprio.em_limite or (vizinho is not None and vizinho.em_limite):
        avisos.append("Nas pontas da distribuição a posição exata não é exibida, para proteger "
                      "participantes com notas muito altas ou muito baixas.")
    return Comparacao(entrada, proprio, brasil, vizinho, sentido, diferenca, superioridade, avisos)


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
    r = etapa_capital()
    print(f"[capital] {len(r['grupos']['publicados'])} grupos publicados, "
          f"{len(r['grupos']['suprimidos_abaixo_do_piso'])} suprimidos pelo piso, "
          f"{r['linhas']} linhas, {r['bytes']} bytes, {r['tempo_segundos']}s")
    print(f"[capital] maior divergência CDF x contagem direta: {r['verificacao']['maior_divergencia_pp']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
