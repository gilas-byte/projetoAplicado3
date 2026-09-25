#!/usr/bin/env python3
"""Benchmark das alternativas de stack do Radar ENEM.

Atende aos objetivos 2 e 4 do Plano de Trabalho: comparar as tecnologias
candidatas com numeros medidos (tempo, pico de memoria, tamanho em disco e
latencia de consulta) em vez de defender a stack so com documentacao.

Etapas:
  etl        CSV RAW -> Parquet ZSTD com as 58 colunas mantidas pelo contrato,
             em cada motor (pandas, pandas+pyarrow, Polars, DuckDB, Spark).
  codecs     Tamanho e custo de leitura do Parquet por codec de compressao.
  consultas  As consultas representativas do produto, em pandas, Polars e
             DuckDB, com o orcamento de runtime simulado (2 nucleos).
  frontend   Custo fixo de memoria e tempo de subida de Streamlit, Dash,
             Shiny para Python e FastAPI (backend de um frontend React).

Cada medicao roda em um processo filho isolado: o pico de memoria e o do
processo filho e de seus descendentes (a JVM do Spark, por exemplo), sem
contaminar uma medicao com o que a anterior deixou alocado.

Nenhuma contagem de participantes sai deste script. As consultas gravam o
resultado so em data/bench/ (ignorado pelo git) para conferir que os motores
concordam; em docs/stack/ vao apenas tempos, memorias, tamanhos e o veredito
"confere/diverge" (ver docs/privacidade.md).

Saidas:
  docs/stack/benchmark.json  - numeros brutos de todas as etapas executadas
  docs/stack/benchmark.md    - tabelas geradas a partir do JSON

Uso:
  ./.venv/bin/python scripts/benchmark_stack.py                  # tudo
  ./.venv/bin/python scripts/benchmark_stack.py --etapas consultas
  ./.venv/bin/python scripts/benchmark_stack.py --etapas etl --anos 2019 \\
      --motores polars duckdb
  ./.venv/bin/python scripts/benchmark_stack.py --relatorio      # so o .md

Dependencias extras (nao fazem parte do pipeline): requirements-benchmark.txt.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import math
import os
import platform
import shutil
import socket
import statistics
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from colunas import ANOS, PISO_GRUPO, mantidas  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
RAW = RAIZ / "data" / "raw"
BENCH = RAIZ / "data" / "bench"
TRUSTED = BENCH / "trusted"
ANALYTICS = BENCH / "analytics"
SAIDA = RAIZ / "docs" / "stack"

MOTORES_ETL = ["pandas", "pandas_pyarrow", "polars", "duckdb", "spark"]
MOTORES_CONSULTA = ["pandas", "polars", "duckdb"]
FRONTENDS = ["streamlit", "dash", "shiny", "fastapi"]
CODECS = ["uncompressed", "snappy", "gzip", "zstd"]

# Orcamento do runtime web (plano, secao 4: hospedagem gratuita com cerca de
# 1 GB de RAM). As consultas rodam presas a 2 nucleos para simular a maquina
# de producao; a memoria nao e limitada a forca (o limite de espaco de
# enderecamento quebra motores que reservam memoria virtual), e sim medida e
# comparada com o orcamento.
NUCLEOS_RUNTIME = 2
ORCAMENTO_RUNTIME_MB = 1024

REPETICOES_CONSULTA = 5
AMOSTRAGEM_S = 0.02

# Parametros das consultas representativas. A nota e a de um usuario
# hipotetico; a edicao e a mais recente do recorte.
ANO_CONSULTA = 2022
NOTA_USUARIO = 650.0

TEXTO = {"TP_SEXO", "SG_UF_ESC", "SG_UF_PROVA", "NO_MUNICIPIO_PROVA"} | {
    f"Q{i:03d}" for i in range(1, 26) if i != 5
}


def tipo_logico(coluna: str) -> str:
    """Tipo de cada coluna mantida, igual nas quatro edicoes (ver profiling)."""
    if coluna in TEXTO:
        return "texto"
    if coluna.startswith("NU_NOTA_"):
        return "real"
    return "inteiro"


COLUNAS = mantidas()


def caminho_csv(ano: int) -> Path:
    return RAW / f"microdados_enem_{ano}" / "DADOS" / f"MICRODADOS_ENEM_{ano}.csv"


def trusted(ano: int) -> Path:
    return TRUSTED / f"enem_{ano}.parquet"


DIST_NOTAS = ANALYTICS / "dist_notas.parquet"


# =================================================================== medicao


def rss_kb(pid: int | str, campo: str = "VmRSS") -> int:
    try:
        with open(f"/proc/{pid}/status") as f:
            for linha in f:
                if linha.startswith(f"{campo}:"):
                    return int(linha.split()[1])
    except (FileNotFoundError, ProcessLookupError, PermissionError):
        pass
    return 0


def descendentes(raiz: int) -> list[int]:
    filhos: dict[int, list[int]] = {}
    for entrada in os.listdir("/proc"):
        if not entrada.isdigit():
            continue
        try:
            with open(f"/proc/{entrada}/stat") as f:
                # O nome do processo vem entre parenteses e pode ter espacos.
                ppid = int(f.read().rsplit(")", 1)[1].split()[1])
        except (FileNotFoundError, ProcessLookupError, IndexError, ValueError):
            continue
        filhos.setdefault(ppid, []).append(int(entrada))
    pids, pilha = [], [raiz]
    while pilha:
        pid = pilha.pop()
        pids.append(pid)
        pilha.extend(filhos.get(pid, []))
    return pids


def rss_arvore_mb(pid: int) -> float:
    return sum(rss_kb(p) for p in descendentes(pid)) / 1024


def _executou(pid: int) -> bool:
    """O filho ja trocou de imagem (exec) e esta rodando este script como `_filho`."""
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            return b"\0_filho\0" in f.read()
    except (FileNotFoundError, ProcessLookupError):
        return False


def executar_filho(tarefa: str, parametros: dict, env: dict | None = None) -> dict:
    """Roda `tarefa` em um processo filho e mede tempo e pico de memoria.

    O pico e o maior entre o VmHWM que o filho le de si mesmo ao terminar
    (exato, mas so do proprio processo) e a soma amostrada da arvore de
    processos (pega a JVM do Spark, mas pode perder picos mais curtos que o
    intervalo de amostragem). O ru_maxrss do wait4 nao serve: no Linux ele
    herda o pico do processo pai no momento do fork. Pelo mesmo motivo a
    amostragem so comeca depois do exec: antes dele o filho ainda compartilha
    a memoria do pai, que pode estar grande (o preparo roda DuckDB aqui).
    """
    BENCH.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "r", suffix=".json", dir=BENCH, delete=False
    ) as saida:
        caminho_saida = saida.name
    log = BENCH / "logs" / f"{tarefa}_{parametros.get('motor', '')}.log"
    log.parent.mkdir(parents=True, exist_ok=True)

    comando = [sys.executable, __file__, "_filho", tarefa, json.dumps(parametros), caminho_saida]
    inicio = time.perf_counter()
    with open(log, "a") as f:
        f.write(f"\n=== {time.strftime('%F %T')} {parametros}\n")
        f.flush()
        proc = subprocess.Popen(comando, stdout=f, stderr=subprocess.STDOUT, env=env)
        pico_amostrado = 0.0
        apos_exec = False
        while True:
            pid, status, _ = os.wait4(proc.pid, os.WNOHANG)
            if pid:
                break
            apos_exec = apos_exec or _executou(proc.pid)
            if apos_exec:
                pico_amostrado = max(pico_amostrado, rss_arvore_mb(proc.pid))
            time.sleep(AMOSTRAGEM_S)
    duracao = time.perf_counter() - inicio

    codigo = os.waitstatus_to_exitcode(status)
    try:
        resultado = json.loads(Path(caminho_saida).read_text() or "{}")
    finally:
        os.unlink(caminho_saida)
    if codigo != 0:
        return {"erro": f"saida {codigo}, ver {log.relative_to(RAIZ)}"}

    resultado["duracao_processo_s"] = round(duracao, 2)
    resultado["pico_mb"] = round(max(resultado.pop("hwm_mb"), pico_amostrado), 1)
    return resultado


def aquecer_cache(arquivo: Path) -> None:
    """Le o arquivo uma vez para que todos os motores partam do cache quente.

    Sem acesso root nao da para esvaziar o cache de paginas entre execucoes;
    a alternativa justa e o oposto: garantir que ninguem pague a leitura fria.
    """
    with open(arquivo, "rb") as f:
        while f.read(64 * 1024 * 1024):
            pass


# ======================================================================= etl


def etl_pandas(csv: Path, destino: Path, motor_csv: str) -> None:
    import pandas as pd

    tipos = {"texto": "string", "real": "float64", "inteiro": "Int64"}
    df = pd.read_csv(
        csv,
        sep=";",
        encoding="latin-1",
        usecols=COLUNAS,
        dtype={c: tipos[tipo_logico(c)] for c in COLUNAS},
        engine=motor_csv,
    )
    df[COLUNAS].to_parquet(destino, compression="zstd", index=False)


def etl_polars(csv: Path, destino: Path) -> None:
    import polars as pl

    # O leitor de CSV do Polars so aceita UTF-8 em modo lazy; o INEP publica
    # em latin-1. `utf8-lossy` trocaria acentos por U+FFFD nos nomes de
    # municipio, entao o arquivo e transcodificado antes, e esse custo entra
    # na medicao.
    utf8 = destino.with_suffix(".utf8.csv")
    try:
        with open(utf8, "wb") as f:
            subprocess.run(["iconv", "-f", "latin1", "-t", "utf-8", str(csv)], stdout=f, check=True)
        tipos = {"texto": pl.String, "real": pl.Float64, "inteiro": pl.Int64}
        (
            pl.scan_csv(
                utf8,
                separator=";",
                schema_overrides={c: tipos[tipo_logico(c)] for c in COLUNAS},
                infer_schema_length=10_000,
            )
            .select(COLUNAS)
            .sink_parquet(destino, compression="zstd")
        )
    finally:
        utf8.unlink(missing_ok=True)


def etl_duckdb(csv: Path, destino: Path) -> None:
    import duckdb

    tipos = {"texto": "VARCHAR", "real": "DOUBLE", "inteiro": "BIGINT"}
    mapa = ", ".join(f"'{c}': '{tipos[tipo_logico(c)]}'" for c in COLUNAS)
    selecao = ", ".join(f'"{c}"' for c in COLUNAS)
    con = duckdb.connect()
    con.execute(f"SET temp_directory='{BENCH / 'tmp_duckdb'}'")
    con.execute(
        f"""
        COPY (
            SELECT {selecao}
            FROM read_csv('{csv}', delim=';', header=true, encoding='latin-1',
                          types={{{mapa}}})
        ) TO '{destino}' (FORMAT parquet, COMPRESSION zstd)
        """
    )
    con.close()


def etl_spark(csv: Path, destino: Path) -> None:
    from pyspark.sql import SparkSession
    from pyspark.sql import functions as F

    spark = (
        SparkSession.builder.master("local[*]")
        .appName("radar-enem-benchmark")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.shuffle.partitions", "8")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("ERROR")
    tipos = {"texto": "string", "real": "double", "inteiro": "bigint"}
    df = spark.read.csv(str(csv), sep=";", header=True, encoding="ISO-8859-1")
    (
        df.select([F.col(c).cast(tipos[tipo_logico(c)]) for c in COLUNAS])
        .write.mode("overwrite")
        .option("compression", "zstd")
        .parquet(str(destino))
    )
    spark.stop()


def filho_etl(p: dict) -> dict:
    csv, destino = caminho_csv(p["ano"]), Path(p["destino"])
    inicio = time.perf_counter()
    if p["motor"] == "pandas":
        etl_pandas(csv, destino, "c")
    elif p["motor"] == "pandas_pyarrow":
        etl_pandas(csv, destino, "pyarrow")
    elif p["motor"] == "polars":
        etl_polars(csv, destino)
    elif p["motor"] == "duckdb":
        etl_duckdb(csv, destino)
    elif p["motor"] == "spark":
        etl_spark(csv, destino)
    return {"duracao_s": round(time.perf_counter() - inicio, 2)}


def tamanho(caminho: Path) -> int:
    if caminho.is_dir():
        return sum(f.stat().st_size for f in caminho.rglob("*.parquet"))
    return caminho.stat().st_size


def conferir_parquet(caminho: Path) -> dict:
    """Linhas, colunas e tipos do Parquet gerado, para comparar os motores."""
    import duckdb

    alvo = f"{caminho}/*.parquet" if caminho.is_dir() else str(caminho)
    con = duckdb.connect()
    linhas = con.execute(f"SELECT count(*) FROM read_parquet('{alvo}')").fetchone()[0]
    esquema = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{alvo}')").fetchall()
    con.close()
    return {
        "linhas": linhas,
        "colunas": len(esquema),
        "tipos": sorted({linha[1] for linha in esquema}),
    }


def etapa_etl(anos: list[int], motores: list[str], resultados: dict, salvar) -> None:
    """Preenche `resultados` (ano -> motor -> medida) e salva apos cada medicao.

    A rodada completa leva dezenas de minutos; se for interrompida, o que ja
    foi medido fica no benchmark.json.
    """
    for ano in anos:
        csv = caminho_csv(ano)
        if not csv.exists():
            print(f"[etl] {ano}: CSV ausente em {csv}, pulando", flush=True)
            continue
        esperado = json.loads(
            (RAIZ / "docs" / "profiling" / f"profiling_{ano}.json").read_text(encoding="utf-8")
        )["volume"]["linhas"]
        aquecer_cache(csv)
        for motor in motores:
            if motor == "spark" and not modulo_disponivel("pyspark"):
                print("[etl] pyspark nao instalado, pulando Spark", flush=True)
                continue
            destino = BENCH / "etl" / motor / f"enem_{ano}.parquet"
            destino.parent.mkdir(parents=True, exist_ok=True)
            remover(destino)
            print(f"[etl] {ano} {motor} ...", flush=True)
            r = executar_filho("etl", {"motor": motor, "ano": ano, "destino": str(destino)})
            if "erro" not in r:
                r["parquet_bytes"] = tamanho(destino)
                r["csv_bytes"] = csv.stat().st_size
                r.update(conferir_parquet(destino))
                r["linhas_conferem"] = r["linhas"] == esperado
                remover(destino)
            print(f"[etl] {ano} {motor}: {r}", flush=True)
            resultados.setdefault(str(ano), {})[motor] = r
            salvar()


def remover(caminho: Path) -> None:
    if caminho.is_dir():
        shutil.rmtree(caminho)
    elif caminho.exists():
        caminho.unlink()


# ================================================================= preparo


def preparar_trusted(anos: list[int]) -> None:
    """Camada TRUSTED de referencia para as consultas, gerada com DuckDB.

    Todos os motores de consulta leem os mesmos arquivos, entao a comparacao
    mede so a consulta, nao diferencas de escrita do Parquet.
    """
    TRUSTED.mkdir(parents=True, exist_ok=True)
    for ano in anos:
        if not trusted(ano).exists():
            print(f"[preparo] TRUSTED {ano}", flush=True)
            etl_duckdb(caminho_csv(ano), trusted(ano))


def preparar_analytics(anos: list[int]) -> None:
    """Artefato ANALYTICS minimo: contagem de elegiveis por nota exata.

    E o formato que o produto usa para responder "qual o meu percentil" sem
    tocar no dado individual. Fica local (data/ e ignorado pelo git).
    """
    import duckdb

    ANALYTICS.mkdir(parents=True, exist_ok=True)
    arquivos = ", ".join(f"'{trusted(a)}'" for a in anos)
    partes = []
    for area in ["CN", "CH", "LC", "MT", "REDACAO"]:
        partes.append(
            f"""
            SELECT NU_ANO AS ano, '{area}' AS area, NU_NOTA_{area} AS nota, count(*) AS n
            FROM read_parquet([{arquivos}])
            WHERE {ELEGIVEL_SQL} AND NU_NOTA_{area} IS NOT NULL
            GROUP BY ALL
            """
        )
    con = duckdb.connect()
    con.execute(
        f"COPY ({' UNION ALL '.join(partes)} ORDER BY ano, area, nota) "
        f"TO '{DIST_NOTAS}' (FORMAT parquet, COMPRESSION zstd)"
    )
    con.close()


# ================================================================ consultas

ELEGIVEL_SQL = (
    "TP_PRESENCA_CN = 1 AND TP_PRESENCA_CH = 1 AND TP_PRESENCA_LC = 1 "
    "AND TP_PRESENCA_MT = 1 AND IN_TREINEIRO = 0"
)
ELEGIVEL_COLS = ["TP_PRESENCA_CN", "TP_PRESENCA_CH", "TP_PRESENCA_LC", "TP_PRESENCA_MT", "IN_TREINEIRO"]
RENDA_BAIXA = ["A", "B", "C"]
SENTINELA_TEXTO, SENTINELA_INT = "<nulo>", -1

CONSULTAS = {
    "q1_percentil": "Percentil de uma nota de MT entre os elegiveis de 2022 (dado individual)",
    "q2_uf": "Media e mediana de MT por UF de prova, 2022, com piso de grupo",
    "q3_recorte": "Renda x dependencia da escola nas 4 edicoes: n, medias e quartis",
    "q4_histograma": "Histograma de MT (faixas de 20 pontos) em um recorte filtrado",
    "q5_percentil_agregado": "Mesmo percentil da q1, lido do artefato ANALYTICS agregado",
}


def consulta_duckdb(qid: str, arquivos: list[str]):
    import duckdb

    con = duckdb.connect()
    con.execute(f"SET threads={NUCLEOS_RUNTIME}")
    con.execute(f"SET memory_limit='{ORCAMENTO_RUNTIME_MB}MB'")
    fonte = "read_parquet([" + ", ".join(f"'{a}'" for a in arquivos) + "])"

    def rodar():
        if qid == "q1_percentil":
            sql = f"""
                SELECT count(*), count(*) FILTER (NU_NOTA_MT < {NOTA_USUARIO}),
                       count(*) FILTER (NU_NOTA_MT = {NOTA_USUARIO})
                FROM {fonte}
                WHERE NU_ANO = {ANO_CONSULTA} AND {ELEGIVEL_SQL} AND NU_NOTA_MT IS NOT NULL"""
            return percentil(*con.execute(sql).fetchone())
        if qid == "q2_uf":
            sql = f"""
                SELECT SG_UF_PROVA, count(NU_NOTA_MT) AS n, avg(NU_NOTA_MT), median(NU_NOTA_MT)
                FROM {fonte}
                WHERE NU_ANO = {ANO_CONSULTA} AND {ELEGIVEL_SQL}
                GROUP BY 1 HAVING n >= {PISO_GRUPO} ORDER BY 1"""
            return con.execute(sql).fetchall()
        if qid == "q3_recorte":
            sql = f"""
                SELECT NU_ANO, Q006, TP_DEPENDENCIA_ADM_ESC, count(NU_NOTA_MT) AS n,
                       avg(NU_NOTA_MT), avg(NU_NOTA_REDACAO),
                       quantile_cont(NU_NOTA_MT, 0.25), quantile_cont(NU_NOTA_MT, 0.5),
                       quantile_cont(NU_NOTA_MT, 0.75)
                FROM {fonte}
                WHERE {ELEGIVEL_SQL}
                GROUP BY 1, 2, 3 HAVING n >= {PISO_GRUPO}"""
            return con.execute(sql).fetchall()
        if qid == "q4_histograma":
            renda = ", ".join(f"'{r}'" for r in RENDA_BAIXA)
            sql = f"""
                SELECT floor(NU_NOTA_MT / 20) * 20 AS faixa, count(*) AS n
                FROM {fonte}
                WHERE NU_ANO = {ANO_CONSULTA} AND {ELEGIVEL_SQL} AND TP_ESCOLA = 2
                  AND Q006 IN ({renda}) AND NU_NOTA_MT IS NOT NULL
                GROUP BY 1 HAVING n >= {PISO_GRUPO} ORDER BY 1"""
            return con.execute(sql).fetchall()
        if qid == "q5_percentil_agregado":
            sql = f"""
                SELECT sum(n), sum(n) FILTER (nota < {NOTA_USUARIO}),
                       coalesce(sum(n) FILTER (nota = {NOTA_USUARIO}), 0)
                FROM read_parquet('{DIST_NOTAS}')
                WHERE ano = {ANO_CONSULTA} AND area = 'MT'"""
            return percentil(*con.execute(sql).fetchone())
        raise ValueError(qid)

    return rodar


def consulta_polars(qid: str, arquivos: list[str]):
    import polars as pl

    mt = pl.col("NU_NOTA_MT")
    elegivel = pl.all_horizontal([pl.col(c) == 1 for c in ELEGIVEL_COLS[:4]]) & (
        pl.col("IN_TREINEIRO") == 0
    )
    do_ano = pl.col("NU_ANO") == ANO_CONSULTA

    def rodar():
        lf = pl.scan_parquet(arquivos)
        if qid == "q1_percentil":
            r = (
                lf.filter(do_ano & elegivel & mt.is_not_null())
                .select(
                    pl.len().alias("total"),
                    (mt < NOTA_USUARIO).sum().alias("abaixo"),
                    (mt == NOTA_USUARIO).sum().alias("igual"),
                )
                .collect()
                .row(0)
            )
            return percentil(*r)
        if qid == "q2_uf":
            return (
                lf.filter(do_ano & elegivel)
                .group_by("SG_UF_PROVA")
                .agg(n=mt.count(), media=mt.mean(), mediana=mt.median())
                .filter(pl.col("n") >= PISO_GRUPO)
                .sort("SG_UF_PROVA")
                .collect()
                .rows()
            )
        if qid == "q3_recorte":
            return (
                lf.filter(elegivel)
                .group_by(["NU_ANO", "Q006", "TP_DEPENDENCIA_ADM_ESC"])
                .agg(
                    n=mt.count(),
                    media_mt=mt.mean(),
                    media_red=pl.col("NU_NOTA_REDACAO").mean(),
                    p25=mt.quantile(0.25, "linear"),
                    p50=mt.quantile(0.5, "linear"),
                    p75=mt.quantile(0.75, "linear"),
                )
                .filter(pl.col("n") >= PISO_GRUPO)
                .collect()
                .rows()
            )
        if qid == "q4_histograma":
            return (
                lf.filter(
                    do_ano
                    & elegivel
                    & (pl.col("TP_ESCOLA") == 2)
                    & pl.col("Q006").is_in(RENDA_BAIXA)
                    & mt.is_not_null()
                )
                .group_by(faixa=(mt / 20).floor() * 20)
                .agg(n=pl.len())
                .filter(pl.col("n") >= PISO_GRUPO)
                .sort("faixa")
                .collect()
                .rows()
            )
        if qid == "q5_percentil_agregado":
            n, nota = pl.col("n"), pl.col("nota")
            r = (
                pl.scan_parquet(DIST_NOTAS)
                .filter((pl.col("ano") == ANO_CONSULTA) & (pl.col("area") == "MT"))
                .select(
                    n.sum().alias("total"),
                    n.filter(nota < NOTA_USUARIO).sum().alias("abaixo"),
                    n.filter(nota == NOTA_USUARIO).sum().alias("igual"),
                )
                .collect()
                .row(0)
            )
            return percentil(*r)
        raise ValueError(qid)

    return rodar


def consulta_pandas(qid: str, arquivos: list[str]):
    import pandas as pd
    import pyarrow as pa

    pa.set_cpu_count(NUCLEOS_RUNTIME)
    pa.set_io_thread_count(NUCLEOS_RUNTIME)
    # Filtros empurrados para o leitor do Parquet (pyarrow): o pandas so recebe
    # as linhas e colunas que a consulta usa. E o uso idiomatico em 2026, nao
    # um espantalho que carrega o arquivo inteiro.
    elegivel = [(c, "==", 1) for c in ELEGIVEL_COLS[:4]] + [("IN_TREINEIRO", "==", 0)]
    do_ano = [("NU_ANO", "==", ANO_CONSULTA)]

    def ler(colunas, filtros):
        return pd.read_parquet(arquivos, columns=colunas, filters=filtros)

    def rodar():
        if qid == "q1_percentil":
            s = ler(["NU_NOTA_MT"], do_ano + elegivel)["NU_NOTA_MT"].dropna()
            return percentil(len(s), (s < NOTA_USUARIO).sum(), (s == NOTA_USUARIO).sum())
        if qid == "q2_uf":
            df = ler(["SG_UF_PROVA", "NU_NOTA_MT"], do_ano + elegivel)
            g = df.groupby("SG_UF_PROVA")["NU_NOTA_MT"].agg(["count", "mean", "median"])
            g = g[g["count"] >= PISO_GRUPO].sort_index()
            return list(g.itertuples(name=None))
        if qid == "q3_recorte":
            chaves = ["NU_ANO", "Q006", "TP_DEPENDENCIA_ADM_ESC"]
            df = ler(chaves + ["NU_NOTA_MT", "NU_NOTA_REDACAO"], elegivel)
            # groupby(dropna=False).quantile() devolve NaN para o grupo de
            # chave nula (escola nao declarada), embora mean() funcione. As
            # chaves nulas viram sentinela antes e voltam a nulo no fim.
            df["Q006"] = df["Q006"].fillna(SENTINELA_TEXTO)
            df["TP_DEPENDENCIA_ADM_ESC"] = df["TP_DEPENDENCIA_ADM_ESC"].fillna(SENTINELA_INT)
            g = df.groupby(chaves)
            r = g.agg(
                n=("NU_NOTA_MT", "count"),
                media_mt=("NU_NOTA_MT", "mean"),
                media_red=("NU_NOTA_REDACAO", "mean"),
            )
            q = g["NU_NOTA_MT"].quantile([0.25, 0.5, 0.75]).unstack()
            r = r.join(q)
            r = r[r["n"] >= PISO_GRUPO]
            return [
                tuple(None if v in (SENTINELA_TEXTO, SENTINELA_INT) else v for v in chave) + tuple(resto)
                for chave, *resto in r.itertuples(name=None)
            ]
        if qid == "q4_histograma":
            filtros = do_ano + elegivel + [("TP_ESCOLA", "==", 2), ("Q006", "in", RENDA_BAIXA)]
            s = ler(["NU_NOTA_MT"], filtros)["NU_NOTA_MT"].dropna()
            faixa = (s // 20) * 20
            c = faixa.value_counts().sort_index()
            c = c[c >= PISO_GRUPO]
            return list(c.items())
        if qid == "q5_percentil_agregado":
            df = pd.read_parquet(
                DIST_NOTAS, filters=[("ano", "==", ANO_CONSULTA), ("area", "==", "MT")]
            )
            return percentil(
                df["n"].sum(),
                df.loc[df["nota"] < NOTA_USUARIO, "n"].sum(),
                df.loc[df["nota"] == NOTA_USUARIO, "n"].sum(),
            )
        raise ValueError(qid)

    return rodar


def percentil(total, abaixo, igual) -> list:
    # Empate conta pela metade: convencao de percentil de posicao usada pelo
    # motor estatistico (plano, objetivo 6, "tratamento de empates").
    return [[(int(abaixo) + int(igual) / 2) / int(total) * 100]]


def normalizar(linhas) -> list:
    """Linhas de qualquer motor em listas comparaveis e serializaveis."""
    saida = []
    for linha in linhas:
        if not isinstance(linha, (list, tuple)):
            linha = [linha]
        normal = []
        for v in _achatar(linha):
            if v is None:
                normal.append(None)
            elif isinstance(v, str):
                normal.append(v)
            else:
                try:
                    f = float(v)
                except (TypeError, ValueError):
                    normal.append(None)  # pd.NA
                    continue
                normal.append(None if math.isnan(f) else f)
        saida.append(normal)
    return sorted(saida, key=lambda l: [(x is None, str(x)) for x in l])


def _achatar(linha):
    # O itertuples do pandas com MultiIndex devolve a chave como tupla aninhada.
    for v in linha:
        if isinstance(v, tuple):
            yield from v
        else:
            yield v


def filho_consulta(p: dict) -> dict:
    os.sched_setaffinity(0, set(range(NUCLEOS_RUNTIME)))
    arquivos = [str(trusted(a)) for a in p["anos"]]
    fabrica = {"duckdb": consulta_duckdb, "polars": consulta_polars, "pandas": consulta_pandas}
    rodar = fabrica[p["motor"]](p["consulta"], arquivos)
    base_mb = rss_kb(os.getpid()) / 1024

    tempos = []
    for _ in range(1 + p["repeticoes"]):
        inicio = time.perf_counter()
        resultado = rodar()
        tempos.append(time.perf_counter() - inicio)
    Path(p["resultado"]).write_text(json.dumps(normalizar(resultado)))
    return {
        "primeira_ms": round(tempos[0] * 1000, 1),
        "mediana_ms": round(statistics.median(tempos[1:]) * 1000, 1),
        "base_mb": round(base_mb, 1),
    }


def conferem(a: list, b: list) -> bool:
    if len(a) != len(b):
        return False
    for la, lb in zip(a, b):
        if len(la) != len(lb):
            return False
        for x, y in zip(la, lb):
            if isinstance(x, float) and isinstance(y, float):
                if not math.isclose(x, y, rel_tol=1e-9, abs_tol=1e-6):
                    return False
            elif x != y:
                return False
    return True


def etapa_consultas(anos: list[int], motores: list[str]) -> dict:
    preparar_trusted(anos)
    # Sempre regenerado: e barato e precisa cobrir exatamente as mesmas edicoes.
    print("[preparo] ANALYTICS dist_notas", flush=True)
    preparar_analytics(anos)

    env = dict(os.environ, POLARS_MAX_THREADS=str(NUCLEOS_RUNTIME))
    pasta_resultados = BENCH / "resultados"
    pasta_resultados.mkdir(parents=True, exist_ok=True)

    saida: dict = {
        "anos": anos,
        "nucleos": NUCLEOS_RUNTIME,
        "orcamento_mb": ORCAMENTO_RUNTIME_MB,
        "repeticoes": REPETICOES_CONSULTA,
        "trusted_bytes": sum(trusted(a).stat().st_size for a in anos),
        "analytics_bytes": DIST_NOTAS.stat().st_size,
        "consultas": {},
    }
    for qid, descricao in CONSULTAS.items():
        medidas: dict = {}
        respostas: dict = {}
        for motor in motores:
            arquivo = pasta_resultados / f"{qid}_{motor}.json"
            print(f"[consultas] {qid} {motor} ...", flush=True)
            r = executar_filho(
                "consulta",
                {
                    "motor": motor,
                    "consulta": qid,
                    "anos": anos,
                    "repeticoes": REPETICOES_CONSULTA,
                    "resultado": str(arquivo),
                },
                env=env,
            )
            if "erro" not in r:
                respostas[motor] = json.loads(arquivo.read_text())
            print(f"[consultas] {qid} {motor}: {r}", flush=True)
            medidas[motor] = r
        referencia = respostas.get("duckdb") or next(iter(respostas.values()), None)
        for motor, resposta in respostas.items():
            medidas[motor]["resultado_confere"] = conferem(resposta, referencia)
        saida["consultas"][qid] = {"descricao": descricao, "motores": medidas}

    # q1 (dado individual) e q5 (agregado) precisam dar o mesmo percentil: e a
    # prova de que o artefato ANALYTICS nao perde informacao para esse uso.
    q1 = pasta_resultados / "q1_percentil_duckdb.json"
    q5 = pasta_resultados / "q5_percentil_agregado_duckdb.json"
    if q1.exists() and q5.exists():
        saida["agregado_confere_com_individual"] = conferem(
            json.loads(q1.read_text()), json.loads(q5.read_text())
        )
    return saida


# =================================================================== codecs


def etapa_codecs(ano: int) -> dict:
    import duckdb

    preparar_trusted([ano])
    pasta = BENCH / "codecs"
    pasta.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    resultados = {}
    for codec in CODECS:
        destino = pasta / f"enem_{ano}_{codec}.parquet"
        inicio = time.perf_counter()
        con.execute(
            f"COPY (SELECT * FROM read_parquet('{trusted(ano)}')) "
            f"TO '{destino}' (FORMAT parquet, COMPRESSION {codec})"
        )
        escrita = time.perf_counter() - inicio
        # Leitura tipica do produto: poucas colunas, agregacao por grupo.
        tempos = []
        for _ in range(REPETICOES_CONSULTA):
            inicio = time.perf_counter()
            con.execute(
                f"SELECT SG_UF_PROVA, avg(NU_NOTA_MT), avg(NU_NOTA_REDACAO) "
                f"FROM read_parquet('{destino}') GROUP BY 1"
            ).fetchall()
            tempos.append(time.perf_counter() - inicio)
        resultados[codec] = {
            "bytes": destino.stat().st_size,
            "escrita_s": round(escrita, 2),
            "leitura_ms": round(statistics.median(tempos) * 1000, 1),
        }
        destino.unlink()
        print(f"[codecs] {codec}: {resultados[codec]}", flush=True)
    con.close()
    return {"ano": ano, "csv_bytes": caminho_csv(ano).stat().st_size, "codecs": resultados}


# ================================================================= frontend

APPS = {
    "streamlit": (
        "app.py",
        """
