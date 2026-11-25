#U Apêndices |

##U Apêndice A – Decision Log resumido

O Decision Log completo, com contexto, alternativas e evidências de cada decisão, está em `docs/decisoes/README.md`. O quadro resume as dez entradas.

Quadro: Resumo das decisões registradas (DL-01 a DL-10)
Larguras: 8,12,30,50
| ID | Data | Assunto | Decisão principal |
| --- | --- | --- | --- |
| DL-01 | 02/11 | Convenções estatísticas do motor v1 | Variância populacional, mediana inferior e arredondamento só na exibição |
| DL-02 | 02/11 | Saída de um integrante e redistribuição | Equipe de três; Guilherme Anselmo assume design, frontend e o quarto módulo |
| DL-03 | 02/11 | Regras do módulo Equidade socioeconômica | Seis faixas de renda em salários mínimos e grupo de contraste fixo; limites de exibição |
| DL-04 | 02/11 | Regras do módulo Recorte territorial | UF de prova, três níveis sem município, restante do país na comparação e limites de exibição |
| DL-05 | 03/11 | Regras do módulo Capital escolar familiar | Maior nível entre pai e mãe, seis níveis, comparação com vizinho opcional |
| DL-06 | 03/11 | Hospedagem em teste no Replit | Projeto privado com artefatos fora do Git; critérios de revisão; substituída em parte pela DL-08 |
| DL-07 | 08/11 | Corte do quarto módulo e prazo de 19/11 | Rede de ensino de origem fora do escopo; cronograma até a entrega |
| DL-08 | 16/11 | Replit definitivo e publicação beta | Reserved VM, barreira de auditoria antes de publicar, agente só com prompt fechado |
| DL-09 | 16/11 | Servidor de estáticos só para as fontes | Fontes locais para não enviar o IP do visitante a terceiros, com quatro condições |
| DL-10 | 24/11 | Pente fino pelo PO e identidade visual | PO executa QA, segurança e otimização com revisão dos demais; usabilidade com usuários e RTO medido ficam de fora |
Fonte: `docs/decisoes/README.md`.

##U Apêndice B – Rastreabilidade no GitHub

O repositório oficial é <https://github.com/gilas-byte/projetoAplicado3>. O quadro lista os Pull Requests integrados desde a fundação de dados, com o autor, quem aprovou na ferramenta de revisão e quem fez o merge. As datas são as do merge registradas pelo GitHub (horário UTC).

