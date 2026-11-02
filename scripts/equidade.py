#!/usr/bin/env python3
"""Módulo Equidade socioeconômica do Radar ENEM.

Autor: Samuel Silva de Rezende. Regras registradas em docs/decisoes (DL-03).

Pergunta do módulo: a mesma nota coloca o participante em posições
diferentes conforme o grupo de renda com que ele é comparado? Para uma nota
informada, o módulo calcula dois cenários (Plano de Trabalho, Diretrizes):

  1. Posição real: entre participantes da mesma faixa de renda familiar (Q006).
  2. Posição simulada: entre participantes de escola privada com renda
     familiar acima de 10 salários mínimos (grupo de contraste).

O arquivo tem três partes:

  - Regras de negócio: faixas de Q006, grupo de contraste, validação da entrada.
  - Agregação offline: lê a TRUSTED e grava data/analytics/dist_equidade.parquet
    (CDF exata por edição, área e grupo, com piso de PISO_GRUPO participantes).
  - Comparação: aplica o motor estatístico v1 (scripts/estatistica.py) aos
    dois cenários.

Nenhuma função daqui devolve registro individual. O artefato contém
frequências por nota e fica restrito ao backend, como o dist_exata.parquet
(ADR-001).

Uso (depois de scripts/etl.py ter gerado a TRUSTED):
  ./.venv/bin/python scripts/equidade.py
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
    percentil_exato_acumulado,
    prob_superioridade,
    resumo,
    z_score,
)

RAIZ = Path(__file__).resolve().parent.parent
TRUSTED = RAIZ / "data" / "trusted" / "enem"
ANALYTICS = RAIZ / "data" / "analytics"
DIST_EQUIDADE = ANALYTICS / "dist_equidade.parquet"
MANIFESTO_EQUIDADE = ANALYTICS / "_manifesto_equidade.json"
DICIONARIO = RAIZ / "docs" / "dicionario"

RECORTE = "renda"
AREAS = {
    "cn": "Ciências da Natureza",
    "ch": "Ciências Humanas",
    "lc": "Linguagens e Códigos",
    "mt": "Matemática",
    "redacao": "Redação",
}

# ============================================================ REGRAS (DL-03)


@dataclass(frozen=True)
class Faixa:
    codigo: str
    rotulo: str
    alternativas: tuple[str, ...]
    sm_min: float  # renda maior que sm_min salários mínimos (R1: a partir de 0)
    sm_max: float | None  # até sm_max salários mínimos; None = sem teto


FAIXAS: tuple[Faixa, ...] = (
    Faixa("R1", "Até 1 salário mínimo", ("A", "B"), 0, 1),
    Faixa("R2", "Mais de 1 até 2 salários mínimos", ("C", "D"), 1, 2),
    Faixa("R3", "Mais de 2 até 3 salários mínimos", ("E", "F"), 2, 3),
    Faixa("R4", "Mais de 3 até 5 salários mínimos", ("G", "H"), 3, 5),
    Faixa("R5", "Mais de 5 até 10 salários mínimos", ("I", "J", "K", "L", "M"), 5, 10),
    Faixa("R6", "Mais de 10 salários mínimos", ("N", "O", "P", "Q"), 10, None),
)
FAIXA_POR_CODIGO = {f.codigo: f for f in FAIXAS}
FAIXA_DA_ALTERNATIVA = {alt: f.codigo for f in FAIXAS for alt in f.alternativas}
ALTERNATIVAS_Q006 = tuple(sorted(FAIXA_DA_ALTERNATIVA))  # "A" .. "Q"

CONTRASTE = "CONTRASTE"
CONTRASTE_ROTULO = "Escola privada e renda familiar acima de 10 salários mínimos"
CONTRASTE_TIPO_ESCOLA = 3  # TP_ESCOLA: 1 não respondeu, 2 pública, 3 privada
CONTRASTE_FAIXA = "R6"

GRUPOS = tuple(f.codigo for f in FAIXAS) + (CONTRASTE,)


class EntradaInvalida(ValueError):
    """Entrada do usuário fora das regras. A mensagem é exibida na interface."""


def faixa_de_q006(alternativa: object) -> str | None:
    """Faixa (R1..R6) da alternativa da Q006, ou None quando a resposta falta.

    Aceita espaços e letra minúscula (" c " vira "C"). Valor fora de A–Q
    levanta EntradaInvalida: não existe faixa "mais próxima" para um código
    desconhecido.
    """
    if alternativa is None:
        return None
    if not isinstance(alternativa, str):
        raise EntradaInvalida("A renda familiar deve ser uma das alternativas da Q006 (A a Q).")
    codigo = alternativa.strip().upper()
    if not codigo:
        return None
    if codigo not in FAIXA_DA_ALTERNATIVA:
        raise EntradaInvalida(f"Alternativa de renda '{alternativa}' não existe na Q006 (A a Q).")
    return FAIXA_DA_ALTERNATIVA[codigo]


def opcoes_q006(ano: int, dicionario: Path = DICIONARIO) -> list[tuple[str, str]]:
    """Alternativas da Q006 com o texto oficial da edição: [(código, texto)].

    O texto vem do dicionário do INEP versionado em docs/dicionario, então a
    pessoa escolhe a mesma frase que leu no questionário, em reais do ano.
    """
    arquivo = dicionario / f"dicionario_{ano}.json"
    if not arquivo.exists():
        raise EntradaInvalida(f"Edição {ano} sem dicionário da Q006.")
    dados = json.loads(arquivo.read_text(encoding="utf-8"))
    categorias = _procurar_variavel(dados, "Q006")
    if categorias is None:
        raise EntradaInvalida(f"Dicionário {ano} sem a variável Q006.")
    faltando = set(ALTERNATIVAS_Q006) - set(categorias)
    if faltando:
        raise EntradaInvalida(f"Dicionário {ano} sem as alternativas {sorted(faltando)} da Q006.")
    return [(c, categorias[c].strip().rstrip(".")) for c in ALTERNATIVAS_Q006]


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


@dataclass(frozen=True)
class Entrada:
    ano: int
    area: str
    nota: float
    alternativa: str
    faixa: str


def validar_entrada(
    ano: object, area: object, nota: object, alternativa: object, anos_disponiveis
) -> Entrada:
    """Confere a entrada do usuário e devolve a versão normalizada.

    Regras:
      - edição entre as disponíveis no artefato;
      - área entre cn, ch, lc, mt e redacao;
      - nota numérica, finita, entre 0 e 1000; nas provas objetivas com no
        máximo uma casa decimal (como o INEP publica); na redação, múltipla
        de 20 (média de duas correções em passos de 40);
      - renda: alternativa da Q006 de A a Q, obrigatória neste módulo.
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
    faixa = faixa_de_q006(alternativa)
    if faixa is None:
        raise EntradaInvalida("Informe a renda familiar para comparar por faixa de renda.")
    return Entrada(ano, area, round(nota, 1), alternativa.strip().upper(), faixa)


