# Dicionario de variaveis do ENEM (2019-2022)

Gerado por `scripts/dicionario.py` a partir dos XLSX oficiais do INEP contidos nos zips. Dominios completos em `dicionario_<ano>.json`.

## 1. Cobertura

Confere o dicionario contra as colunas que o CSV realmente tem (segundo `docs/profiling/`). Divergencia aqui significa coluna sem dominio documentado, ou dominio documentado para coluna inexistente.

| Edicao | Vars. no dicionario | Colunas no CSV | So no dicionario | So no CSV |
| --- | --- | --- | --- | --- |
| 2019 | 76 | 76 | - | - |
| 2020 | 76 | 76 | - | - |
| 2021 | 76 | 76 | - | - |
| 2022 | 76 | 76 | - | - |

## 2. Mesmo codigo, rotulo diferente

O codigo existe nas quatro edicoes e nenhuma checagem de dominio acusa problema, mas o rotulo mudou. Nas tres variaveis abaixo o codigo e relativo a edicao e continua comparavel entre anos; o que nao se pode e exibir o rotulo de uma edicao como se valesse para todas. Ver `docs/contrato/` para a regra de cada uma. `CO_PROVA_*` fica de fora porque o codigo do caderno e reemitido a cada aplicacao por construcao.

### `Q006` — Qual é a renda mensal de sua família? (Some a sua renda com a dos seus familiares.)

17 codigo(s) com rotulo diferente entre edicoes.

| Codigo | 2019 | 2020 | 2021 | 2022 |
| --- | --- | --- | --- | --- |
| `A` | Nenhuma renda. | Nenhuma Renda | Nenhuma Renda | Nenhuma Renda |
| `B` | Até R$ 998,00. | Até R$ 1.045,00 | Até R$ 1.100,00 | Até R$ 1.212,00 |
| `C` | De R$ 998,01 até R$ 1.497,00. | De R$ 1.045,01 até R$ 1.567,50 | De R$ 1.100,01 até R$ 1.650,00. | De R$ 1.212,01 até R$ 1.818,00. |
| `D` | De R$ 1.497,01 até R$ 1.996,00. | De R$ 1.567,51 até R$ 2.090,00 | De R$ 1.650,01 até R$ 2.200,00. | De R$ 1.818,01 até R$ 2.424,00. |
| `E` | De R$ 1.996,01 até R$ 2.495,00. | De R$ 2.090,01 até R$ 2.612,50 | De R$ 2.200,01 até R$ 2.750,00. | De R$ 2.424,01 até R$ 3.030,00. |
| `F` | De R$ 2.495,01 até R$ 2.994,00. | De R$ 2.612,51 até R$ 3.135,00 | De R$ 2.750,01 até R$ 3.300,00. | De R$ 3.030,01 até R$ 3.636,00. |
| `G` | De R$ 2.994,01 até R$ 3.992,00. | De R$ 3.135,01 até R$ 4.180,00 | De R$ 3.300,01 até R$ 4.400,00. | De R$ 3.636,01 até R$ 4.848,00. |
| `H` | De R$ 3.992,01 até R$ 4.990,00. | De R$ 4.180,01 até R$ 5.225,00 | De R$ 4.400,01 até R$ 5.500,00. | De R$ 4.848,01 até R$ 6.060,00. |
| `I` | De R$ 4.990,01 até R$ 5.988,00. | De R$ 5.225,01 até R$ 6.270,00 | De R$ 5.500,01 até R$ 6.600,00. | De R$ 6.060,01 até R$ 7.272,00. |
| `J` | De R$ 5.988,01 até R$ 6.986,00. | De R$ 6.270,01 até R$ 7.315,00 | De R$ 6.600,01 até R$ 7.700,00. | De R$ 7.272,01 até R$ 8.484,00. |
| `K` | De R$ 6.986,01 até R$ 7.984,00. | De R$ 7.315,01 até R$ 8.360,00 | De R$ 7.700,01 até R$ 8.800,00. | De R$ 8.484,01 até R$ 9.696,00. |
| `L` | De R$ 7.984,01 até R$ 8.982,00. | De R$ 8.360,01 até R$ 9.405,00 | De R$ 8.800,01 até R$ 9.900,00. | De R$ 9.696,01 até R$ 10.908,00. |
| `M` | De R$ 8.982,01 até R$ 9.980,00. | De R$ 9.405,01 até R$ 10.450,00 | De R$ 9.900,01 até R$ 11.000,00. | De R$ 10.908,01 até R$ 12.120,00. |
| `N` | De R$ 9.980,01 até R$ 11.976,00. | De R$ 10.450,01 até R$ 12.540,00 | De R$ 11.000,01 até R$ 13.200,00. | De R$ 12.120,01 até R$ 14.544,00. |
| `O` | De R$ 11.976,01 até R$ 14.970,00. | De R$ 12.540,01 até R$ 15.675,00 | De R$ 13.200,01 até R$ 16.500,00. | De R$ 14.544,01 até R$ 18.180,00. |
| `P` | De R$ 14.970,01 até R$ 19.960,00. | De R$ 15.675,01 até R$ 20.900,00 | De R$ 16.500,01 até R$ 22.000,00. | De R$ 18.180,01 até R$ 24.240,00. |
| `Q` | Mais de R$ 19.960,00. | Acima de R$ 20.900,00 | Acima de R$ 22.000,00. | Acima de R$ 24.240,00. |

