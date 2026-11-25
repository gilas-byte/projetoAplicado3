# Prompt do agente do Replit (publicação beta)

Versionado conforme a DL-08, item 4: o agente do Replit só configura e confere a
publicação, com este prompt fechado da equipe, e não altera o código do produto.
Usado em 18/11/2026 na primeira publicação (beta). Passo a passo humano em
[`replit.md`](replit.md).

---

Você vai preparar e publicar o app Radar ENEM, que já está pronto no repositório. Sua tarefa é só configurar, conferir e publicar. **Não altere o código do produto.**

## Contexto
- App em Python 3.12 com Streamlit 1.66.1 e DuckDB: `app/app.py` mais as 3 páginas em `app/pages/`.
- A configuração do Replit já está no arquivo `.replit` do repositório: módulo `python-3.12`, botão Run, deploy com `streamlit run app/app.py` na porta 8501, porta externa 80. O passo a passo oficial está em `docs/deploy/replit.md`. Siga esses dois arquivos.
- Os dados ficam em `data/analytics/` e **não estão no git, de propósito** (`.gitignore`, `docs/privacidade.md` R1). São 5 arquivos agregados que eu vou enviar arrastando para o painel de arquivos:
  - `dist_notas.parquet`
  - `dist_exata.parquet`
  - `dist_equidade.parquet`
  - `dist_territorial.parquet`
  - `dist_capital.parquet`
- **Não gere, baixe, recrie ou simule esses dados.** Não use dados de exemplo.

## Regras (obrigatórias)
1. Não edite, crie nem apague arquivos em `app/`, `scripts/`, `tests/`, `docs/`, `.streamlit/`, `requirements.txt`, `.replit` ou `.gitignore`. Se achar que algum precisa mudar, pare e me explique o motivo, sem alterar nada.
2. Não faça commit nem push, e não use o painel de Git do Replit.
3. Não coloque nenhum `.parquet` ou `.csv` no git e não mova os arquivos de `data/analytics/`.
4. Não crie banco de dados, Object Storage, Secrets, autenticação nem serviços extras. O app não precisa de nada disso.
5. Não troque de versão de Python nem de pacote, e não instale nada além do `requirements.txt`.
6. O projeto deve continuar **privado**. Se não estiver, me avise antes de qualquer outra coisa.

## Passos
1. **Conferir o ambiente.** Confirme que o `.replit` do repositório está sendo usado e rode `pip install -r requirements.txt`.
2. **Esperar os dados.** Verifique se os 5 arquivos estão em `data/analytics/`. Se faltar algum, **pare** e me peça para enviar, dizendo quais faltam. Não continue sem eles.
3. **Rodar a auditoria (barreira de qualidade).** Rode `python scripts/auditar_artefatos.py`. Só continue se terminar com `OK`. Se falhar, pare e me mostre a saída completa. Não tente corrigir os dados nem o script.
4. **Rodar os testes.** Rode `python -m unittest discover -s tests` e `python scripts/verificar_piso.py`. Os dois devem passar (são 282 testes). Se algo falhar, pare e me mostre a saída.
5. **Testar no editor.** Clique em Run e confira as 4 páginas: Início, Equidade socioeconômica, Recorte territorial e Capital escolar familiar. Em cada uma, preencha Matemática = 650 e clique em Comparar; o resultado deve aparecer sem erro. Em Equidade, escolha a renda "D)"; em Recorte territorial, a UF "SC"; em Capital escolar, pai "D)" e mãe "E)".
6. **Configurar a publicação.** Use *Publish* com **Reserved VM**, máquina compartilhada (0,5 vCPU e 2 GB de RAM), sempre ligada. **Não use Autoscale nem Static.** Os comandos de build e run são os do bloco `[deployment]` do `.replit`. Se houver a opção *Enable app monitoring*, ative. Se você não puder clicar em Publish, deixe tudo configurado e me avise que eu clico.
7. **Aquecer o app.** Depois de publicado, abra uma vez as 4 páginas no link público (`*.replit.app`).
8. **Conferir a saúde e a privacidade pela rede.** No Shell, rode `python scripts/checar_saude.py <link público> --vezes 20 --gravar`. Deve terminar sem erro e com `"artefatos_expostos": []`.
9. **Medir o desempenho.** No Shell, rode `python scripts/medir_desempenho.py --ambiente replit`.
10. **Checar o git.** Rode `git status` e confirme que nenhum `.parquet` ou `.csv` aparece na lista.

## O que me entregar no final (copie as saídas, sem resumir números)
- O link público da publicação.
- O tipo de máquina da publicação (deve ser Reserved VM, 0,5 vCPU, 2 GB).
- A saída completa de `auditar_artefatos.py`.
- A última linha do `unittest` e a saída do `verificar_piso.py`.
- O conteúdo dos dois JSON gerados em `docs/deploy/medicoes/` (saúde e desempenho).
- A memória usada pela publicação com as 4 páginas abertas, como aparece no painel de recursos do Replit.
- A saída de `git status`.
- Qualquer aviso ou erro que tenha aparecido, mesmo que você tenha conseguido seguir.
