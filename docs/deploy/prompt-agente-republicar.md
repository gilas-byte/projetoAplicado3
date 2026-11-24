# Prompt do agente do Replit (republicar depois de um merge)

Versionado conforme a DL-08, item 4: o agente do Replit só sincroniza, confere e publica,
com um prompt fechado da equipe, e não altera o código do produto. Usado em 24/11/2026 na
republicação da identidade visual (PR #38), já com os ajustes que essa execução mostrou
serem necessários (autorização do Git, reinício do Run e o `.replit` alterado pelo Node.js).
A primeira publicação usou [`prompt-agente-replit.md`](prompt-agente-replit.md).

---

Tarefa: atualizar o workspace com a `main` do GitHub e republicar o Radar ENEM. Sua tarefa é só sincronizar, conferir e republicar. **Não altere o código do produto.**

## Regras (obrigatórias)
1. NUNCA faça push, "Sincronizar alterações" ou qualquer envio para o GitHub. O GitHub é a fonte oficial e só recebe mudanças por PR com revisão.
2. Não edite, crie nem apague arquivos em `app/`, `scripts/`, `tests/`, `docs/`, `.streamlit/`, `requirements*.txt`, `.replit` ou `.gitignore`.
3. Não use Node.js nem automação de navegador: o Replit acrescenta `nodejs-24` ao `.replit` quando isso acontece.
4. Não mexa em `data/analytics/` (os 5 `.parquet` ficam fora do git, de propósito) e não coloque nenhum `.parquet` ou `.csv` no git.
5. Não instale pacotes além do `requirements.txt` e não troque versões.
6. Não mude a configuração da publicação: Reserved VM compartilhada (0,5 vCPU, 2 GB), região South America, monitoramento ligado, análises de visitantes e widget de feedback desligados.
7. Não execute tarefas antigas da fila nem correções automáticas do Centro de segurança. Siga só este prompt.
8. Se qualquer passo falhar, pare, mostre a saída completa e não tente corrigir.

## Passos (no Shell)
1. Mostre o estado: `git status --short` e `git log --oneline -6`. Se o `.replit` aparecer modificado, mostre `git diff -- .replit` e pare.
2. Autorizo `DANGEROUSLY_ALLOW_GIT=1` somente nestes três comandos, nesta ordem:
   - `DANGEROUSLY_ALLOW_GIT=1 git branch backup-replit-<data>`
   - `DANGEROUSLY_ALLOW_GIT=1 git fetch origin`
   - `DANGEROUSLY_ALLOW_GIT=1 git reset --hard origin/main`
3. Confira: `git log --oneline -3` (o primeiro é o merge esperado), `git status --short` (vazio) e `ls data/analytics` (5 `.parquet`).
4. `pip install -r requirements.txt`
5. `python scripts/auditar_artefatos.py` (deve terminar com `OK`).
6. `python -m unittest discover -s tests` (todos OK) e `python scripts/verificar_piso.py`.
7. **Pare o Run e inicie de novo** (o Streamlit não recarrega o `app/ui.py` já importado) e confira no editor que a mudança do PR aparece. O rodapé mostra o commit.
8. `git status --short` de novo: tem de estar vazio. Então Republish com a mesma configuração. Se não puder clicar, deixe pronto e avise.
9. Depois de publicado: `python scripts/checar_saude.py https://radarenem-projetoaplicado3-kirasapiens.replit.app --vezes 20` (sem falhas e com `"artefatos_expostos": []`) e `git status --short`.

## O que me entregar (saídas completas, sem resumir números)
- As saídas dos passos 1, 3, 5, 6, 8 e 9.
- O status da publicação (Ao vivo), com a data e a hora do build.
- Qualquer aviso ou erro, mesmo que você tenha conseguido seguir.
