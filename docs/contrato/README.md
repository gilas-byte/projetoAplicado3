# Contrato de dados — Radar ENEM (2019-2022)

Gerado por `scripts/contrato.py`. As decisoes ficam em `scripts/colunas.py`; os numeros vem de `docs/profiling/` e os dominios de `docs/dicionario/`. Versao legivel do `contrato.json`, que e o que o ETL consome.

## 1. Escopo

Das 76 colunas das quatro edicoes, **58 seguem para a camada ANALYTICS** e **18 sao descartadas** na passagem RAW -> TRUSTED.

| Edicao | CSV bruto | Colunas mantidas | Colunas descartadas | % descartado |
| --- | --- | --- | --- | --- |
| 2019 | 2.24 GB | 0.44 GB | 1.45 GB | 76.7% |
| 2020 | 1.89 GB | 0.44 GB | 1.05 GB | 70.6% |
| 2021 | 1.40 GB | 0.28 GB | 0.88 GB | 75.6% |
| 2022 | 1.46 GB | 0.29 GB | 0.92 GB | 75.9% |
| **Total** | | **1.45 GB** | **4.30 GB** | **74.7%** |

O peso por coluna foi medido (`strlen` sobre o valor em texto), nao estimado. Quase todo o descarte esta em `TX_RESPOSTAS_*` e `TX_GABARITO_*`: 8 colunas que guardam a resposta e o gabarito item a item e sozinhas respondem pela maior parte do arquivo, sem servir a nenhuma pergunta descritiva do produto.

## 2. Populacao elegivel

A populacao de comparacao de cada edicao e quem **compareceu as quatro areas** (`TP_PRESENCA_* = 1`) e **nao e treineiro** (`IN_TREINEIRO = 0`). Eliminados (`TP_PRESENCA_* = 2`) saem e sao contabilizados a parte: exclusao silenciosa e vedada pelo plano.

| Edicao | Inscritos | Presentes nas 4 | Treineiros | Elegiveis | % do total |
| --- | --- | --- | --- | --- | --- |
| 2019 | 5.095.171 | 3.701.910 | 616.667 | 3.174.212 | 62.3% |
| 2020 | 5.783.109 | 2.588.681 | 557.425 | 2.242.169 | 38.8% |
| 2021 | 3.389.832 | 2.238.107 | 437.190 | 1.870.734 | 55.2% |
| 2022 | 3.476.105 | 2.344.823 | 512.732 | 1.927.753 | 55.5% |

A elegibilidade e aplicada **por edicao**, nunca entre edicoes: as quatro nao sao a mesma populacao e o produto compara posicao relativa dentro de cada ano.

## 3. Regras de harmonizacao

Tres variaveis mudam de rotulo entre edicoes sem mudar o conjunto de codigos. **Os codigos permanecem comparaveis** porque sao relativos a edicao; o que nao se pode e exibir o rotulo de um ano como se valesse para os outros.

### `TP_ANO_CONCLUIU` -> `anos_desde_conclusao`

O codigo e um deslocamento relativo, nao um ano: vale ano_da_prova - codigo. Preservado como `anos_desde_conclusao` (comparavel entre edicoes) e derivado `ano_conclusao = ano - codigo` para leitura absoluta. O maior codigo de cada edicao (13/14/15/16, sempre igual a ano - 2006) rotula 'Antes de 2007' e vira ano_conclusao nulo com marca propria. Codigo 0 = nao informado.

### `TP_ST_CONCLUSAO` -> `situacao_conclusao`

Codigo preservado. O rotulo cita o ano da prova ('concluirei em 2019' vs 'em 2022'), mas o significado e relativo a edicao e portanto estavel: 2 = conclui no ano da prova, 3 = conclui depois. Comparavel entre edicoes desde que o rotulo nao seja exibido como ano absoluto.

### `Q006` -> `renda_familiar`

