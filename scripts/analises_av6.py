#!/usr/bin/env python3
"""Análises estatísticas da AV6 sobre os artefatos reais da camada ANALYTICS.

Quatro análises, todas sobre distribuições agregadas (nenhum dado individual):

1. Caixa protegida por edição e área: quartis, IQR e bigodes nos percentis 5 e
   95 (boxplot do Plano de Trabalho, item 6; Estatística I, ementa).
2. Drift entre edições (Engenharia de Dados e MLOps, aula 10 e laboratório de
   Data Drift): estatística D de Kolmogorov-Smirnov, exata, e PSI.
3. Z-Score contra a curva normal: quanto o percentil Φ(z) erraria em relação
   ao percentil exato (motivo da CDF exata, ADR-001), com assimetria e curtose.
4. Amostragem (Estatística I, ementa): erro dos quantis estimados com amostra
   aleatória simples e com amostra estratificada por UF, contra a população.

Entrada: data/analytics/dist_exata.parquet e dist_territorial.parquet (fora do
git). Saída: docs/av6/analises_av6.json, com o hash das entradas e o commit do
código. Nenhuma contagem abaixo do piso vai para a saída: os tamanhos
publicados são de edições e áreas inteiras ou de amostras com milhares de pessoas.

Uso:
  ./.venv/bin/python scripts/analises_av6.py            # todas as análises
  ./.venv/bin/python scripts/analises_av6.py --rapido   # amostragem com 20 repetições
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import subprocess
import sys
import time
from bisect import bisect_right
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path

import duckdb

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))

from estatistica import (  # noqa: E402
    caixa_protegida,
    ks_distancia,
    percentil_normal,
    psi,
    quantil,
    resumo,
)

ANALYTICS = RAIZ / "data" / "analytics"
DIST_EXATA = ANALYTICS / "dist_exata.parquet"
DIST_TERRITORIAL = ANALYTICS / "dist_territorial.parquet"
SAIDA = RAIZ / "docs" / "av6" / "analises_av6.json"

AREAS = ("cn", "ch", "lc", "mt", "redacao")
QUANTIS_AMOSTRA = (0.10, 0.25, 0.50, 0.75, 0.90)


def sha256(caminho: Path) -> str:
    h = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def commit_atual() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=RAIZ, capture_output=True,
                              text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def carregar_exata() -> dict[tuple[int, str], list[tuple[float, int, int]]]:
    linhas = duckdb.execute(
        "SELECT ano, area, nota, n, abaixo FROM read_parquet(?) ORDER BY ano, area, nota",
        [str(DIST_EXATA)],
    ).fetchall()
    cdfs: dict[tuple[int, str], list[tuple[float, int, int]]] = {}
    for ano, area, nota, n, abaixo in linhas:
        cdfs.setdefault((int(ano), area), []).append((float(nota), int(n), int(abaixo)))
    return cdfs


def carregar_ufs(ano: int, area: str) -> dict[str, list[tuple[float, int, int]]]:
    linhas = duckdb.execute(
        "SELECT grupo, nota, n, abaixo FROM read_parquet(?) "
        "WHERE ano = ? AND area = ? AND grupo LIKE 'UF-%' ORDER BY grupo, nota",
        [str(DIST_TERRITORIAL), ano, area],
    ).fetchall()
    ufs: dict[str, list[tuple[float, int, int]]] = {}
    for grupo, nota, n, abaixo in linhas:
        ufs.setdefault(grupo, []).append((float(nota), int(n), int(abaixo)))
    return ufs


# ------------------------------------------------------------- 1. caixa


def analise_caixas(cdfs) -> list[dict]:
    saida = []
    for (ano, area), cdf in sorted(cdfs.items()):
        medidas = resumo(cdf)
        caixa = caixa_protegida(cdf)
        saida.append({
            "ano": ano, "area": area, "participantes": medidas["N"],
            "media": round(medidas["media"], 2), "desvio": round(medidas["desvio"], 2),
            "p05": caixa["bigode_inferior"], "q1": caixa["q1"], "mediana": caixa["mediana"],
            "q3": caixa["q3"], "iqr": round(caixa["iqr"], 1), "p95": caixa["bigode_superior"],
        })
    return saida


# ------------------------------------------------------------- 2. drift


def analise_drift(cdfs) -> list[dict]:
    anos = sorted({ano for ano, _ in cdfs})
    pares = list(zip(anos, anos[1:])) + ([(anos[0], anos[-1])] if len(anos) > 2 else [])
    saida = []
    for area in AREAS:
        for ref, atual in pares:
            a, b = cdfs[(ref, area)], cdfs[(atual, area)]
            saida.append({
                "area": area, "referencia": ref, "atual": atual,
                "ks_d": round(ks_distancia(a, b), 4),
                "psi": round(psi(a, b), 4),
                "mediana_referencia": quantil(a, 0.5), "mediana_atual": quantil(b, 0.5),
            })
    return saida


# ------------------------------------------------------------- 3. normal


def momentos(cdf) -> tuple[float, float]:
    """Assimetria e curtose em excesso (momentos populacionais)."""
    medidas = resumo(cdf)
    media, desvio, total = medidas["media"], medidas["desvio"], medidas["N"]
    m3 = sum(n * (nota - media) ** 3 for nota, n, _ in cdf) / total
    m4 = sum(n * (nota - media) ** 4 for nota, n, _ in cdf) / total
    return m3 / desvio ** 3, m4 / desvio ** 4 - 3


def analise_normal(cdfs) -> list[dict]:
    saida = []
    for (ano, area), cdf in sorted(cdfs.items()):
        medidas = resumo(cdf)
        media, desvio, total = medidas["media"], medidas["desvio"], medidas["N"]
        soma_abs, maior = 0.0, 0.0
        for nota, n, abaixo in cdf:
            exato = (abaixo + n / 2) / total * 100
            erro = abs(percentil_normal((nota - media) / desvio) - exato)
            soma_abs += n * erro
            maior = max(maior, erro)
        pontos = {}
        for p in (0.10, 0.50, 0.90):
            nota = quantil(cdf, p)
            _, n, abaixo = next(item for item in cdf if item[0] == nota)
            pontos[f"p{int(p * 100):02d}"] = {
                "nota": nota,
                "percentil_exato": round((abaixo + n / 2) / total * 100, 2),
                "percentil_normal": round(percentil_normal((nota - media) / desvio), 2),
            }
        assimetria, curtose = momentos(cdf)
        saida.append({
            "ano": ano, "area": area,
            "erro_medio_pp": round(soma_abs / total, 2), "erro_maximo_pp": round(maior, 2),
            "assimetria": round(assimetria, 3), "curtose_excesso": round(curtose, 3),
            "pontos": pontos,
        })
    return saida


# ------------------------------------------------------------- 4. amostragem


def sorteador(cdf):
    """Função que sorteia uma nota da distribuição (com reposição)."""
    notas = [nota for nota, _, _ in cdf]
    acumulado = [abaixo + n for _, n, abaixo in cdf]
    total = acumulado[-1]
    return lambda gerador: notas[bisect_right(acumulado, gerador.randrange(total))]


def quantil_amostra(ordenada: list[float], p: float) -> float:
    indice = max(-(-Fraction(str(p)) * len(ordenada) // 1) - 1, 0)
    return ordenada[int(indice)]


def analise_amostragem(cdfs, ano: int, area: str, fracao: float, repeticoes: int,
                       semente: int = 2026) -> dict:
    ufs = carregar_ufs(ano, area)
    populacao = cdfs[(ano, area)]
    total = sum(cdf[-1][1] + cdf[-1][2] for cdf in ufs.values())
    tamanho = round(total * fracao)
    reais = {p: quantil(populacao, p) for p in QUANTIS_AMOSTRA}
    sorteia_pop = sorteador(populacao)
    estratos = {uf: (sorteador(cdf), round(tamanho * (cdf[-1][1] + cdf[-1][2]) / total))
                for uf, cdf in ufs.items()}
    gerador = random.Random(semente)
    erros = {"simples": {p: [] for p in QUANTIS_AMOSTRA}, "estratificada": {p: [] for p in QUANTIS_AMOSTRA}}
    for _ in range(repeticoes):
        simples = sorted(sorteia_pop(gerador) for _ in range(tamanho))
        estratificada = sorted(s(gerador) for s, n_h in estratos.values() for _ in range(n_h))
        for p in QUANTIS_AMOSTRA:
            erros["simples"][p].append(quantil_amostra(simples, p) - reais[p])
            erros["estratificada"][p].append(quantil_amostra(estratificada, p) - reais[p])

    def resumir(lista):
        return {"erro_medio_absoluto": round(sum(abs(e) for e in lista) / len(lista), 2),
                "rmse": round((sum(e * e for e in lista) / len(lista)) ** 0.5, 2),
                "maior_erro_absoluto": round(max(abs(e) for e in lista), 2)}

    return {
        "ano": ano, "area": area, "fracao": fracao, "tamanho_amostra": tamanho,
        "populacao": total, "repeticoes": repeticoes, "estratos": len(ufs),
        "alocacao": "proporcional ao tamanho da UF", "sorteio": "com reposição",
        "quantis": {
            f"p{int(p * 100):02d}": {"populacao": reais[p],
                                      "simples": resumir(erros["simples"][p]),
                                      "estratificada": resumir(erros["estratificada"][p])}
            for p in QUANTIS_AMOSTRA
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--rapido", action="store_true", help="amostragem com 20 repetições")
    args = parser.parse_args()
    for caminho in (DIST_EXATA, DIST_TERRITORIAL):
        if not caminho.exists():
            print(f"Falta {caminho.relative_to(RAIZ)}; rode o pipeline ou copie os artefatos.")
            return 1

    inicio = time.perf_counter()
    cdfs = carregar_exata()
    repeticoes = 20 if args.rapido else 200
    resultado = {
        "gerado_em_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "versao_codigo_git": commit_atual(),
        "entradas": {c.name: sha256(c) for c in (DIST_EXATA, DIST_TERRITORIAL)},
        "caixas": analise_caixas(cdfs),
        "drift": analise_drift(cdfs),
        "normal": analise_normal(cdfs),
        "amostragem": [analise_amostragem(cdfs, 2022, area, 0.01, repeticoes)
                       for area in ("mt", "redacao")],
    }
    resultado["tempo_segundos"] = round(time.perf_counter() - inicio, 1)
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps(resultado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: {SAIDA.relative_to(RAIZ)} em {resultado['tempo_segundos']} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
