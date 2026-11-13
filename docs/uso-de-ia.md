# Declaração de uso de inteligência artificial

Este documento registra, de forma transparente, o uso de ferramenta de inteligência
artificial (IA) generativa no histórico do repositório do Radar ENEM. A equipe decidiu
**não reescrever o histórico**: os commits já publicados ficam exatamente como foram
feitos, com os mesmos hashes, e esta página explica o que eles mostram.

## Commits com coautoria de IA registrada

Treze commits do `main` trazem na mensagem a linha
`Co-Authored-By: Claude ... <noreply@anthropic.com>`. É por causa dessa linha que o
GitHub mostra "Claude" na lista de colaboradores do repositório. Claude é um assistente
de IA da Anthropic; ele não tem acesso ao repositório e não é membro da equipe.

Em todos os treze o autor humano é **Vinícius Joacir dos Anjos**, que conduziu o uso
da ferramenta, revisou o resultado e fez o commit. A responsabilidade pelo conteúdo é
do autor humano.

| Commit | Data | Assunto |
| --- | --- | --- |
| `19a00ba` | 18/09/2026 | docs: plano de trabalho AV1 (Radar ENEM, Equipe A) |
| `721a506` | 18/09/2026 | feat(dados): rastreabilidade da camada RAW e politica de versionamento |
| `f13f083` | 18/09/2026 | fix(dados): remove a edicao 2024 do manifesto de hashes |
| `5ef0066` | 18/09/2026 | feat(profiling): caracterizacao das quatro edicoes (2019-2022) |
| `7c26624` | 18/09/2026 | feat(dicionario): extrai dominios do INEP e aponta a lista de harmonizacao |
| `ca12644` | 18/09/2026 | feat(contrato): contrato de dados e profiling dos 25 campos do questionario |
| `3acd712` | 22/09/2026 | feat(lgpd): piso de tamanho de grupo e politica de protecao de dados |
| `57c250a` | 25/09/2026 | feat(stack): benchmark das alternativas e decisao da stack |
| `2aa102e` | 25/09/2026 | feat(etl): pipeline RAW -> TRUSTED -> ANALYTICS em DuckDB |
| `e5cc13b` | 25/09/2026 | feat(app): MVP nota -> percentil -> visualizacao em Streamlit |
| `d832070` | 28/09/2026 | docs: atualiza equipe no README e adiciona roteiro da AV2 |
| `c45de6b` | 13/10/2026 | docs(av3): relatorio tecnico de engenharia de dados com a execucao real do ETL |
| `63c7c0c` | 01/11/2026 | feat(motor): medidas v1 sobre a CDF exata com testes |

Para conferir a lista:

```bash
git log origin/main -i --grep='co-authored-by: claude' --format='%h %an %ad %s' --date=short
```

Nenhum outro commit do repositório tem coautoria de IA registrada (situação em
10/11/2026).

## Por que o histórico não foi reescrito

Retirar essa linha exigiria reescrever o histórico do `main`. Isso mudaria o hash de
todos os commits posteriores a 18/09/2026, inclusive os citados nos capítulos da AV4 e
nas tags de entrega, obrigaria um *force-push* e quebraria os PRs abertos e os clones
de cada integrante. Os commits originais continuariam acessíveis pelas tags e pelos PRs
já fechados. Manter o registro e declará-lo aqui é mais honesto e preserva a
rastreabilidade.

## Commits a partir de 10/11/2026

A partir desta data, os commits são registrados apenas com o autor humano, sem linha de
coautoria de IA. O autor do commit responde pelo conteúdo que publica. O uso de
ferramentas de IA como apoio (revisão, redação, conferência de cálculos) continua sendo
declarado no relatório final do projeto.

## Autoria do restante do trabalho

A autoria de cada contribuição pode ser conferida pelos campos de autor dos commits
(`git log`, `git blame`), pelos PRs e pelas revisões no GitHub, e pelas tags de entrega
individual.

Declaração registrada por Samuel Silva de Rezende (PO), em 10/11/2026, a partir da
decisão da equipe.
