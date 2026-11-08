# Publicação no Replit (teste)

Responsável: Samuel Silva de Rezende (PO). Decisão em
[`docs/decisoes/README.md`](../decisoes/README.md#dl-06--hospedagem-em-teste-no-replit) (DL-06).
A configuração está em [`.replit`](../../.replit).

## O que precisa estar pronto

- Conta do Replit com plano Core (créditos mensais pagam a publicação).
- Os quatro artefatos da camada ANALYTICS, gerados pelo pipeline com os microdados
  reais. Eles **não** estão no GitHub (`.gitignore`, `docs/privacidade.md` R1):

  | Arquivo | Gerado por | Tamanho (execução de 03/11/2026) |
  | --- | --- | --- |
  | `dist_notas.parquet` | `scripts/etl.py` | 0,26 MB |
  | `dist_exata.parquet` | `scripts/etl.py` | 0,40 MB |
  | `dist_equidade.parquet` | `scripts/equidade.py` | 1,93 MB |
  | `dist_territorial.parquet` | `scripts/territorial.py` | 7,96 MB |

## Passo a passo

1. **Criar o projeto a partir do GitHub.** No Replit: *Create App* → *Import from
   GitHub* → `https://github.com/gilas-byte/projetoAplicado3`. O Replit lê o `.replit`
   do repositório.
2. **Deixar o projeto privado.** Nas configurações do projeto, marcar como privado.
   Os artefatos têm frequências por nota e só podem ficar no backend (ADR-001); num
   projeto público qualquer visitante veria os arquivos.
3. **Enviar os artefatos.** No painel de arquivos, criar a pasta `data/analytics/` e
   arrastar para ela os quatro `.parquet`. Como `data/` está no `.gitignore`, eles
   nunca entram num commit feito pelo Replit.
4. **Testar no editor.** Clicar em *Run*. O app abre na aba de pré-visualização; conferir
   a página principal, a Equidade e o Recorte territorial.
5. **Publicar.** *Deploy* (ou *Publish*) → escolher o tipo:
   - **Reserved VM, máquina compartilhada (0,5 vCPU, 2 GB):** sempre ligada; usar na
     semana da banca e quando o link estiver no relatório final.
   - **Autoscale:** mais barato para testes, mas desliga quando ninguém acessa, e o
     primeiro acesso seguinte demora para responder.
6. **Aquecer o app depois de cada publicação.** Abrir uma vez a página principal, a
   Equidade e o Recorte territorial. A primeira abertura do territorial carrega 2,2
   milhões de linhas (10 s no teste com 2 vCPU); a partir daí os dados ficam em memória.
7. **Registrar o link** público (`*.replit.app`) no README e no relatório final (entrega de 19/11/2026, DL-07).

## Atualizar o app

- **Código:** no *Shell* do Replit, `git pull`, e publicar de novo.
- **Dados:** gerar os artefatos com o pipeline, substituir os arquivos em
  `data/analytics/` e publicar de novo.

## Medições de referência

Teste local em 03/11/2026, com os quatro artefatos reais, 2 vCPU, Python 3.13 e
Streamlit 1.64: memória de cerca de 600 MB com as três páginas abertas; resposta de
uma consulta entre 0,4 e 1,4 s; primeira abertura do territorial em 10,4 s e as
seguintes em 2,2 s. As medições no Replit entram aqui depois da primeira publicação.

## Checklist de privacidade antes de divulgar o link

- [ ] Projeto do Replit privado.
- [ ] `git status` no Replit não lista nenhum `.parquet` ou `.csv`.
- [ ] O app não oferece download de artefato (o Streamlit não serve arquivos estáticos
      por padrão, e `showErrorDetails = "type"` esconde valores digitados nos erros).
- [ ] `python scripts/verificar_piso.py` passa.