# ====================================================== AGREGAÇÃO OFFLINE


def sql_contagens(fonte: str, area: str) -> str:
    """SELECT (ano, grupo, nota, n) da área, para as seis faixas e o contraste.

    Um participante entra na sua faixa de renda e, se for de escola privada
    com renda R6, também no contraste. Fica de fora quem não é elegível, não
    tem nota na área ou não tem Q006 válida (DL-03, item 5).
    """
    casos = " ".join(f"WHEN '{alt}' THEN '{faixa}'" for alt, faixa in FAIXA_DA_ALTERNATIVA.items())
    alternativas_r6 = ", ".join(f"'{a}'" for a in FAIXA_POR_CODIGO[CONTRASTE_FAIXA].alternativas)
    return f"""
        WITH base AS (
            SELECT ano, nota_{area} AS nota, tipo_escola,
                   CASE renda_familiar {casos} END AS faixa,
                   renda_familiar IN ({alternativas_r6}) AS renda_r6
            FROM {fonte}
            WHERE elegivel AND nota_{area} IS NOT NULL
        )
        SELECT ano, faixa AS grupo, nota, count(*) AS n
        FROM base WHERE faixa IS NOT NULL GROUP BY 1, 2, 3
        UNION ALL
        SELECT ano, '{CONTRASTE}' AS grupo, nota, count(*) AS n
        FROM base WHERE renda_r6 AND tipo_escola = {CONTRASTE_TIPO_ESCOLA} GROUP BY 1, 2, 3
        ORDER BY 1, 2, 3
    """