Codigo A-Q preservado e derivada `renda_sm` com o piso da faixa em multiplos do salario minimo da edicao. As 17 faixas sao definidas em multiplos do minimo, entao o codigo ja e comparavel entre edicoes nessa unidade; o que NAO e comparavel e o valor nominal em reais. Comparacao de poder de compra exige deflator, que o produto nao aplica - e uma limitacao declarada, nao um ajuste pendente.

Salario minimo usado na conversao de `Q006`:

| Edicao | 2019 | 2020 | 2021 | 2022 |
| --- | --- | --- | --- | --- |
| Salario minimo | R$ 998,00 | R$ 1.045,00 | R$ 1.100,00 | R$ 1.212,00 |

Categorias que entram ou saem ao longo do periodo — filtrar por uma delas restringe o recorte as edicoes em que existe:

| Variavel | Codigo | Situacao |
| --- | --- | --- |
| `TP_COR_RACA` | `6` | Documentada em 2021-2022; ocorre so em 2021, abaixo do piso de grupo. Categoria propria, nunca agrupada com `0`, suprimida de toda saida. |
| `TP_ENSINO` | `3` | EJA. Documentada em 2019-2020, nunca observada. |
| `TP_ESCOLA` | `4` | 'Exterior'. Documentada em 2019-2020, nunca observada. |

## 4. Campos mantidos

`cat.` = categorias no dicionario da edicao mais recente em que a variavel tem dominio. `aus.` = maior percentual de ausencia entre as quatro edicoes.

