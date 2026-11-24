#C Produto, equipe e processo | Visão geral do Radar ENEM, requisitos e forma de trabalho

## Visão geral do produto

O Radar ENEM é uma aplicação web de quatro páginas, construída em Streamlit, que responde a uma pergunta por página. Todas usam a mesma população de comparação (participantes elegíveis da edição, com nota na área), o mesmo motor estatístico e o mesmo formulário de notas, de modo que um usuário que aprende a usar uma página sabe usar as outras.

Quadro: Páginas do Radar ENEM e a pergunta que cada uma responde
Larguras: 20,44,36
| Página | Pergunta | Grupos de comparação |
| --- | --- | --- |
| Início | Em que posição a minha nota fica entre todos os participantes elegíveis da edição? | Brasil (população elegível da edição) |
| Equidade socioeconômica | A mesma nota ocupa posições diferentes entre quem tem a mesma renda familiar e entre participantes de escola privada de alta renda? | Seis faixas de renda (R1 a R6) e o grupo de contraste |
| Recorte territorial | A mesma nota ocupa a mesma posição no estado, na região e no Brasil? | 27 UFs, 5 regiões do IBGE e Brasil |
| Capital escolar familiar | A mesma nota ocupa a mesma posição entre participantes cujos responsáveis têm a mesma escolaridade? | Seis níveis de escolaridade (A a G) e Brasil |
Fonte: elaborado pela equipe a partir das páginas do app (`app/app.py` e `app/pages/`).

O fluxo de uso é o mesmo em todas as páginas:

- o usuário escolhe a edição de comparação (2019 a 2022);
- informa uma ou mais notas (as cinco são opcionais, basta uma) e, nos módulos, o atributo de comparação (alternativa de renda do questionário, UF da prova ou escolaridade dos responsáveis, sempre com o texto exato do questionário daquela edição);
- clica no botão de comparação; o app calcula a posição de cada nota em cada grupo e mostra o resultado em duas abas, "Visão simples" e "Visão técnica";
- o bloco "Como a comparação é feita" explica quem entra no grupo, como o percentil é calculado, o que o resultado não significa e qual é a fonte.

Nada é gravado: o que o usuário digita existe só na memória da sessão e desaparece ao fechar a aba (regra R6, seção 5.9).

## Requisitos funcionais e não funcionais

Os requisitos vêm do Plano de Trabalho (item 7). O relatório da AV3 registrou a situação de cada um em 13/10/2026, quando vários dependiam dos módulos e da hospedagem. O quadro a seguir mostra a situação final, com a evidência de atendimento; a avaliação detalhada, com números, está na seção 7.5.

Quadro: Requisitos do Plano de Trabalho e situação final
Larguras: 8,32,12,48
| ID | Requisito | Situação | Evidência |
| --- | --- | --- | --- |
| RF01 | O usuário informa notas e os atributos de cada módulo | Atendido | Formulários das quatro páginas, com alternativas lidas do dicionário de cada edição (seção 5.1) |
| RF02 | Estatísticas do grupo de referência: N, tendência, dispersão, percentil e Z-Score | Atendido | Motor estatístico (`scripts/estatistica.py`) e visão técnica de cada página (capítulo 4) |
| RF03 | Módulos comparativos autorais, um por integrante | Atendido com corte registrado | Três módulos (Equidade, Recorte territorial, Capital escolar); o quarto saiu do escopo pela DL-07 |
| RF04 | Visualizações e explicações metodológicas, com limitações | Atendido | Histograma, curvas, caixa protegida, gráfico de medianas por UF e blocos de explicação (capítulo 5) |
| RF05 | Tratar entradas inválidas e grupos insuficientes sem falhar | Atendido | Mensagens de erro em português, "grupo insuficiente" abaixo do piso, testes de casos de erro (seções 4.12 e 5.9) |
| RF06 | Aplicação web pública e gratuita para o usuário | Atendido | Publicada no Replit desde 19/11/2026, sem cadastro (capítulos 6 e 7) |
| RNF01 | Não carregar o CSV bruto no runtime | Atendido | O app lê só os cinco artefatos da ANALYTICS, 12,6 MB (seção 3.7) |
| RNF02 | Consultas representativas em até 3 s no ambiente-alvo | Atendido | Consulta p95 de 70 a 416 ms no ambiente de publicação; primeira abertura mais lenta em 4,1 s, uma vez por publicação (seção 7.2) |
| RNF03 | Pipeline reprodutível, versionado, testado e rastreável | Atendido | Um comando por camada, hash da fonte, manifestos com `run_id`, 282 testes, CI, PRs revisados e tags (seções 2.5 e 3.12) |
| RNF04 | Não persistir os dados informados pelo usuário | Atendido | Entradas só no estado da sessão, sem URL, log ou analytics de terceiros, com teste automatizado (seção 5.9) |
| RNF05 | Segurança, acessibilidade, clareza, responsividade e monitoramento | Atendido | Auditoria de dependências, proteções do servidor, WCAG 2.1 AA sem violações, telas para celular e monitor externo (seções 5.8, 6.11 e 6.12) |
Fonte: elaborado pela equipe a partir do Plano de Trabalho (item 7), do relatório da AV3 (seção 4) e das evidências citadas.

