#!/usr/bin/env python3
"""ETL do Radar ENEM: RAW -> TRUSTED -> ANALYTICS, em DuckDB.

Implementa o contrato de dados (scripts/colunas.py) com a stack decidida em
docs/stack/README.md.

TRUSTED  data/trusted/enem/ano=<ano>/data_0.parquet (particionado por edicao)
         - so as colunas mantidas pelo contrato, com os nomes internos;
         - `NU_INSCRICAO` descartado (docs/privacidade.md, R2);
         - derivadas do contrato: `ano_conclusao`, `conclusao_antes_2007`
           (de TP_ANO_CONCLUIU) e `renda_sm` (de Q006);
         - `elegivel`: presente nas quatro areas e nao treineiro.
         Um manifesto (_manifesto.json) registra fonte, hash e funil de
         elegibilidade de cada edicao.

ANALYTICS data/analytics/dist_notas.parquet
         Distribuicao das notas dos elegiveis por edicao e area, em faixas
         de nota com pelo menos PISO_GRUPO participantes cada (R3). Responde
         "qual o meu percentil" sem tocar no dado individual. O erro da
         faixa e medido contra o percentil exato a cada execucao.

Tudo fica em data/, fora do git (R1).

Uso:
  ./.venv/bin/python scripts/etl.py                 # quatro edicoes + ANALYTICS
  ./.venv/bin/python scripts/etl.py --anos 2022     # so uma edicao + ANALYTICS
  ./.venv/bin/python scripts/etl.py --so-analytics  # reaproveita a TRUSTED
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent))

from colunas import ANOS, CONTRATO, PISO_GRUPO, mantidas, tipo  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
RAW = RAIZ / "data" / "raw"
TRUSTED = RAIZ / "data" / "trusted" / "enem"
ANALYTICS = RAIZ / "data" / "analytics"
DIST_NOTAS = ANALYTICS / "dist_notas.parquet"
MANIFESTO = TRUSTED / "_manifesto.json"

AREAS = ["cn", "ch", "lc", "mt", "redacao"]

# Piso de cada faixa de Q006 em multiplos do salario minimo da edicao
# (docs/dicionario, secao 2). A e B tem piso 0: A e "nenhuma renda", B e
# "ate 1 salario"; o codigo continua distinguindo as duas.
PISO_RENDA_SM = {
    "A": 0, "B": 0, "C": 1, "D": 1.5, "E": 2, "F": 2.5, "G": 3, "H": 4, "I": 5,
    "J": 6, "K": 7, "L": 8, "M": 9, "N": 10, "O": 12, "P": 15, "Q": 20,
}

# O maior codigo de TP_ANO_CONCLUIU de cada edicao rotula "Antes de 2007"
# e vale sempre ano - 2006 (ver contrato).
ULTIMO_ANO_EXPLICITO = 2007

TIPOS_SQL = {"texto": "VARCHAR", "real": "DOUBLE", "inteiro": "BIGINT"}


def caminho_csv(ano: int) -> Path:
    return RAW / f"microdados_enem_{ano}" / "DADOS" / f"MICRODADOS_ENEM_{ano}.csv"


def conectar() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    tmp = RAIZ / "data" / "tmp_duckdb"
    con.execute(f"SET temp_directory='{tmp}'")
    return con


# ================================================================== TRUSTED


def selecao_trusted(ano: int) -> str:
    """SELECT da passagem RAW -> TRUSTED, com as regras do contrato."""
    colunas = ['"NU_ANO" AS ano']
    for c in mantidas():
        if c != "NU_ANO":
            colunas.append(f'"{c}" AS {CONTRATO[c]["interno"]}')

    antes_2007 = ano - (ULTIMO_ANO_EXPLICITO - 1)
    renda = " ".join(f"WHEN '{k}' THEN {v}" for k, v in PISO_RENDA_SM.items())
    presentes = " AND ".join(f"TP_PRESENCA_{a} = 1" for a in ["CN", "CH", "LC", "MT"])
    colunas += [
        # Codigo 0 = nao informado; o maior codigo = "antes de 2007".
        f"CASE WHEN TP_ANO_CONCLUIU BETWEEN 1 AND {antes_2007 - 1} "
        f"THEN {ano} - TP_ANO_CONCLUIU END AS ano_conclusao",
        f"TP_ANO_CONCLUIU = {antes_2007} AS conclusao_antes_2007",
        f"CAST(CASE Q006 {renda} END AS DOUBLE) AS renda_sm",
        f"({presentes} AND IN_TREINEIRO = 0) AS elegivel",
    ]
    return ",\n       ".join(colunas)


def ler_csv(csv: Path) -> str:
    tipos = ", ".join(f"'{c}': '{TIPOS_SQL[tipo(c)]}'" for c in mantidas())
    return (
        f"read_csv('{csv}', delim=';', header=true, encoding='latin-1', "
        f"types={{{tipos}}})"
    )


def gerar_trusted(
    con: duckdb.DuckDBPyConnection, csv: Path, ano: int, destino: Path
) -> Path:
    """Grava a edicao em destino/ano=<ano>/ e devolve a pasta da particao.

    Escreve num arquivo temporario e so troca a particao no fim: uma
    interrupcao nao deixa a TRUSTED com uma edicao pela metade. O `ano` sai
    do arquivo (vem do nome da pasta, particao Hive), entao a consulta
    confere linha a linha que o NU_ANO do CSV e o da edicao. O PARTITION_BY
    do DuckDB faria o mesmo, mas dobrava o pico de memoria (5,1 GB contra
    2,4 GB em 2022).
    """
    final = destino / f"ano={ano}"
    final.mkdir(parents=True, exist_ok=True)
    temporario = final / ".data_0.parquet.tmp"
    try:
        con.execute(
            f"""
            COPY (
                SELECT * EXCLUDE (ano)
                FROM (SELECT {selecao_trusted(ano)} FROM {ler_csv(csv)})
                WHERE CASE WHEN ano IS DISTINCT FROM {ano}
                           THEN error('NU_ANO diferente de {ano} em {csv.name}')
                           ELSE true END
            ) TO '{temporario}' (FORMAT parquet, COMPRESSION zstd)
            """
        )
    except duckdb.Error:
        temporario.unlink(missing_ok=True)
        if not any(final.iterdir()):
            final.rmdir()
        raise
    temporario.replace(final / "data_0.parquet")
    return final


def funil(con: duckdb.DuckDBPyConnection, particao: Path) -> dict:
    """Funil de elegibilidade da edicao (contrato: TP_PRESENCA_*, IN_TREINEIRO)."""
    presencas = [f"presenca_{a}" for a in ["cn", "ch", "lc", "mt"]]
    algum = lambda v: " OR ".join(f"{p} = {v}" for p in presencas)  # noqa: E731
    linha = con.execute(
        f"""
        SELECT count(*),
               count(*) FILTER (treineiro = 1),
               count(*) FILTER (treineiro = 0 AND ({algum(2)})),
               count(*) FILTER (treineiro = 0 AND NOT ({algum(2)}) AND ({algum(0)})),
               count(*) FILTER (elegivel)
        FROM read_parquet('{particao}/*.parquet')
        """
    ).fetchone()
    chaves = ["inscritos", "treineiros", "eliminados", "faltou_alguma_area", "elegiveis"]
    return dict(zip(chaves, linha))


def hash_zip(ano: int) -> str | None:
    arquivo = RAW / "hashes.sha256"
    if not arquivo.exists():
        return None
    for linha in arquivo.read_text().splitlines():
        sha, nome = linha.split()
        if nome == f"microdados_enem_{ano}.zip":
            return sha
    return None


def etapa_trusted(anos: list[int]) -> None:
    manifesto = json.loads(MANIFESTO.read_text()) if MANIFESTO.exists() else {}
    con = conectar()
    for ano in anos:
        csv = caminho_csv(ano)
        if not csv.exists():
            raise FileNotFoundError(f"{csv} (rode scripts/verify_raw.sh e extraia o zip)")
        esperado = json.loads(
            (RAIZ / "docs" / "profiling" / f"profiling_{ano}.json").read_text(encoding="utf-8")
        )["volume"]["linhas"]

        inicio = time.perf_counter()
        particao = gerar_trusted(con, csv, ano, TRUSTED)
        f = funil(con, particao)
        if f["inscritos"] != esperado:
            raise ValueError(f"{ano}: {f['inscritos']} linhas, profiling diz {esperado}")

        manifesto[str(ano)] = {
            "fonte": f"microdados_enem_{ano}.zip",
            "sha256": hash_zip(ano),
            "csv_bytes": csv.stat().st_size,
            "parquet_bytes": sum(p.stat().st_size for p in particao.glob("*.parquet")),
            "funil": f,
            "gerado_em": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "duckdb": duckdb.__version__,
        }
        MANIFESTO.write_text(json.dumps(manifesto, indent=2, ensure_ascii=False))
        print(
            f"[trusted] {ano}: {f['inscritos']} linhas, {f['elegiveis']} elegiveis, "
            f"{time.perf_counter() - inicio:.1f}s",
            flush=True,
        )
    con.close()


# ================================================================ ANALYTICS


def faixas(contagens: list[tuple[float, int]], piso: int = PISO_GRUPO) -> list[tuple[float, float, int]]:
    """Junta notas consecutivas ate cada faixa ter pelo menos `piso` pessoas.

    `contagens` e (nota, n) em ordem crescente de nota. Devolve
    (nota_min, nota_max, n). A sobra final abaixo do piso entra na ultima
    faixa; se o total nao chega ao piso, nada e publicado.
    """
    saida: list[tuple[float, float, int]] = []
    inicio, acumulado = None, 0
    for nota, n in contagens:
        if inicio is None:
            inicio = nota
        acumulado += n
        if acumulado >= piso:
            saida.append((inicio, nota, acumulado))
            inicio, acumulado = None, 0
    if acumulado and saida:
        nota_min, _, n = saida[-1]
        saida[-1] = (nota_min, contagens[-1][0], n + acumulado)
    return saida


def percentil_faixas(faixas_area: list[tuple[float, float, int]], nota: float) -> float:
    """Percentil de posicao de `nota` (0 a 100) a partir das faixas.

    Mesma convencao do percentil exato (empate conta pela metade). Dentro de
    uma faixa com varias notas a posicao e interpolada; o erro fica limitado
    ao peso da faixa (n da faixa / total).
    """
    total = sum(n for _, _, n in faixas_area)
    abaixo = 0.0
    for nota_min, nota_max, n in faixas_area:
        if nota_max < nota:
            abaixo += n
        elif nota_min <= nota:
            fracao = 0.5 if nota_min == nota_max else (nota - nota_min) / (nota_max - nota_min)
            abaixo += n * fracao
            break
        else:
            break
    return abaixo / total * 100


def percentil_exato(con: duckdb.DuckDBPyConnection, fonte: str, ano: int, area: str, nota: float) -> float:
    total, abaixo, igual = con.execute(
        f"""
        SELECT count(*), count(*) FILTER (nota_{area} < {nota}),
               count(*) FILTER (nota_{area} = {nota})
        FROM {fonte}
        WHERE ano = {ano} AND elegivel AND nota_{area} IS NOT NULL
        """
    ).fetchone()
    return (abaixo + igual / 2) / total * 100


def etapa_analytics() -> None:
    fonte = f"read_parquet('{TRUSTED}/*/*.parquet', hive_partitioning=true)"
    con = conectar()
    anos = [r[0] for r in con.execute(f"SELECT DISTINCT ano FROM {fonte} ORDER BY 1").fetchall()]

    linhas = []
    distribuicao: dict[tuple[int, str], list] = {}
    for ano in anos:
        for area in AREAS:
            contagens = con.execute(
                f"""
                SELECT nota_{area}, count(*) FROM {fonte}
                WHERE ano = {ano} AND elegivel AND nota_{area} IS NOT NULL
                GROUP BY 1 ORDER BY 1
                """
            ).fetchall()
            f = faixas(contagens)
            distribuicao[(ano, area)] = f
            linhas += [(ano, area, a, b, n) for a, b, n in f]

    ANALYTICS.mkdir(parents=True, exist_ok=True)
    temporario = DIST_NOTAS.with_suffix(".tmp.parquet")
    con.execute(
        "CREATE TABLE dist (ano BIGINT, area VARCHAR, nota_min DOUBLE, nota_max DOUBLE, n BIGINT)"
    )
    con.executemany("INSERT INTO dist VALUES (?, ?, ?, ?, ?)", linhas)
    con.execute(f"COPY dist TO '{temporario}' (FORMAT parquet, COMPRESSION zstd)")
    temporario.replace(DIST_NOTAS)
    print(f"[analytics] dist_notas: {len(linhas)} faixas, edicoes {anos}", flush=True)

    # Conferencia contra o dado individual: o erro de cada percentil tem de
    # caber no peso da maior faixa da area.
    pior = 0.0
    for (ano, area), f in distribuicao.items():
        total = sum(n for *_, n in f)
        limite = max(n for *_, n in f) / total * 100
        for nota in [f[0][0], 400.0, 500.0, 612.3, 650.0, 800.0, f[-1][1]]:
            erro = abs(percentil_faixas(f, nota) - percentil_exato(con, fonte, ano, area, nota))
            if erro > limite + 1e-9:
                raise AssertionError(f"{ano} {area} nota {nota}: erro {erro:.4f} > {limite:.4f}")
            pior = max(pior, erro)
    print(f"[analytics] percentil por faixa x exato: maior erro {pior:.4f} pontos percentuais", flush=True)
    con.close()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--anos", nargs="+", type=int, default=ANOS, choices=ANOS)
    ap.add_argument("--so-analytics", action="store_true", help="nao regenera a TRUSTED")
    args = ap.parse_args()

    if not args.so_analytics:
        etapa_trusted(args.anos)
    etapa_analytics()
    return 0


if __name__ == "__main__":
    sys.exit(main())
