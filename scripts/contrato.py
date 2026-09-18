#!/usr/bin/env python3
"""Gera o contrato de dados do Radar ENEM.

Atende ao item 5 do Plano de Trabalho: "para cada campo utilizado serao
documentados nome INEP, nome interno, tipo, dominio/categorias, regra de
ausencia, transformacao, elegibilidade e modulos consumidores".

O contrato nao e escrito a mao: as decisoes ficam em `scripts/colunas.py`
e este script as cruza com os fatos medidos (`docs/profiling/`) e
documentados (`docs/dicionario/`). Assim uma decisao nunca contradiz o
dado observado sem que a divergencia apareca.

Saidas (em docs/contrato/):
  contrato.json - um registro por campo, para consumo do ETL
  README.md     - contrato legivel, com as decisoes e suas justificativas

Uso:
  ./.venv/bin/python scripts/contrato.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from colunas import (  # noqa: E402
    ANOS,
    CONTRATO,
    SALARIO_MINIMO,
    descartadas,
    mantidas,
)

RAIZ = Path(__file__).resolve().parent.parent
PROFILING = RAIZ / "docs" / "profiling"
DICIONARIO = RAIZ / "docs" / "dicionario"
SAIDA = RAIZ / "docs" / "contrato"

# Piso de tamanho de grupo: abaixo disso o recorte nao e exibido. Proposta
# tecnica, pendente de aceite do PO (ver secao "Decisoes em aberto").
PISO_GRUPO = 100


def carregar() -> tuple[dict, dict]:
    perfis, dicts = {}, {}
    for ano in ANOS:
        p = PROFILING / f"profiling_{ano}.json"
        d = DICIONARIO / f"dicionario_{ano}.json"
        if not p.exists() or not d.exists():
            raise FileNotFoundError(
                f"Faltam insumos de {ano}. Rode antes:\n"
                f"  ./.venv/bin/python scripts/profiling.py\n"
                f"  ./.venv/bin/python scripts/dicionario.py"
            )
        perfis[ano] = json.loads(p.read_text(encoding="utf-8"))
        dicts[ano] = json.loads(d.read_text(encoding="utf-8"))
    return perfis, dicts


def montar(perfis: dict, dicts: dict) -> dict:
    """Cruza decisao + fato observado + dominio documentado, campo a campo."""
    campos = {}
    for inep, decisao in CONTRATO.items():
        por_ano = {}
        for ano in ANOS:
            col = next(
                (c for c in perfis[ano]["colunas"] if c["coluna"] == inep), None
            )
            var = dicts[ano]["variaveis"].get(inep, {})
            por_ano[ano] = {
                "tipo_observado": col["tipo"] if col else None,
                "pct_ausentes": col["pct_ausentes"] if col else None,
                "distintos": col["distintos"] if col else None,
                "bytes_texto": col["bytes_texto"] if col else None,
                "categorias": var.get("categorias", {}),
            }
        descricoes = [dicts[a]["variaveis"].get(inep, {}).get("descricao", "") for a in ANOS]
        campos[inep] = {
            "inep": inep,
            "descricao_inep": next((d for d in descricoes if d), ""),
            **decisao,
            "por_ano": por_ano,
        }
    return campos


# ---------------------------------------------------------------- relatorio


def gb(n: int | float) -> str:
    return f"{n / 1024 ** 3:.2f} GB"


def milhar(n) -> str:
    return f"{n:,}".replace(",", ".") if isinstance(n, int) else str(n)


def reais(valor: float) -> str:
    """Formata em pt-BR: milhar com ponto, decimal com virgula."""
    inteiro, _, centavos = f"{valor:,.2f}".partition(".")
    return f"R$ {inteiro.replace(',', '.')},{centavos}"


def gerar_relatorio(campos: dict, perfis: dict) -> str:
    L = []
    L.append("# Contrato de dados — Radar ENEM (2019-2022)")
    L.append("")
    L.append(
        "Gerado por `scripts/contrato.py`. As decisoes ficam em "
        "`scripts/colunas.py`; os numeros vem de `docs/profiling/` e os "
        "dominios de `docs/dicionario/`. Versao legivel do "
        "`contrato.json`, que e o que o ETL consome."
    )
    L.append("")

    mant, desc = mantidas(), descartadas()

    # --- 1. escopo -------------------------------------------------------
    L.append("## 1. Escopo")
    L.append("")
    L.append(
        f"Das 76 colunas das quatro edicoes, **{len(mant)} seguem para a "
        f"camada ANALYTICS** e **{len(desc)} sao descartadas** na passagem "
        "RAW -> TRUSTED."
    )
    L.append("")
    b_mant = b_desc = 0
    linhas_vol = []
    for ano in ANOS:
        por_col = {c["coluna"]: c["bytes_texto"] for c in perfis[ano]["colunas"]}
        m = sum(por_col.get(c, 0) for c in mant)
        d = sum(por_col.get(c, 0) for c in desc)
        b_mant += m
        b_desc += d
        linhas_vol.append(
            f"| {ano} | {gb(perfis[ano]['volume']['csv_bytes'])} | {gb(m)} | "
            f"{gb(d)} | {100 * d / (m + d):.1f}% |"
        )
    L.append("| Edicao | CSV bruto | Colunas mantidas | Colunas descartadas | % descartado |")
    L.append("| --- | --- | --- | --- | --- |")
    L.extend(linhas_vol)
    L.append(
        f"| **Total** | | **{gb(b_mant)}** | **{gb(b_desc)}** | "
        f"**{100 * b_desc / (b_mant + b_desc):.1f}%** |"
    )
    L.append("")
    L.append(
        "O peso por coluna foi medido (`strlen` sobre o valor em texto), nao "
        "estimado. Quase todo o descarte esta em `TX_RESPOSTAS_*` e "
        "`TX_GABARITO_*`: 8 colunas que guardam a resposta e o gabarito item "
        "a item e sozinhas respondem pela maior parte do arquivo, sem "
        "servir a nenhuma pergunta descritiva do produto."
    )
    L.append("")

    # --- 2. elegibilidade ------------------------------------------------
    L.append("## 2. Populacao elegivel")
    L.append("")
    L.append(
        "A populacao de comparacao de cada edicao e quem **compareceu as "
        "quatro areas** (`TP_PRESENCA_* = 1`) e **nao e treineiro** "
        "(`IN_TREINEIRO = 0`). Eliminados (`TP_PRESENCA_* = 2`) saem e sao "
        "contabilizados a parte: exclusao silenciosa e vedada pelo plano."
    )
    L.append("")
    L.append("| Edicao | Inscritos | Presentes nas 4 | Treineiros | Elegiveis | % do total |")
    L.append("| --- | --- | --- | --- | --- | --- |")
    for ano in ANOS:
        f = perfis[ano]["presenca"]["funil"]
        eleg = f["presentes_nas_quatro_areas_sem_treineiros"]
        L.append(
            f"| {ano} | {milhar(f['inscritos'])} | "
            f"{milhar(f['presentes_nas_quatro_areas'])} | "
            f"{milhar(f['treineiros'])} | {milhar(eleg)} | "
            f"{100 * eleg / f['inscritos']:.1f}% |"
        )
    L.append("")
    L.append(
        "A elegibilidade e aplicada **por edicao**, nunca entre edicoes: as "
        "quatro nao sao a mesma populacao e o produto compara posicao "
        "relativa dentro de cada ano."
    )
    L.append("")

    # --- 3. harmonizacao -------------------------------------------------
    L.append("## 3. Regras de harmonizacao")
    L.append("")
    L.append(
        "Tres variaveis mudam de rotulo entre edicoes sem mudar o conjunto "
        "de codigos. **Os codigos permanecem comparaveis** porque sao "
        "relativos a edicao; o que nao se pode e exibir o rotulo de um ano "
        "como se valesse para os outros."
    )
    L.append("")
    for inep in ["TP_ANO_CONCLUIU", "TP_ST_CONCLUSAO", "Q006"]:
        c = campos[inep]
        L.append(f"### `{inep}` -> `{c['interno']}`")
        L.append("")
        L.append(c["transformacao"])
        L.append("")
    L.append("Salario minimo usado na conversao de `Q006`:")
    L.append("")
    L.append("| Edicao | " + " | ".join(str(a) for a in ANOS) + " |")
    L.append("| --- |" + " --- |" * len(ANOS))
    L.append(
        "| Salario minimo | "
        + " | ".join(reais(SALARIO_MINIMO[a]) for a in ANOS)
        + " |"
    )
    L.append("")
    L.append(
        "Categorias que entram ou saem ao longo do periodo — filtrar por "
        "uma delas restringe o recorte as edicoes em que existe:"
    )
    L.append("")
    L.append("| Variavel | Codigo | Situacao |")
    L.append("| --- | --- | --- |")
    L.append(
        "| `TP_COR_RACA` | `6` | Documentada em 2021-2022; ocorre so em "
        "2021, com 5 registros. Categoria propria, nunca agrupada com `0`. |"
    )
    L.append("| `TP_ENSINO` | `3` | EJA. Existe so em 2019-2020. |")
    L.append("| `TP_ESCOLA` | `4` | 'Exterior'. Documentada em 2019-2020, nunca observada. |")
    L.append("")

    # --- 4. campos mantidos ---------------------------------------------
    L.append("## 4. Campos mantidos")
    L.append("")
    L.append(
        "`cat.` = categorias no dicionario da edicao mais recente em que a "
        "variavel tem dominio. `aus.` = maior percentual de ausencia entre "
        "as quatro edicoes."
    )
    L.append("")
    L.append("| Nome INEP | Nome interno | Tipo | cat. | aus. | Regra de ausencia |")
    L.append("| --- | --- | --- | --- | --- | --- |")
    for inep in mant:
        c = campos[inep]
        tipo = next(
            (c["por_ano"][a]["tipo_observado"] for a in ANOS if c["por_ano"][a]["tipo_observado"]),
            "-",
        )
        cats = next(
            (len(c["por_ano"][a]["categorias"]) for a in reversed(ANOS)
             if c["por_ano"][a]["categorias"]),
            0,
        )
        aus = max(
            (c["por_ano"][a]["pct_ausentes"] or 0) for a in ANOS
        )
        L.append(
            f"| `{inep}` | `{c['interno']}` | {tipo} | {cats or '-'} | "
            f"{aus:.1f}% | {c['ausencia']} |"
        )
    L.append("")

    L.append("### Transformacoes e papel na elegibilidade")
    L.append("")
    L.append("Campos cuja regra nao e a identidade, ou que filtram populacao.")
    L.append("")
    for inep in mant:
        c = campos[inep]
        trivial = c["transformacao"].startswith("Nenhuma")
        if trivial and c["elegibilidade"].startswith("Nao participa"):
            continue
        L.append(f"**`{inep}` -> `{c['interno']}`**")
        L.append("")
        if not trivial:
            L.append(f"- Transformacao: {c['transformacao']}")
        if not c["elegibilidade"].startswith("Nao participa"):
            L.append(f"- Elegibilidade: {c['elegibilidade']}")
        if c["nota"]:
            L.append(f"- Nota: {c['nota']}")
        L.append("")

    # --- 5. campos descartados ------------------------------------------
    L.append("## 5. Campos descartados")
    L.append("")
    L.append("| Nome INEP | Peso (4 edicoes) | Motivo |")
    L.append("| --- | --- | --- |")
    for inep in sorted(
        desc,
        key=lambda x: -sum(campos[x]["por_ano"][a]["bytes_texto"] or 0 for a in ANOS),
    ):
        c = campos[inep]
        peso = sum(c["por_ano"][a]["bytes_texto"] or 0 for a in ANOS)
        L.append(f"| `{inep}` | {gb(peso)} | {c['nota']} |")
    L.append("")

    # --- 6. decisoes em aberto ------------------------------------------
    L.append("## 6. Decisoes em aberto")
    L.append("")
    L.append(
        f"1. **Piso de tamanho de grupo.** Proposta tecnica: nao exibir "
        f"recorte com menos de **{PISO_GRUPO} participantes** elegiveis. "
        f"Cobre o caso concreto ja detectado (`TP_COR_RACA = 6`, com 5 "
        f"registros em 2021) e mantem folga sobre o minimo estatistico "
        f"usual de 30. Pendente de aceite do PO."
    )
    L.append(
        "2. **Modulos consumidores.** O plano preve quatro modulos autorais "
        "definidos na Sprint 5; ate la os campos estao marcados como `a "
        "definir`. Os campos de nota, presenca e `IN_TREINEIRO` ja constam "
        "como `todos`, por sustentarem a elegibilidade comum."
    )
    L.append(
        "3. **Deflator.** As faixas de `Q006` sao estaveis em multiplos do "
        "salario minimo, mas comparar poder de compra entre 2019 e 2022 "
        "exigiria deflacionar. O produto **nao** aplica deflator: e uma "
        "limitacao declarada, coerente com a ressalva do plano de que o "
        "Radar ENEM e instrumento descritivo."
    )
    L.append("")

    return "\n".join(L)


def main() -> int:
    SAIDA.mkdir(parents=True, exist_ok=True)
    perfis, dicts = carregar()
    campos = montar(perfis, dicts)

    destino = SAIDA / "contrato.json"
    destino.write_text(
        json.dumps(
            {
                "recorte": ANOS,
                "piso_grupo": PISO_GRUPO,
                "salario_minimo": SALARIO_MINIMO,
                "campos": campos,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"contrato -> {destino.relative_to(RAIZ)}")

    relatorio = SAIDA / "README.md"
    relatorio.write_text(gerar_relatorio(campos, perfis), encoding="utf-8")
    print(f"relatorio -> {relatorio.relative_to(RAIZ)}")
    print(f"  {len(mantidas())} campos mantidos, {len(descartadas())} descartados")
    return 0


if __name__ == "__main__":
    sys.exit(main())