Quadro: Pull Requests do projeto
Larguras: 7,47,12,13,12,9
| PR | Título | Autor | Aprovação | Merge | Data |
| --- | --- | --- | --- | --- | --- |
| #3 | Fundação de dados: camada RAW, profiling, dicionário, contrato e LGPD (2019–2022) | Vinícius | — | Guilherme | 25/09 |
| #4 | Stack, ETL e MVP: benchmark, pipeline RAW → TRUSTED → ANALYTICS e app de percentil | Vinícius | — | Guilherme | 25/09 |
| #5 | Stack etl mvp | Vinícius | — | Guilherme | 28/09 |
| #6 | docs: equipe atualizada e roteiro da AV2 | Vinícius | — | Vinícius | 28/09 |
| #7 | feat(av3): percentil exato, validação do ETL e testes de ponta a ponta | Samuel | Vinícius | Vinícius | 13/10 |
| #8 | docs(av3): relatório técnico de engenharia de dados com a execução real do ETL | Vinícius | — | Vinícius | 14/10 |
| #9 | chore: unificar autores no historico com .mailmap | Vinícius | — | Vinícius | 29/10 |
| #10 | Módulo Equidade socioeconômica (AV4) – Samuel | Samuel | Vinícius | Vinícius | 02/11 |
| #11 | feat(motor): medidas v1 sobre a CDF exata com testes | Vinícius | — | Vinícius | 02/11 |
| #12 | feat(territorial): modulo Recorte territorial (UF, regiao e Brasil) | Vinícius | Samuel | Vinícius | 03/11 |
| #13 | Equidade: limites de exibição do percentil (DL-03, item 10) e aceite da DL-04 | Samuel | Vinícius | Vinícius | 03/11 |
| #14 | docs: ADR-001 aceito pelo PO e status do README atualizado | Samuel | Vinícius | Guilherme | 05/11 |
| #15 | docs(decisoes): DL-05 regras do modulo Capital escolar familiar | Guilherme | Samuel, Vinícius | Vinícius | 09/11 |
| #16 | docs(decisoes): aceite da DL-05, hospedagem no Replit (DL-06) e corte do Rede de ensino com prazo final em 19/11 (DL-07) | Samuel | Vinícius | Guilherme | 09/11 |
| #17 | refactor(estatistica): funções de exibição compartilhadas saem dos módulos autorais | Vinícius | Samuel | Vinícius | 10/11 |
| #18 | docs(readme): status de 15/11 com os módulos, a hospedagem e o prazo final | Samuel | Vinícius | Samuel | 16/11 |
| #19 | docs(territorial): relatorio autoral do modulo Recorte territorial (AV4) | Vinícius | Samuel | Guilherme | 10/11 |
| #20 | feat(capital): módulo capital escolar familiar (código, página e testes) | Guilherme | Samuel | Guilherme | 10/11 |
| #21 | docs(ia): declaração de uso de IA nos commits já publicados | Samuel | Vinícius | Vinícius | 13/11 |
| #22 | docs(capital): medianas por nível, probabilidade de superioridade e exemplo da interface | Guilherme | Samuel | Guilherme | 16/11 |
| #23 | fix(app): vírgula do texto do percentil na Equidade virava ponto | Samuel | Vinícius | Samuel | 16/11 |
| #24 | docs(av4): capítulo da Equidade em Word como modelo e padrão dos capítulos individuais | Samuel | Vinícius | Samuel | 16/11 |
| #27 | fix: ignorar arquivo .env e secrets do Streamlit | Vinícius | Samuel | Guilherme | 16/11 |
| #28 | docs(av4): capitulo 2 - Recorte territorial (Word) | Vinícius | — | Guilherme | 16/11 |
| #29 | docs(av4): capítulo do módulo capital escolar familiar em word | Guilherme | Samuel | Guilherme | 16/11 |
| #30 | feat(front): tema escuro, anel animado e sidebar nova | Guilherme | Samuel | Guilherme | 16/11 |
| #31 | docs(av4): capitulo 2 cita a tag av4-territorial-vinicius | Vinícius | Samuel | Vinícius | 16/11 |
| #32 | docs(av4): relatório consolidado da AV4 (Word e PDF) e cronograma atualizado | Samuel | Vinícius | Samuel | 18/11 |
| #33 | av6: deploy no Replit, estatística, engenharia e dashboard com visão simples e técnica | Samuel | Vinícius | Samuel | 17/11 |
| #34 | fix(capital): tabela da visão técnica cabe na largura da página | Samuel | Vinícius | Samuel | 17/11 |
| #35 | fix(deps): Streamlit 1.66.1 e Pillow 13.0.0 para publicar no Replit | Samuel | Guilherme | Samuel | 18/11 |
| #36 | fix(deps): fixa as dependências indiretas e alinha o .replit com a publicação | Samuel | Vinícius | Samuel | 19/11 |
| #37 | docs(deploy): medições da beta no Replit e link público (DL-06, DL-08) | Samuel | Vinícius | Samuel | 19/11 |
| #38 | feat(front): logotipos do Radar ENEM e da KiraSapiens e bordas e arcos em azul neon | Samuel | Guilherme | Guilherme | 24/11 |
| #39 | av6: pente fino (otimização, QA, segurança, acessibilidade e monitoramento) | Samuel | Vinícius | Samuel | 25/11 |
Fonte: API do GitHub, consultada em 24/11/2026, depois do merge do PR #39.