| Nome INEP | Nome interno | Tipo | cat. | aus. | Regra de ausencia |
| --- | --- | --- | --- | --- | --- |
| `NU_ANO` | `ano` | BIGINT | - | 0.0% | Nunca ausente nas quatro edicoes. |
| `TP_PRESENCA_CN` | `presenca_cn` | BIGINT | 3 | 0.0% | Nunca ausente nas quatro edicoes. |
| `TP_PRESENCA_CH` | `presenca_ch` | BIGINT | 3 | 0.0% | Nunca ausente nas quatro edicoes. |
| `TP_PRESENCA_LC` | `presenca_lc` | BIGINT | 3 | 0.0% | Nunca ausente nas quatro edicoes. |
| `TP_PRESENCA_MT` | `presenca_mt` | BIGINT | 3 | 0.0% | Nunca ausente nas quatro edicoes. |
| `IN_TREINEIRO` | `treineiro` | BIGINT | 2 | 0.0% | Nunca ausente nas quatro edicoes. |
| `NU_NOTA_CN` | `nota_cn` | DOUBLE | - | 55.1% | Ausente quando o participante nao fez a prova da area. Ausencia e nota zero sao estados distintos: zero significa prova feita e zerada. |
| `NU_NOTA_CH` | `nota_ch` | DOUBLE | - | 52.4% | Ausente quando o participante nao fez a prova da area. Ausencia e nota zero sao estados distintos: zero significa prova feita e zerada. |
| `NU_NOTA_LC` | `nota_lc` | DOUBLE | - | 52.4% | Ausente quando o participante nao fez a prova da area. Ausencia e nota zero sao estados distintos: zero significa prova feita e zerada. |
| `NU_NOTA_MT` | `nota_mt` | DOUBLE | - | 55.1% | Ausente quando o participante nao fez a prova da area. Ausencia e nota zero sao estados distintos: zero significa prova feita e zerada. |
| `NU_NOTA_REDACAO` | `nota_redacao` | BIGINT | - | 52.4% | Ausente quando o participante nao fez a prova da area. Ausencia e nota zero sao estados distintos: zero significa prova feita e zerada. |
| `NU_NOTA_COMP1` | `nota_redacao_comp1` | BIGINT | - | 52.4% | Ausente quando o participante nao fez a prova da area. Ausencia e nota zero sao estados distintos: zero significa prova feita e zerada. |
| `NU_NOTA_COMP2` | `nota_redacao_comp2` | BIGINT | - | 52.4% | Ausente quando o participante nao fez a prova da area. Ausencia e nota zero sao estados distintos: zero significa prova feita e zerada. |
| `NU_NOTA_COMP3` | `nota_redacao_comp3` | BIGINT | - | 52.4% | Ausente quando o participante nao fez a prova da area. Ausencia e nota zero sao estados distintos: zero significa prova feita e zerada. |
| `NU_NOTA_COMP4` | `nota_redacao_comp4` | BIGINT | - | 52.4% | Ausente quando o participante nao fez a prova da area. Ausencia e nota zero sao estados distintos: zero significa prova feita e zerada. |
| `NU_NOTA_COMP5` | `nota_redacao_comp5` | BIGINT | - | 52.4% | Ausente quando o participante nao fez a prova da area. Ausencia e nota zero sao estados distintos: zero significa prova feita e zerada. |
| `TP_STATUS_REDACAO` | `status_redacao` | BIGINT | 8 | 52.4% | Ausente quando o participante nao fez a prova da area. Ausencia e nota zero sao estados distintos: zero significa prova feita e zerada. |
| `TP_LINGUA` | `lingua_estrangeira` | BIGINT | 2 | 0.0% | Nunca ausente nas quatro edicoes. |
| `TP_FAIXA_ETARIA` | `faixa_etaria` | BIGINT | 20 | 0.0% | Nunca ausente nas quatro edicoes. |
| `TP_SEXO` | `sexo` | VARCHAR | 2 | 0.0% | Nunca ausente nas quatro edicoes. |
| `TP_ESTADO_CIVIL` | `estado_civil` | BIGINT | 5 | 0.0% | Nunca ausente nas quatro edicoes. |
| `TP_COR_RACA` | `cor_raca` | BIGINT | 7 | 0.0% | Nunca ausente nas quatro edicoes. |
| `TP_NACIONALIDADE` | `nacionalidade` | BIGINT | 5 | 0.0% | Nunca ausente nas quatro edicoes. |
| `TP_ST_CONCLUSAO` | `situacao_conclusao` | BIGINT | 4 | 0.0% | Nunca ausente nas quatro edicoes. |
| `TP_ANO_CONCLUIU` | `anos_desde_conclusao` | BIGINT | 17 | 0.0% | Nunca ausente nas quatro edicoes. |
| `TP_ESCOLA` | `tipo_escola` | BIGINT | 3 | 0.0% | Nunca ausente nas quatro edicoes. |
| `TP_ENSINO` | `tipo_ensino` | BIGINT | 2 | 77.5% | 64% a 77% de ausencia: preenchida apenas para quem declarou escola. |
| `TP_DEPENDENCIA_ADM_ESC` | `dependencia_adm_escola` | BIGINT | 4 | 84.4% | Preenchida apenas para quem declarou escola (73% a 84% de ausencia). Ausencia significa 'nao declarou', nao 'sem escola'. |
| `TP_LOCALIZACAO_ESC` | `localizacao_escola` | BIGINT | 2 | 84.4% | Preenchida apenas para quem declarou escola (73% a 84% de ausencia). Ausencia significa 'nao declarou', nao 'sem escola'. |
| `SG_UF_ESC` | `uf_escola` | VARCHAR | - | 84.4% | Preenchida apenas para quem declarou escola (73% a 84% de ausencia). Ausencia significa 'nao declarou', nao 'sem escola'. |
| `SG_UF_PROVA` | `uf_prova` | VARCHAR | - | 0.0% | Nunca ausente nas quatro edicoes. |
| `CO_MUNICIPIO_PROVA` | `cod_municipio_prova` | BIGINT | - | 0.0% | Nunca ausente nas quatro edicoes. |
| `NO_MUNICIPIO_PROVA` | `municipio_prova` | VARCHAR | - | 0.0% | Nunca ausente nas quatro edicoes. |
| `Q001` | `escolaridade_pai` | VARCHAR | 8 | 1.7% | Praticamente sem ausencia, exceto 2020 (1,66%), quando o questionario nao foi respondido por parte dos inscritos. |
| `Q002` | `escolaridade_mae` | VARCHAR | 8 | 1.7% | Praticamente sem ausencia, exceto 2020 (1,66%), quando o questionario nao foi respondido por parte dos inscritos. |
| `Q003` | `ocupacao_pai` | VARCHAR | 6 | 1.7% | Praticamente sem ausencia, exceto 2020 (1,66%), quando o questionario nao foi respondido por parte dos inscritos. |
| `Q004` | `ocupacao_mae` | VARCHAR | 6 | 1.7% | Praticamente sem ausencia, exceto 2020 (1,66%), quando o questionario nao foi respondido por parte dos inscritos. |
| `Q005` | `pessoas_domicilio` | BIGINT | 20 | 1.7% | Praticamente sem ausencia, exceto 2020 (1,66%), quando o questionario nao foi respondido por parte dos inscritos. |
| `Q006` | `renda_familiar` | VARCHAR | 17 | 1.7% | Praticamente sem ausencia, exceto 2020 (1,66%), quando o questionario nao foi respondido por parte dos inscritos. |
| `Q007` | `empregado_domestico` | VARCHAR | 4 | 1.7% | Praticamente sem ausencia, exceto 2020 (1,66%), quando o questionario nao foi respondido por parte dos inscritos. |
| `Q008` | `banheiros` | VARCHAR | 5 | 1.7% | Praticamente sem ausencia, exceto 2020 (1,66%), quando o questionario nao foi respondido por parte dos inscritos. |
| `Q009` | `quartos` | VARCHAR | 5 | 1.7% | Praticamente sem ausencia, exceto 2020 (1,66%), quando o questionario nao foi respondido por parte dos inscritos. |
| `Q010` | `carros` | VARCHAR | 5 | 1.7% | Praticamente sem ausencia, exceto 2020 (1,66%), quando o questionario nao foi respondido por parte dos inscritos. |
| `Q011` | `motocicletas` | VARCHAR | 5 | 1.7% | Praticamente sem ausencia, exceto 2020 (1,66%), quando o questionario nao foi respondido por parte dos inscritos. |
| `Q012` | `geladeiras` | VARCHAR | 5 | 1.7% | Praticamente sem ausencia, exceto 2020 (1,66%), quando o questionario nao foi respondido por parte dos inscritos. |
| `Q013` | `freezers` | VARCHAR | 5 | 1.7% | Praticamente sem ausencia, exceto 2020 (1,66%), quando o questionario nao foi respondido por parte dos inscritos. |
| `Q014` | `maquinas_lavar` | VARCHAR | 5 | 1.7% | Praticamente sem ausencia, exceto 2020 (1,66%), quando o questionario nao foi respondido por parte dos inscritos. |
| `Q015` | `maquinas_secar` | VARCHAR | 5 | 1.7% | Praticamente sem ausencia, exceto 2020 (1,66%), quando o questionario nao foi respondido por parte dos inscritos. |
| `Q016` | `micro_ondas` | VARCHAR | 5 | 1.7% | Praticamente sem ausencia, exceto 2020 (1,66%), quando o questionario nao foi respondido por parte dos inscritos. |
| `Q017` | `lava_loucas` | VARCHAR | 5 | 1.7% | Praticamente sem ausencia, exceto 2020 (1,66%), quando o questionario nao foi respondido por parte dos inscritos. |
| `Q018` | `aspirador` | VARCHAR | 2 | 1.7% | Praticamente sem ausencia, exceto 2020 (1,66%), quando o questionario nao foi respondido por parte dos inscritos. |
| `Q019` | `televisores` | VARCHAR | 5 | 1.7% | Praticamente sem ausencia, exceto 2020 (1,66%), quando o questionario nao foi respondido por parte dos inscritos. |
| `Q020` | `dvd` | VARCHAR | 2 | 1.7% | Praticamente sem ausencia, exceto 2020 (1,66%), quando o questionario nao foi respondido por parte dos inscritos. |
| `Q021` | `tv_assinatura` | VARCHAR | 2 | 1.7% | Praticamente sem ausencia, exceto 2020 (1,66%), quando o questionario nao foi respondido por parte dos inscritos. |
| `Q022` | `celulares` | VARCHAR | 5 | 1.7% | Praticamente sem ausencia, exceto 2020 (1,66%), quando o questionario nao foi respondido por parte dos inscritos. |
| `Q023` | `telefone_fixo` | VARCHAR | 2 | 1.7% | Praticamente sem ausencia, exceto 2020 (1,66%), quando o questionario nao foi respondido por parte dos inscritos. |
| `Q024` | `computadores` | VARCHAR | 5 | 1.7% | Praticamente sem ausencia, exceto 2020 (1,66%), quando o questionario nao foi respondido por parte dos inscritos. |
| `Q025` | `acesso_internet` | VARCHAR | 2 | 1.7% | Praticamente sem ausencia, exceto 2020 (1,66%), quando o questionario nao foi respondido por parte dos inscritos. |