### `TP_ANO_CONCLUIU` — Ano de Conclusão do Ensino Médio

13 codigo(s) com rotulo diferente entre edicoes.

| Codigo | 2019 | 2020 | 2021 | 2022 |
| --- | --- | --- | --- | --- |
| `1` | 2018 | 2019 | 2020 | 2021 |
| `2` | 2017 | 2018 | 2019 | 2020 |
| `3` | 2016 | 2017 | 2018 | 2019 |
| `4` | 2015 | 2016 | 2017 | 2018 |
| `5` | 2014 | 2015 | 2016 | 2017 |
| `6` | 2013 | 2014 | 2015 | 2016 |
| `7` | 2012 | 2013 | 2014 | 2015 |
| `8` | 2011 | 2012 | 2013 | 2014 |
| `9` | 2010 | 2011 | 2012 | 2013 |
| `10` | 2009 | 2010 | 2011 | 2012 |
| `11` | 2008 | 2009 | 2010 | 2011 |
| `12` | 2007 | 2008 | 2009 | 2010 |
| `13` | Antes de 2007 | 2007 | 2008 | 2009 |

### `TP_ST_CONCLUSAO` — Situação de conclusão do Ensino Médio

2 codigo(s) com rotulo diferente entre edicoes.

| Codigo | 2019 | 2020 | 2021 | 2022 |
| --- | --- | --- | --- | --- |
| `2` | Estou cursando e concluirei o Ensino Médio em 2019 | Estou cursando e concluirei o Ensino Médio em 2020 | Estou cursando e concluirei o Ensino Médio em 2021 | Estou cursando e concluirei o Ensino Médio em 2022 |
| `3` | Estou cursando e concluirei o Ensino Médio após 2019 | Estou cursando e concluirei o Ensino Médio após 2020 | Estou cursando e concluirei o Ensino Médio após 2021 | Estou cursando e concluirei o Ensino Médio após 2022 |

## 3. Codigos que entram ou saem

O conjunto de codigos nao e o mesmo nas quatro edicoes. Menos perigoso que o caso anterior, porque um filtro por codigo inexistente devolve vazio em vez de resposta errada, mas ainda exige decisao explicita.

| Variavel | Codigo | Rotulo | Edicoes em que existe |
| --- | --- | --- | --- |
| `TP_ANO_CONCLUIU` | `14` | Antes de 2007 | 2020, 2021, 2022 |
| `TP_ANO_CONCLUIU` | `15` | Antes de 2007 | 2021, 2022 |
| `TP_ANO_CONCLUIU` | `16` | Antes de 2007 | 2022 |
| `TP_COR_RACA` | `6` | Não dispõe da informação | 2021, 2022 |
| `TP_ENSINO` | `3` | Educação de Jovens e Adultos | 2019, 2020 |
| `TP_ESCOLA` | `4` | Exterior | 2019, 2020 |

> `CO_PROVA_CN/CH/LC/MT` foram omitidos das duas secoes acima: o codigo do caderno de prova e reemitido a cada aplicacao, entao praticamente nenhum codigo se repete entre edicoes. Os dominios completos estao nos JSON.

## 4. Documentado x observado