def gerar_linhas(con, fonte: str, piso: int = PISO_GRUPO) -> tuple[list[tuple], dict]:
    """Linhas do artefato e funil do módulo, aplicando o piso por grupo.

    Devolve (linhas, funil). Cada linha é (ano, area, recorte, grupo, nota,
    n, abaixo, total). Grupos com total < piso não geram linha nenhuma; o
    funil só registra que foram suprimidos, sem a contagem.
    """
    por_grupo: dict[tuple[int, str, str], list[tuple[float, int]]] = {}
    for area in AREAS:
        for ano, grupo, nota, n in con.execute(sql_contagens(fonte, area)).fetchall():
            por_grupo.setdefault((int(ano), area, grupo), []).append((float(nota), int(n)))

    linhas, suprimidos, publicados = [], [], {}
    for (ano, area, grupo), contagens in sorted(por_grupo.items()):
        total = sum(n for _, n in contagens)
        if total < piso:
            suprimidos.append(f"{ano}/{area}/{grupo}")
            continue
        acumulada = construir_acumulada(contagens)
        if acumulada[-1][1] + acumulada[-1][2] != total:
            raise AssertionError(f"{ano}/{area}/{grupo}: CDF não conserva contagens")
        publicados[f"{ano}/{area}/{grupo}"] = total
        linhas.extend((ano, area, RECORTE, grupo, nota, n, abaixo, total) for nota, n, abaixo in acumulada)
    return linhas, {"publicados": publicados, "suprimidos_abaixo_do_piso": suprimidos}


def auditar_q006(con, fonte: str) -> dict:
    """Elegíveis por situação da Q006, por edição (só para o manifesto local)."""
    validas = ", ".join(f"'{a}'" for a in ALTERNATIVAS_Q006)
    saida = {}
    for ano, total, ausente, invalida in con.execute(
        f"""SELECT ano, count(*),
                   count(*) FILTER (renda_familiar IS NULL OR trim(renda_familiar) = ''),
                   count(*) FILTER (trim(renda_familiar) <> '' AND renda_familiar NOT IN ({validas}))
            FROM {fonte} WHERE elegivel GROUP BY 1 ORDER BY 1"""
    ).fetchall():
        saida[str(ano)] = {"elegiveis": total, "q006_ausente": ausente, "q006_invalida": invalida}
    return saida


def percentil_direto(con, fonte: str, ano: int, area: str, grupo: str, nota: float) -> float:
    """Percentil por contagem direta na TRUSTED, sem passar pela CDF."""
    if grupo == CONTRASTE:
        alts = FAIXA_POR_CODIGO[CONTRASTE_FAIXA].alternativas
        filtro = f"renda_familiar IN ({', '.join(repr(a) for a in alts)}) AND tipo_escola = {CONTRASTE_TIPO_ESCOLA}"
    else:
        filtro = f"renda_familiar IN ({', '.join(repr(a) for a in FAIXA_POR_CODIGO[grupo].alternativas)})"
    total, abaixo, iguais = con.execute(
        f"""SELECT count(*), count(*) FILTER (nota_{area} < ?), count(*) FILTER (nota_{area} = ?)
            FROM {fonte} WHERE ano = ? AND elegivel AND nota_{area} IS NOT NULL AND {filtro}""",
        [nota, nota, ano],
    ).fetchone()
    return (abaixo + iguais / 2) / total * 100


