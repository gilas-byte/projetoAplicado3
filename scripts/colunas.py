#!/usr/bin/env python3
"""Fonte unica das listas de colunas e do contrato de dados do Radar ENEM.

Os scripts de profiling, dicionario e contrato importam daqui. Antes este
arquivo nao existia e cada script mantinha a sua propria lista, que ja
tinham divergido entre si.

O dicionario `CONTRATO` responde ao item 5 do Plano de Trabalho: para cada
campo, nome INEP, nome interno, destino, regra de ausencia, transformacao,
papel na elegibilidade e modulos consumidores.
"""

from __future__ import annotations

ANOS = [2019, 2020, 2021, 2022]

# Salario minimo nacional vigente na aplicacao de cada edicao. Base da
# conversao de Q006 em multiplos do salario minimo.
SALARIO_MINIMO = {2019: 998.00, 2020: 1045.00, 2021: 1100.00, 2022: 1212.00}

NOTAS = [
    "NU_NOTA_CN",
    "NU_NOTA_CH",
    "NU_NOTA_LC",
    "NU_NOTA_MT",
    "NU_NOTA_REDACAO",
]

NOTAS_COMPETENCIA = [f"NU_NOTA_COMP{i}" for i in range(1, 6)]

PRESENCA = [
    "TP_PRESENCA_CN",
    "TP_PRESENCA_CH",
    "TP_PRESENCA_LC",
    "TP_PRESENCA_MT",
]

QUESTIONARIO = [f"Q{i:03d}" for i in range(1, 26)]

# Categoricas que recebem distribuicao detalhada no profiling e dominio
# explicito no relatorio do dicionario. Cardinalidade contada de forma
# exata (ver scripts/profiling.py).
RECORTE = [
    "TP_FAIXA_ETARIA",
    "TP_SEXO",
    "TP_ESTADO_CIVIL",
    "TP_COR_RACA",
    "TP_NACIONALIDADE",
    "TP_ST_CONCLUSAO",
    "TP_ANO_CONCLUIU",
    "TP_ESCOLA",
    "TP_ENSINO",
    "IN_TREINEIRO",
    "TP_DEPENDENCIA_ADM_ESC",
    "TP_LOCALIZACAO_ESC",
    "SG_UF_ESC",
    "SG_UF_PROVA",
    "TP_LINGUA",
    "TP_STATUS_REDACAO",
] + QUESTIONARIO

# SG_UF_* nao tem dominio categorico no dicionario do INEP (a sigla e o
# proprio valor), entao fica fora das secoes que cruzam dominio documentado.
SEM_DOMINIO_DOCUMENTADO = {"SG_UF_ESC", "SG_UF_PROVA"}
RECORTE_COM_DOMINIO = [c for c in RECORTE if c not in SEM_DOMINIO_DOCUMENTADO]


# --------------------------------------------------------------- contrato

# Regras de ausencia reaproveitadas.
AUS_NUNCA = "Nunca ausente nas quatro edicoes."
AUS_NOTA = (
    "Ausente quando o participante nao fez a prova da area. Ausencia e nota "
    "zero sao estados distintos: zero significa prova feita e zerada."
)
AUS_ESCOLA = (
    "Preenchida apenas para quem declarou escola (73% a 84% de ausencia). "
    "Ausencia significa 'nao declarou', nao 'sem escola'."
)
AUS_QUEST = (
    "Praticamente sem ausencia, exceto 2020 (1,66%), quando o questionario "
    "nao foi respondido por parte dos inscritos."
)

ELEG_NAO = "Nao participa da elegibilidade."
MOD_DEFINIR = "a definir (Sprint 5)"
MOD_TODOS = "todos"


def _campo(
    interno: str,
    destino: str,
    ausencia: str,
    *,
    transformacao: str = "Nenhuma. Codigo do INEP preservado.",
    elegibilidade: str = ELEG_NAO,
    modulos: str = MOD_DEFINIR,
    nota: str = "",
) -> dict:
    return {
        "interno": interno,
        "destino": destino,
        "ausencia": ausencia,
        "transformacao": transformacao,
        "elegibilidade": elegibilidade,
        "modulos": modulos,
        "nota": nota,
    }