import duckdb, plotly.graph_objects as go, streamlit as st
st.title("Radar ENEM")
st.plotly_chart(go.Figure(go.Bar(x=["a", "b"], y=[1, 2])))
""",
    ),
    "dash": (
        "app.py",
        """
import sys, duckdb, plotly.graph_objects as go
from dash import Dash, dcc, html
app = Dash(__name__)
app.layout = html.Div([html.H1("Radar ENEM"), dcc.Graph(figure=go.Figure(go.Bar(x=["a", "b"], y=[1, 2])))])
app.run(port=int(sys.argv[1]), debug=False)
""",
    ),
    "shiny": (
        "app.py",
        """
import duckdb, plotly.graph_objects as go
from shiny import App, ui
fig = go.Figure(go.Bar(x=["a", "b"], y=[1, 2]))
app_ui = ui.page_fluid(ui.h1("Radar ENEM"), ui.HTML(fig.to_html(include_plotlyjs="cdn", full_html=False)))
app = App(app_ui, None)
""",
    ),
    "fastapi": (
        "app.py",
        """
import duckdb
from fastapi import FastAPI
app = FastAPI()
@app.get("/saude")
def saude():
    return {"ok": True}
""",
    ),
}


def porta_livre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def etapa_frontend(frameworks: list[str]) -> dict:
    resultados = {}
    for fw in frameworks:
        pacote = {"fastapi": "uvicorn"}.get(fw, fw)
        if not modulo_disponivel(pacote) or not modulo_disponivel(fw):
            print(f"[frontend] {fw} nao instalado, pulando", flush=True)
            continue
        pasta = Path(tempfile.mkdtemp(prefix=f"bench_{fw}_", dir=BENCH))
        nome, codigo = APPS[fw]
        (pasta / nome).write_text(codigo)
        porta = porta_livre()
        if fw == "streamlit":
            cmd = [sys.executable, "-m", "streamlit", "run", nome, "--server.port", str(porta),
                   "--server.headless", "true", "--browser.gatherUsageStats", "false"]
            url = f"http://127.0.0.1:{porta}/_stcore/health"
        elif fw == "shiny":
            cmd = [sys.executable, "-m", "shiny", "run", nome, "--port", str(porta)]
            url = f"http://127.0.0.1:{porta}/"
        elif fw == "dash":
            cmd = [sys.executable, nome, str(porta)]
            url = f"http://127.0.0.1:{porta}/"
        else:
            cmd = [sys.executable, "-m", "uvicorn", "app:app", "--port", str(porta)]
            url = f"http://127.0.0.1:{porta}/saude"

        inicio = time.perf_counter()
        proc = subprocess.Popen(cmd, cwd=pasta, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subida = None
        try:
            while time.perf_counter() - inicio < 60:
                try:
                    with urllib.request.urlopen(url, timeout=1) as resp:
                        if resp.status == 200:
                            subida = time.perf_counter() - inicio
                            break
                except OSError:
                    time.sleep(0.05)
            time.sleep(2)
            ocioso = 0.0
            for _ in range(10):
                ocioso = max(ocioso, rss_arvore_mb(proc.pid))
                time.sleep(0.1)
        finally:
            proc.terminate()
            proc.wait(timeout=10)
            shutil.rmtree(pasta, ignore_errors=True)
        resultados[fw] = {
            "subida_s": round(subida, 2) if subida else None,
            "ocioso_mb": round(ocioso, 1),
        }
        print(f"[frontend] {fw}: {resultados[fw]}", flush=True)
    return resultados


# ================================================================ relatorio


def modulo_disponivel(nome: str) -> bool:
    import importlib.util

    return importlib.util.find_spec(nome) is not None


def versao(pacote: str) -> str | None:
    try:
        return importlib.metadata.version(pacote)
    except importlib.metadata.PackageNotFoundError:
        return None


def ambiente() -> dict:
    cpu = next(
        (l.split(":", 1)[1].strip() for l in open("/proc/cpuinfo") if l.startswith("model name")),
        platform.processor(),
    )
    ram = next(int(l.split()[1]) for l in open("/proc/meminfo") if l.startswith("MemTotal"))
    java = None
    if shutil.which("java"):
        java = subprocess.run(["java", "-version"], capture_output=True, text=True).stderr.splitlines()[0]
    pacotes = ["pandas", "pyarrow", "polars", "duckdb", "pyspark", "streamlit", "dash", "shiny", "fastapi", "uvicorn", "plotly"]
    return {
        "data": time.strftime("%Y-%m-%d"),
        "cpu": cpu,
        "nucleos": os.cpu_count(),
        "ram_gb": round(ram / 1024 / 1024, 1),
        "so": f"{platform.system()} {platform.release()}",
        "python": platform.python_version(),
        "java": java,
        "versoes": {p: versao(p) for p in pacotes},
    }


def gb(b: int) -> str:
    return f"{b / 1024**3:.2f} GB"


def mb(b: int) -> str:
    return f"{b / 1024**2:.1f} MB"


def gerar_relatorio(d: dict) -> str:
    L = ["# Benchmark da stack (numeros medidos)", ""]
    L.append(
        "Gerado por `scripts/benchmark_stack.py` a partir de `benchmark.json`. "
        "A analise e a decisao estao em [`README.md`](README.md)."
    )
    L.append("")
    amb = d.get("ambiente", {})
    if amb:
        L.append("## Ambiente")
        L.append("")
        L.append(f"- Maquina: {amb['cpu']}, {amb['nucleos']} threads, {amb['ram_gb']} GB de RAM, {amb['so']}")
        L.append(f"- Python {amb['python']}; {amb.get('java') or 'sem Java'}")
        v = ", ".join(f"{k} {x}" for k, x in amb["versoes"].items() if x)
        L.append(f"- Versoes: {v}")
        L.append(f"- Execucao: {amb['data']}")
        L.append("")

    etl = d.get("etl")
    if etl:
        L.append("## 1. ETL: CSV RAW -> Parquet ZSTD (58 colunas do contrato)")
        L.append("")
        L.append(
            "Uma execucao por motor e edicao, com o CSV ja no cache do sistema "
            "operacional. Todos os nucleos da maquina liberados (etapa offline). "
            "`Pico` e a memoria residente maxima do processo e seus filhos. O "
            "tempo do Polars inclui a transcodificacao latin-1 -> UTF-8."
        )
        L.append("")
        motores = [m for m in MOTORES_ETL if any(m in etl[a] for a in etl)]
        L.append("| Edicao | CSV | " + " | ".join(f"{m} tempo | {m} pico" for m in motores) + " |")
        L.append("| --- | --- |" + " --- | --- |" * len(motores))
        for ano in sorted(etl):
            celulas = []
            csv_b = next((r.get("csv_bytes") for r in etl[ano].values() if "csv_bytes" in r), 0)
            for m in motores:
                r = etl[ano].get(m)
                if not r or "erro" in r:
                    celulas += ["falhou" if r else "-", "-"]
                else:
                    celulas += [f"{r['duracao_processo_s']:.1f}s", f"{r['pico_mb'] / 1024:.2f} GB"]
            L.append(f"| {ano} | {gb(csv_b)} | " + " | ".join(celulas) + " |")
        L.append("")
        L.append("Tamanho do Parquet gerado e conferencia de linhas contra o profiling:")
        L.append("")
        L.append("| Edicao | " + " | ".join(motores) + " |")
        L.append("| --- |" + " --- |" * len(motores))
        for ano in sorted(etl):
            celulas = []
            for m in motores:
                r = etl[ano].get(m)
                if not r or "erro" in r:
                    celulas.append("-")
                else:
                    ok = "ok" if r["linhas_conferem"] else "DIVERGE"
                    celulas.append(f"{mb(r['parquet_bytes'])} ({ok})")
            L.append(f"| {ano} | " + " | ".join(celulas) + " |")
        L.append("")
        tipos = {m: r.get("tipos") for a in etl for m, r in etl[a].items() if "tipos" in r}
        if tipos:
            L.append("Tipos fisicos gravados por motor: " + "; ".join(f"{m}: {', '.join(t)}" for m, t in tipos.items()) + ".")
            L.append("")

    codecs = d.get("codecs")
    if codecs:
        L.append(f"## 2. Compressao do Parquet (edicao {codecs['ano']})")
        L.append("")
        L.append(
            f"Mesmas 58 colunas, gravadas pelo DuckDB. CSV original completo: "
            f"{gb(codecs['csv_bytes'])}. `Leitura` e a mediana de "
            f"{REPETICOES_CONSULTA} execucoes de uma agregacao por UF sobre 2 colunas."
        )
        L.append("")
        L.append("| Codec | Tamanho | Razao sobre o CSV | Escrita | Leitura |")
        L.append("| --- | --- | --- | --- | --- |")
        for codec, r in codecs["codecs"].items():
            razao = codecs["csv_bytes"] / r["bytes"]
            L.append(f"| {codec} | {mb(r['bytes'])} | {razao:.1f}x | {r['escrita_s']:.1f}s | {r['leitura_ms']:.0f} ms |")
        L.append("")

    cons = d.get("consultas")
    if cons:
        L.append("## 3. Consultas representativas no orcamento de runtime")
        L.append("")
        L.append(
            f"Processo preso a {cons['nucleos']} nucleos (afinidade de CPU), "
            f"lendo a camada TRUSTED das edicoes {', '.join(map(str, cons['anos']))} "
            f"({mb(cons['trusted_bytes'])} em Parquet) ou o artefato ANALYTICS "
            f"agregado ({mb(cons['analytics_bytes'])}). `1a` e a primeira execucao "
            f"no processo; `mediana` e a de {cons['repeticoes']} execucoes seguintes. "
            f"`Pico` inclui o interpretador e as bibliotecas importadas (`base`); o "
            f"orcamento de referencia e {cons['orcamento_mb']} MB. Toda consulta "
            f"aplica o piso de {PISO_GRUPO} participantes por grupo."
        )
        L.append("")
        motores = [m for m in MOTORES_CONSULTA if any(m in q["motores"] for q in cons["consultas"].values())]
        L.append("| Consulta | " + " | ".join(f"{m} 1a / mediana | {m} pico" for m in motores) + " | Resultados |")
        L.append("| --- |" + " --- | --- |" * len(motores) + " --- |")
        for qid, q in cons["consultas"].items():
            celulas, confere, completo = [], True, True
            for m in motores:
                r = q["motores"].get(m)
                if not r or "erro" in r:
                    celulas += ["falhou", "-"]
                    completo = False
                    continue
                celulas += [
                    f"{r['primeira_ms']:.0f} / {r['mediana_ms']:.0f} ms",
                    f"{r['pico_mb']:.0f} MB",
                ]
                confere &= r.get("resultado_confere", False)
            # Motor que falhou nao e divergencia: so os que rodaram sao comparados.
            veredito = "DIVERGEM" if not confere else "iguais" if completo else "iguais (incompleto)"
            L.append(f"| `{qid}` | " + " | ".join(celulas) + f" | {veredito} |")
        L.append("")
        for qid, q in cons["consultas"].items():
            L.append(f"- `{qid}`: {q['descricao']}.")
        L.append("")
        bases = {m: r["base_mb"] for q in cons["consultas"].values() for m, r in q["motores"].items() if "base_mb" in r}
        if bases:
            L.append("Memoria so com as bibliotecas importadas, antes da primeira consulta: " + ", ".join(f"{m} {v:.0f} MB" for m, v in bases.items()) + ".")
            L.append("")
        if "agregado_confere_com_individual" in cons:
            ok = cons["agregado_confere_com_individual"]
            L.append(f"Percentil pelo artefato agregado (`q5`) igual ao calculado sobre o dado individual (`q1`): {'sim' if ok else 'NAO'}.")
            L.append("")

    fe = d.get("frontend")
    if fe:
        L.append("## 4. Custo fixo do servidor de interface")
        L.append("")
        L.append(
            "App minimo de cada framework importando DuckDB e Plotly, medido 2 s "
            "depois de responder a primeira requisicao HTTP. E o piso de memoria "
            "antes de qualquer sessao de usuario; o custo por sessao sera medido "
            "no prototipo."
        )
        L.append("")
        L.append("| Framework | Subida | Memoria ociosa |")
        L.append("| --- | --- | --- |")
        for fw, r in fe.items():
            sub = f"{r['subida_s']:.1f}s" if r["subida_s"] else "nao subiu"
            L.append(f"| {fw} | {sub} | {r['ocioso_mb']:.0f} MB |")
        L.append("")
    return "\n".join(L)


# ===================================================================== main


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "_filho":
        tarefa, parametros, saida = sys.argv[2], json.loads(sys.argv[3]), sys.argv[4]
        resultado = {"etl": filho_etl, "consulta": filho_consulta}[tarefa](parametros)
        resultado["hwm_mb"] = rss_kb("self", "VmHWM") / 1024
        Path(saida).write_text(json.dumps(resultado))
        return 0

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--etapas", nargs="+", default=["etl", "codecs", "consultas", "frontend"],
                    choices=["etl", "codecs", "consultas", "frontend"])
    ap.add_argument("--anos", nargs="+", type=int, default=ANOS)
    ap.add_argument("--motores", nargs="+", default=MOTORES_ETL, choices=MOTORES_ETL)
    ap.add_argument("--relatorio", action="store_true", help="so regenera o benchmark.md")
    args = ap.parse_args()

    SAIDA.mkdir(parents=True, exist_ok=True)
    arquivo = SAIDA / "benchmark.json"
    dados = json.loads(arquivo.read_text(encoding="utf-8")) if arquivo.exists() else {}

    def salvar() -> None:
        # Escrita atomica: uma interrupcao no meio nao deixa o JSON truncado.
        temporario = arquivo.with_suffix(".json.tmp")
        temporario.write_text(json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8")
        temporario.replace(arquivo)

    if not args.relatorio:
        dados["ambiente"] = ambiente()
        if "etl" in args.etapas:
            etapa_etl(args.anos, args.motores, dados.setdefault("etl", {}), salvar)
        if "codecs" in args.etapas:
            dados["codecs"] = etapa_codecs(max(args.anos, key=lambda a: caminho_csv(a).stat().st_size))
            salvar()
        if "consultas" in args.etapas:
            motores = [m for m in args.motores if m in MOTORES_CONSULTA] or MOTORES_CONSULTA
            dados["consultas"] = etapa_consultas(args.anos, motores)
            salvar()
        if "frontend" in args.etapas:
            dados["frontend"] = etapa_frontend(FRONTENDS)
            salvar()
        print(f"-> {arquivo.relative_to(RAIZ)}", flush=True)

    relatorio = SAIDA / "benchmark.md"
    relatorio.write_text(gerar_relatorio(dados), encoding="utf-8")
    print(f"-> {relatorio.relative_to(RAIZ)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
