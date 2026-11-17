#!/usr/bin/env python3
"""Barreira de qualidade antes de publicar: confere os artefatos da ANALYTICS.

Roda no computador da equipe e no Shell do Replit, antes de cada publicação
(docs/deploy/replit.md). Para cada um dos cinco artefatos que o app lê:

1. existe, abre como Parquet e tem as colunas esperadas;
2. a chave do grão não se repete: (ano, area, nota_min) nas faixas e
   (ano, area, recorte, grupo, nota) nas CDFs (docs/modelagem/README.md);
3. n é positivo, as notas estão entre 0 e 1000 e cada CDF é coerente: dentro
   do grupo, `abaixo` de uma nota é a soma dos `n` anteriores e
   `total = abaixo + n` da última nota;
4. nenhum grupo publicado tem menos de PISO_GRUPO participantes, e nenhuma faixa
   do histograma também (R3);
5. o Brasil é o mesmo em todos: o total de elegíveis por edição e área na CDF
   nacional é igual ao grupo BR do Recorte territorial e do Capital escolar;
6. o SHA-256 confere com docs/deploy/artefatos.sha256 (execução de referência).
   Diferença de hash é aviso, não erro, porque o pipeline pode ser rodado de novo;
   com --estrito vira erro.

Se tudo passar, grava data/analytics/_manifesto_publicacao.json (fora do git) com
a data, o commit do código e o hash, o tamanho e o número de linhas de cada
artefato. O rodapé do app lê esse arquivo para mostrar a versão dos dados.
O manifesto não tem nenhuma contagem de grupo, só metadados dos arquivos.

Saída 0: pode publicar. Saída 1: não publicar.

Uso:
  python scripts/auditar_artefatos.py               # confere e grava o manifesto
  python scripts/auditar_artefatos.py --estrito     # hash diferente da referência também falha
  python scripts/auditar_artefatos.py --explicar    # mostra o plano (EXPLAIN ANALYZE) da consulta do app
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import duckdb

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))

from colunas import PISO_GRUPO  # noqa: E402

ANALYTICS = Path(os.environ.get("RADAR_ANALYTICS", RAIZ / "data" / "analytics"))
REFERENCIA = RAIZ / "docs" / "deploy" / "artefatos.sha256"
MANIFESTO = ANALYTICS / "_manifesto_publicacao.json"

COLUNAS_CDF = ["ano", "area", "recorte", "grupo", "nota", "n", "abaixo", "total"]
ARTEFATOS = {
    "dist_notas.parquet": ["ano", "area", "nota_min", "nota_max", "n"],
    "dist_exata.parquet": ["ano", "area", "nota", "n", "abaixo", "total"],
    "dist_equidade.parquet": COLUNAS_CDF,
    "dist_territorial.parquet": COLUNAS_CDF,
    "dist_capital.parquet": COLUNAS_CDF,
}


def sha256(caminho: Path) -> str:
    h = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def referencia() -> dict[str, str]:
    if not REFERENCIA.exists():
        return {}
    saida = {}
    for linha in REFERENCIA.read_text(encoding="utf-8").splitlines():
        if linha.strip() and not linha.startswith("#"):
            valor, nome = linha.split()
            saida[nome] = valor
    return saida


def commit_atual() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=RAIZ, capture_output=True,
                              text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def um(con, sql: str, params: list) -> int:
    return con.execute(sql, params).fetchone()[0]


def conferir(con, nome: str, caminho: Path) -> list[str]:
    """Lista de falhas do artefato (vazia se passou)."""
    falhas = []
    colunas = [c[0] for c in con.execute("DESCRIBE SELECT * FROM read_parquet(?)", [str(caminho)]).fetchall()]
    if colunas != ARTEFATOS[nome]:
        return [f"colunas {colunas}, esperado {ARTEFATOS[nome]}"]
    fonte = f"read_parquet('{caminho.as_posix()}')"  # caminho do servidor, não do usuário

    if nome == "dist_notas.parquet":
        chave, minimo = "ano, area, nota_min", "n"
        if um(con, f"SELECT count(*) FROM {fonte} WHERE n < ?", [PISO_GRUPO]):
            falhas.append(f"faixa do histograma com menos de {PISO_GRUPO} participantes")
        if um(con, f"SELECT count(*) FROM {fonte} WHERE nota_min > nota_max OR nota_min < 0 OR nota_max > 1000", []):
            falhas.append("faixa com limites invalidos")
    else:
        grupo = "ano, area" if nome == "dist_exata.parquet" else "ano, area, recorte, grupo"
        chave, minimo = f"{grupo}, nota", "n"
        if um(con, f"SELECT count(*) FROM {fonte} WHERE nota < 0 OR nota > 1000", []):
            falhas.append("nota fora de 0 a 1000")
        # abaixo da nota i = soma dos n anteriores do mesmo grupo; total = último abaixo + n.
        incoerentes = um(con, f"""
            SELECT count(*) FROM (
                SELECT abaixo, total, n,
                       coalesce(sum(n) OVER (PARTITION BY {grupo} ORDER BY nota
                                             ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING), 0) AS esperado,
                       sum(n) OVER (PARTITION BY {grupo}) AS soma
                FROM {fonte}) WHERE abaixo <> esperado OR total <> soma""", [])
        if incoerentes:
            falhas.append(f"{incoerentes} linha(s) com abaixo/total incoerentes com a soma de n")
        pequenos = um(con, f"SELECT count(*) FROM (SELECT max(total) AS t FROM {fonte} GROUP BY {grupo}) "
                           "WHERE t < ?", [PISO_GRUPO])
        if pequenos:
            falhas.append(f"{pequenos} grupo(s) publicados com menos de {PISO_GRUPO} participantes")
    if um(con, f"SELECT count(*) FROM {fonte} WHERE {minimo} <= 0", []):
        falhas.append("n zero ou negativo")
    repetidas = um(con, f"SELECT count(*) FROM (SELECT {chave} FROM {fonte} GROUP BY {chave} HAVING count(*) > 1)", [])
    if repetidas:
        falhas.append(f"{repetidas} chave(s) do grao repetidas ({chave})")
    return falhas


def conferir_brasil(con) -> list[str]:
    """O total nacional por edição e área tem de ser o mesmo nos três artefatos que o têm."""
    totais = {}
    consultas = {
        "dist_exata": "SELECT ano, area, max(total) FROM read_parquet(?) GROUP BY 1, 2",
        "dist_territorial": "SELECT ano, area, max(total) FROM read_parquet(?) WHERE grupo = 'BR' GROUP BY 1, 2",
        "dist_capital": "SELECT ano, area, max(total) FROM read_parquet(?) WHERE grupo = 'BR' GROUP BY 1, 2",
    }
    for nome, sql in consultas.items():
        totais[nome] = {(a, b): t for a, b, t in con.execute(sql, [str(ANALYTICS / f"{nome}.parquet")]).fetchall()}
    falhas = []
    base = totais["dist_exata"]
    for nome in ("dist_territorial", "dist_capital"):
        if totais[nome] != base:
            diferentes = sorted(k for k in base.keys() | totais[nome].keys() if base.get(k) != totais[nome].get(k))
            falhas.append(f"Brasil de {nome} difere da CDF nacional em {len(diferentes)} edicao(oes)/area(s)")
    return falhas


def explicar(con) -> None:
    """Plano real da consulta que o app faz ao abrir (Banco de Dados II: analisar o plano antes de otimizar)."""
    print("\nEXPLAIN ANALYZE da carga da CDF nacional (app/app.py, carregar_exatas):")
    plano = con.execute(
        "EXPLAIN ANALYZE SELECT ano, area, nota, n, abaixo FROM read_parquet(?) ORDER BY ano, area, nota",
        [str(ANALYTICS / "dist_exata.parquet")],
    ).fetchall()
    for _, texto in plano:
        print(texto)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--estrito", action="store_true", help="hash diferente da referencia tambem falha")
    parser.add_argument("--explicar", action="store_true", help="mostra o EXPLAIN ANALYZE da consulta do app")
    args = parser.parse_args()

    inicio = time.perf_counter()
    con = duckdb.connect()
    ref = referencia()
    falhas, avisos, arquivos = [], [], {}
    for nome in ARTEFATOS:
        caminho = ANALYTICS / nome
        if not caminho.exists():
            falhas.append(f"{nome}: ausente em {caminho}")
            continue
        try:
            problemas = conferir(con, nome, caminho)
        except duckdb.Error as erro:
            problemas = [f"nao abriu como Parquet ({erro.__class__.__name__})"]
        falhas += [f"{nome}: {p}" for p in problemas]
        hash_ = sha256(caminho)
        if nome in ref and ref[nome] != hash_:
            (falhas if args.estrito else avisos).append(f"{nome}: SHA-256 diferente da referencia")
        linhas = um(con, "SELECT count(*) FROM read_parquet(?)", [str(caminho)])
        arquivos[nome] = {"sha256": hash_, "bytes": caminho.stat().st_size, "linhas": linhas,
                          "igual_a_referencia": ref.get(nome) == hash_}
        tamanho = f"{caminho.stat().st_size / 1e6:.2f}".replace(".", ",")
        print(f"{'OK   ' if not problemas else 'FALHA'} {nome}: {linhas:,}".replace(",", ".")
              + f" linhas, {tamanho} MB")
    if not any(f.endswith("ausente em " + str(ANALYTICS / n)) for f in falhas for n in ARTEFATOS):
        try:
            falhas += conferir_brasil(con)
        except duckdb.Error:
            falhas.append("nao foi possivel conferir o total nacional entre artefatos")

    for aviso in avisos:
        print(f"AVISO {aviso}")
    if falhas:
        print(f"\n{len(falhas)} falha(s); NAO publicar:")
        for falha in falhas:
            print(f"  - {falha}")
        return 1

    if args.explicar:
        explicar(con)
    manifesto = {
        "auditado_em_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "versao_codigo_git": commit_atual(),
        "piso_grupo": PISO_GRUPO,
        "verificacoes": ["colunas", "chave_do_grao_unica", "n_positivo", "notas_entre_0_e_1000",
                         "cdf_coerente", "piso_por_grupo", "brasil_igual_entre_artefatos", "sha256"],
        "artefatos": arquivos,
        "tempo_segundos": round(time.perf_counter() - inicio, 2),
    }
    MANIFESTO.write_text(json.dumps(manifesto, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nOK: {len(arquivos)} artefatos conferidos em {manifesto['tempo_segundos']} s; "
          f"manifesto em {MANIFESTO.relative_to(RAIZ) if MANIFESTO.is_relative_to(RAIZ) else MANIFESTO}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