Cruza o dominio do dicionario com os valores que aparecem de fato nos CSVs (`docs/profiling/`). `so no dado` e o caso grave: valor sem rotulo oficial. `so no dicionario` e categoria prevista que nunca ocorreu - o filtro existe mas devolveria vazio.

| Variavel | Edicao | So no dado | So no dicionario |
| --- | --- | --- | --- |
| `TP_COR_RACA` | 2022 | - | `6` |
| `TP_ESCOLA` | 2019 | - | `4` |
| `TP_ESCOLA` | 2020 | - | `4` |

## 5. Dominios das variaveis de recorte

Rotulos da edicao mais recente disponivel. Sao as variaveis que viram filtro no produto.

### `TP_FAIXA_ETARIA` — Faixa etária2

Tipo: Numérica · fonte: dicionario 2022

| Codigo | Rotulo |
| --- | --- |
| `1` | Menor de 17 anos |
| `2` | 17 anos |
| `3` | 18 anos |
| `4` | 19 anos |
| `5` | 20 anos |
| `6` | 21 anos |
| `7` | 22 anos |
| `8` | 23 anos |
| `9` | 24 anos |
| `10` | 25 anos |
| `11` | Entre 26 e 30 anos |
| `12` | Entre 31 e 35 anos |
| `13` | Entre 36 e 40 anos |
| `14` | Entre 41 e 45 anos |
| `15` | Entre 46 e 50 anos |
| `16` | Entre 51 e 55 anos |
| `17` | Entre 56 e 60 anos |
| `18` | Entre 61 e 65 anos |
| `19` | Entre 66 e 70 anos |
| `20` | Maior de 70 anos |

### `TP_SEXO` — Sexo

Tipo: Alfanumérica · fonte: dicionario 2022

| Codigo | Rotulo |
| --- | --- |
| `M` | Masculino |
| `F` | Feminino |

### `TP_ESTADO_CIVIL` — Estado Civil

Tipo: Numérica · fonte: dicionario 2022

| Codigo | Rotulo |
| --- | --- |
| `0` | Não informado |
| `1` | Solteiro(a) |
| `2` | Casado(a)/Mora com companheiro(a) |
| `3` | Divorciado(a)/Desquitado(a)/Separado(a) |
| `4` | Viúvo(a) |

### `TP_COR_RACA` — Cor/raça

Tipo: Numérica · fonte: dicionario 2022

| Codigo | Rotulo |
| --- | --- |
| `0` | Não declarado |
| `1` | Branca |
| `2` | Preta |
| `3` | Parda |
| `4` | Amarela |
| `5` | Indígena |
| `6` | Não dispõe da informação |

### `TP_NACIONALIDADE` — Nacionalidade

Tipo: Numérica · fonte: dicionario 2022

| Codigo | Rotulo |
| --- | --- |
| `0` | Não informado |
| `1` | Brasileiro(a) |
| `2` | Brasileiro(a) Naturalizado(a) |
| `3` | Estrangeiro(a) |
| `4` | Brasileiro(a) Nato(a), nascido(a) no exterior |

### `TP_ST_CONCLUSAO` — Situação de conclusão do Ensino Médio

Tipo: Numérica · fonte: dicionario 2022

| Codigo | Rotulo |
| --- | --- |
| `1` | Já concluí o Ensino Médio |
| `2` | Estou cursando e concluirei o Ensino Médio em 2022 |
| `3` | Estou cursando e concluirei o Ensino Médio após 2022 |
| `4` | Não concluí e não estou cursando o Ensino Médio |

### `TP_ANO_CONCLUIU` — Ano de Conclusão do Ensino Médio

Tipo: Numérica · fonte: dicionario 2022

| Codigo | Rotulo |
| --- | --- |
| `0` | Não informado |
| `1` | 2021 |
| `2` | 2020 |
| `3` | 2019 |
| `4` | 2018 |
| `5` | 2017 |
| `6` | 2016 |
| `7` | 2015 |
| `8` | 2014 |
| `9` | 2013 |
| `10` | 2012 |
| `11` | 2011 |
| `12` | 2010 |
| `13` | 2009 |
| `14` | 2008 |
| `15` | 2007 |
| `16` | Antes de 2007 |

### `TP_ESCOLA` — Tipo de escola do Ensino Médio

Tipo: Numérica · fonte: dicionario 2022