def etapa_equidade(trusted: Path = TRUSTED, destino: Path = DIST_EQUIDADE,
                   manifesto: Path = MANIFESTO_EQUIDADE, piso: int = PISO_GRUPO) -> dict:
    """TRUSTED -> dist_equidade.parquet, conferido contra contagem direta.

    Grava num temporário e só troca o arquivo final depois das conferências;
    falha no meio não deixa artefato parcial publicado.
    """
    import duckdb

    fonte = f"read_parquet('{trusted}/*/*.parquet', hive_partitioning=true)"
    con = duckdb.connect()
    inicio = time.perf_counter()
    try:
        linhas, funil = gerar_linhas(con, fonte, piso)
        if not linhas:
            raise ValueError("nenhum grupo de renda atingiu o piso; publicação abortada")
        destino.parent.mkdir(parents=True, exist_ok=True)
        temporario = destino.with_name(f".{destino.name}.tmp")
        try:
            con.execute("CREATE TEMP TABLE eq (ano BIGINT, area VARCHAR, recorte VARCHAR, grupo VARCHAR,"
                        " nota DOUBLE, n BIGINT, abaixo BIGINT, total BIGINT)")
            con.executemany("INSERT INTO eq VALUES (?, ?, ?, ?, ?, ?, ?, ?)", linhas)
            con.execute(f"COPY eq TO '{temporario}' (FORMAT parquet, COMPRESSION zstd)")
            cdfs = carregar(temporario)
            maior = 0.0
            for (ano, area, grupo), cdf in cdfs.items():
                notas = [item[0] for item in cdf]
                for nota in {notas[0], notas[-1], notas[len(notas) // 2], notas[0] - 1, notas[-1] + 1,
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
            "regras": "docs/decisoes/README.md#dl-03",
            "piso": piso,
            "grupos": funil,
            "q006": auditar_q006(con, fonte),
            "verificacao": {"metodo": "percentil da CDF x contagem direta na TRUSTED",
                            "maior_divergencia_pp": maior},
            "linhas": len(linhas),
            "bytes": destino.stat().st_size,
            "tempo_segundos": round(time.perf_counter() - inicio, 3),
        }
        manifesto.write_text(json.dumps(resultado, indent=2, ensure_ascii=False), encoding="utf-8")
        return resultado
    finally:
        con.close()


def carregar(arquivo: Path = DIST_EQUIDADE) -> dict[tuple[int, str, str], list[tuple[float, int, int]]]:
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
    percentil: float = 0.0
    media: float = 0.0
    mediana: float = 0.0
    desvio: float = 0.0
    z: float | None = None


@dataclass(frozen=True)
class Comparacao:
    entrada: Entrada
    real: Cenario
    simulado: Cenario
    diferenca_pp: float | None = None  # percentil real - percentil simulado
    prob_superioridade: float | None = None  # P(faixa > contraste) + 0,5 P(=)
    avisos: list[str] = field(default_factory=list)


def _cenario(cdfs, ano: int, area: str, grupo: str, rotulo: str, nota: float) -> Cenario:
    cdf = cdfs.get((ano, area, grupo))
    if not cdf:
        return Cenario(grupo, rotulo, False,
                       f"grupo insuficiente: menos de {PISO_GRUPO} participantes nesta edição e área")
    medidas = resumo(cdf)
    try:
        z = z_score(cdf, nota)
    except ValueError:  # desvio zero: todas as notas iguais
        z = None
    return Cenario(grupo, rotulo, True, n=medidas["N"], percentil=percentil_exato_acumulado(cdf, nota),
                   media=medidas["media"], mediana=medidas["mediana"], desvio=medidas["desvio"], z=z)


def comparar(cdfs, entrada: Entrada) -> Comparacao:
    """Os dois cenários do módulo para uma entrada já validada.

    Nunca levanta exceção por falta de grupo: o cenário sem dados volta com
    disponivel=False e o motivo, e as medidas entre grupos ficam None.
    """
    ano, area, nota = entrada.ano, entrada.area, entrada.nota
    real = _cenario(cdfs, ano, area, entrada.faixa, FAIXA_POR_CODIGO[entrada.faixa].rotulo, nota)
    simulado = _cenario(cdfs, ano, area, CONTRASTE, CONTRASTE_ROTULO, nota)
    avisos = []
    if entrada.faixa == CONTRASTE_FAIXA:
        avisos.append("Sua faixa de renda é a mesma do grupo de contraste; o contraste "
                      "restringe a comparação a quem declarou escola privada.")
    if real.z is None and real.disponivel or simulado.z is None and simulado.disponivel:
        avisos.append("Z-Score indefinido em grupo com todas as notas iguais.")
    diferenca = superioridade = None
    if real.disponivel and simulado.disponivel:
        diferenca = real.percentil - simulado.percentil
        superioridade = prob_superioridade(cdfs[(ano, area, entrada.faixa)], cdfs[(ano, area, CONTRASTE)])
    return Comparacao(entrada, real, simulado, diferenca, superioridade, avisos)


# ======================================================= EXIBIÇÃO (DL-01)


def formatar_percentil(p: float) -> str:
    return f"{p:.1f}".replace(".", ",") + "%"


def formatar_nota(nota: float) -> str:
    return f"{nota:.1f}".replace(".", ",")


def formatar_z(z: float | None) -> str:
    return "indefinido" if z is None else f"{z:+.2f}".replace(".", ",")


def main() -> int:
    if not TRUSTED.exists():
        print(f"TRUSTED não encontrada em {TRUSTED}. Rode antes: scripts/etl.py", file=sys.stderr)
        return 1
    r = etapa_equidade()
    print(f"[equidade] {len(r['grupos']['publicados'])} grupos publicados, "
          f"{len(r['grupos']['suprimidos_abaixo_do_piso'])} suprimidos pelo piso, "
          f"{r['linhas']} linhas, {r['bytes']} bytes, {r['tempo_segundos']}s")
    print(f"[equidade] maior divergência CDF x contagem direta: {r['verificacao']['maior_divergencia_pp']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