O RNF02 merece uma observação. A primeira abertura da página do Recorte territorial depois de cada publicação ou reinício carrega 2,2 milhões de linhas e levou 4,1 s no ambiente do Replit. Esse custo é pago uma vez por processo, e não por usuário: o artefato fica em cache compartilhado entre todas as sessões (seção 6.10), e o procedimento de publicação inclui abrir as quatro páginas logo depois de publicar, para que nenhum visitante pague esse tempo (seção 6.6).

## Equipe, papéis e evolução

O Plano de Trabalho previu quatro integrantes e quatro módulos autorais. Guilherme Zamboni Menegacio, responsável por design, frontend e suporte, deixou a equipe antes da AV2. A mudança foi registrada na DL-02: Guilherme da Silva Anselmo assumiu também design e frontend, além do módulo Rede de ensino de origem, que depois saiu do escopo (DL-07).

Quadro: Papéis da equipe na versão final do projeto
Larguras: 24,22,54
| Integrante | Papel | Responsabilidades principais |
| --- | --- | --- |
| Samuel Silva de Rezende (matrícula 2192212) | Líder da equipe e Product Owner | Visão do produto, escopo, priorização, regras e aceite do motor estatístico, Decision Log, módulo Equidade socioeconômica, hospedagem no Replit (DL-06 e DL-08), pente fino da AV6 (DL-10) e consolidação dos relatórios |
| Vinícius Joacir dos Anjos (matrícula 2175294) | Líder de Desenvolvimento e IA | Fundação de dados, benchmark da stack, pipeline ETL, MVP, motor estatístico v1, módulo Recorte territorial e revisão da maior parte dos PRs |
| Guilherme da Silva Anselmo (matrícula 2182147) | QA, Validações, Integridade e Segurança · Design e Frontend | Integração dos primeiros PRs, regras e código do módulo Capital escolar familiar, interface com tema escuro e fontes locais (DL-09), revisão da identidade visual e das dependências |
Fonte: elaborado pela equipe a partir do Plano de Trabalho, da DL-02 e do histórico do GitHub. A atuação detalhada de cada integrante está no Apêndice C.

Ao longo do projeto, o PO assumiu frentes que eram de outros integrantes para cumprir as datas dos professores: a hospedagem, que estava com Vinícius no plano da Sprint 6 (DL-06), e o pente fino de QA, segurança e otimização da AV6, que pelo Plano seria do responsável por QA (DL-10). Nos dois casos a decisão foi registrada antes da execução, e a rastreabilidade foi mantida: cada mudança entrou por Pull Request, com revisão de outro integrante e CI verde. A autoria individual dos módulos da AV4 não foi afetada, porque nenhum integrante escreveu a lógica do módulo de outro.

## Processo de trabalho e cronograma

O projeto foi conduzido de forma iterativa e incremental (HIGHSMITH, 2012), em sprints de duas semanas associadas às avaliações. O quadro compara o cronograma do Plano de Trabalho com o que foi realizado.

