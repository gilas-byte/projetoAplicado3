# Publicação no Replit

Responsável: Samuel Silva de Rezende (PO). Decisão em
[`docs/decisoes/README.md`](../decisoes/README.md#dl-08--replit-como-hospedagem-definitiva-e-publicação-beta) (DL-06 e DL-08).
A configuração está em [`.replit`](../../.replit). Modelo de serviço, segurança, custo e
operação em [`docs/av6/nuvem.md`](../av6/nuvem.md).

## O que precisa estar pronto

- Conta do Replit com plano Core (créditos mensais pagam a publicação).
- Os **cinco** artefatos da camada ANALYTICS, gerados pelo pipeline com os microdados
  reais. Eles **não** estão no GitHub (`.gitignore`, `docs/privacidade.md` R1). Os hashes
  de referência estão em [`artefatos.sha256`](artefatos.sha256).

  | Arquivo | Gerado por | Tamanho | Usado pela página |
  | --- | --- | --- | --- |
  | `dist_notas.parquet` | `scripts/etl.py` | 0,26 MB | Início (histograma) |
  | `dist_exata.parquet` | `scripts/etl.py` | 0,40 MB | Início (percentil exato) |
  | `dist_equidade.parquet` | `scripts/equidade.py` | 1,93 MB | Equidade socioeconômica |
  | `dist_territorial.parquet` | `scripts/territorial.py` | 7,96 MB | Recorte territorial |
  | `dist_capital.parquet` | `scripts/capital_escolar.py` | 2,08 MB | Capital escolar familiar |

## Passo a passo

1. **Criar o projeto a partir do GitHub.** No Replit: *Create App* → *Import from
   GitHub* → `https://github.com/gilas-byte/projetoAplicado3`. O Replit lê o `.replit`
   do repositório.
2. **Deixar o projeto privado.** Nas configurações do projeto, marcar como privado.
   Os artefatos têm frequências por nota e só podem ficar no backend (ADR-001); num
   projeto público qualquer visitante veria os arquivos.
3. **Enviar os artefatos.** No painel de arquivos, criar a pasta `data/analytics/` e
   arrastar para ela os cinco `.parquet`. Como `data/` está no `.gitignore`, eles
   nunca entram num commit feito pelo Replit.
4. **Conferir os artefatos (barreira de qualidade).** No *Shell* do projeto:

   ```
   pip install -q -r requirements.txt
   python scripts/auditar_artefatos.py
   ```

   Só seguir se terminar com `OK`. A auditoria confere colunas, chave do grão, piso de
   100 por grupo, coerência das CDFs, o total do Brasil entre artefatos e o SHA-256
   contra a referência. Ela grava `data/analytics/_manifesto_publicacao.json`, que o
   rodapé do app usa para mostrar a data e o commit dos dados.
5. **Testar no editor.** Clicar em *Run*. Conferir as quatro páginas: Início, Equidade,
   Recorte territorial e Capital escolar familiar.
6. **Publicar.** *Publish* → **Reserved VM**, máquina compartilhada (0,5 vCPU, 2 GB),
   sempre ligada (justificativa em `docs/av6/nuvem.md`, seção 1). Se o diálogo oferecer
   **Enable app monitoring**, ativar.
7. **Aquecer o app depois de cada publicação.** Abrir uma vez as quatro páginas. A
   primeira abertura do territorial carrega 2,2 milhões de linhas; depois os dados ficam
   em memória.
8. **Conferir saúde e privacidade pela rede.** De qualquer computador com o repositório:

   ```
   python scripts/checar_saude.py https://<app>.replit.app --vezes 20 --gravar
   ```

   Termina com erro se o app não responder ou se algum artefato puder ser baixado.
9. **Medir no ambiente real.** No *Shell* do Replit:

   ```
   python scripts/medir_desempenho.py --ambiente replit
   ```

   Commitar os dois JSON de `docs/deploy/medicoes/` e preencher a tabela abaixo.
10. **Registrar o link** público (`*.replit.app`) no README, na DL-06 e no relatório final.

## Dependências e filtro de pacotes do Replit

O Replit instala os pacotes por um filtro (Package Firewall, da Socket) que recusa com
erro 403 versões com vulnerabilidade conhecida. Em 18/11/2026 ele recusou o Pillow 12.3.0
e o 12.2.0, que o Streamlit 1.64 exigia (`pillow<13`): o CVE-2026-112900 (crítico, CVSS
9,2) e outras falhas afetam todas as versões anteriores à 13.0.0. Por isso o
`requirements.txt` passou para o Streamlit 1.66.1, o primeiro que aceita `pillow<14`, e
fixa `pillow==13.0.0`. O app não importa o Pillow diretamente; ele vem com o Streamlit.

Na primeira publicação, a verificação de segurança da tela Publish (que bloqueia
vulnerabilidades críticas) acusou anyio 4.9.0, certifi 2026.7.22, h11 0.9.0 e idna 3.9.0,
embora o pip tivesse instalado anyio 4.16.0, certifi 2026.10.23, h11 0.16.0 e idna 3.20.
A verificação lê os manifestos (`requirements.txt` e `requirements-benchmark.txt`) e
supõe versões para as dependências indiretas que não estão fixadas. Por isso o
`requirements.txt` também fixa essas quatro, nas versões instaladas e testadas. Os alertas
que sobram (setuptools, altos e médios) vêm só do `requirements-benchmark.txt`, que o app
não instala, e não bloqueiam a publicação.

Se uma instalação no Replit voltar com 403, não contorne o filtro (por exemplo, trocando o
índice de pacotes): ache a versão corrigida, teste com os 273 testes e atualize o
`requirements.txt` por PR.

## Atualizar o app

- **Código:** no *Shell* do Replit, `git pull`, rodar a auditoria (passo 4) e publicar de novo.
- **Dados:** gerar os artefatos com o pipeline, substituir os arquivos em
  `data/analytics/`, atualizar `artefatos.sha256` por PR, rodar a auditoria e publicar de novo.
- **Voltar uma versão (rollback):** no *Shell*, `git checkout <commit anterior>`, auditoria e
  publicar. O commit em produção aparece no rodapé do app.

Atenção: a publicação é uma cópia do projeto no momento em que se clica em *Publish*.
Arquivos gravados pelo app durante a execução não sobrevivem a uma nova publicação, e
trocar artefatos só vale depois de publicar de novo.

## Medições

**Referência local (03/11/2026, DL-06, ainda com o Streamlit 1.64):** 2 vCPU, Python 3.13, Streamlit 1.64, artefatos
reais: memória de cerca de 600 MB com três páginas abertas; consulta entre 0,4 e 1,4 s;
primeira abertura do territorial em 10,4 s e as seguintes em 2,2 s.

**Ambiente de desenvolvimento (16/11/2026):** `medir_desempenho.py` com as quatro
páginas no mesmo processo: carga do territorial em 2,8 s; consulta p95 entre 65 ms
(Início) e 370 ms (Recorte territorial); pico de memória de cerca de 1,2 GB. O pico é o
dobro da estimativa de 03/11 e fica dentro dos 2 GB da VM compartilhada, mas com margem
menor; por isso a medição no Replit é obrigatória antes de fechar a DL-06.

**Replit (beta):** preencher depois da publicação.

| Medida | Valor | Como foi medido |
| --- | --- | --- |
| Memória da publicação com as 4 páginas abertas | | Painel de recursos do Replit |
| Carga do Recorte territorial (primeira abertura) | | `medir_desempenho.py --ambiente replit` |
| Consulta p50 / p95 por página | | `medir_desempenho.py --ambiente replit` |
| Saúde p50 / p95 pela rede | | `checar_saude.py --gravar` |
| Tempo até o resultado aparecer (navegador, 10 repetições por página) | | Cronômetro do navegador (DevTools → Network/Performance) |
| Artefatos expostos | | `checar_saude.py` (deve ser lista vazia) |
| Tempo para recriar a publicação do zero (RTO) | | Do import ao link no ar |

## Checklist de privacidade antes de divulgar o link

- [ ] Projeto do Replit privado.
- [ ] `git status` no Replit não lista nenhum `.parquet` ou `.csv`.
- [ ] `python scripts/auditar_artefatos.py` termina com `OK`.
- [ ] `python scripts/checar_saude.py <url>` termina sem falha e com
      `"artefatos_expostos": []`. O servidor de estáticos está ligado
      (`enableStaticServing`) só para `app/static/` (fontes IBM Plex, licença OFL); `data/`
      fica fora dessa pasta e caminho com `..` volta 400 (DL-09).
      `showErrorDetails = "type"` esconde valores digitados nos erros.
- [ ] `python scripts/verificar_piso.py` passa.
