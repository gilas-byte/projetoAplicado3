# Teste de usabilidade e acessibilidade — protocolo da AV6

Protocolo para validar o Radar ENEM com pessoas do público-alvo antes do relatório
final. Segue o "teste das cinco tarefas" da disciplina de Business Intelligence e Data
Visualization (aulas de dashboards e de visualizações interativas): o objetivo é saber
se a pessoa entende o resultado sozinha, sem explicação oral.

- **Responsável pela condução:** QA (definido na issue de distribuição de tarefas da AV6).
- **Ambiente:** link público da beta no Replit, no celular e no computador.
- **Participantes:** 3 a 5 pessoas que fizeram ou vão fazer o ENEM, de fora da equipe.
- **Consentimento:** explicar que nada do que a pessoa digita é gravado (R6) e pedir que
  use notas reais ou inventadas, como preferir. A ficha não registra nome, notas
  digitadas nem dado pessoal: só o perfil genérico (por exemplo, "vestibulanda, celular").

## Tarefas

Ler cada tarefa em voz alta, sem mostrar onde clicar. Anotar se a pessoa conseguiu
sozinha, o tempo aproximado, onde travou e o que perguntou.

| # | Tarefa | Sucesso quando a pessoa... |
| --- | --- | --- |
| 1 | "Descubra em que posição a sua nota de Matemática ficaria no ENEM 2022." | lê o percentil e explica com as próprias palavras ("fiquei acima de X% dos participantes") |
| 2 | "De onde vêm esses dados e de quando são?" | encontra a fonte e a data no rodapé ou no "Como a posição é calculada" |
| 3 | "Compare a sua posição no seu estado e no Brasil." | abre o Recorte territorial, escolhe a UF e lê as duas posições |
| 4 | "Por que aparece 'acima de 99,9%' e não o número exato?" (só se o caso aparecer) ou "O que quer dizer a caixa do gráfico?" | encontra a explicação na página ou na legenda |
| 5 | "Volte para a página inicial e refaça com outra edição." | navega pela barra lateral e troca a edição sem ajuda |

## Ficha por participante

| Campo | Anotação |
| --- | --- |
| Perfil genérico | |
| Dispositivo e navegador | |
| Tarefa 1: conseguiu? tempo? dúvida? | |
| Tarefa 2 | |
| Tarefa 3 | |
| Tarefa 4 | |
| Tarefa 5 | |
| O que achou mais confuso | |
| Nota de 1 a 5 para "entendi o resultado sem ajuda" | |

## Verificações de acessibilidade (feitas pela equipe)

| Verificação | Como | Situação |
| --- | --- | --- |
| Contraste das cores de papel e de contexto | Automático: `tests/test_ui.py`, `TestContraste` (3:1 para gráficos, 4,5:1 para texto, nos dois temas) | Passa |
| Mensagem compreensível em escala de cinza | Ativar o filtro de escala de cinza do sistema e repetir a tarefa 3 | A fazer |
| Daltonismo (protanopia e deuteranopia) | Simulador de visão de cores do navegador (DevTools → Rendering → Emulate vision deficiencies) | A fazer |
| Navegação só pelo teclado | Tab e Enter do formulário até o resultado; foco visível | A fazer |
| Movimento reduzido | Ativar "reduzir movimento" no sistema: o anel e as animações param (`prefers-reduced-motion`) | A fazer |
| Celular | Repetir as tarefas 1 e 3 num celular | A fazer |

## Registro dos resultados

Os resultados entram numa tabela resumida (sem dado pessoal) na seção de validação do
relatório final da AV6, com as correções que saírem deles. Cada correção vira issue ou
PR próprio.