### Transformacoes e papel na elegibilidade

Campos cuja regra nao e a identidade, ou que filtram populacao.

**`NU_ANO` -> `ano`**

- Transformacao: Constante dentro de cada edicao; vira coluna de particao do Parquet.

**`TP_PRESENCA_CN` -> `presenca_cn`**

- Transformacao: 0=faltou, 1=presente, 2=eliminado. Codigo preservado.
- Elegibilidade: Criterio primario: elegivel exige valor 1 nas quatro areas. Eliminados (2) sao excluidos e contabilizados no funil.

**`TP_PRESENCA_CH` -> `presenca_ch`**

- Transformacao: 0=faltou, 1=presente, 2=eliminado. Codigo preservado.
- Elegibilidade: Criterio primario: elegivel exige valor 1 nas quatro areas. Eliminados (2) sao excluidos e contabilizados no funil.

**`TP_PRESENCA_LC` -> `presenca_lc`**

- Transformacao: 0=faltou, 1=presente, 2=eliminado. Codigo preservado.
- Elegibilidade: Criterio primario: elegivel exige valor 1 nas quatro areas. Eliminados (2) sao excluidos e contabilizados no funil.

**`TP_PRESENCA_MT` -> `presenca_mt`**

- Transformacao: 0=faltou, 1=presente, 2=eliminado. Codigo preservado.
- Elegibilidade: Criterio primario: elegivel exige valor 1 nas quatro areas. Eliminados (2) sao excluidos e contabilizados no funil.