Quadro: Cronograma planejado e realizado
Larguras: 15,40,45
| Sprint e período | Planejado | Realizado |
| --- | --- | --- |
| 0 – 10/08 a 25/08 | Planejamento, AV1, recorte 2019 a 2022, papéis e riscos | Plano de Trabalho entregue (AV1), versionado no commit `19a00ba` |
| 1 – 26/08 a 08/09 | Fundação de dados, profiling, contrato, hash e POC de nuvem | Hash, profiling, dicionário, contrato e política de LGPD (PR #3, 25/09). A POC de nuvem não foi feita nesta sprint |
| 2 – 09/09 a 22/09 | ETL v1, Parquet, benchmark e motor v0 | Benchmark e pipeline em DuckDB (PRs #4 e #5) |
| 3 – 23/09 a 29/09 | MVP ponta a ponta, AV2 | MVP nota, percentil e histograma; apresentação da AV2 em 29/09 |
| 4 – 30/09 a 13/10 | Engenharia consolidada, AV3 | Percentil exato, validação do ETL, CI e relatório da AV3 (PRs #7 e #8, 13/10) |
| 5 – 14/10 a 27/10 | Motor v1, regras dos módulos, beta em nuvem | Motor v1 e regras dos módulos concluídos entre 02/11 e 09/11 (PRs #10 a #16); a beta ficou para a Sprint 7 |
| 6 – 28/10 a 10/11 | Módulos v2, interface integrada, acessibilidade e segurança | Três módulos no `main` até 10/11 (PRs #10, #12 e #20); corte do quarto módulo (DL-07); nova interface (PR #30, 16/11) |
| 7 – 11/11 a 24/11 | Aplicação pública estável, AV4 e AV6 | AV4 consolidada (PR #32), atualizações da AV6 (PR #33), beta publicada em 19/11 (PRs #35 a #37), identidade visual (PR #38) e pente fino (PR #39) |
| 8 – 25/11 a 01/12 | Banca: freeze, ensaio e contingência | Release `v1.0`, monitoramento contínuo e banca em 01/12/2026 |
Fonte: elaborado pela equipe a partir do Plano de Trabalho (item 11), da DL-07 e do histórico de PRs no GitHub.

Dois desvios de cronograma pesaram no resultado. O primeiro foi a prova de conceito em nuvem, prevista para a Sprint 1 e feita só na Sprint 7. A equipe priorizou a fundação de dados e o motor estatístico, e a escolha do provedor só foi decidida em 03/11 (DL-06). O efeito foi concentrar na última sprint a descoberta de restrições da plataforma, como o filtro de pacotes do Replit, que recusou a versão do Pillow por causa de uma vulnerabilidade conhecida (seção 6.7). O segundo foi o atraso do módulo Capital escolar familiar: o código entrou em 10/11, no limite, e o capítulo autoral em 15/11, cinco dias depois do prazo da DL-07, após cobrança nas issues #25 e #26. A resposta do PO foi a prevista no Plano para atraso de módulo individual: reduzir escopo (corte do quarto módulo) antes de transferir autoria.

Em 08/11, o professor de Engenharia de Dados pediu o relatório final de tudo até 19/11, e a equipe adotou essa data como referência (DL-07). Em 24/11, o mesmo professor pediu a AV3, e não a AV6; a equipe enviou a AV3 para manter a entrega padronizada com o que foi feito no Projeto Aplicado, e o relatório final segue como entrega da AV6.

### Riscos previstos e como se materializaram

O Plano de Trabalho registrou uma matriz de riscos. O quadro mostra o que aconteceu com cada um.

Quadro: Riscos do Plano de Trabalho e desfecho
Larguras: 24,38,38
| Risco | Resposta prevista | Desfecho |
| --- | --- | --- |
| Dataset exceder memória ou tempo | Processamento offline, seleção de colunas, Parquet, pré-agregação e benchmark | Não se materializou: pipeline em 112,3 s com pico de 2,65 GB; app com 12,6 MB de dados |
| Limites ou custos do provedor de nuvem | POC antecipada, medição de memória, alternativa em contêiner | Materializou-se em parte: o filtro de pacotes e a verificação de segurança do Replit atrasaram a beta em dois dias; memória e custo ficaram dentro do previsto |
| Erro de definição estatística | Metodologia documentada, casos sintéticos e revisão | Mitigado: CDF conferida contra contagem direta (0,0 pp), convenções na DL-01 e testes com resultado conhecido |
| Perda silenciosa de registros | Funil de qualidade e testes de invariantes | Não ocorreu: as categorias do funil somam o total de inscritos em todas as edições |
| Atraso de módulo individual | Reduzir escopo antes de transferir autoria | Materializou-se: corte do quarto módulo (DL-07) e atraso de cinco dias de um capítulo |
| Conflito de autoria da AV4 | Um autor por módulo, PRs rastreáveis | Não ocorreu: tags individuais `av4-*` e funções compartilhadas separadas (PR #17) |
| Interpretação social inadequada | Linguagem observacional e tamanho do grupo explícito | Mitigado: avisos de leitura em todas as páginas, comparação com outro nível opcional e N sempre visível |
| Falha de publicação ou da banca | Freeze, teste de fumaça e monitoramento do link | Mitigado: monitor externo a cada 3 horas e procedimento de republicação de cerca de 3 minutos |
| Mudança relevante de escopo ou stack | ADR, análise de impacto e aprovação do PO | Aplicado: troca de Polars por DuckDB, ADR-001 do percentil exato e DLs de hospedagem |
Fonte: elaborado pela equipe a partir do Plano de Trabalho (item 12) e do Decision Log.

## Governança do desenvolvimento

O Plano previa que toda integração relevante ocorreria por Pull Request revisado por pelo menos um integrante diferente do autor, com releases nos principais marcos e registro das decisões. A prática adotada foi a seguinte.

### Pull Requests e revisão

Do PR #3 ao PR #39, todas as mudanças de código e de documentação entraram na `main` por Pull Request. Nas primeiras entregas (PRs #3 a #6, #8 e #9), a integração foi feita por um integrante diferente do autor, mas sem aprovação formal registrada na ferramenta de revisão, o que o relatório da AV3 apontou como pendência. A partir do PR #10, a aprovação passou a ser registrada no GitHub em quase todos os PRs (as exceções foram o #11 e o #28, integrados por outro integrante sem aprovação registrada), e as revisões deixaram de ser apenas formais: no PR #37, o revisor pediu e obteve cinco correções de texto e de medida; no PR #38, o revisor apontou sete problemas (texto alternativo do logotipo, posição do bloco de execução dos testes, um teste fraco, dependência de seletores internos do Streamlit, um efeito visual sem uso, detecção de tema pela cor e fundo transparente), todos corrigidos antes do merge; no PR #39, o revisor pediu quatro ajustes (legenda do percentil de acordo com o posto médio, congelamento recursivo do cache, regra para vulnerabilidade nova no `pip-audit` e reativação do monitor depois de 60 dias sem atividade), atendidos antes da aprovação. O Apêndice B lista os PRs, os autores, os revisores e quem fez o merge.

### Integração contínua

O workflow `.github/workflows/qualidade.yml` roda no GitHub Actions a cada Pull Request e a cada push na `main`. Na versão final, ele compila os módulos, roda o linter ruff (regras F, E9 e B), audita as dependências com pip-audit, executa os 282 testes com dados sintéticos, roda o `verificar_piso.py` e falha se algum arquivo `.csv`, `.parquet` ou `.zip` estiver versionado. Um segundo workflow, `monitor-producao.yml`, verifica a aplicação publicada a cada três horas (seção 6.12).

### Registro de decisões

As decisões de produto, metodologia, equipe e infraestrutura estão no Decision Log (`docs/decisoes/README.md`), com dez entradas, de DL-01 a DL-10. Cada uma traz data, responsável, situação, contexto, decisão e evidência no repositório, e nenhuma é apagada: quando muda, a entrada antiga recebe a indicação da substituta. A decisão de arquitetura mais importante, o percentil exato pela CDF empírica, tem um ADR próprio (`docs/av3/DECISAO-001-percentil-exato.md`), aceito pelo PO em 03/11/2026 (PR #14) e revisado pelo QA no pente fino da AV6. O Apêndice A resume as dez decisões.

### Tags e releases

As entregas individuais da AV4 foram marcadas com as tags `av4-equidade-samuel`, `av4-territorial-vinicius` e `av4-capital-gilas`. A beta publicada em 19/11/2026 recebeu a tag `v1.0-beta`, e a versão descrita neste relatório, o commit `48a32cd` da `main` (merge do pente fino, PR #39), recebeu a tag `v1.0`. As notas de cada release estão em `docs/releases/README.md`.

### Uso de inteligência artificial

O uso de ferramentas de IA generativa no desenvolvimento é declarado em `docs/uso-de-ia.md` e no Apêndice D. Treze commits do início do projeto registram coautoria de IA na mensagem; a equipe decidiu não reescrever o histórico para não alterar os hashes citados nos relatórios e nas tags, e a partir de 10/11/2026 os commits passaram a registrar apenas o autor humano, que responde pelo conteúdo.
