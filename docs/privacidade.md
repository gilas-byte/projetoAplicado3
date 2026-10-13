# Protecao de dados (LGPD) — Radar ENEM

Regras que o projeto segue para cumprir a Lei no 13.709/2018 (LGPD) e os
compromissos do Plano de Trabalho (secao "Etica, privacidade e
responsabilidade", RNF04 e item 10, "Escopo excluido"). Toda regra aponta
onde esta implementada ou, se ainda nao ha codigo, em que etapa entra.

## 1. Natureza dos dados

Os Microdados do ENEM sao publicados pelo INEP ja **anonimizados**: nunca
trazem nome, CPF, endereco, e-mail ou data de nascimento, e o numero de
inscricao e uma mascara sequencial. Mesmo assim, o INEP reconhece que a
definicao de dado anonimizado da LGPD (art. 5o, III) depende dos "meios
tecnicos razoaveis" disponiveis e, por cautela, adotou a partir de 2020 um
**modelo simplificado de microdados** (ver `Leia_Me_Enem_2019.pdf`, que
acompanha o zip). Consequencias para o projeto:

- **Colunas reduzidas.** As quatro edicoes tem 76 colunas. Idade so existe
  em faixa (`TP_FAIXA_ETARIA`) e nao ha codigo de escola. Recorte que
  dependa de idade exata ou de identificar a escola nao e viavel.
- **Registros excluidos pelo INEP.** Participantes de cadernos com poucos
  inscritos foram retirados da base (em 2019: CN 543-546, CH 547-550/564,
  LC 551-554/565, MT 555-558). A populacao do produto e um pouco menor que
  o total de inscritos; isso e declarado como limitacao, nao corrigido.
- **Sem ligacao entre edicoes.** A mascara de `NU_INSCRICAO` nao identifica
  o mesmo participante em anos diferentes.

A anonimizacao do INEP nao dispensa cuidado: cruzar varias variaveis em um
recorte pequeno (municipio + cor/raca + faixa etaria + renda) pode isolar
poucas pessoas. As regras abaixo existem para que o projeto **nao desfaca**
a protecao feita na origem.

## 2. Regras

### R1. Microdados nunca vao para o repositorio

Nenhuma camada de dados (RAW, TRUSTED, ANALYTICS) e versionada; so o hash
SHA-256 dos zips.
Onde: `.gitignore`, `data/raw/hashes.sha256`.

### R2. Identificador descartado

`NU_INSCRICAO` sai na passagem RAW -> TRUSTED. O produto so publica
agregados e o identificador nao tem uso analitico.
Onde: `scripts/colunas.py` (`CONTRATO["NU_INSCRICAO"]`); aplicado em
`scripts/etl.py`, que so leva para a TRUSTED as colunas mantidas.

### R3. Piso de tamanho de grupo

Nenhum **grupo de comparação, célula de tabela exposta ou barra de histograma**
com menos de 100 participantes (`PISO_GRUPO`) deve ser publicado. A regra
aplica-se à **exibição pública**, inclusive quando filtros forem adicionados.
A CDF exata criada para resolver o requisito de percentil precisa conservar
frequências internas por nota (inclusive valores abaixo de 100). Essas
frequências NÃO devem ser publicadas, exportadas como arquivo estático,
consultadas diretamente por API ou incluídas no GitHub. O risco residual de
inferência por consultas repetidas precisa ser reavaliado antes do deploy.
A regra vale:

- para cada **celula** de um cruzamento, nao so para o total do recorte;
- para artefatos versionados em `docs/` (o profiling ja sai suprimido:
  categoria com `n` e `pct` nulos e `suprimido: true`);
- para a camada ANALYTICS e para a interface, que mostra "grupo
  insuficiente" em vez do numero.

Onde: `PISO_GRUPO` em `scripts/colunas.py`; supressao em
`scripts/profiling.py` (`perfil_recorte`); verificacao em
`scripts/verificar_piso.py`. Na ANALYTICS, `scripts/estatistica.py` (`faixas`, usado pelo ETL):
a distribuicao de notas junta notas vizinhas ate cada faixa ter ao menos
100 participantes, com erro de percentil medido a cada execucao. Na
interface: `app/app.py` para histograma; a CDF interna consta de
`data/analytics/dist_exata.parquet`, protegida pelo deploy privado do backend.

O valor 100 e proposta tecnica pendente de aceite do PO. Tambem atende ao
item "Grupos pequenos" do plano, com folga sobre o minimo estatistico usual
de 30.

**Limite conhecido.** Numa distribuicao de uma unica variavel nacional, a
contagem suprimida pode ser deduzida pela diferenca entre o total e as
demais categorias. Nesse caso o risco e desprezivel, porque saber quantas
pessoas no Brasil tem um atributo nao isola ninguem. Nos **cruzamentos**
da ANALYTICS a deducao pela diferenca e o risco real, e a supressao ali
precisa ser complementar: se uma celula cai, ao menos mais uma celula da
mesma linha ou coluna tambem cai, ou o total nao e exibido.

### R4. Dados sensiveis so agregados

`TP_COR_RACA` e dado pessoal sensivel (origem racial, art. 5o, II). Entra
apenas em agregados sujeitos ao R3, com linguagem observacional (o
recorte descreve, nao explica causa).
Onde: `SENSIVEIS` em `scripts/colunas.py`; campo `sensivel` no
`docs/contrato/contrato.json`.

### R5. Recorte municipal com cuidado redobrado

`CO_MUNICIPIO_PROVA` e o campo de maior risco do contrato: em municipios
pequenos, poucos cruzamentos bastam para chegar a grupos de 1 a 5 pessoas.
Todo agregado municipal passa pelo R3 celula a celula, e cruzamentos
municipais com mais de uma variavel de perfil so sao exibidos se todas as
celulas passarem.
Onde: nota do campo em `scripts/colunas.py`; aplicacao no modulo de
recorte territorial.

### R6. Entrada do usuario nao e persistida

Notas, faixa de renda, escola e municipio informados na interface sao dados
pessoais no momento em que chegam ao produto (RNF04). Eles:

- sao usados apenas para calcular o resultado da sessao;
- nao sao gravados em banco, arquivo ou armazenamento do navegador;
- nao aparecem em logs do servidor nem em mensagens de erro;
- nao trafegam na URL (usar corpo de requisicao, nunca query string);
- nao sao enviados a ferramentas de analytics ou monitoramento de terceiros.

Onde: `app/app.py` (notas so no estado da sessao, sem `st.query_params`)
e `.streamlit/config.toml` (sem estatisticas de uso para o Streamlit; erros
mostram so o tipo da excecao). Teste em `tests/test_app.py`. Revisao
obrigatoria no checklist de privacidade do PR.

### R7. Sem reidentificacao nem enriquecimento

O projeto nao cruza os microdados com fontes externas que tragam dados de
pessoas (listas de aprovados, noticias de "nota maxima", redes sociais) e
nao tenta ligar registros entre edicoes. Item 10 do plano.

## 3. Checklist para PR

Antes de aprovar um PR que toque dados ou interface:

- [ ] `./.venv/bin/python scripts/verificar_piso.py` passa.
- [ ] Nenhum CSV, Parquet ou extrato de microdados entrou no commit.
- [ ] Todo agregado novo aplica `PISO_GRUPO` por celula (R3, R5).
- [ ] Nenhuma entrada do usuario vai para log, URL, storage ou terceiros (R6).
- [ ] Textos sobre recortes sensiveis usam linguagem observacional (R4).


## 4. Revisão de privacidade para percentis exatos (AV3)

Para eliminar a aproximação do percentil por interpolação de faixas,
o backend utiliza frequências discretas agregadas por nota e área/edição.
Essa arquitetura **não** expõe registros individuais; todavia, uma
frequência de nota específica pode ser menor que 100. Não se deve alegar
que todo agregado armazenado respeita o piso. O piso permanece obrigatório
para grupos e gráficos públicos; uma CDF detalhada permanece confinada no
servidor, não versionada ou acessível para download.

**Ações antes da implantação:** restringir acesso ao artefato, impedir
endpoints de frequência/contagem detalhada, validar que os gráficos vêm da
estrutura de faixas, verificar logs e política de retenção, executar testes
com recortes pequenos e avaliar consultas reiteradas e diferença entre grupos.
A indicação de percentil com uma casa decimal é arredondamento do resultado
exato, não um método de aproximação da distribuição.

**Pendente:** aceite formal de risco e de política de piso pelo Product Owner
na branch revisada; teste em ambiente de nuvem efetivo.