**`IN_TREINEIRO` -> `treineiro`**

- Transformacao: 0/1. Codigo preservado.
- Elegibilidade: Criterio primario: treineiros (1) ficam fora da populacao de comparacao, porque nao disputam vaga e sua distribuicao de notas responde a outra motivacao.

**`TP_STATUS_REDACAO` -> `status_redacao`**

- Transformacao: Codigo preservado. Distingue anulada, em branco e situacoes especiais.
- Nota: Necessaria para separar redacao zerada por anulacao de redacao zerada por desempenho.

**`TP_LINGUA` -> `lingua_estrangeira`**

- Transformacao: 0=ingles, 1=espanhol. Codigo preservado.
- Nota: Afeta a prova de LC; recorte relevante para comparar notas de LC.

**`TP_FAIXA_ETARIA` -> `faixa_etaria`**

- Transformacao: 20 faixas, estaveis nas quatro edicoes.

**`TP_COR_RACA` -> `cor_raca`**

- Transformacao: Codigo preservado. O codigo 6 ('Nao dispoe da informacao') so existe no dicionario de 2021-2022 e so ocorre em 2021, abaixo do piso de tamanho de grupo: tratado como categoria propria, nunca agrupado com 0 ('Nao declarado'), e suprimido de toda saida.

**`TP_ST_CONCLUSAO` -> `situacao_conclusao`**