| Codigo | Rotulo |
| --- | --- |
| `1` | Não Respondeu |
| `2` | Pública |
| `3` | Privada |

### `TP_ENSINO` — Tipo de instituição que concluiu ou concluirá o Ensino Médio

Tipo: Numérica · fonte: dicionario 2022

| Codigo | Rotulo |
| --- | --- |
| `1` | Ensino Regular |
| `2` | Educação Especial - Modalidade Substitutiva |

### `IN_TREINEIRO` — Indica se o inscrito fez a prova com intuito de apenas treinar seus conhecimentos3

Tipo: Numérica · fonte: dicionario 2022

| Codigo | Rotulo |
| --- | --- |
| `1` | Sim |
| `0` | Não |

### `TP_DEPENDENCIA_ADM_ESC` — Dependência administrativa (Escola)

Tipo: Numérica · fonte: dicionario 2022

| Codigo | Rotulo |
| --- | --- |
| `1` | Federal |
| `2` | Estadual |
| `3` | Municipal |
| `4` | Privada |

### `TP_LOCALIZACAO_ESC` — Localização (Escola)

Tipo: Numérica · fonte: dicionario 2022

| Codigo | Rotulo |
| --- | --- |
| `1` | Urbana |
| `2` | Rural |

### `TP_LINGUA` — Língua Estrangeira

Tipo: Numérica · fonte: dicionario 2022

| Codigo | Rotulo |
| --- | --- |
| `0` | Inglês |
| `1` | Espanhol |

### `TP_STATUS_REDACAO` — Situação da redação do participante

Tipo: Numérica · fonte: dicionario 2022

| Codigo | Rotulo |
| --- | --- |
| `1` | Sem problemas |
| `2` | Anulada |
| `3` | Cópia Texto Motivador |
| `4` | Em Branco |
| `6` | Fuga ao tema |
| `7` | Não atendimento ao tipo textual |
| `8` | Texto insuficiente |
| `9` | Parte desconectada |

### `Q001` — Até que série seu pai, ou o homem responsável por você, estudou?

Tipo: Alfanumérica · fonte: dicionario 2022

| Codigo | Rotulo |
| --- | --- |
| `A` | Nunca estudou. |
| `B` | Não completou a 4ª série/5º ano do Ensino Fundamental. |
| `C` | Completou a 4ª série/5º ano, mas não completou a 8ª série/9º ano do Ensino Fundamental. |
| `D` | Completou a 8ª série/9º ano do Ensino Fundamental, mas não completou o Ensino Médio. |
| `E` | Completou o Ensino Médio, mas não completou a Faculdade. |
| `F` | Completou a Faculdade, mas não completou a Pós-graduação. |
| `G` | Completou a Pós-graduação. |
| `H` | Não sei. |

### `Q002` — Até que série sua mãe, ou a mulher responsável por você, estudou?

Tipo: Alfanumérica · fonte: dicionario 2022

| Codigo | Rotulo |
| --- | --- |
| `A` | Nunca estudou. |
| `B` | Não completou a 4ª série/5º ano do Ensino Fundamental. |
| `C` | Completou a 4ª série/5º ano, mas não completou a 8ª série/9º ano do Ensino Fundamental. |
| `D` | Completou a 8ª série/9º ano do Ensino Fundamental, mas não completou o Ensino Médio. |
| `E` | Completou o Ensino Médio, mas não completou a Faculdade. |
| `F` | Completou a Faculdade, mas não completou a Pós-graduação. |
| `G` | Completou a Pós-graduação. |
| `H` | Não sei. |

### `Q003` — A partir da apresentação de algumas ocupações divididas em grupos ordenados, indique o grupo que contempla a ocupação mais próxima da ocupação do seu pai ou do homem responsável por você. (Se ele não estiver trabalhando, escolha uma ocupação pensando no último trabalho dele).

Tipo: Alfanumérica · fonte: dicionario 2022

