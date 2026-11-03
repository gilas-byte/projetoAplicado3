#!/usr/bin/env python3
"""Auditoria dos limites de exibição do módulo Recorte territorial (DL-04, item 8).

Reproduz os números citados na DL-04 a partir de data/analytics/dist_territorial.parquet:

  1. Regra atual (limite já arredondado): rótulos falsos e inversões de ordem.
  2. Regra anterior (limite sem arredondar): quantos grupos têm inversão.
  3. Risco residual: mudanças da posição exibida em nota de uma só pessoa,
     sem limite e com limite, e quantas ficam em grupos com menos de 100 mil.
  4. Menor "abaixo + metade dos empatados" entre as posições exatas exibidas.
  5. Alcance do limite: pessoas até a ponta (empatados pela metade) na nota
     observada mais distante que ainda aparece em limite, por grupo.

Varredura: grupos de UF e região (o Brasil segue exato, ADR-001), notas de 0
a 1000 de 0,1 em 0,1. Os itens 1, 2 e 4 cobrem as quatro edições e as cinco
áreas; o item 3 cobre 2022 e as quatro áreas objetivas, como a tabela da DL-04.

O resultado vai para data/analytics/_auditoria_limites.json (fora do git) e
para a tela. Nenhuma nota individual é gravada: só contagens agregadas.

Uso (depois de scripts/territorial.py):
  ./.venv/bin/python scripts/auditoria_limites.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from colunas import PISO_GRUPO  # noqa: E402
from territorial import (  # noqa: E402
    ANALYTICS,
    BRASIL,
    DIST_TERRITORIAL,
    carregar,
    formatar_percentil,
    limites_exibicao,
    texto_da_posicao,
)

SAIDA = ANALYTICS / "_auditoria_limites.json"
GRADE = range(0, 10001)  # notas em décimos: 0,0 a 1000,0
AREAS_OBJETIVAS = ("cn", "ch", "lc", "mt")
GRANDE = 100_000


def varrer(cdf):
    """Para cada nota da grade: (décimos, 2·abaixo + iguais, iguais, abaixo). Um passe só."""
    por_decimo = {round(nota * 10): (n, abaixo) for nota, n, abaixo in cdf}
    total = cdf[-1][1] + cdf[-1][2]
    abaixo = 0
    for d in GRADE:
        n, _ = por_decimo.get(d, (0, None))
        yield d, 2 * abaixo + n, n, abaixo
        abaixo += n
    if abaixo != total:
        raise AssertionError("grade não cobre todas as notas do grupo")


def chave(texto: str) -> tuple:
    """Posição lida na tela: "abaixo de X" fica logo abaixo de X, "acima de X" logo acima.

    Inversão é uma nota maior mostrar posição que se lê como menor: "100,0%"
    seguido de "acima de 99,9%" é inversão (99,9 < 100,0).
    """
    if texto.startswith("abaixo de"):
        return (float(texto[10:].rstrip("%").replace(",", ".")), 0)
    if texto.startswith("acima de"):
        return (float(texto[9:].rstrip("%").replace(",", ".")), 2)
    return (float(texto.rstrip("%").replace(",", ".")), 1)


def texto_sem_arredondar_limite(dobro: int, total: int, piso: int = PISO_GRUPO) -> str:
    """Regra anterior: compara p com 100·(N−piso)/N e 100·piso/N sem arredondar."""
    inferior, superior = limites_exibicao(total, piso)
    # p > 100(N−piso)/N  <=>  dobro > 2(N−piso);  p < 100·piso/N  <=>  dobro < 2·piso
    if dobro > 2 * (total - piso):
        return f"acima de {superior / 10:.1f}%".replace(".", ",")
    if dobro < 2 * piso:
        return f"abaixo de {inferior / 10:.1f}%".replace(".", ",")
    return formatar_percentil(dobro * 100 / (2 * total))


def auditar(cdfs, piso: int = PISO_GRUPO) -> dict:
    grupos = {k: v for k, v in cdfs.items() if k[2] != BRASIL}
    falsos = inversoes = 0
    grupos_inversao_antiga = set()
    menor_lado = None  # menor "abaixo + metade dos empatados" (ou o simétrico) entre exatas
    exemplo_lado = None
    menor_estrito = None
    exatas_com_menos_de_piso_estrito = 0
    alcance: dict[tuple, tuple[float, int]] = {}
    residual = {"sem_limite": 0, "com_limite": 0, "com_limite_grupo_menor_100mil": 0}
    combinacoes = {"sem_limite": set(), "com_limite": set()}
    combinacoes_total = set()

    for (ano, area, grupo), cdf in sorted(grupos.items()):
        total = cdf[-1][1] + cdf[-1][2]
        inferior, superior = limites_exibicao(total, piso)
        do_residual = ano == 2022 and area in AREAS_OBJETIVAS
        if do_residual:
            combinacoes_total.add((area, grupo))
        anterior = anterior_antigo = None
        texto_ant = livre_ant = None
        for d, dobro, n, abaixo in varrer(cdf):
            p = dobro * 100 / (2 * total)
            texto, em_limite = texto_da_posicao(dobro, total, piso)
            # 1. rótulo falso e inversão na regra atual
            if texto.startswith("acima de") and not p > superior / 10:
                falsos += 1
            if texto.startswith("abaixo de") and not p < inferior / 10:
                falsos += 1
            k = chave(texto)
            if anterior is not None and k < anterior:
                inversoes += 1
            anterior = k
            # 2. inversão na regra anterior
            k_antigo = chave(texto_sem_arredondar_limite(dobro, total, piso))
            if anterior_antigo is not None and k_antigo < anterior_antigo:
                grupos_inversao_antiga.add((ano, area, grupo))
            anterior_antigo = k_antigo
            # 4. lado mínimo das posições exatas, com empatados pela metade, e o
            #    menor número de pessoas estritamente abaixo/acima (empates grandes)
            if not em_limite:
                lado = min(dobro, 2 * total - dobro) / 2
                if menor_lado is None or lado < menor_lado:
                    menor_lado = lado
                    exemplo_lado = {"ano": ano, "area": area, "grupo": grupo, "nota": d / 10,
                                    "texto": texto, "estritamente_abaixo": abaixo,
                                    "empatados": n, "total": total}
                estrito = min(abaixo, total - abaixo - n)
                if menor_estrito is None or estrito < menor_estrito["estritamente_de_um_lado"]:
                    menor_estrito = {"estritamente_de_um_lado": estrito, "ano": ano, "area": area,
                                     "grupo": grupo, "nota": d / 10, "texto": texto,
                                     "estritamente_abaixo": abaixo, "empatados": n,
                                     "estritamente_acima": total - abaixo - n, "total": total}
                if abaixo < piso or total - abaixo - n < piso:
                    exatas_com_menos_de_piso_estrito += 1
            # 5. alcance do limite: pessoas até a ponta (empatados pela metade)
            #    na nota observada mais distante que ainda aparece em limite
            if em_limite and n:
                distancia = total - abaixo - n / 2 if texto.startswith("acima") else abaixo + n / 2
                if distancia > alcance.get((ano, area, grupo), (0, 0))[0]:
                    alcance[(ano, area, grupo)] = (distancia, total)
            # 3. risco residual: a posição exibida muda na nota de uma só pessoa
            livre = formatar_percentil(p)
            if do_residual and texto_ant is not None and n == 1:
                if livre != livre_ant:
                    residual["sem_limite"] += 1
                    combinacoes["sem_limite"].add((area, grupo))
                if texto != texto_ant:
                    residual["com_limite"] += 1
                    combinacoes["com_limite"].add((area, grupo))
                    if total < GRANDE:
                        residual["com_limite_grupo_menor_100mil"] += 1
            texto_ant, livre_ant = texto, livre

    return {
        "grupos_varridos": len(grupos),
        "regra_atual": {"rotulos_falsos": falsos, "inversoes": inversoes},
        "regra_anterior_grupos_com_inversao": len(grupos_inversao_antiga),
        "menor_lado_posicao_exata": {"abaixo_mais_metade_empatados": menor_lado, "exemplo": exemplo_lado,
                                     "menor_estritamente_de_um_lado": menor_estrito,
                                     "posicoes_exatas_com_menos_de_piso_estritamente_de_um_lado":
                                         exatas_com_menos_de_piso_estrito},
        "risco_residual_2022_areas_objetivas": {
            "combinacoes_varridas": len(combinacoes_total),
            "ocorrencias": residual,
            "combinacoes_com_ocorrencia": {k: len(v) for k, v in combinacoes.items()},
        },
        "alcance_do_limite": {
            "grupos_acima_de_150_pessoas": sum(dist > 150 for dist, _ in alcance.values()),
            "exemplos_matematica_2019": {
                grupo: {"pessoas_ate_a_ponta": alcance[(2019, "mt", grupo)][0],
                        "participantes": alcance[(2019, "mt", grupo)][1]}
                for grupo in ("UF-RR", "UF-SP", "RG-NE") if (2019, "mt", grupo) in alcance
            },
        },
    }


def main() -> int:
    if not DIST_TERRITORIAL.exists():
        print("Artefato ausente. Rode antes: scripts/territorial.py", file=sys.stderr)
        return 1
    resultado = auditar(carregar(DIST_TERRITORIAL))
    SAIDA.write_text(json.dumps(resultado, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(resultado, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