- Transformacao: Codigo preservado. O rotulo cita o ano da prova ('concluirei em 2019' vs 'em 2022'), mas o significado e relativo a edicao e portanto estavel: 2 = conclui no ano da prova, 3 = conclui depois. Comparavel entre edicoes desde que o rotulo nao seja exibido como ano absoluto.
- Elegibilidade: Nao filtra por si, mas separa egressos de concluintes nos recortes.

**`TP_ANO_CONCLUIU` -> `anos_desde_conclusao`**

- Transformacao: O codigo e um deslocamento relativo, nao um ano: vale ano_da_prova - codigo. Preservado como `anos_desde_conclusao` (comparavel entre edicoes) e derivado `ano_conclusao = ano - codigo` para leitura absoluta. O maior codigo de cada edicao (13/14/15/16, sempre igual a ano - 2006) rotula 'Antes de 2007' e vira ano_conclusao nulo com marca propria. Codigo 0 = nao informado.

**`TP_ESCOLA` -> `tipo_escola`**

- Transformacao: Codigo preservado. O codigo 4 ('Exterior') consta no dicionario de 2019-2020 e nunca ocorre nos dados; nao vira categoria do produto.

**`TP_ENSINO` -> `tipo_ensino`**

- Transformacao: Codigo preservado. O codigo 3 ('Educacao de Jovens e Adultos') consta no dicionario de 2019-2020, mas nunca ocorre nos dados de nenhuma edicao: nao ha recorte por EJA.

**`SG_UF_PROVA` -> `uf_prova`**

- Transformacao: Sigla preservada. 27 unidades federativas nas quatro edicoes.

**`CO_MUNICIPIO_PROVA` -> `cod_municipio_prova`**

- Transformacao: Codigo IBGE preservado; chave estavel para recorte municipal.
- Nota: LGPD: e o campo de maior risco de reidentificacao do contrato. Municipio cruzado com cor/raca, faixa etaria ou renda gera grupos de poucas pessoas; todo agregado municipal passa pelo piso de tamanho de grupo antes de sair da camada ANALYTICS.

**`NO_MUNICIPIO_PROVA` -> `municipio_prova`**

- Transformacao: Nome preservado para exibicao; o codigo IBGE e a chave.

**`Q005` -> `pessoas_domicilio`**

- Transformacao: Numero de pessoas no domicilio, ja numerico.

**`Q006` -> `renda_familiar`**

- Transformacao: Codigo A-Q preservado e derivada `renda_sm` com o piso da faixa em multiplos do salario minimo da edicao. As 17 faixas sao definidas em multiplos do minimo, entao o codigo ja e comparavel entre edicoes nessa unidade; o que NAO e comparavel e o valor nominal em reais. Comparacao de poder de compra exige deflator, que o produto nao aplica - e uma limitacao declarada, nao um ajuste pendente.
- Nota: Entrada informada pelo usuario no produto.

## 5. Campos descartados