| Codigo | Rotulo |
| --- | --- |
| `A` | Grupo 1: Lavrador, agricultor sem empregados, bóia fria, criador de animais (gado, porcos, galinhas, ovelhas, cavalos etc.), apicultor, pescador, lenhador, seringueiro, extrativista. |
| `B` | Grupo 2: Diarista, empregado doméstico, cuidador de idosos, babá, cozinheiro (em casas particulares), motorista particular, jardineiro, faxineiro de empresas e prédios, vigilante, porteiro, carteiro, office-boy, vendedor, caixa, atendente de loja, auxiliar administrativo, recepcionista, servente de pedreiro, repositor de mercadoria. |
| `C` | Grupo 3: Padeiro, cozinheiro industrial ou em restaurantes, sapateiro, costureiro, joalheiro, torneiro mecânico, operador de máquinas, soldador, operário de fábrica, trabalhador da mineração, pedreiro, pintor, eletricista, encanador, motorista, caminhoneiro, taxista. |
| `D` | Grupo 4: Professor (de ensino fundamental ou médio, idioma, música, artes etc.), técnico (de enfermagem, contabilidade, eletrônica etc.), policial, militar de baixa patente (soldado, cabo, sargento), corretor de imóveis, supervisor, gerente, mestre de obras, pastor, microempresário (proprietário de empresa com menos de 10 empregados), pequeno comerciante, pequeno proprietário de terras, trabalhador autônomo ou por conta própria. |
| `E` | Grupo 5: Médico, engenheiro, dentista, psicólogo, economista, advogado, juiz, promotor, defensor, delegado, tenente, capitão, coronel, professor universitário, diretor em empresas públicas ou privadas, político, proprietário de empresas com mais de 10 empregados. |
| `F` | Não sei. |

### `Q004` — A partir da apresentação de algumas ocupações divididas em grupos ordenados, indique o grupo que contempla a ocupação mais próxima da ocupação da sua mãe ou da mulher responsável por você. (Se ela não estiver trabalhando, escolha uma ocupação pensando no último trabalho dela).

Tipo: Numérica · fonte: dicionario 2022

| Codigo | Rotulo |
| --- | --- |
| `A` | Grupo 1: Lavradora, agricultora sem empregados, bóia fria, criadora de animais (gado, porcos, galinhas, ovelhas, cavalos etc.), apicultora, pescadora, lenhadora, seringueira, extrativista. |
| `B` | Grupo 2: Diarista, empregada doméstica, cuidadora de idosos, babá, cozinheira (em casas particulares), motorista particular, jardineira, faxineira de empresas e prédios, vigilante, porteira, carteira, office-boy, vendedora, caixa, atendente de loja, auxiliar administrativa, recepcionista, servente de pedreiro, repositora de mercadoria. |
| `C` | Grupo 3: Padeira, cozinheira industrial ou em restaurantes, sapateira, costureira, joalheira, torneira mecânica, operadora de máquinas, soldadora, operária de fábrica, trabalhadora da mineração, pedreira, pintora, eletricista, encanadora, motorista, caminhoneira, taxista. |
| `D` | Grupo 4: Professora (de ensino fundamental ou médio, idioma, música, artes etc.), técnica (de enfermagem, contabilidade, eletrônica etc.), policial, militar de baixa patente (soldado, cabo, sargento), corretora de imóveis, supervisora, gerente, mestre de obras, pastora, microempresária (proprietária de empresa com menos de 10 empregados), pequena comerciante, pequena proprietária de terras, trabalhadora autônoma ou por conta própria. |
| `E` | Grupo 5: Médica, engenheira, dentista, psicóloga, economista, advogada, juíza, promotora, defensora, delegada, tenente, capitã, coronel, professora universitária, diretora em empresas públicas ou privadas, política, proprietária de empresas com mais de 10 empregados. |
| `F` | Não sei. |

### `Q005` — Incluindo você, quantas pessoas moram atualmente em sua residência?

Tipo: Numérica · fonte: dicionario 2022

| Codigo | Rotulo |
| --- | --- |
| `1` | 1, pois moro sozinho(a). |
| `2` | 2 |
| `3` | 3 |
| `4` | 4 |
| `5` | 5 |
| `6` | 6 |
| `7` | 7 |
| `8` | 8 |
| `9` | 9 |
| `10` | 10 |
| `11` | 11 |
| `12` | 12 |
| `13` | 13 |
| `14` | 14 |
| `15` | 15 |
| `16` | 16 |
| `17` | 17 |
| `18` | 18 |
| `19` | 19 |
| `20` | 20 |

### `Q006` — Qual é a renda mensal de sua família? (Some a sua renda com a dos seus familiares.)

Tipo: Alfanumérica · fonte: dicionario 2022