Quadro: Tags de entrega e de versão
Larguras: 26,22,52
| Tag | Commit | Marco |
| --- | --- | --- |
| `av4-equidade-samuel` | `14304aa` (branch do PR #10) | Entrega individual da AV4, módulo Equidade |
| `av4-territorial-vinicius` | `6ad25bf` (commit do módulo, PR #12) | Entrega individual da AV4, módulo Recorte territorial |
| `av4-capital-gilas` | `dc6a6ba` (merge do PR #20) | Entrega individual da AV4, módulo Capital escolar |
| `v1.0-beta` | `eb695db` (merge do PR #37) | Publicação beta no Replit, 19/11/2026 |
| `v1.0` | `48a32cd` (merge do PR #39) | Versão final descrita neste relatório, 24/11/2026 |
Fonte: `git tag -l` e `docs/releases/README.md`.

Quadro: Commits por integrante (sem commits de merge)
Larguras: 50,20,30
| Integrante | Commits | Observação |
| --- | --- | --- |
| Samuel Silva de Rezende | 85 | Inclui os 8 commits do PR #39 |
| Guilherme da Silva Anselmo | 31 | Inclui os commits feitos como `gilas-byte` e `Gilasexe` |
| Vinícius Joacir dos Anjos | 21 | Inclui os commits feitos como `Vinicius_joacir` |
Fonte: `git shortlog -sn --no-merges` na `main`, com o `.mailmap` do repositório, depois do merge do PR #39 (24/11/2026).

Para conferir a autoria de qualquer trecho:

```
git log --format='%h %ad %an %s' --date=short -- <arquivo>
git blame <arquivo>
git log origin/main --merges --format='%h %ad %s' --date=short
```

##U Apêndice C – Atuação da equipe

A atuação de cada integrante está descrita em terceira pessoa, a partir do histórico do repositório, dos PRs e do Decision Log.

#### Samuel Silva de Rezende – Líder da equipe e Product Owner

Samuel conduziu a visão do produto, o escopo e as prioridades, e foi o responsável pelo aceite das regras do motor estatístico e dos módulos. Na AV3, implementou o percentil empírico exato por posto médio, a geração da CDF exata no ETL com manifesto e hashes, a validação da CDF contra a contagem direta, o teste de ponta a ponta com microdados sintéticos e o primeiro workflow de CI (PR #7), além de propor o ADR-001. Na AV4, desenvolveu o módulo Equidade socioeconômica (PRs #10 e #13), com as regras da DL-03, e consolidou o relatório da equipe (PR #32). Registrou as decisões de equipe, de prazo e de hospedagem (DL-01, DL-02, DL-06 a DL-10), assumiu a publicação no Replit, que estava prevista para outro integrante, e conduziu a beta, a correção das dependências e as medições no ambiente real (PRs #35 a #37). Na AV6, implementou as análises estatísticas, a auditoria de artefatos, o modelo dimensional, o dicionário de indicadores e as visões simples e técnica (PR #33), a identidade visual (PR #38) e o pente fino de QA, segurança, otimização, acessibilidade e monitoramento (PR #39), e redigiu este relatório. Revisou e integrou PRs dos outros integrantes, como os do módulo territorial e do módulo de capital escolar.

#### Vinícius Joacir dos Anjos – Líder de Desenvolvimento e IA

Vinícius construiu a fundação de dados do projeto: a rastreabilidade da camada RAW com os hashes da fonte, o profiling das quatro edições, o dicionário harmonizado, o contrato de dados e a política de proteção de dados com o piso de 100 participantes (PR #3). Fez a pesquisa e o benchmark da stack que levou à troca do Polars pelo DuckDB, o pipeline RAW, TRUSTED e ANALYTICS e o MVP da aplicação (PRs #4 e #5), e redigiu o relatório técnico da AV3 (PR #8). Na Sprint 5, implementou o motor estatístico v1 sobre a CDF exata (PR #11). Na AV4, desenvolveu o módulo Recorte territorial (PR #12), com as regras da DL-04, incluindo os limites de exibição do percentil contra inferência por consultas repetidas, que depois foram adotados pelos outros módulos, e a auditoria desses limites sobre os dados reais; extraiu as funções de exibição compartilhadas para o motor (PR #17) e entregou o relatório e o capítulo autoral do módulo (PRs #19, #28 e #31). Também corrigiu o `.gitignore` para proteger arquivos de segredos (PR #27) e unificou os autores do histórico com o `.mailmap` (PR #9). Foi o revisor da maior parte dos PRs do projeto, com revisões que pediram correções de conteúdo, como as cinco sugestões aplicadas no PR #37 e os quatro ajustes pedidos no PR #39 do pente fino (legenda do percentil, congelamento do cache, regra do `pip-audit` e operação do monitor), atendidos antes da aprovação.

#### Guilherme da Silva Anselmo – QA, Validações, Integridade e Segurança · Design e Frontend

Guilherme integrou os primeiros PRs da fundação de dados e do pipeline (PRs #3 a #5) e, depois da saída de Guilherme Zamboni, assumiu também design e frontend (DL-02). Na AV4, escreveu as regras do módulo Capital escolar familiar (DL-05, PR #15) e desenvolveu o módulo, com a página e os testes (PR #20), a documentação dos resultados com os microdados reais (PR #22) e o capítulo autoral (PR #29). Construiu a nova interface do produto (PR #30): o tema escuro e o claro, o anel animado do percentil, a barra lateral própria, os novos gráficos das páginas e as fontes IBM Plex servidas localmente, cuja decisão ficou registrada na DL-09. Na AV6, revisou e aprovou a correção de dependências do PR #35 e a identidade visual do PR #38, em que apontou sete problemas de acessibilidade, testes e robustez do CSS, todos corrigidos antes do merge.

##U Apêndice D – Declaração de uso de inteligência artificial

A equipe usou ferramentas de inteligência artificial generativa como apoio no desenvolvimento e na documentação, e declara esse uso de forma transparente, conforme `docs/uso-de-ia.md`.

- **Histórico do repositório.** Treze commits do `main`, todos de autoria de Vinícius Joacir dos Anjos, entre 18/09 e 01/11/2026, registram na mensagem a coautoria do Claude, assistente de IA da Anthropic. A equipe decidiu não reescrever o histórico, para não alterar os hashes citados nos relatórios e nas tags. A partir de 10/11/2026, os commits registram apenas o autor humano, que responde pelo conteúdo.
- **Capítulos autorais da AV4.** Cada autor declarou no próprio capítulo a ferramenta usada e em que tarefas.
- **Agente do Replit.** Foi usado só para configurar a publicação, com prompt fechado e versionado, sem alterar código do produto (DL-08, item 4).
- **Pente fino e relatório da AV6.** O PO usou o Claude (Anthropic) como apoio na revisão de código, na conferência de cálculos e medições, na automação das capturas de tela, na redação e revisão deste relatório e na montagem do documento no modelo institucional. As decisões de produto, de metodologia e de escopo, a validação dos números contra o código e os artefatos e a revisão final do texto são da equipe, que responde integralmente pelo conteúdo.

Nenhuma ferramenta de IA tem acesso de escrita ao repositório ou é membro da equipe, e nenhum dado pessoal de participantes do ENEM foi fornecido a essas ferramentas: os microdados ficam na máquina da equipe e só agregados com piso de 100 participantes circulam fora dela.

##U Apêndice E – Como reproduzir

Com os quatro arquivos `.zip` do INEP em `data/raw/`, o pipeline e as análises são reproduzidos pelos comandos abaixo, na raiz do repositório. Os testes não precisam dos microdados.

```
python -m venv .venv && ./.venv/bin/pip install -r requirements.txt
./scripts/verify_raw.sh                         # confere o SHA-256 da fonte
# extrair cada zip em data/raw/microdados_enem_<ano>/
./.venv/bin/python scripts/etl.py               # RAW -> TRUSTED -> ANALYTICS (cerca de 2 min)
./.venv/bin/python scripts/equidade.py          # artefatos dos módulos
./.venv/bin/python scripts/territorial.py
./.venv/bin/python scripts/capital_escolar.py
./.venv/bin/python scripts/auditar_artefatos.py # barreira antes de publicar
./.venv/bin/python scripts/analises_av6.py      # análises estatísticas da AV6 (cerca de 15 s)
./.venv/bin/python -m unittest discover -s tests   # 282 testes, sem microdados
./.venv/bin/streamlit run app/app.py            # aplicação local
python scripts/checar_saude.py https://radarenem-projetoaplicado3-kirasapiens.replit.app --vezes 5
```

O relatório em Word é montado a partir das fontes em `docs/av6/relatorio/` com `python docs/av6/relatorio/montar_docx.py`, que reaproveita o cabeçalho, o rodapé e os estilos do modelo institucional da AV4.
