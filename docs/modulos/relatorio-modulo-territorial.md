# Relatório do módulo autoral — Recorte territorial

| Campo | Valor |
| --- | --- |
| Projeto | Radar ENEM — Projeto Aplicado III, Equipe A |
| Módulo | Recorte territorial (UF, região e Brasil) |
| Autor | Vinícius Joacir dos Anjos |
| Curso / turma | Bacharelado em Ciência de Dados e IA, UniSENAI/SC Florianópolis, 4ª fase, turma 444311 |
| Orientador | Gustavo Stangherlin Cantarelli |
| Repositório | https://github.com/gilas-byte/projetoAplicado3 |
| Versão analisada | `main`, commit `8d70f06` (merge do PR #17, 10/11/2026) |
| Regras do módulo | `docs/decisoes/README.md`, DL-04 (aceita pelo PO em 03/11/2026) |
| Arquivos do módulo | `scripts/territorial.py`, `scripts/auditoria_limites.py`, `app/pages/2_Recorte_territorial.py`, `tests/test_territorial.py` |

Os números de grupos, rótulos e ocorrências da auditoria (§4.4) vêm da execução de `scripts/auditoria_limites.py` sobre os microdados reais em 03/11/2026, registrada na DL-04, item 8. Os resultados de teste (§4.3) foram medidos em 10/11/2026 no commit `8d70f06`. Os microdados do INEP não estão no repositório.

---

## 1. Pergunta do módulo

**A mesma nota ocupa a mesma posição no estado, na região e no Brasil?**

O participante informa a UF onde fez a prova e uma ou mais notas. Para cada nota, o módulo devolve três cenários lado a lado — posição na UF, na região do IBGE e no Brasil — e medidas que comparam as distribuições entre esses níveis.

O módulo atende ao item 8 do Plano de Trabalho: "comparar o desempenho com UF, região e referência nacional/geral da edição, com análise das diferenças de distribuição e tamanho dos grupos".

O resultado é descritivo. Uma UF com mediana mais alta não "causa" notas mais altas: as UFs diferem em renda, rede de ensino e perfil de quem faz a prova. A página informa isso ao usuário (bloco "Como a comparação é feita", item "Leitura").

---

## 2. Regras de negócio e formulação da análise comparativa

Todas as regras desta seção estão na DL-04 e implementadas em `scripts/territorial.py`. A referência entre parênteses indica o item da DL-04.

### 2.1 Variável territorial (item 1)

| Opção | Preenchimento entre elegíveis | Decisão |
| --- | --- | --- |
| `SG_UF_PROVA` (UF do local de prova) | 100% nas quatro edições | **Usada**, mantida na TRUSTED como `uf_prova` |
| `SG_UF_ESC` (UF da escola) | Falta para 64,1% (2022) a 76,0% (2020) | Descartada |
| `CO_MUNICIPIO_PROVA` | — | Descartada (item 3) |

**Por que a UF da prova:** só quem conclui o ensino médio no ano informa a escola. Usar `SG_UF_ESC` restringiria o módulo a concluintes e excluiria a maioria dos participantes. Por isso a interface pergunta "Em qual UF você fez a prova?", e não "onde você mora".

**Por que sem município:** municípios pequenos ficariam abaixo do piso de 100 ou perto dele. A diferença entre a UF e a soma dos municípios publicados permitiria deduzir os suprimidos (`docs/privacidade.md`, R3).

### 2.2 Níveis de comparação (item 2)

| Nível | Composição | Código no artefato |
| --- | --- | --- |
| UF | 27 unidades federativas | `UF-<sigla>` |
| Região | 5 regiões do IBGE, derivadas da UF pela tabela fixa `REGIOES` | `RG-<N, NE, SE, S, CO>` |
| Brasil | Todos os elegíveis com UF válida | `BR` |

**Por que o prefixo:** "SE" é Sergipe e também a abreviação de Sudeste. Sigla solta seria ambígua no artefato (item 4). O teste `test_codigos_de_grupo_sem_ambiguidade` garante que nenhum código se repete.

Não há cruzamento do território com outra variável (renda, rede, cor/raça).

### 2.3 População de referência (item 6)

Participante **elegível** (definido no contrato de dados): presente nas quatro provas objetivas e `IN_TREINEIRO = 0`, com nota na área consultada. É a mesma população das outras páginas. Consequência verificável: a CDF do grupo `BR` do módulo é igual à CDF de `dist_exata.parquet`, usada na página inicial.

### 2.4 Medidas calculadas

**Em cada nível (UF, região, Brasil)**, sobre a CDF exata do grupo:

| Medida | Definição | Função |
| --- | --- | --- |
| Percentil | (abaixo + iguais / 2) / N × 100 — posto médio, sem interpolação (ADR-001) | `dobro_posicao` |
| Média, desvio-padrão | Populacional (divisor N), porque cada edição é a população elegível inteira (DL-01) | `resumo` |
| Mediana | Menor nota com acumulado ≥ 0,5·N (mediana inferior, DL-01) | `quantil` |
| Z-Score | (nota − média) / desvio; indefinido se desvio = 0 | `z_score` |
| Tamanho do grupo | N de elegíveis com nota na área | `resumo` |

**Entre níveis** (item 9):

| Medida | Definição | Por que assim |
| --- | --- | --- |
| Diferença UF − Brasil | percentil na UF − percentil no Brasil, em pontos percentuais | Responde diretamente à pergunta do módulo. Omitida quando a UF está em limite (§2.6) |
| Probabilidade de superioridade da UF | P(UF > resto) + 0,5·P(UF = resto), onde **resto = Brasil sem a própria UF** | Comparar com o Brasil inteiro colocaria a UF dos dois lados e puxaria o valor para 50%, principalmente em SP (~16% dos inscritos) |
| Probabilidade de superioridade da região | Mesma fórmula, região contra o Brasil sem a região | Mesmo motivo |
| Posição da mediana da UF entre as 27 | 1 + número de UFs com mediana estritamente maior | Situa o estado no país |

**Exemplo da probabilidade de superioridade** (reproduzível com `restante` e `prob_superioridade`):

- UF: notas 500, 500, 600. Brasil: 500, 500, 500, 600, 700.
- Resto = Brasil sem a UF = {500, 700}.
- Pares UF × resto: 3 × 2 = 6. UF vence em 1 par (600 > 500); empata em 2 (500 = 500).
- Resultado: (1 + 0,5 × 2) / 6 = **0,333**.

`restante` levanta `ValueError` se a UF tiver alguma nota com frequência maior que a do Brasil. Isso impede calcular a medida sobre artefatos inconsistentes.

### 2.5 Empates e ausências

| Situação | Regra | Onde |
| --- | --- | --- |
| Participantes com a mesma nota do usuário | Contam pela metade no percentil (posto médio) | `dobro_posicao` |
| UFs com a mesma mediana | Dividem a posição ("1, 2, 2, 4"); a sigla não desempata. A interface diz com quantas está empatada | `posicao_da_mediana` |
| Nota nula na área | Participante fora da CDF dessa área | `sql_contagens` (`nota_{area} IS NOT NULL`) |
| `uf_prova` vazia ou fora das 27 siglas | Participante sai de **todos** os grupos, inclusive do Brasil, para UFs somarem a região e regiões somarem o Brasil sem resto. Contagem gravada no manifesto local | `sql_contagens`, `auditar_uf` (item 5) |
| Grupo com N < 100 | Não é gravado; a interface mostra "grupo insuficiente" | `sql_artefato`, `_cenario` (item 7) |

Empates na mediana ocorrem em 9 das 20 combinações de edição × área, incluindo as 4 da Redação, onde a mediana é sempre múltipla de 20 (item 9). Nas quatro edições reais não há UF ausente ou inválida entre os elegíveis (item 5).

### 2.6 Limites de exibição do percentil (item 8)

**Problema.** Média, mediana e desvio são fixos por grupo; o percentil muda com a nota digitada. Quem testa notas seguidas mapeia as pontas de uma UF pequena. Em Roraima, Matemática 2022 (N = 3.984), a mudança de posição entre duas notas vizinhas nos extremos revela a nota de uma única pessoa.

**Regra.** Em UF e região, com uma casa decimal e `PISO_GRUPO = 100`:

- limite superior = ⌊1000 × (N − 100) / N⌋ décimos de ponto;
- limite inferior = ⌈1000 × 100 / N⌉ décimos de ponto;
- percentil acima do superior → interface mostra "acima de X%"; abaixo do inferior → "abaixo de X%"; nos demais casos, o percentil exato.

**Exemplo (Roraima, Matemática 2022):** superior = ⌊1000 × 3.884 / 3.984⌋ = 974 → 97,4%; inferior = ⌈100.000 / 3.984⌉ = 26 → 2,6%.

**Três decisões de implementação:**

1. **Comparar o percentil, não contar pessoas acima.** Com empates, contar pessoas gera rótulo falso. Minas Gerais, Redação 2020: 1.820 pessoas empatadas em 980 e 1 acima. A posição real é 99,59%, abaixo do limite de 99,9%. A regra por contagem diria "acima de 99,9%".
2. **Comparar com o limite já arredondado.** Com o limite sem arredondar, 281 dos 640 grupos exibem uma nota maior com posição menor ("100,0%" seguido de "acima de 99,9%"). Com o limite arredondado: 0 inversões.
3. **Conta em inteiros.** `limites_exibicao` e `texto_da_posicao` comparam `1000 × dobro` com `limite × 2N`. Nenhum erro de ponto flutuante desloca a borda.

**Dependência entre medidas (item 8.7).** Quando a UF está em limite, a diferença UF − Brasil não é exibida: somada ao percentil exato do Brasil, ela devolveria o valor escondido.

**Alcance.** O Brasil continua com percentil exato, conforme o ADR-001 (item 8.6). A mesma regra foi adotada depois pelo módulo Equidade (DL-03, item 10).

### 2.7 Fora do escopo

Município, UF da escola, cruzamento do território com outras variáveis e leitura causal. Registrado na DL-04, campo "Fora do escopo".

---

## 3. Mapeamento de inputs e interface de interação

Página: `app/pages/2_Recorte_territorial.py`, aberta pelo menu lateral do app Streamlit (`streamlit run app/app.py`).

### 3.1 Inputs

| # | Campo na tela | Componente | Domínio aceito | Controle na interface | Validação no backend (`validar_entrada`) | Mensagem na falha |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Edição de comparação | `st.selectbox` (fora do formulário) | Edições presentes no artefato, mais recente primeiro | Só lista edições com grupo publicado | `int`, não `bool`, presente em `anos_disponiveis` | "Edição … indisponível para comparação." |
| 2 | Em qual UF você fez a prova? | `st.selectbox`, `index=None`, rótulo "SC · Santa Catarina" | 27 siglas | Começa vazio; obriga escolha explícita | Normaliza espaços e caixa (" sc " → "SC"); rejeita vazio, `None`, sigla inexistente, nome por extenso, código de região | "Informe a UF onde você fez a prova." / "UF '…' não existe. Use a sigla de uma das 27 unidades federativas." |
| 3–6 | Ciências da Natureza, Ciências Humanas, Linguagens e Códigos, Matemática | `st.number_input`, `step=0.1`, `format="%.1f"` | 0 a 1000, uma casa decimal | `min_value=0.0`, `max_value=1000.0`, começa vazio ("não informada") | Número real finito, não `bool`, entre 0 e 1000, no máximo uma casa decimal | "A nota de … deve estar entre 0 e 1000." / "… tem no máximo uma casa decimal." / "… precisa ser um número finito." |
| 7 | Redação | `st.number_input`, `step=20.0` | 0 a 1000, múltipla de 20 | Passo de 20 nos botões | Múltipla de 20 (tolerância `1e-9`) | "A nota da redação é sempre múltipla de 20 (ex.: 620, 640)." |

**Por que a validação se repete no backend:** os limites do `number_input` controlam só a interface. `validar_entrada` é chamada pela página e pode ser chamada por qualquer outro cliente (testes, deploy futuro); as regras de domínio ficam num único lugar, no módulo.

**Notas opcionais:** o usuário pode informar de 1 a 5 notas. Cada nota informada gera uma comparação independente.

### 3.2 Fluxo de interação

1. A página carrega `dist_territorial.parquet` uma vez por processo (`@st.cache_data`).
2. O usuário escolhe a edição, a UF e preenche as notas que tiver.
3. Ao clicar em **Comparar**, a página confere UF e pelo menos uma nota (avisos em `st.warning`).
4. Para cada área informada, `validar_entrada` normaliza a entrada. Se uma nota for inválida, o erro aparece e as outras áreas continuam sendo comparadas.
5. `comparar` monta os três cenários e as medidas entre níveis; `mostrar` exibe o resultado.

O formulário (`st.form`) evita recálculo a cada tecla: a comparação só roda no envio.

### 3.3 Saídas exibidas

| Elemento | Conteúdo |
| --- | --- |
| Três métricas lado a lado | Posição na UF, na região e no Brasil. Em limite, legenda com quantas pessoas o limite cobre ("entre as cerca de N pessoas mais perto do topo") |
| Frases de comparação | Diferença UF − Brasil em pontos percentuais; probabilidade de superioridade da UF e da região; posição da mediana da UF entre as 27, com empate quando houver |
| Tabela | Grupo, participantes, média, mediana, desvio-padrão, Z da nota |
| Gráfico de densidades | Três curvas (UF, região, Brasil) com a nota do usuário marcada. Usa `densidade_protegida`: cada faixa tem pelo menos 100 pessoas |
| Gráfico de medianas (expansível) | Barras horizontais das 27 UFs; UF do usuário destacada, UFs da mesma região em tom intermediário |
| "Como a comparação é feita" | Território usado, população, definição de posição, comparação com o restante do país, privacidade e leitura não causal |

### 3.4 Privacidade da interação

| Regra (`docs/privacidade.md`) | Implementação |
| --- | --- |
| R6 — nada do que é digitado é gravado | Valores só no estado da sessão; nenhum log; nenhuma escrita em disco |
| Nada na URL | Testado em `test_dados_digitados_nao_vao_para_a_url` (`query_params` vazio após o envio) |
| Erro não expõe valores | `.streamlit/config.toml`: `client.showErrorDetails = "type"` |
| R3 — piso de 100 | Grupos menores não são gravados; gráfico em faixas de ≥ 100 pessoas |

---

## 4. Estratégia de validação e resiliência contra erros

### 4.1 Camadas de validação

| Camada | O que verifica | Onde | Comportamento na falha |
| --- | --- | --- | --- |
| 1. Widget | Faixa 0–1000, passo, UF de lista fechada | `number_input`, `selectbox` | Interface impede o valor |
| 2. Página | UF escolhida, pelo menos uma nota | `main()` | `st.warning`, nada é calculado |
| 3. Domínio | Tipo, finitude, faixa, casas decimais, passo da redação, sigla da UF, edição disponível | `validar_entrada` | `EntradaInvalida` com mensagem; a área é pulada, as outras seguem |
| 4. Dados no runtime | Artefato ausente, artefato sem grupos, grupo abaixo do piso, desvio zero, UF sem resto do país | `main()`, `_cenario`, `comparar` | Mensagem na tela; cenário com `disponivel=False`; aviso no lugar do Z-Score. `comparar` nunca levanta exceção por falta de grupo |
| 5. Publicação do artefato | Três conferências independentes e escrita atômica (§4.2) | `etapa_territorial` | `AssertionError`; nenhum arquivo é publicado |

### 4.2 Conferências antes de publicar o artefato

`etapa_territorial` só substitui `dist_territorial.parquet` depois de três verificações:

| # | Conferência | Como | O que pega |
| --- | --- | --- | --- |
| 1 | CDF em SQL = CDF em Python | `sql_artefato` (funções de janela do DuckDB) contra `calcular_cdfs` (`construir_acumulada`), grupo a grupo | Erro em janela, ordenação ou piso |
| 2 | Soma entre níveis | UFs somam a região e regiões somam o Brasil, nota a nota, antes do piso (`conferir_somas`) | UF na região errada, participante perdido ou contado duas vezes |
| 3 | CDF = contagem direta | Percentil da CDF contra `count(*)` na TRUSTED em até 8 notas por grupo (mínima, máxima, mediana, fora da faixa, 400, 500, 650); tolerância `1e-9` | Erro no cálculo do percentil |

**Escrita atômica:** o Parquet é gravado em `.dist_territorial.parquet.tmp` e só renomeado depois das conferências; o bloco `finally` apaga o temporário. Uma falha nunca deixa artefato parcial em uso pelo app.

### 4.3 Testes automatizados

Os testes não precisam dos microdados: geram dados sintéticos em tempo de execução.

**Resultado em 10/11/2026** (commit `8d70f06`, Python 3.13.18): `tests/test_territorial.py` — **59 testes OK em 32,6 s**; suíte completa — **152 testes OK em 57,2 s**; `verificar_piso.py` OK.

| Classe | Testes | O que cobre |
| --- | --- | --- |
| `TestTerritorio` | 5 | 27 UFs em 5 regiões sem repetição; tabela igual à do IBGE; códigos sem ambiguidade; UFs iguais às do dicionário do INEP |
| `TestValidacaoEntrada` | 3 | Normalização (" sc " → "SC"); 16 entradas inválidas (edição 2018, `True` como edição, área inexistente, nota `None`, texto, NaN, infinito, −0,1, 1000,1, duas casas, redação 610, UF vazia, `None`, "XX", "Santa Catarina", "NE"); Sergipe aceito |
| `TestComparacao` | 17 | Três cenários; medidas iguais às do motor; superioridade contra o restante; restante = Brasil − UF; empate de mediana; UF abaixo do piso; nota fora da distribuição; desvio zero; país com uma UF só |
| `TestLimitesExibicao` | 11 | Fórmula de Roraima; arredondamento; grupo < 200 sem posição exata; borda exata; empates sem rótulo falso; varredura sem inversão; Brasil exato |
| `TestAuditoria` | 5 | Regra atual sem rótulo falso nem inversão; regra anterior inverte; 100 pessoas de cada lado contando empates pela metade |
| `TestAgregacao` | 9 | Ponta a ponta: RAW sintético → ETL real → `dist_territorial`, contra cálculo bruto em Python. Composição com PR exatamente no piso (100) e RS abaixo (99 + 1 treineiro). Inclui três testes de falha induzida (abaixo) |
| `TestUfInvalidaNaTrusted` | 1 | UF "XX" e vazia ficam fora de todos os grupos e aparecem no manifesto |
| `TestPagina` | 8 | Página no `AppTest` do Streamlit: três cenários na tela; sem UF; sem nota; grupo insuficiente; redação inválida sem exceção; nada na URL; artefato ausente |

**Testes de falha induzida** — provam que as conferências da §4.2 bloqueiam a publicação:

| Teste | Defeito injetado | Resultado esperado e verificado |
| --- | --- | --- |
| `test_divergencia_entre_sql_e_python_bloqueia_a_publicacao` | SQL soma 1 em toda frequência (`n + 1`) | `AssertionError`; arquivo de destino não existe |
| `test_regiao_errada_bloqueia_a_publicacao` | SC classificada no Sudeste | `AssertionError` na soma UFs → região; arquivo não existe |
| `test_piso_inalcancavel_nao_publica_nada` | Piso de 10.000 | `ValueError`; arquivo não existe |

O CI (`.github/workflows/qualidade.yml`) roda a suíte inteira em todo Pull Request, junto com `compileall`, `verificar_piso.py` e o bloqueio de `.csv`, `.parquet` e `.zip` versionados.

### 4.4 Auditoria dos limites sobre os dados reais

`scripts/auditoria_limites.py` varre `dist_territorial.parquet` em notas de 0 a 1000, de 0,1 em 0,1. Execução de 03/11/2026, 40 s, 640 grupos (4 edições × 5 áreas × 32 grupos de UF e região):

| Verificação | Resultado |
| --- | --- |
| Rótulos falsos com a regra adotada | 0 |
| Inversões de ordem com a regra adotada | 0 |
| Grupos com inversão se o limite não fosse arredondado | 281 de 640 |
| Grupos em que o limite cobre mais de 150 pessoas | 196 de 640 |
| Mudanças de posição em nota de uma só pessoa (2022, áreas objetivas), sem limite | 3.116 |
| Idem, com limite | 2.812 (−10%) |

O risco residual (2.812 ocorrências no meio da distribuição, 2.714 em grupos com menos de 100 mil participantes) foi aceito pelo PO em 03/11/2026, com os motivos registrados na DL-04, "Aceite do PO".

### 4.5 Casos de erro e comportamento

| Situação | O que o usuário vê | Teste |
| --- | --- | --- |
| Artefato não gerado | "Artefato do módulo ausente. Rode `scripts/etl.py` e depois `scripts/territorial.py`." | `test_artefato_ausente` |
| UF não escolhida | "Informe a UF onde você fez a prova." | `test_sem_uf_pede_a_uf` |
| Nenhuma nota | "Informe ao menos uma nota." | `test_sem_nota_pede_ao_menos_uma` |
| Redação 610 | Erro "múltipla de 20"; página não quebra | `test_redacao_invalida_mostra_erro_sem_quebrar` |
| UF abaixo do piso | Métrica "—" e "grupo insuficiente: menos de 100 participantes…"; região e Brasil continuam | `test_uf_abaixo_do_piso_vira_grupo_insuficiente` |
| Grupo com todas as notas iguais | Z "indefinido" e aviso | `test_desvio_zero_vira_aviso` |
| Nota acima da maior observada | Posição calculada sem exceção | `test_nota_fora_da_distribuicao` |

---

## 5. Comprovação de autoria e rastreabilidade no GitHub

### 5.1 Commits do módulo

| Commit | Data | Branch / PR | Conteúdo |
| --- | --- | --- | --- |
| `6ad25bf` | 03/11/2026 11:03 | `modulo-territorial` → PR #12 (merge `1920a92`, 03/11/2026 15:05) | Criação do módulo: `territorial.py` (652 linhas), `auditoria_limites.py` (196), página (235), testes (765), DL-04 (148 linhas em `docs/decisoes/README.md`), `privacidade.md`, `README.md`. 7 arquivos, +2.002 linhas |
| `b23c2da` | 08/11/2026 23:27 | `estatistica-compartilhada` → PR #17 (merge `8d70f06`, 10/11/2026 09:21) | Refatoração: funções de exibição comuns saem de `territorial.py` e `equidade.py` para `scripts/estatistica.py`; novo `tests/test_modulos_independentes.py` (3 testes) |

O autor dos dois commits é `viniciusjoaciranjos@gmail.com`. O nome bruto do commit `6ad25bf` é "Vinicius_joacir"; o `.mailmap` do repositório (PR #9) o unifica como "Vinícius Joacir dos Anjos" em `git log` e `git shortlog`.

### 5.2 Autoria linha a linha

`git blame` no commit `8d70f06`:

| Arquivo | Linhas | Linhas de Vinícius Joacir dos Anjos |
| --- | --- | --- |
| `scripts/territorial.py` | 567 | 567 (100%) |
| `scripts/auditoria_limites.py` | 194 | 194 (100%) |
| `app/pages/2_Recorte_territorial.py` | 233 | 233 (100%) |
| `tests/test_territorial.py` | 766 | 766 (100%) |

Os quatro arquivos declaram o autor no docstring do topo.

### 5.3 Separação entre lógica do módulo e componentes compartilhados

A "Observação de autoria AV4" do Plano de Trabalho permite reutilizar componentes compartilhados, desde que regras, testes e commits do módulo sejam do autor.

| Pertence ao módulo (autoria exclusiva) | Reutilizado de componente compartilhado |
| --- | --- |
| Tabela UF → região, códigos de grupo, `validar_entrada` | `PISO_GRUPO` (`scripts/colunas.py`) |
| SQL de contagem por UF/região/Brasil, `calcular_cdfs`, `conferir_somas`, `percentil_direto`, `etapa_territorial` | `construir_acumulada`, `resumo`, `quantil`, `z_score`, `prob_superioridade` (motor v1, `scripts/estatistica.py`) |
| `restante`, `comparar`, `posicao_da_mediana`, `medianas_ufs` | `limites_exibicao`, `texto_da_posicao`, `dobro_posicao`, `densidade_protegida` (em `estatistica.py` desde o PR #17) |
| Página, gráficos, textos de explicação | ETL e TRUSTED (`scripts/etl.py`) |
| Auditoria dos limites | — |

As funções de limite (`limites_exibicao`, `texto_da_posicao`, `dobro_posicao`, `alcance_do_limite`) foram escritas para este módulo no commit `6ad25bf` e movidas para `estatistica.py` no `b23c2da`, sem mudança de comportamento, porque a Equidade e o Capital escolar passaram a usá-las. `tests/test_modulos_independentes.py` lê os imports com `ast` e falha se um módulo autoral importar outro.

### 5.4 Decisão registrada e aceita

A DL-04 registra autor, data (02/11/2026), contexto, 11 itens de decisão, escopo excluído, evidências no código e o aceite do PO (Samuel Silva de Rezende, 03/11/2026, revisado no PR #12), inclusive do risco residual do item 8.9.

### 5.5 Como verificar

```sh
git clone https://github.com/gilas-byte/projetoAplicado3 && cd projetoAplicado3

# commits do módulo, com autor e data
git log --format='%h %ad %aN <%aE> | %s' --date=short -- \
  scripts/territorial.py app/pages/2_Recorte_territorial.py \
  tests/test_territorial.py scripts/auditoria_limites.py

# autoria linha a linha
git blame --line-porcelain scripts/territorial.py | grep '^author ' | sort | uniq -c

# testes do módulo (não precisam dos microdados)
python -m unittest tests/test_territorial.py -v
```

### 5.6 Limites da rastreabilidade

| Ponto | Situação |
| --- | --- |
| Granularidade | O módulo entrou em um único commit (+2.002 linhas). O histórico não mostra as etapas intermediárias do desenvolvimento |
| Tag de release | Não há tag do módulo. O módulo Equidade tem `av4-equidade-samuel` |
| Merge do PR #12 | O commit de merge `1920a92` tem Vinícius como autor. A revisão de Samuel está registrada na DL-04; o registro da revisão no GitHub não foi consultado nesta análise (Informação não especificada) |

---

## 6. Limitações conhecidas do módulo

| Limitação | Efeito | Fonte |
| --- | --- | --- |
| UF da prova ≠ UF de residência ou da escola | Quem fez a prova fora do estado onde estudou é comparado com a UF da prova | DL-04, item 1 |
| Risco residual no meio da distribuição | Em grupos pequenos, a mudança da posição exibida ainda pode coincidir com a nota de uma só pessoa (2.812 ocorrências em 2022) | DL-04, item 8.9 |
| Custo dos limites nos grupos grandes | Até ~1,1 mil pessoas perdem a posição exata (Nordeste, 2019) | DL-04, item 8.3 |
| Grupo com N < 200 | Limites se cruzam; nunca há posição exata. Não ocorre hoje (menor grupo: 3.984) | DL-04, item 8.8 |
| Resultados reais não versionados | Não existe `docs/modulos/territorial-resultados.md` equivalente ao da Equidade; tamanho e número de linhas de `dist_territorial.parquet`: Informação não especificada | `docs/modulos/` |
| Sem deploy | Latência real da página não medida; publicação prevista no Replit até 13/11/2026 | DL-06, DL-07 |

---

## 7. Próximos passos

| # | Ação | Estimativa |
| --- | --- | --- |
| 1 | Criar a tag `av4-territorial-vinicius` no merge `1920a92` e enviá-la ao GitHub | 2 min |
| 2 | Rodar `scripts/territorial.py` e registrar em `docs/modulos/territorial-resultados.md` volumetria, medianas por UF e um exemplo da interface | 30 min com a TRUSTED já gerada |
| 3 | Medir o tempo de resposta da página após o deploy no Replit (RNF02: ≤ 3 s) | 15 min após o deploy |
