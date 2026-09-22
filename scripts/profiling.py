#!/usr/bin/env python3
"""Profiling das quatro edicoes dos Microdados do ENEM (2019-2022).

Atende ao item 5 do Plano de Trabalho ("Profiling inicial"): volume
bruto/descompactado, linhas, colunas, tipos, cardinalidades, valores
ausentes, distribuicao das notas, presenca nas provas e variaveis
candidatas a recorte.

Cada edicao e materializada uma unica vez em uma tabela DuckDB temporaria;
o custo de parsear o CSV e pago uma vez e as demais consultas rodam sobre a
tabela. Nada e carregado na memoria do Python.

Saidas (em docs/profiling/):
  profiling_<ano>.json  - numeros brutos, para alimentar o contrato de dados
  README.md             - relatorio consolidado das quatro edicoes

Uso:
  ./.venv/bin/python scripts/profiling.py            # todas as edicoes
  ./.venv/bin/python scripts/profiling.py 2019 2020  # subconjunto
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent))

RAIZ = Path(__file__).resolve().parent.parent
RAW = RAIZ / "data" / "raw"
SAIDA = RAIZ / "docs" / "profiling"

ANOS_PADRAO = [2019, 2020, 2021, 2022]

from colunas import NOTAS, PISO_GRUPO, PRESENCA, RECORTE  # noqa: E402

# TP_PRESENCA: 0 = faltou, 1 = presente, 2 = eliminado (dicionario do INEP).
ROTULO_PRESENCA = {0: "faltou", 1: "presente", 2: "eliminado"}

PERCENTIS = [0.05, 0.25, 0.50, 0.75, 0.95]


def caminho_csv(ano: int) -> Path:
    return RAW / f"microdados_enem_{ano}" / "DADOS" / f"MICRODADOS_ENEM_{ano}.csv"


def caminho_zip(ano: int) -> Path:
    return RAW / f"microdados_enem_{ano}.zip"


def num(valor):
    """Converte Decimal/None do DuckDB em algo serializavel em JSON."""
    if valor is None:
        return None
    if isinstance(valor, (int, str)):
        return valor
    return float(valor)


def materializar(con: duckdb.DuckDBPyConnection, ano: int) -> float:
    """Le o CSV da edicao para a tabela `enem`. Devolve a duracao em segundos."""
    csv = caminho_csv(ano)
    if not csv.exists():
        raise FileNotFoundError(
            f"CSV da edicao {ano} nao encontrado em {csv}.\n"
            f"Extraia o zip antes: unzip -o {caminho_zip(ano)} 'DADOS/*' "
            f"-d {RAW / f'microdados_enem_{ano}'}/"
        )
    inicio = time.perf_counter()
    con.execute(
        """
        CREATE OR REPLACE TABLE enem AS
        SELECT * FROM read_csv(?, delim=';', header=true, encoding='latin-1')
        """,
        [str(csv)],
    )
    return time.perf_counter() - inicio


def perfil_colunas(con: duckdb.DuckDBPyConnection, total: int) -> list[dict]:
    """Tipo, ausencias e cardinalidade de cada uma das colunas."""
    colunas = con.execute("DESCRIBE enem").fetchall()
    nomes = [linha[0] for linha in colunas]
    tipos = {linha[0]: linha[1] for linha in colunas}

    # Um unico SELECT com 2 agregacoes por coluna: uma passagem pela tabela.
    #
    # A contagem de distintos e exata nas colunas categoricas, porque o numero
    # de categorias vira dominio no contrato de dados e um erro de +-1 ali
    # inventa ou apaga uma categoria. Nas demais (NU_INSCRICAO, TX_RESPOSTAS,
    # notas continuas) a cardinalidade so serve como ordem de grandeza e o
    # approx evita o custo de um COUNT(DISTINCT) exato sobre milhoes de valores.
    exatas = set(RECORTE) | set(PRESENCA)
    partes = []
    for i, nome in enumerate(nomes):
        partes.append(f'COUNT("{nome}") AS preenchidos_{i}')
        if nome in exatas:
            partes.append(f'COUNT(DISTINCT "{nome}") AS distintos_{i}')
        else:
            partes.append(f'approx_count_distinct("{nome}") AS distintos_{i}')
        # Peso da coluna no arquivo, para sustentar a selecao de colunas do
        # contrato com numero medido em vez de estimativa. E o tamanho do
        # valor em texto (strlen conta bytes UTF-8), que aproxima a pegada no CSV
        # de origem; nos poucos campos acentuados o UTF-8 fica alguns bytes
        # acima do latin-1 original.
        partes.append(f'SUM(strlen(CAST("{nome}" AS VARCHAR))) AS bytes_{i}')
    valores = con.execute(f"SELECT {', '.join(partes)} FROM enem").fetchone()

    perfil = []
    for i, nome in enumerate(nomes):
        preenchidos = valores[3 * i]
        distintos = valores[3 * i + 1]
        octetos = valores[3 * i + 2] or 0
        ausentes = total - preenchidos
        perfil.append(
            {
                "coluna": nome,
                "tipo": tipos[nome],
                "preenchidos": preenchidos,
                "ausentes": ausentes,
                "pct_ausentes": round(100 * ausentes / total, 2) if total else None,
                "distintos": distintos,
                "distintos_exato": nome in exatas,
                "bytes_texto": int(octetos),
            }
        )
    return perfil


def perfil_notas(con: duckdb.DuckDBPyConnection) -> list[dict]:
    """Estatistica descritiva das notas, restrita a quem tem nota registrada.

    Ausencia de nota e um estado distinto de nota zero (o plano exige essa
    separacao), entao os agregados abaixo ignoram nulos por construcao e o
    campo `n` informa sobre quantos participantes cada numero foi calculado.
    """
    resultado = []
    for coluna in NOTAS:
        quantis = ", ".join(
            f"quantile_cont(\"{coluna}\", {p}) AS p{int(p * 100):02d}" for p in PERCENTIS
        )
        linha = con.execute(
            f"""
            SELECT COUNT("{coluna}") AS n,
                   AVG("{coluna}") AS media,
                   stddev_samp("{coluna}") AS desvio,
                   MIN("{coluna}") AS minimo,
                   {quantis},
                   MAX("{coluna}") AS maximo,
                   SUM(CASE WHEN "{coluna}" = 0 THEN 1 ELSE 0 END) AS zeros
            FROM enem
            """
        ).fetchone()
        resultado.append(
            {
                "coluna": coluna,
                "n": linha[0],
                "media": num(linha[1]),
                "desvio_padrao": num(linha[2]),
                "minimo": num(linha[3]),
                "p05": num(linha[4]),
                "p25": num(linha[5]),
                "p50": num(linha[6]),
                "p75": num(linha[7]),
                "p95": num(linha[8]),
                "maximo": num(linha[9]),
                "zeros": linha[10],
            }
        )
    return resultado


def perfil_presenca(con: duckdb.DuckDBPyConnection, total: int) -> dict:
    """Distribuicao de presenca por area e o funil de elegibilidade."""
    por_area = {}
    for coluna in PRESENCA:
        linhas = con.execute(
            f'SELECT "{coluna}", COUNT(*) FROM enem GROUP BY 1 ORDER BY 1'
        ).fetchall()
        por_area[coluna] = [
            {
                "codigo": codigo,
                "rotulo": ROTULO_PRESENCA.get(codigo, "nao mapeado"),
                "n": n,
                "pct": round(100 * n / total, 2) if total else None,
            }
            for codigo, n in linhas
        ]

    condicao_todas = " AND ".join(f'"{c}" = 1' for c in PRESENCA)
    presentes_todas = con.execute(
        f"SELECT COUNT(*) FROM enem WHERE {condicao_todas}"
    ).fetchone()[0]
    treineiros = con.execute(
        "SELECT COUNT(*) FROM enem WHERE IN_TREINEIRO = 1"
    ).fetchone()[0]
    elegiveis = con.execute(
        f"SELECT COUNT(*) FROM enem WHERE {condicao_todas} AND IN_TREINEIRO = 0"
    ).fetchone()[0]

    return {
        "por_area": por_area,
        "funil": {
            "inscritos": total,
            "presentes_nas_quatro_areas": presentes_todas,
            "treineiros": treineiros,
            "presentes_nas_quatro_areas_sem_treineiros": elegiveis,
            "pct_presentes_nas_quatro_areas": round(100 * presentes_todas / total, 2)
            if total
            else None,
        },
    }


def perfil_recorte(con: duckdb.DuckDBPyConnection, total: int) -> dict:
    """Distribuicao das variaveis candidatas a recorte socioeconomico.

    Categorias com menos de PISO_GRUPO participantes saem com `n` e `pct`
    nulos e `suprimido: true` (LGPD, ver docs/privacidade.md). O codigo da
    categoria continua listado: o dicionario usa essa lista para cruzar
    dominio documentado x observado, e saber que o codigo ocorre nao
    expoe ninguem - a contagem pequena, sim.
    """
    resultado = {}
    for coluna in RECORTE:
        linhas = con.execute(
            f"""
            SELECT "{coluna}" AS categoria, COUNT(*) AS n
            FROM enem GROUP BY 1 ORDER BY 2 DESC LIMIT 30
            """
        ).fetchall()
        resultado[coluna] = [
            {"categoria": categoria, "n": None, "pct": None, "suprimido": True}
            if n < PISO_GRUPO
            else {
                "categoria": categoria,
                "n": n,
                "pct": round(100 * n / total, 2) if total else None,
            }
            for categoria, n in linhas
        ]
    return resultado


def perfil_ano(con: duckdb.DuckDBPyConnection, ano: int) -> dict:
    print(f"[{ano}] materializando CSV...", flush=True)
    duracao = materializar(con, ano)
    total = con.execute("SELECT COUNT(*) FROM enem").fetchone()[0]
    n_colunas = len(con.execute("DESCRIBE enem").fetchall())
    print(f"[{ano}] {total:,} linhas x {n_colunas} colunas em {duracao:.1f}s", flush=True)

    zip_ = caminho_zip(ano)
    perfil = {
        "ano": ano,
        "volume": {
            "zip_bytes": zip_.stat().st_size if zip_.exists() else None,
            "csv_bytes": caminho_csv(ano).stat().st_size,
            "linhas": total,
            "colunas": n_colunas,
            "segundos_leitura_csv": round(duracao, 1),
        },
    }

    print(f"[{ano}] colunas (ausencias e cardinalidade)...", flush=True)
    perfil["colunas"] = perfil_colunas(con, total)
    print(f"[{ano}] notas...", flush=True)
    perfil["notas"] = perfil_notas(con)
    print(f"[{ano}] presenca...", flush=True)
    perfil["presenca"] = perfil_presenca(con, total)
    print(f"[{ano}] variaveis de recorte...", flush=True)
    perfil["recorte"] = perfil_recorte(con, total)
    return perfil


# ---------------------------------------------------------------- relatorio


def gb(n_bytes: int | None) -> str:
    if not n_bytes:
        return "-"
    return f"{n_bytes / 1024 ** 3:.2f} GB"


def milhar(n) -> str:
    return f"{n:,}".replace(",", ".") if isinstance(n, int) else "-"


def gerar_relatorio(perfis: list[dict]) -> str:
    perfis = sorted(perfis, key=lambda p: p["ano"])
    anos = [p["ano"] for p in perfis]
    L = []

    L.append("# Profiling dos Microdados do ENEM (2019-2022)")
    L.append("")
    L.append(
        "Gerado por `scripts/profiling.py`. Numeros brutos em "
        "`profiling_<ano>.json`. Atende ao item 5 do Plano de Trabalho."
    )
    L.append("")

    L.append("## 1. Volumetria")
    L.append("")
    L.append("| Edicao | ZIP | CSV | Linhas | Colunas | Leitura |")
    L.append("| --- | --- | --- | --- | --- | --- |")
    for p in perfis:
        v = p["volume"]
        L.append(
            f"| {p['ano']} | {gb(v['zip_bytes'])} | {gb(v['csv_bytes'])} | "
            f"{milhar(v['linhas'])} | {v['colunas']} | {v['segundos_leitura_csv']}s |"
        )
    L.append("")

    L.append("## 2. Funil de presenca e elegibilidade")
    L.append("")
    L.append(
        "`presentes nas 4` = participantes com `TP_PRESENCA_* = 1` nas quatro "
        "areas. A ultima coluna remove os treineiros e e a populacao candidata "
        "a base de comparacao do produto."
    )
    L.append("")
    L.append("| Edicao | Inscritos | Presentes nas 4 | % | Treineiros | Elegiveis |")
    L.append("| --- | --- | --- | --- | --- | --- |")
    for p in perfis:
        f = p["presenca"]["funil"]
        L.append(
            f"| {p['ano']} | {milhar(f['inscritos'])} | "
            f"{milhar(f['presentes_nas_quatro_areas'])} | "
            f"{f['pct_presentes_nas_quatro_areas']}% | "
            f"{milhar(f['treineiros'])} | "
            f"{milhar(f['presentes_nas_quatro_areas_sem_treineiros'])} |"
        )
    L.append("")

    L.append("## 3. Notas")
    L.append("")
    L.append(
        "Calculado sobre quem tem nota registrada (`n`). Nota ausente e nota "
        "zero sao estados distintos: a coluna `zeros` conta apenas os zeros."
    )
    L.append("")
    for coluna in NOTAS:
        L.append(f"### {coluna}")
        L.append("")
        L.append("| Edicao | n | Media | Desvio | p05 | p25 | Mediana | p75 | p95 | Max | Zeros |")
        L.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        for p in perfis:
            e = next(x for x in p["notas"] if x["coluna"] == coluna)

            def f1(chave):
                valor = e[chave]
                return f"{valor:.1f}" if isinstance(valor, float) else "-"

            L.append(
                f"| {p['ano']} | {milhar(e['n'])} | {f1('media')} | {f1('desvio_padrao')} | "
                f"{f1('p05')} | {f1('p25')} | {f1('p50')} | {f1('p75')} | {f1('p95')} | "
                f"{f1('maximo')} | {milhar(e['zeros'])} |"
            )
        L.append("")

    L.append("## 4. Variaveis candidatas a recorte")
    L.append("")
    L.append(
        "Cardinalidade e percentual de ausencia por edicao. Cardinalidade "
        "estavel entre edicoes e pre-requisito para comparar os quatro anos "
        "sem reescrever as categorias."
    )
    L.append("")
    colunas_dist = " | ".join(f"{a} cat." for a in anos)
    colunas_aus = " | ".join(f"{a} aus." for a in anos)
    L.append(f"| Variavel | {colunas_dist} | {colunas_aus} |")
    L.append("| --- |" + " --- |" * (2 * len(anos)))
    for coluna in RECORTE:
        distintos, ausentes = [], []
        for p in perfis:
            achado = next((c for c in p["colunas"] if c["coluna"] == coluna), None)
            distintos.append(str(achado["distintos"]) if achado else "-")
            ausentes.append(f"{achado['pct_ausentes']}%" if achado else "-")
        L.append(f"| `{coluna}` | " + " | ".join(distintos) + " | " + " | ".join(ausentes) + " |")
    L.append("")
    L.append(
        "`cat.` = categorias distintas (contagem exata, nulos excluidos); "
        "`aus.` = percentual de ausencia."
    )
    L.append("")

    L.append("## 5. Colunas com ausencia relevante")
    L.append("")
    L.append("Colunas com mais de 10% de ausencia em pelo menos uma edicao.")
    L.append("")
    todas = [c["coluna"] for c in perfis[0]["colunas"]]
    relevantes = []
    for coluna in todas:
        pcts = []
        for p in perfis:
            achado = next((c for c in p["colunas"] if c["coluna"] == coluna), None)
            pcts.append(achado["pct_ausentes"] if achado else None)
        if any(v is not None and v > 10 for v in pcts):
            relevantes.append((coluna, pcts))
    L.append("| Coluna | " + " | ".join(str(a) for a in anos) + " |")
    L.append("| --- |" + " --- |" * len(anos))
    for coluna, pcts in relevantes:
        L.append(
            f"| `{coluna}` | "
            + " | ".join(f"{v}%" if v is not None else "-" for v in pcts)
            + " |"
        )
    L.append("")

    return "\n".join(L)


def main() -> int:
    anos = [int(a) for a in sys.argv[1:]] or ANOS_PADRAO
    SAIDA.mkdir(parents=True, exist_ok=True)

    temporario = tempfile.mkdtemp(prefix="profiling_enem_")
    perfis = []
    try:
        con = duckdb.connect(os.path.join(temporario, "profiling.duckdb"))
        con.execute("SET memory_limit='4GB'")
        con.execute("SET threads=6")
        con.execute(f"SET temp_directory='{temporario}'")

        for ano in anos:
            perfis.append(perfil_ano(con, ano))
            destino = SAIDA / f"profiling_{ano}.json"
            destino.write_text(
                json.dumps(perfis[-1], indent=2, ensure_ascii=False), encoding="utf-8"
            )
            print(f"[{ano}] -> {destino.relative_to(RAIZ)}", flush=True)
        con.close()
    finally:
        shutil.rmtree(temporario, ignore_errors=True)

    # O relatorio consolidado so faz sentido com as quatro edicoes lado a lado;
    # numa execucao parcial, reaproveita os JSONs ja gravados.
    todos = []
    for ano in ANOS_PADRAO:
        arquivo = SAIDA / f"profiling_{ano}.json"
        if arquivo.exists():
            todos.append(json.loads(arquivo.read_text(encoding="utf-8")))
    if todos:
        relatorio = SAIDA / "README.md"
        relatorio.write_text(gerar_relatorio(todos), encoding="utf-8")
        print(f"relatorio -> {relatorio.relative_to(RAIZ)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