| Codigo | Rotulo |
| --- | --- |
| `A` | Nenhuma Renda |
| `B` | Até R$ 1.212,00 |
| `C` | De R$ 1.212,01 até R$ 1.818,00. |
| `D` | De R$ 1.818,01 até R$ 2.424,00. |
| `E` | De R$ 2.424,01 até R$ 3.030,00. |
| `F` | De R$ 3.030,01 até R$ 3.636,00. |
| `G` | De R$ 3.636,01 até R$ 4.848,00. |
| `H` | De R$ 4.848,01 até R$ 6.060,00. |
| `I` | De R$ 6.060,01 até R$ 7.272,00. |
| `J` | De R$ 7.272,01 até R$ 8.484,00. |
| `K` | De R$ 8.484,01 até R$ 9.696,00. |
| `L` | De R$ 9.696,01 até R$ 10.908,00. |
| `M` | De R$ 10.908,01 até R$ 12.120,00. |
| `N` | De R$ 12.120,01 até R$ 14.544,00. |
| `O` | De R$ 14.544,01 até R$ 18.180,00. |
| `P` | De R$ 18.180,01 até R$ 24.240,00. |
| `Q` | Acima de R$ 24.240,00. |

### `Q007` — Em sua residência trabalha empregado(a) doméstico(a)?

Tipo: Alfanumérica · fonte: dicionario 2022

| Codigo | Rotulo |
| --- | --- |
| `A` | Não. |
| `B` | Sim, um ou dois dias por semana. |
| `C` | Sim, três ou quatro dias por semana. |
| `D` | Sim, pelo menos cinco dias por semana. |

### `Q008` — Na sua residência tem banheiro?

Tipo: Alfanumérica · fonte: dicionario 2022

| Codigo | Rotulo |
| --- | --- |
| `A` | Não. |
| `B` | Sim, um. |
| `C` | Sim, dois. |
| `D` | Sim, três. |
| `E` | Sim, quatro ou mais. |

### `Q009` — Na sua residência tem quartos para dormir?

Tipo: Alfanumérica · fonte: dicionario 2022

| Codigo | Rotulo |
| --- | --- |
| `A` | Não. |
| `B` | Sim, um. |
| `C` | Sim, dois. |
| `D` | Sim, três. |
| `E` | Sim, quatro ou mais. |

### `Q010` — Na sua residência tem carro?

Tipo: Alfanumérica · fonte: dicionario 2022

| Codigo | Rotulo |
| --- | --- |
| `A` | Não. |
| `B` | Sim, um. |
| `C` | Sim, dois. |
| `D` | Sim, três. |
| `E` | Sim, quatro ou mais. |

### `Q011` — Na sua residência tem motocicleta?

Tipo: Alfanumérica · fonte: dicionario 2022

| Codigo | Rotulo |
| --- | --- |
| `A` | Não. |
| `B` | Sim, uma. |
| `C` | Sim, duas. |
| `D` | Sim, três. |
| `E` | Sim, quatro ou mais. |

### `Q012` — Na sua residência tem geladeira?

Tipo: Alfanumérica · fonte: dicionario 2022

| Codigo | Rotulo |
| --- | --- |
| `A` | Não. |
| `B` | Sim, uma. |
| `C` | Sim, duas. |
| `D` | Sim, três. |
| `E` | Sim, quatro ou mais. |

### `Q013` — Na sua residência tem freezer (independente ou segunda porta da geladeira)?

Tipo: Alfanumérica · fonte: dicionario 2022

| Codigo | Rotulo |
| --- | --- |
| `A` | Não. |
| `B` | Sim, um. |
| `C` | Sim, dois. |
| `D` | Sim, três. |
| `E` | Sim, quatro ou mais. |

### `Q014` — Na sua residência tem máquina de lavar roupa? (o tanquinho NÃO deve ser considerado)

Tipo: Alfanumérica · fonte: dicionario 2022

| Codigo | Rotulo |
| --- | --- |
| `A` | Não. |
| `B` | Sim, uma. |
| `C` | Sim, duas. |
| `D` | Sim, três. |
| `E` | Sim, quatro ou mais. |

### `Q015` — Na sua residência tem máquina de secar roupa (independente ou em conjunto com a máquina de lavar roupa)?

Tipo: Alfanumérica · fonte: dicionario 2022

