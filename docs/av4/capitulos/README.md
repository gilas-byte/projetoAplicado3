# Capítulos individuais da AV4

Cada integrante entrega o capítulo autoral do seu módulo em **Word (.docx)**, nesta pasta. O PO
(Samuel Silva de Rezende) junta os três capítulos em um único documento consolidado, que é
enviado no AVA. Os capítulos precisam seguir o mesmo modelo, para a junção não exigir
retrabalho de formatação.

| Capítulo | Módulo | Autor | Arquivo | Situação |
| --- | --- | --- | --- | --- |
| 1 | Equidade socioeconômica | Samuel Silva de Rezende | [`AV4_Capitulo_Samuel_Equidade_Socioeconomica.docx`](AV4_Capitulo_Samuel_Equidade_Socioeconomica.docx) | entregue (modelo) |
| 2 | Recorte territorial | Vinícius Joacir dos Anjos | `AV4_Capitulo_Vinicius_Recorte_Territorial.docx` | conteúdo pronto em [`docs/modulos/relatorio-modulo-territorial.md`](../../modulos/relatorio-modulo-territorial.md); falta o .docx |
| 3 | Capital escolar familiar | Guilherme da Silva Anselmo | `AV4_Capitulo_Guilherme_Capital_Escolar_Familiar.docx` | pendente |

A numeração dos capítulos segue a ordem das páginas do app (1, 2 e 3).

## Modelo

O capítulo 1 é o modelo. O jeito mais simples é **copiar o arquivo dele, renomear e trocar o
conteúdo**, mantendo cabeçalho, rodapé, estilos, caixas e quadros. Assim o cabeçalho e o rodapé do
padrão SENAI (FM-NP-270-SENAI-009) e as margens já vêm certos.

## Estrutura

Mesmas seções, com o número do seu capítulo (2.1, 2.2… ou 3.1, 3.2…):

1. **Faixa de título:** "CAPÍTULO N – MÓDULO <NOME>" e, abaixo, "Capítulo autoral de <nome> (<papel>)".
2. **Identificação do módulo** (quadro): autor e matrícula, módulo, repositório, versão entregue
   (tag ou commit), branch, pull request(s), evolução depois da entrega, arquivos de autoria e
   componentes compartilhados utilizados.
3. **N.1 Pergunta do módulo e contexto.**
4. **N.2 Regras de negócio e formulação da análise comparativa** (variáveis do INEP, grupos,
   ausências e inválidos, piso de divulgação, fórmulas, fluxo de processamento).
5. **N.3 Inputs criados e interface de interação** (quadro de inputs e capturas de tela do app).
6. **N.4 Estratégia de validação e resiliência contra erros** (quadro de casos de teste com o
   nome do teste, e a saída do terminal com a contagem atual de testes).
7. **N.5 Execução com os microdados reais** (manifesto, tempos, grupos publicados e resultados).
8. **N.6 Comprovação de autoria e rastreabilidade no GitHub** (quadro de commits com hash, data
   e descrição; PRs e revisores; comandos para conferir a autoria; links diretos).
9. **N.7 Limitações e próximos passos.**
10. **N.8 Declaração de uso de inteligência artificial** (ferramenta, em que tarefas foi usada,
    o que foi decisão do autor, e que o autor revisou e responde pelo conteúdo; ver
    [`docs/uso-de-ia.md`](../../uso-de-ia.md)).

## Formatação

- Fonte Calibri 10,5 pt no texto; A4 com margens de 3 cm (esquerda e superior) e 2 cm.
- Cada seção fica numa **caixa**: barra cinza (#D9D9D9) com o título em maiúsculas e negrito,
  conteúdo emoldurado abaixo.
- **Quadros e figuras:** legenda acima ("**Quadro N** – descrição", "**Figura N** – descrição"),
  com numeração contínua dentro do capítulo, e linha "Fonte: …" abaixo, em 8,5 pt.
- Quadros com borda cinza, cabeçalho sombreado (#F2F2F2) e texto de 8 a 9 pt.
- Nomes de arquivos, funções, commits e comandos em Consolas; blocos de terminal em caixa cinza
  clara (#F7F7F7), Consolas 8 pt.
- Capturas de tela da **versão atual** do app, com os artefatos reais.
- Texto formal, sem marcadores decorativos, com o autor referido como "o autor".
- Números com vírgula decimal e ponto de milhar (87,1%; 558.228).

## Entrega

1. Branch própria a partir da `main`, com o .docx nesta pasta e o nome indicado na tabela.
2. Pull request com revisão de outro integrante, como nos demais PRs.
3. Prazo: definido na issue de aviso da AV4.

Depois que os três capítulos estiverem na `main`, o PO monta o documento consolidado e o envia
no AVA.