def _descartada(motivo: str) -> dict:
    return {
        "interno": "-",
        "destino": "descartada",
        "ausencia": "-",
        "transformacao": "-",
        "elegibilidade": ELEG_NAO,
        "modulos": "-",
        "nota": motivo,
    }


CONTRATO: dict[str, dict] = {}

# --- particao -----------------------------------------------------------
CONTRATO["NU_ANO"] = _campo(
    "ano",
    "particao",
    AUS_NUNCA,
    transformacao="Constante dentro de cada edicao; vira coluna de particao do Parquet.",
    modulos=MOD_TODOS,
)

# --- identificacao ------------------------------------------------------
CONTRATO["NU_INSCRICAO"] = _descartada(
    "Identificador individual. O produto so publica agregados, entao o "
    "numero de inscricao nao tem uso analitico e carrega risco de "
    "reidentificacao. Removido na passagem RAW -> TRUSTED."
)

# --- elegibilidade ------------------------------------------------------
for area in ["CN", "CH", "LC", "MT"]:
    CONTRATO[f"TP_PRESENCA_{area}"] = _campo(
        f"presenca_{area.lower()}",
        "analytics",
        AUS_NUNCA,
        transformacao="0=faltou, 1=presente, 2=eliminado. Codigo preservado.",
        elegibilidade=(
            "Criterio primario: elegivel exige valor 1 nas quatro areas. "
            "Eliminados (2) sao excluidos e contabilizados no funil."
        ),
        modulos=MOD_TODOS,
    )

CONTRATO["IN_TREINEIRO"] = _campo(
    "treineiro",
    "analytics",
    AUS_NUNCA,
    transformacao="0/1. Codigo preservado.",
    elegibilidade=(
        "Criterio primario: treineiros (1) ficam fora da populacao de "
        "comparacao, porque nao disputam vaga e sua distribuicao de notas "
        "responde a outra motivacao."
    ),
    modulos=MOD_TODOS,
)

# --- notas --------------------------------------------------------------
for area in ["CN", "CH", "LC", "MT"]:
    CONTRATO[f"NU_NOTA_{area}"] = _campo(
        f"nota_{area.lower()}",
        "analytics",
        AUS_NOTA,
        transformacao="Nenhuma. Escala TRI de 0 a 1000, ja comparavel dentro da edicao.",
        modulos=MOD_TODOS,
        nota="Entrada informada pelo usuario no produto.",
    )

CONTRATO["NU_NOTA_REDACAO"] = _campo(
    "nota_redacao",
    "analytics",
    AUS_NOTA,
    transformacao="Nenhuma. Escala de 0 a 1000.",
    modulos=MOD_TODOS,
    nota="Entrada informada pelo usuario no produto.",
)

for i in range(1, 6):
    CONTRATO[f"NU_NOTA_COMP{i}"] = _campo(
        f"nota_redacao_comp{i}",
        "analytics",
        AUS_NOTA,
        transformacao="Nenhuma. Escala de 0 a 200 por competencia.",
        nota="Competencia interna da redacao; nao e entrada do usuario.",
    )

CONTRATO["TP_STATUS_REDACAO"] = _campo(
    "status_redacao",
    "analytics",
    AUS_NOTA,
    transformacao="Codigo preservado. Distingue anulada, em branco e situacoes especiais.",
    nota="Necessaria para separar redacao zerada por anulacao de redacao zerada por desempenho.",
)

CONTRATO["TP_LINGUA"] = _campo(
    "lingua_estrangeira",
    "analytics",
    AUS_NUNCA,
    transformacao="0=ingles, 1=espanhol. Codigo preservado.",
    nota="Afeta a prova de LC; recorte relevante para comparar notas de LC.",
)

# --- participante -------------------------------------------------------
CONTRATO["TP_FAIXA_ETARIA"] = _campo(
    "faixa_etaria", "analytics", AUS_NUNCA, transformacao="20 faixas, estaveis nas quatro edicoes."
)
CONTRATO["TP_SEXO"] = _campo("sexo", "analytics", AUS_NUNCA)
CONTRATO["TP_ESTADO_CIVIL"] = _campo("estado_civil", "analytics", AUS_NUNCA)
CONTRATO["TP_COR_RACA"] = _campo(
    "cor_raca",
    "analytics",
    AUS_NUNCA,
    transformacao=(
        "Codigo preservado. O codigo 6 ('Nao dispoe da informacao') so "
        "existe no dicionario de 2021-2022 e so ocorre em 2021, com 5 "
        "registros: tratado como categoria propria, nunca agrupado com 0 "
        "('Nao declarado'), e suprimido pelo piso de tamanho de grupo."
    ),
)
CONTRATO["TP_NACIONALIDADE"] = _campo("nacionalidade", "analytics", AUS_NUNCA)