| Codigo | Rotulo |
| --- | --- |
| `A` | Não. |
| `B` | Sim, uma. |
| `C` | Sim, duas. |
| `D` | Sim, três. |
| `E` | Sim, quatro ou mais. |

### `Q016` — Na sua residência tem forno micro-ondas?

Tipo: Alfanumérica · fonte: dicionario 2022

| Codigo | Rotulo |
| --- | --- |
| `A` | Não. |
| `B` | Sim, um. |
| `C` | Sim, dois. |
| `D` | Sim, três. |
| `E` | Sim, quatro ou mais. |

### `Q017` — Na sua residência tem máquina de lavar louça?

Tipo: Alfanumérica · fonte: dicionario 2022

| Codigo | Rotulo |
| --- | --- |
| `A` | Não. |
| `B` | Sim, uma. |
| `C` | Sim, duas. |
| `D` | Sim, três. |
| `E` | Sim, quatro ou mais. |

### `Q018` — Na sua residência tem aspirador de pó?

Tipo: Alfanumérica · fonte: dicionario 2022

| Codigo | Rotulo |
| --- | --- |
| `A` | Não. |
| `B` | Sim. |

### `Q019` — Na sua residência tem televisão em cores?

Tipo: Alfanumérica · fonte: dicionario 2022

| Codigo | Rotulo |
| --- | --- |
| `A` | Não. |
| `B` | Sim, uma. |
| `C` | Sim, duas. |
| `D` | Sim, três. |
| `E` | Sim, quatro ou mais. |

### `Q020` — Na sua residência tem aparelho de DVD?

Tipo: Alfanumérica · fonte: dicionario 2022

| Codigo | Rotulo |
| --- | --- |
| `A` | Não. |
| `B` | Sim. |

### `Q021` — Na sua residência tem TV por assinatura?

Tipo: Alfanumérica · fonte: dicionario 2022

| Codigo | Rotulo |
| --- | --- |
| `A` | Não. |
| `B` | Sim. |

### `Q022` — Na sua residência tem telefone celular?

Tipo: Alfanumérica · fonte: dicionario 2022

| Codigo | Rotulo |
| --- | --- |
| `A` | Não. |
| `B` | Sim, um. |
| `C` | Sim, dois. |
| `D` | Sim, três. |
| `E` | Sim, quatro ou mais. |

### `Q023` — Na sua residência tem telefone fixo?

Tipo: Alfanumérica · fonte: dicionario 2022

| Codigo | Rotulo |
| --- | --- |
| `A` | Não. |
| `B` | Sim. |

### `Q024` — Na sua residência tem computador?

Tipo: Alfanumérica · fonte: dicionario 2022

| Codigo | Rotulo |
| --- | --- |
| `A` | Não. |
| `B` | Sim, um. |
| `C` | Sim, dois. |
| `D` | Sim, três. |
| `E` | Sim, quatro ou mais. |

### `Q025` — Na sua residência tem acesso à Internet?

Tipo: Alfanumérica · fonte: dicionario 2022

| Codigo | Rotulo |
| --- | --- |
| `A` | Não. |
| `B` | Sim. |

### `TP_PRESENCA_CN` — Presença na prova objetiva de Ciências da Natureza

Tipo: Numérica · fonte: dicionario 2022

| Codigo | Rotulo |
| --- | --- |
| `0` | Faltou à prova |
| `1` | Presente na prova |
| `2` | Eliminado na prova |

### `TP_PRESENCA_CH` — Presença na prova objetiva de Ciências Humanas

Tipo: Numérica · fonte: dicionario 2022

| Codigo | Rotulo |
| --- | --- |
| `0` | Faltou à prova |
| `1` | Presente na prova |
| `2` | Eliminado na prova |

### `TP_PRESENCA_LC` — Presença na prova objetiva de Linguagens e Códigos

Tipo: Numérica · fonte: dicionario 2022

| Codigo | Rotulo |
| --- | --- |
| `0` | Faltou à prova |
| `1` | Presente na prova |
| `2` | Eliminado na prova |

### `TP_PRESENCA_MT` — Presença na prova objetiva de Matemática

Tipo: Numérica · fonte: dicionario 2022

| Codigo | Rotulo |
| --- | --- |
| `0` | Faltou à prova |
| `1` | Presente na prova |
| `2` | Eliminado na prova |