| Nome INEP | Peso (4 edicoes) | Motivo |
| --- | --- | --- |
| `TX_GABARITO_LC` | 0.54 GB | Gabarito item a item; so faz sentido junto de TX_RESPOSTAS. |
| `TX_RESPOSTAS_LC` | 0.53 GB | Respostas item a item (45 a 50 caracteres por registro). Fora do escopo descritivo e responsavel pela maior parte do volume do CSV. |
| `TX_RESPOSTAS_CH` | 0.48 GB | Respostas item a item (45 a 50 caracteres por registro). Fora do escopo descritivo e responsavel pela maior parte do volume do CSV. |
| `TX_GABARITO_CH` | 0.48 GB | Gabarito item a item; so faz sentido junto de TX_RESPOSTAS. |
| `TX_RESPOSTAS_CN` | 0.46 GB | Respostas item a item (45 a 50 caracteres por registro). Fora do escopo descritivo e responsavel pela maior parte do volume do CSV. |
| `TX_GABARITO_CN` | 0.46 GB | Gabarito item a item; so faz sentido junto de TX_RESPOSTAS. |
| `TX_RESPOSTAS_MT` | 0.46 GB | Respostas item a item (45 a 50 caracteres por registro). Fora do escopo descritivo e responsavel pela maior parte do volume do CSV. |
| `TX_GABARITO_MT` | 0.46 GB | Gabarito item a item; so faz sentido junto de TX_RESPOSTAS. |
| `NU_INSCRICAO` | 0.20 GB | Identificador individual. O produto so publica agregados, entao o numero de inscricao nao tem uso analitico e carrega risco de reidentificacao. Removido na passagem RAW -> TRUSTED. |
| `NO_MUNICIPIO_ESC` | 0.04 GB | Idem CO_MUNICIPIO_ESC. |
| `CO_PROVA_LC` | 0.03 GB | Codigo do caderno, reemitido a cada aplicacao. So serve para analise item a item, fora do escopo descritivo do produto. |
| `CO_PROVA_CH` | 0.03 GB | Codigo do caderno, reemitido a cada aplicacao. So serve para analise item a item, fora do escopo descritivo do produto. |
| `CO_UF_PROVA` | 0.03 GB | Redundante com SG_UF_PROVA, que e mais legivel. |
| `CO_PROVA_CN` | 0.03 GB | Codigo do caderno, reemitido a cada aplicacao. So serve para analise item a item, fora do escopo descritivo do produto. |
| `CO_PROVA_MT` | 0.03 GB | Codigo do caderno, reemitido a cada aplicacao. So serve para analise item a item, fora do escopo descritivo do produto. |
| `CO_MUNICIPIO_ESC` | 0.02 GB | Recorte geografico do produto usa o local de prova, que existe para todos. O municipio da escola falta em 73% a 84% dos registros. |
| `CO_UF_ESC` | 0.01 GB | Redundante com SG_UF_ESC. |
| `TP_SIT_FUNC_ESC` | 0.00 GB | Situacao de funcionamento da escola. Atributo do estabelecimento, nao do participante; fora dos recortes previstos. |

## 6. Protecao de dados (LGPD)

Regras completas em [`docs/privacidade.md`](../privacidade.md). O que o contrato impoe ao ETL:

- **Piso de grupo:** nenhuma contagem ou estatistica calculada sobre menos de **100 participantes** sai da camada ANALYTICS. Vale para cada celula de um cruzamento, nao so para o total do recorte.
- **Dados sensiveis** (art. 5o, II): `TP_COR_RACA`. So agregados e sujeitos ao piso; o campo `sensivel` do `contrato.json` marca quais sao.
- **Identificador:** `NU_INSCRICAO` e descartado na passagem RAW -> TRUSTED (secao 5).
- **Recorte municipal:** `CO_MUNICIPIO_PROVA` e o campo de maior risco. Cruzamentos municipais passam pelo piso celula a celula.

## 7. Decisoes em aberto

1. **Valor do piso de tamanho de grupo.** Ja aplicado com **100 participantes** (secao 6), o que mantem folga sobre o minimo estatistico usual de 30. O valor segue pendente de aceite do PO; mudar exige alterar `PISO_GRUPO` em `scripts/colunas.py` e regerar profiling e contrato.
2. **Modulos consumidores.** O plano preve quatro modulos autorais definidos na Sprint 5; ate la os campos estao marcados como `a definir`. Os campos de nota, presenca e `IN_TREINEIRO` ja constam como `todos`, por sustentarem a elegibilidade comum.
3. **Deflator.** As faixas de `Q006` sao estaveis em multiplos do salario minimo, mas comparar poder de compra entre 2019 e 2022 exigiria deflacionar. O produto **nao** aplica deflator: e uma limitacao declarada, coerente com a ressalva do plano de que o Radar ENEM e instrumento descritivo.