CONTRATO["TP_ST_CONCLUSAO"] = _campo(
    "situacao_conclusao",
    "analytics",
    AUS_NUNCA,
    transformacao=(
        "Codigo preservado. O rotulo cita o ano da prova ('concluirei em "
        "2019' vs 'em 2022'), mas o significado e relativo a edicao e "
        "portanto estavel: 2 = conclui no ano da prova, 3 = conclui depois. "
        "Comparavel entre edicoes desde que o rotulo nao seja exibido como "
        "ano absoluto."
    ),
    elegibilidade="Nao filtra por si, mas separa egressos de concluintes nos recortes.",
)

CONTRATO["TP_ANO_CONCLUIU"] = _campo(
    "anos_desde_conclusao",
    "analytics",
    AUS_NUNCA,
    transformacao=(
        "O codigo e um deslocamento relativo, nao um ano: vale "
        "ano_da_prova - codigo. Preservado como `anos_desde_conclusao` "
        "(comparavel entre edicoes) e derivado `ano_conclusao = ano - "
        "codigo` para leitura absoluta. O maior codigo de cada edicao "
        "(13/14/15/16, sempre igual a ano - 2006) rotula 'Antes de 2007' e "
        "vira ano_conclusao nulo com marca propria. Codigo 0 = nao informado."
    ),
)

CONTRATO["TP_ESCOLA"] = _campo(
    "tipo_escola",
    "analytics",
    AUS_NUNCA,
    transformacao=(
        "Codigo preservado. O codigo 4 ('Exterior') consta no dicionario de "
        "2019-2020 e nunca ocorre nos dados; nao vira categoria do produto."
    ),
)

CONTRATO["TP_ENSINO"] = _campo(
    "tipo_ensino",
    "analytics",
    "64% a 77% de ausencia: preenchida apenas para quem declarou escola.",
    transformacao=(
        "Codigo preservado. O codigo 3 ('Educacao de Jovens e Adultos') "
        "existe so em 2019-2020: recorte por EJA nao e comparavel nas "
        "quatro edicoes e fica restrito a essas duas."
    ),
)

# --- escola e local -----------------------------------------------------
CONTRATO["TP_DEPENDENCIA_ADM_ESC"] = _campo(
    "dependencia_adm_escola", "analytics", AUS_ESCOLA
)
CONTRATO["TP_LOCALIZACAO_ESC"] = _campo("localizacao_escola", "analytics", AUS_ESCOLA)
CONTRATO["SG_UF_ESC"] = _campo("uf_escola", "analytics", AUS_ESCOLA)
CONTRATO["SG_UF_PROVA"] = _campo(
    "uf_prova",
    "analytics",
    AUS_NUNCA,
    transformacao="Sigla preservada. 27 unidades federativas nas quatro edicoes.",
)
CONTRATO["CO_MUNICIPIO_PROVA"] = _campo(
    "cod_municipio_prova",
    "analytics",
    AUS_NUNCA,
    transformacao="Codigo IBGE preservado; chave estavel para recorte municipal.",
)
CONTRATO["NO_MUNICIPIO_PROVA"] = _campo(
    "municipio_prova",
    "analytics",
    AUS_NUNCA,
    transformacao="Nome preservado para exibicao; o codigo IBGE e a chave.",
)

CONTRATO["CO_UF_PROVA"] = _descartada("Redundante com SG_UF_PROVA, que e mais legivel.")
CONTRATO["CO_MUNICIPIO_ESC"] = _descartada(
    "Recorte geografico do produto usa o local de prova, que existe para "
    "todos. O municipio da escola falta em 73% a 84% dos registros."
)
CONTRATO["NO_MUNICIPIO_ESC"] = _descartada("Idem CO_MUNICIPIO_ESC.")
CONTRATO["CO_UF_ESC"] = _descartada("Redundante com SG_UF_ESC.")
CONTRATO["TP_SIT_FUNC_ESC"] = _descartada(
    "Situacao de funcionamento da escola. Atributo do estabelecimento, nao "
    "do participante; fora dos recortes previstos."
)

