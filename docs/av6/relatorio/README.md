# Relatório final da AV6 — fontes e montagem

O documento entregue é `docs/av6/AV6_Relatorio_Final_RadarENEM_EquipeA.docx` (Word editável) e,
depois de gerado no Word, o PDF com o mesmo nome. Esta pasta guarda as fontes do texto e os
scripts que montam o Word no modelo institucional da AV4 (cabeçalho e rodapé SENAI, caixas de
seção, quadros e figuras numerados e sumário).

| Arquivo | Conteúdo |
| --- | --- |
| `00_capa.json` | Textos da capa e do quadro de identificação |
| `01_resumo.md` | Resumo e abstract |
| `10_introducao.md` a `18_conclusoes.md` | Capítulos 1 a 9 (o 8 é a justificativa técnica por área) |
| `90_referencias.md`, `95_apendices.md` | Referências e apêndices A a E |
| `figuras/` | Capturas do app (24/11/2026, código do PR #39, artefatos reais), diagrama de arquitetura (`.svg` e `.png`) e gráficos das análises |
| `montar_docx.py` | Monta o `.docx` a partir das fontes; a marcação aceita está no cabeçalho do script |
| `paginar.py` | Monta, renderiza no LibreOffice, adia figuras que deixariam buraco no fim da página (`adiamentos.json`), mede a página de cada título e monta de novo com os números do sumário |
| `gerar-pdf-av6.ps1` | No Windows, com o Word: refaz o sumário (entradas e números de página), salva o `.docx` e exporta o PDF |

## Como atualizar

1. Editar o texto no Word diretamente (o `.docx` é o documento oficial), **ou** editar as fontes
   desta pasta e rodar `python docs/av6/relatorio/paginar.py` (precisa de LibreOffice e
   `pdftotext`). Editar as fontes e remontar descarta edições feitas à mão no Word.
2. Gerar o PDF no Word: `powershell -ExecutionPolicy Bypass -File docs\av6\relatorio\gerar-pdf-av6.ps1`.