# --- prova objetiva: itens ---------------------------------------------
for area in ["CN", "CH", "LC", "MT"]:
    CONTRATO[f"CO_PROVA_{area}"] = _descartada(
        "Codigo do caderno, reemitido a cada aplicacao. So serve para "
        "analise item a item, fora do escopo descritivo do produto."
    )
    CONTRATO[f"TX_RESPOSTAS_{area}"] = _descartada(
        "Respostas item a item (45 a 50 caracteres por registro). Fora do "
        "escopo descritivo e responsavel pela maior parte do volume do CSV."
    )
    CONTRATO[f"TX_GABARITO_{area}"] = _descartada(
        "Gabarito item a item; so faz sentido junto de TX_RESPOSTAS."
    )

# --- questionario socioeconomico ---------------------------------------
CONTRATO["Q001"] = _campo("escolaridade_pai", "analytics", AUS_QUEST)
CONTRATO["Q002"] = _campo("escolaridade_mae", "analytics", AUS_QUEST)
CONTRATO["Q003"] = _campo("ocupacao_pai", "analytics", AUS_QUEST)
CONTRATO["Q004"] = _campo("ocupacao_mae", "analytics", AUS_QUEST)
CONTRATO["Q005"] = _campo(
    "pessoas_domicilio",
    "analytics",
    AUS_QUEST,
    transformacao="Numero de pessoas no domicilio, ja numerico.",
)
CONTRATO["Q006"] = _campo(
    "renda_familiar",
    "analytics",
    AUS_QUEST,
    transformacao=(
        "Codigo A-Q preservado e derivada `renda_sm` com o piso da faixa em "
        "multiplos do salario minimo da edicao. As 17 faixas sao definidas "
        "em multiplos do minimo, entao o codigo ja e comparavel entre "
        "edicoes nessa unidade; o que NAO e comparavel e o valor nominal em "
        "reais. Comparacao de poder de compra exige deflator, que o produto "
        "nao aplica - e uma limitacao declarada, nao um ajuste pendente."
    ),
    nota="Entrada informada pelo usuario no produto.",
)
CONTRATO["Q007"] = _campo("empregado_domestico", "analytics", AUS_QUEST)
CONTRATO["Q008"] = _campo("banheiros", "analytics", AUS_QUEST)
CONTRATO["Q009"] = _campo("quartos", "analytics", AUS_QUEST)
CONTRATO["Q010"] = _campo("carros", "analytics", AUS_QUEST)
CONTRATO["Q011"] = _campo("motocicletas", "analytics", AUS_QUEST)
CONTRATO["Q012"] = _campo("geladeiras", "analytics", AUS_QUEST)
CONTRATO["Q013"] = _campo("freezers", "analytics", AUS_QUEST)
CONTRATO["Q014"] = _campo("maquinas_lavar", "analytics", AUS_QUEST)
CONTRATO["Q015"] = _campo("maquinas_secar", "analytics", AUS_QUEST)
CONTRATO["Q016"] = _campo("micro_ondas", "analytics", AUS_QUEST)
CONTRATO["Q017"] = _campo("lava_loucas", "analytics", AUS_QUEST)
CONTRATO["Q018"] = _campo("aspirador", "analytics", AUS_QUEST)
CONTRATO["Q019"] = _campo("televisores", "analytics", AUS_QUEST)
CONTRATO["Q020"] = _campo("dvd", "analytics", AUS_QUEST)
CONTRATO["Q021"] = _campo("tv_assinatura", "analytics", AUS_QUEST)
CONTRATO["Q022"] = _campo("celulares", "analytics", AUS_QUEST)
CONTRATO["Q023"] = _campo("telefone_fixo", "analytics", AUS_QUEST)
CONTRATO["Q024"] = _campo("computadores", "analytics", AUS_QUEST)
CONTRATO["Q025"] = _campo("acesso_internet", "analytics", AUS_QUEST)


def mantidas() -> list[str]:
    return [c for c, d in CONTRATO.items() if d["destino"] != "descartada"]


def descartadas() -> list[str]:
    return [c for c, d in CONTRATO.items() if d["destino"] == "descartada"]
