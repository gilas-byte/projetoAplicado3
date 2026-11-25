#C Metodologia de engenharia de Big Data | Da fonte do INEP aos artefatos publicados

## Caracterização do volume e do problema de dados

Um problema de Big Data costuma ser caracterizado pelos seus "Vs" (volume, velocidade, variedade, veracidade e valor). No Radar ENEM, eles se apresentam da seguinte forma.

- **Volume.** Quatro arquivos CSV, um por edição, com 7,51 GB e 17.744.217 linhas no total, 76 colunas cada. Compactados, os arquivos do INEP somam 2,40 GB. Ler um único arquivo inteiro levou de 14,9 s a 24,4 s no profiling e alguns gigabytes de memória.
- **Velocidade.** Lote anual: a fonte muda uma vez por edição do ENEM, e as quatro edições do recorte já estão publicadas. Não há fluxo contínuo de eventos.
- **Variedade.** Dado estruturado, mas heterogêneo na semântica: códigos do questionário que mudam de rótulo entre edições, faixas de renda expressas em reais de cada ano, dicionários em PDF e planilha, valores ausentes com significados diferentes (prova não feita, nota zero, "não sei", campo vazio).
- **Veracidade.** Os dados são oficiais, mas o próprio INEP retira participantes de cadernos com poucos inscritos e adota um modelo simplificado desde 2020. O projeto preserva a fonte intacta, identificada por hash, e declara essas exclusões como limitação.
- **Valor.** O valor está na redução: a pergunta do produto é respondida por distribuições agregadas que ocupam algumas centenas de kilobytes por edição, desde que a agregação seja exata e auditável.

O volume não exige processamento distribuído: o maior CSV tem 2,41 GB e a camada intermediária inteira, depois de tipada e comprimida, ocupa 374,3 MB, que cabem com folga na memória de um notebook. O desafio é de arquitetura: separar o trabalho pesado, que pode levar minutos, do atendimento ao usuário, que precisa levar milissegundos, numa máquina de 2 GB de memória.

## Arquitetura de dados

A solução segue o padrão de separação entre processamento em lote e atendimento a consultas descrito por Kleppmann (2017): o processamento pesado roda uma vez, fora do ar, na máquina da equipe, e produz artefatos compactados; a aplicação online apenas consulta esses artefatos, sem carregar a base bruta. A organização em três camadas corresponde à arquitetura medalhão (bronze, prata e ouro).

Figura: f_arquitetura.png | 16 | Arquitetura final da solução: camadas de dados, repositório, nuvem e monitoramento
Fonte: elaborado pela equipe Radar ENEM (arquivo-fonte `docs/av6/relatorio/figuras/arquitetura_av6.svg`).

Quadro: Camadas de dados do Radar ENEM
Larguras: 14,30,24,14,18
| Camada | Conteúdo | Formato e local | Tamanho | Quem lê |
| --- | --- | --- | --- | --- |
| RAW (bronze) | Arquivo oficial do INEP, sem alteração | `.zip` e CSV latin-1 em `data/raw/` | 2,40 GB (zip); 7,51 GB (CSV) | Só o ETL |
| TRUSTED (prata) | Um registro por inscrito, 58 colunas do contrato tipadas e 4 derivadas, com a marca de elegibilidade | Parquet ZSTD em `data/trusted/enem/ano=<ano>/` | 374,3 MB | ETL, módulos e análises da equipe |
| ANALYTICS (ouro) | Distribuições das notas dos elegíveis: faixas protegidas, CDF nacional e CDFs por grupo dos três módulos | Parquet ZSTD em `data/analytics/` | 12,6 MB (5 arquivos) | A aplicação web, só no backend |
Fonte: relatório da AV3 (seção 2.2), `docs/modelagem/README.md` e `_manifesto_publicacao.json` da execução de referência.

Nenhuma das três camadas é versionada no Git (regra R1). O repositório guarda o código, a documentação, os hashes da fonte e os hashes dos artefatos publicados. Essa separação entre o ciclo de vida dos dados e o ciclo de vida da aplicação é também o princípio que orienta a implantação em nuvem (seção 6.4).

## Ingestão e rastreabilidade da fonte

A ingestão é manual e acontece uma vez por edição. Um integrante baixa o `.zip` do portal de dados abertos do INEP para `data/raw/` e roda `scripts/verify_raw.sh`, que compara o SHA-256 do arquivo com o registrado em `data/raw/hashes.sha256`, versionado no repositório. Só depois o arquivo é extraído. Assim, qualquer máquina da equipe processa exatamente os mesmos bytes, e cada execução do pipeline registra de qual arquivo partiu.

A automação do download foi avaliada e não adotada: a fonte é estática, publicada uma vez por ano, e o código de download teria de ser mantido sem ganho mensurável. O hash cumpre o papel que importa, que é garantir a identidade da fonte.

## Profiling e contrato de dados

### Profiling

Antes de qualquer transformação, `scripts/profiling.py` caracterizou as quatro edições: volume, tipos, cardinalidade, ausências e distribuição de cada variável relevante, com o resultado em `docs/profiling/`. O profiling registrou, por exemplo, que oito colunas de respostas e gabaritos item a item (`TX_RESPOSTAS_*` e `TX_GABARITO_*`) respondem sozinhas por mais da metade do volume do CSV, que a UF da escola falta para 64% a 76% dos participantes elegíveis e que a renda familiar não foi respondida por 1,66% dos inscritos de 2020. Esses números orientaram decisões posteriores: a seleção de colunas, a escolha da UF de prova no módulo territorial e o tratamento de ausências nos módulos. Os agregados versionados do profiling já saem com o piso de privacidade aplicado: categorias com menos de 100 pessoas aparecem como suprimidas.

### Dicionário harmonizado

`scripts/dicionario.py` extraiu os domínios das variáveis dos dicionários do INEP de cada edição (`docs/dicionario/`) e apontou as variáveis cujos rótulos mudam entre edições. Os rótulos das alternativas de renda, por exemplo, trazem os valores em reais de cada ano. Por isso a TRUSTED preserva os códigos do INEP, e não os textos: traduzir para texto na carga fixaria o rótulo de um ano como se valesse para os outros. A interface lê o texto exato do questionário da edição escolhida pelo usuário.

### Contrato de dados como fonte única

`scripts/colunas.py` define, para cada uma das 76 colunas, o destino (mantida ou descartada), o nome interno, o tipo e a regra de ausência. O ETL não tem lista própria de colunas: consulta o contrato. A partir dele, `scripts/contrato.py` gera `docs/contrato/contrato.json` e a versão legível em `docs/contrato/README.md`, de modo que mudar uma regra é mudar um arquivo, e a documentação é regerada a partir dele. Das 76 colunas, 58 são mantidas e 18 descartadas, entre elas o identificador `NU_INSCRICAO`, removido na passagem RAW para TRUSTED (regra R2), e as colunas de respostas item a item, que o produto não usa.

## Pipeline RAW para TRUSTED

O pipeline está em `scripts/etl.py` e roda com um comando. Ele depende do contrato (`scripts/colunas.py`), das funções estatísticas (`scripts/estatistica.py`) e do DuckDB 1.5.5 como motor de execução.

### Leitura tipada

A função `ler_csv` monta a chamada `read_csv` do DuckDB com o separador e a codificação do INEP e com o tipo de cada coluna fixado pelo contrato. Fixar os tipos impede que o motor os deduza por amostragem, o que poderia ler uma coluna como inteiro numa edição e como texto em outra. O DuckDB lê latin-1 diretamente, sem a etapa de conversão para UTF-8 que o Polars exigiria.

### Seleção, renomeação e colunas derivadas

Cada coluna mantida é renomeada para o nome interno, e quatro colunas são derivadas na carga:

- `ano_conclusao`: o código de `TP_ANO_CONCLUIU` é um deslocamento em relação ao ano da prova, e não um ano; a coluna converte para o ano absoluto, deixando nulos o "não informado" e o código que rotula "antes de 2007";
- `conclusao_antes_2007`: marca própria para esse último caso, para que não se confunda com "não informado";
- `renda_sm`: piso da faixa de renda da `Q006` em múltiplos do salário mínimo da edição, a unidade em que as 17 faixas são comparáveis entre 2019 e 2022;
- `elegivel`: verdadeiro para quem esteve presente nas quatro áreas e não é treineiro. É a população de comparação do produto.

### Gravação comprimida, atômica e conferida

O trecho central da carga lê o CSV e grava o Parquet numa única consulta `COPY`, sem materializar a edição inteira na memória do Python:

```
COPY (
    SELECT * EXCLUDE (ano)
    FROM (SELECT {selecao_trusted(ano)} FROM {ler_csv(csv)})
    WHERE CASE WHEN ano IS DISTINCT FROM {ano}
               THEN error('NU_ANO diferente de {ano} em {csv.name}')
               ELSE true END
) TO '{temporario}' (FORMAT parquet, COMPRESSION zstd)
```

Três cuidados estão nesse trecho. O arquivo é gravado com nome temporário e só substitui a partição no fim, de modo que uma interrupção não deixa uma edição pela metade (escrita atômica). A coluna `ano` sai do arquivo porque passa a vir do nome da pasta (partição no estilo Hive), mas antes disso o `WHERE` aborta a carga se algum registro tiver `NU_ANO` diferente da edição esperada, o que detectaria um arquivo colocado na pasta errada. E a compressão ZSTD é aplicada coluna a coluna.

O particionamento por edição é feito com uma consulta por edição, e não com o `PARTITION_BY` do DuckDB, porque a medição mostrou que o `PARTITION_BY` dobrava o pico de memória (5,1 GB contra 2,4 GB na edição de 2022). O particionamento tem também uma justificativa estatística, medida na AV6: as edições são populações diferentes, e o produto nunca compara notas entre elas (seção 4.11).

## Funil de elegibilidade

Depois de gravar cada edição, a função `funil()` relê a partição e conta os inscritos por destino: treineiros, eliminados em alguma área, faltosos em alguma área e elegíveis. As categorias são mutuamente exclusivas e somam o total de inscritos, de modo que nenhum registro se perde em silêncio entre o CSV e a TRUSTED. O Plano de Trabalho veda exclusão silenciosa, e a TRUSTED mantém todos os inscritos, marcados.

Quadro: Funil de elegibilidade das quatro edições
Larguras: 10,15,14,12,19,15,15
| Edição | Inscritos | Treineiros | Eliminados | Faltaram em alguma área | Elegíveis | % elegível |
| --- | --- | --- | --- | --- | --- | --- |
| 2019 | 5.095.171 | 616.667 | 5.272 | 1.299.020 | 3.174.212 | 62,3% |
| 2020 | 5.783.109 | 557.425 | 5.077 | 2.978.438 | 2.242.169 | 38,8% |
| 2021 | 3.389.832 | 437.190 | 4.691 | 1.077.217 | 1.870.734 | 55,2% |
| 2022 | 3.476.105 | 512.732 | 5.243 | 1.030.377 | 1.927.753 | 55,5% |
| **Total** | **17.744.217** | **2.124.014** | **20.283** | **6.385.052** | **9.214.868** | **51,9%** |
Fonte: execução de `scripts/etl.py` de 13/10/2026 sobre os microdados do INEP (relatório da AV3, seção 3.5).

A proporção de elegíveis em 2020, de 38,8%, é o retrato da pandemia no próprio dado: quase três milhões de inscritos faltaram em pelo menos uma área. Por isso o produto descreve a posição de uma nota entre quem fez as quatro provas, e não entre todos os inscritos.

O número de linhas gravadas é comparado com o registrado no profiling para cada edição. Se divergir, a execução falha. Passando, o ETL grava em `data/trusted/enem/_manifesto.json` a linhagem da edição: arquivo de origem, hash, bytes de entrada e saída, funil, data, versão do DuckDB e identificador da execução.

## Camada ANALYTICS e artefatos dos módulos

A camada ANALYTICS responde à pergunta do produto sem tocar no dado individual. Ela tem dois tipos de artefato.

**Faixas protegidas, para os histogramas.** A função `faixas()` percorre as notas em ordem crescente e junta notas vizinhas até acumular pelo menos 100 participantes. A sobra final, se ficar abaixo do piso, entra na última faixa; se o total da área não chegar a 100, nada é publicado. O resultado, `dist_notas.parquet`, alimenta os gráficos sem nunca expor um grupo pequeno.

**Distribuições acumuladas exatas, para o percentil.** A função `construir_acumulada()` transforma as contagens por nota numa tabela com uma linha por nota distinta: a nota, quantos a tiraram (`n`), quantos ficaram abaixo dela (`abaixo`) e o total do grupo. Com ela, o percentil de qualquer nota sai por busca binária, sem interpolação (seção 4.3). A função rejeita notas repetidas, fora de ordem ou com frequência não positiva, para que um erro na consulta não vire um percentil errado.

Os três módulos autorais seguem o mesmo esquema, com uma CDF por grupo de comparação. O quadro resume os cinco artefatos publicados.

Quadro: Artefatos da camada ANALYTICS publicados na aplicação
Larguras: 22,13,12,53
| Artefato | Linhas | Tamanho | Conteúdo |
| --- | --- | --- | --- |
| `dist_notas.parquet` | 63.657 | 0,26 MB | Faixas de nota com 100 ou mais participantes, por edição e área (histogramas) |
| `dist_exata.parquet` | 81.525 | 0,40 MB | CDF nacional exata, uma linha por nota distinta, por edição e área |
| `dist_equidade.parquet` | 515.218 | 1,93 MB | CDFs das seis faixas de renda e do grupo de contraste (140 grupos) |
| `dist_territorial.parquet` | 2.226.487 | 7,96 MB | CDFs das 27 UFs, das 5 regiões e do Brasil (640 grupos de UF e região) |
| `dist_capital.parquet` | 508.214 | 2,08 MB | CDFs dos seis níveis de escolaridade e do Brasil (140 grupos) |
| **Total** | **3.395.101** | **12,6 MB** | 4 edições × 5 áreas; nenhum grupo publicado com menos de 100 participantes |
Fonte: `_manifesto_publicacao.json` da auditoria de 18/11/2026 (commit `cdb2c8e`) e relatórios de execução dos módulos (`docs/modulos/`).

Das 81.525 linhas da CDF nacional, 23.047 (28%) têm frequência menor que 100, e a menor é 1. Isso não viola o piso, que vale para o que é exibido, mas obriga a tratar as CDFs como dado interno: elas não são versionadas, não são servidas como arquivo estático e não são expostas por API (ADR-001). A seção 6.11 mostra como isso foi conferido no link público.

### Conferências antes de publicar

Os artefatos são gravados com nome temporário e só substituem os anteriores depois de quatro conferências: conservação de contagens (as faixas e a CDF de cada edição e área somam o total de elegíveis com nota), integridade do arquivo relido, erro das faixas limitado ao peso da maior faixa e exatidão da CDF. Nesta última, para até onze notas de cada edição e área (a menor, a maior, a mediana das observadas, valores fora do intervalo, uma nota não observada e cinco valores fixos), o percentil pela CDF é comparado com a contagem direta sobre o dado individual da TRUSTED, com tolerância de 10⁻⁹. Na execução de referência, a maior divergência foi **0,0 ponto percentual**. Os três módulos repetem a mesma conferência para cada grupo: a CDF gerada em SQL coincidiu linha a linha com a montada em Python, e a divergência contra a contagem direta foi 0,0 em todos.

## Modelo dimensional e integridade

A camada ANALYTICS foi documentada como modelo dimensional na AV6 (`docs/modelagem/README.md`), na sequência clássica da modelagem dimensional: processo de negócio, grão, dimensões e fatos. O processo de negócio modelado é "a distribuição das notas dos participantes elegíveis de uma edição, por área e por grupo de comparação".

**Frase do grão:** cada linha equivale a uma nota distinta observada, numa edição, numa área e num grupo de comparação, com quantos participantes elegíveis tiveram exatamente essa nota e quantos ficaram abaixo dela.

Quadro: Colunas da tabela fato de distribuição
Larguras: 14,26,60
| Coluna | Papel | Observação |
| --- | --- | --- |
| `ano` | Chave da dimensão edição | 2019 a 2022; também partição física da TRUSTED |
| `area` | Chave da dimensão área | `cn`, `ch`, `lc`, `mt`, `redacao` |
| `recorte` | Chave da dimensão módulo | `renda`, `territorial`, `capital` |
| `grupo` | Chave da dimensão grupo | Códigos com prefixo (`BR`, `RG-S`, `UF-SC`, `R1`, `CONTRASTE`, `NV-E`), para que "SE" de Sergipe não se confunda com o Sudeste |
| `nota` | Chave degenerada | A chave do grão termina nela |
| `n` | Medida aditiva | Pode ser somada entre notas, entre UFs de uma região e entre regiões |
| `abaixo` | Medida semiaditiva | Acumulada dentro do grupo; não se soma entre notas |
| `total` | Medida não aditiva entre linhas | Repete o N do grupo em todas as linhas dele |
Fonte: `docs/modelagem/README.md`, seção 2.

As dimensões são pequenas e estáveis (cinco áreas, quatro edições, 27 UFs, seis faixas, seis níveis) e ficam no código de cada módulo, e não em tabelas separadas. Um modelo estrela físico, com tabelas de dimensão e chaves substitutas, não traria ganho para um conjunto somente leitura de 12,6 MB lido inteiro em memória. Média, mediana, desvio e quartis não são guardados prontos: são calculados pelo motor a partir das linhas, o que evita o erro clássico de somar ou tirar média de médias de grupos de tamanhos diferentes.

O projeto não usa banco relacional (seção 6.4), mas aplica as restrições que um esquema declararia. Elas são verificadas por `scripts/auditar_artefatos.py` antes de cada publicação.

Quadro: Restrições de integridade e equivalentes no projeto
Larguras: 42,30,28
| Restrição que um SGBD declararia | Equivalente no projeto | Onde |
| --- | --- | --- |
| `PRIMARY KEY (ano, area, recorte, grupo, nota)` | Chave do grão sem repetição | `auditar_artefatos.py` |
| `CHECK (n > 0)` | Frequência positiva | `auditar_artefatos.py`; `construir_acumulada` |
| `CHECK (nota BETWEEN 0 AND 1000)` | Faixa de nota | `auditar_artefatos.py`; validação da entrada |
| `CHECK` de coerência (`abaixo` = soma dos `n` anteriores) | CDF coerente | `auditar_artefatos.py` |
| Integridade entre tabelas | Total do Brasil igual entre artefatos | `auditar_artefatos.py` |
| `CHECK (total >= 100)` | Piso de privacidade por grupo | `auditar_artefatos.py`; ETL de cada módulo |
| Tipos e nulidade por coluna | Contrato de dados | `scripts/colunas.py` |
Fonte: `docs/modelagem/README.md`, seção 3.

A TRUSTED é deliberadamente uma tabela larga, sem normalização: é uma camada analítica, lida por varredura colunar, sem atualização linha a linha, e não sofre as anomalias que a normalização evita num sistema transacional. O equivalente a índice é o próprio layout físico: Parquet colunar, partição por edição e artefatos ordenados por grupo e nota, o que permite a busca binária na CDF em memória. O comando `python scripts/auditar_artefatos.py --explicar` mostra o plano de execução (`EXPLAIN ANALYZE`) da consulta que o app faz ao abrir: uma varredura do Parquet com projeção das colunas usadas, sem filtro, porque o app carrega cada distribuição uma vez e responde às consultas em memória.

## Volumetria e otimização

Os números desta seção foram medidos numa execução completa do pipeline sobre os microdados reais, em 13/10/2026, num notebook com Intel Core i5-9300H (8 threads), 15,4 GB de memória, Python 3.12.3 e DuckDB 1.5.5.

Quadro: Volumetria por edição
Larguras: 10,13,13,16,14,18,16
| Edição | ZIP do INEP | CSV (RAW) | Parquet (TRUSTED) | Razão CSV/Parquet | Linhas | Grupos de linhas |
| --- | --- | --- | --- | --- | --- | --- |
| 2019 | 660 MB | 2,41 GB | 111,4 MB | 21,6× | 5.095.171 | 42 |
| 2020 | 621 MB | 2,02 GB | 114,0 MB | 17,8× | 5.783.109 | 47 |
| 2021 | 498 MB | 1,51 GB | 73,1 MB | 20,6× | 3.389.832 | 28 |
| 2022 | 621 MB | 1,57 GB | 75,8 MB | 20,7× | 3.476.105 | 29 |
| **Total** | **2,40 GB** | **7,51 GB** | **374,3 MB** | **20,1×** | **17.744.217** | **146** |
Fonte: manifesto da TRUSTED da execução de 13/10/2026 (relatório da AV3, seção 5.2).

A TRUSTED ocupa 374,3 MB, **95,0% a menos que o CSV** e 6,4 vezes menos que os próprios arquivos compactados do INEP, com todas as linhas preservadas. O quadro seguinte decompõe a redução por estratégia.

Quadro: Origem da redução de volume
Larguras: 50,22,28
| Passo | Volume aproximado | Estratégia |
| --- | --- | --- |
| CSV completo, 76 colunas | 7,51 GB | Ponto de partida |
| Só as 58 colunas do contrato, ainda em texto | 1,56 GB | Seleção de colunas |
| Mesmas colunas tipadas em Parquet, sem compressão | 521 MB | Formato colunar e tipagem |
| Parquet com ZSTD | 374 MB | Compressão por coluna |
| Distribuições agregadas (faixas e CDF nacional) | 0,65 MB | Pré-agregação |
Fonte: relatório da AV3, seção 5.4, com o peso de cada coluna medido no profiling.

A seleção de colunas é o maior ganho isolado: 74,7% do volume do CSV está nas 18 colunas que o produto não usa. A tipagem transforma códigos de um ou dois caracteres em inteiros codificados por dicionário, e valores ausentes, que chegam a 84% em colunas de escola, quase não ocupam espaço. A compressão ZSTD reduz em mais 30% o Parquet já codificado. O particionamento por edição não reduz bytes, mas reduz leitura: uma consulta sobre uma edição abre um arquivo de 73 a 114 MB em vez de 374 MB.

Quadro: Tempo do pipeline por etapa
Larguras: 60,40
| Etapa | Tempo |
| --- | --- |
| TRUSTED 2019 | 9,3 s |
| TRUSTED 2020 | 9,4 s |
| TRUSTED 2021 | 6,6 s |
| TRUSTED 2022 | 6,6 s |
| ANALYTICS nacional, com as conferências | 80,1 s |
| **Total** | **112,3 s** |
Fonte: execução de 13/10/2026 medida com `/usr/bin/time -v` (relatório da AV3, seção 5.3).

O pico de memória do processo foi de **2,65 GB**: o pipeline cabe num notebook de 8 GB, o equipamento previsto no Plano. Quase todo o tempo da etapa ANALYTICS está nas conferências contra o dado individual (cerca de 360 contagens); sem elas, a execução levava 65 s. É um custo de validação, pago offline, que troca 47 s de lote pela garantia de que o percentil publicado coincide com a contagem direta. Os módulos acrescentam suas etapas: a Equidade levou 35,1 s numa máquina virtual de 2 vCPU, e o Capital escolar, de 57,8 s a 99,1 s por edição.

No runtime, a carga de `dist_exata.parquet` levou 0,12 s e a de `dist_notas.parquet` 0,07 s, uma vez por processo; o percentil de uma nota pela CDF, 0,11 ms. Para comparação, o mesmo percentil calculado sobre a TRUSTED de 2022 levaria 71 ms, e a consulta mais pesada prevista sobre o dado individual (renda × dependência da escola nas quatro edições, com quartis) levaria 1,04 s e 497 MB de memória no DuckDB. A pré-agregação é o que permite responder em milissegundos numa máquina de 2 GB.

## Escolha da stack por benchmark

O Plano de Trabalho previa Polars na transformação e DuckDB nas consultas, com Spark apenas se houvesse necessidade mensurável. Em vez de escolher por opinião, a equipe fez um benchmark sobre os dados reais das quatro edições (`docs/stack/`, 25/09/2026), medindo tempo, pico de memória residente amostrado a cada 20 ms e comportamento com o crescimento do volume.

Quadro: Benchmark dos motores de processamento no ETL, por edição
Larguras: 34,33,33
| Motor | Tempo | Pico de memória |
| --- | --- | --- |
| pandas (parser C) | 45 a 76 s | 2,9 a 4,9 GiB |
| pandas (parser pyarrow) | 9 a 17 s | 4,8 a 7,0 GiB |
| Polars, com conversão de latin-1 | 8 a 15 s | 1,9 a 2,7 GiB |
| **DuckDB** | **6 a 9 s** | **2,2 a 2,4 GiB** |
| Spark local | 29 a 40 s | 1,6 GiB |
Fonte: `docs/stack/benchmark.md` (25/09/2026), quatro edições reais.

Quadro: Consultas no orçamento do runtime (2 núcleos, 1 GB)
Larguras: 34,22,22,22
| Consulta | pandas | Polars | DuckDB |
| --- | --- | --- | --- |
| Filtro e agregação em 2022 | 149 a 274 ms, até 514 MB | 44 a 84 ms, até 350 MB | 71 a 98 ms, até 111 MB |
| Quatro edições, quartis por grupo | 2.351 ms, **2.044 MB** | 967 ms, **2.111 MB** | 1.037 ms, 497 MB |
| Artefato ANALYTICS | 5 ms, 160 MB | 2 ms, 69 MB | 2 ms, 65 MB |
Fonte: `docs/stack/README.md`, seção 4.4 (mediana de 5 execuções e pico do processo).

Quadro: Codecs de compressão do Parquet (edição 2019, 58 colunas)
Larguras: 22,20,22,16,20
| Codec | Tamanho | Razão sobre o CSV | Escrita | Leitura de uma agregação |
| --- | --- | --- | --- | --- |
| Sem compressão | 142,0 MiB | 16,2× | 2,3 s | 23 ms |
| snappy | 125,1 MiB | 18,4× | 2,2 s | 25 ms |
| gzip | 102,4 MiB | 22,4× | 4,3 s | 32 ms |
| **zstd** | **101,4 MiB** | **22,6×** | **2,4 s** | **36 ms** |
Fonte: `docs/stack/benchmark.md` (25/09/2026).

As decisões que resultaram do benchmark foram:

- **DuckDB no ETL e no runtime**, em vez de Polars no ETL. O DuckDB foi o mais rápido nas quatro edições, lê o latin-1 do INEP sem conversão e gera um Parquet cerca de 20% menor. Nas consultas, foi o único motor que ficou abaixo de 1 GB em todas, porque respeita o `memory_limit` e derrama para disco. Um motor só nas duas pontas elimina uma dependência e uma segunda sintaxe para a equipe manter.
- **Parquet com ZSTD**, que chega ao tamanho do gzip com a velocidade de escrita do snappy; os 11 ms a mais por leitura em relação ao snappy são irrelevantes diante da meta de 3 s.
- **Spark medido e não adotado.** Levou de 4 a 5 vezes o tempo do DuckDB em dados que cabem numa máquina. Ele passaria a fazer sentido se o ETL de uma edição deixasse de caber na memória de uma máquina mesmo com derramamento para disco, o que não ocorre: o pico ficou estável entre edições de 1,4 a 2,2 GB de CSV.
- **Streamlit com Plotly na interface.** O custo fixo dos frameworks avaliados foi equivalente (73 a 100 MB de memória ociosa), e a diferença está no esforço de desenvolvimento: uma aplicação React com FastAPI exigiria duas bases de código e duas publicações, incompatíveis com o prazo do semestre.

## Barreira de qualidade antes de publicar

Na AV6, a publicação dos artefatos passou a depender de uma barreira explícita (DL-08, item 3). O script `scripts/auditar_artefatos.py` confere os cinco arquivos de `data/analytics/` e só termina com saída 0 se todas as verificações passarem: colunas esperadas, chave do grão única, frequência positiva, notas entre 0 e 1.000, CDF coerente, piso de 100 por grupo, total do Brasil igual entre os artefatos e SHA-256 igual ao da execução de referência (`docs/deploy/artefatos.sha256`). O resultado é gravado em `data/analytics/_manifesto_publicacao.json`, que o app lê para mostrar no rodapé a data da conferência e o commit do código. Na auditoria de 18/11/2026, os cinco artefatos passaram em todas as verificações e coincidiram com a referência.

A auditoria roda de novo no ambiente do Replit antes de cada publicação, no Shell do projeto, o que confere também que os arquivos enviados à nuvem são os mesmos gerados pelo pipeline (seção 6.6).

## Linhagem, reprodutibilidade e manifestos

A cadeia que liga um número exibido na tela à fonte do INEP pode ser percorrida em seis passos:

- `data/raw/hashes.sha256`, versionado, registra o SHA-256 dos quatro arquivos do INEP, e `scripts/verify_raw.sh` confere os arquivos locais contra ele;
- `_manifesto.json` liga cada partição da TRUSTED ao arquivo de origem e ao seu hash, com o funil da edição;
- `_manifesto_analytics.json` liga os artefatos ao commit do código que os gerou, com tamanho, número de linhas e SHA-256 de cada um;
- desde a AV6, os dois manifestos registram o mesmo `run_id` (data e hora UTC mais oito caracteres aleatórios), para que se saiba de qual execução saiu cada artefato;
- `docs/deploy/artefatos.sha256` fixa os hashes dos artefatos publicados, e `_manifesto_publicacao.json` registra a auditoria feita antes da publicação;
- o rodapé de cada página do app mostra a data da conferência e o commit.

**Reprodutibilidade.** A mesma entrada e a mesma versão do pipeline geram resultados logicamente equivalentes: mesmas linhas, mesmo funil, mesmas faixas e CDFs. Os arquivos da TRUSTED não são idênticos byte a byte entre execuções, porque a escrita paralela do DuckDB pode ordenar os grupos de linhas de forma diferente (a partição de 2021 variou 0,06% de tamanho). Por isso a conferência da TRUSTED é feita por contagem e por conteúdo, e os artefatos da ANALYTICS, que são ordenados explicitamente, são conferidos por hash. Os testes automatizados reproduzem o pipeline inteiro com microdados sintéticos gerados em tempo de execução, sem nenhum dado do INEP no repositório (Apêndice E).

## Técnicas de Big Data avaliadas e não adotadas

O Plano de Trabalho condiciona recursos distribuídos, NoSQL, streaming e modelos de aprendizado de máquina a uma necessidade real e mensurável. O quadro resume o que foi avaliado e por que ficou de fora.

Quadro: Técnicas de Big Data não adotadas e justificativa
Larguras: 26,74
| Técnica | Justificativa |
| --- | --- |
| Spark e processamento distribuído | Medido: 4 a 5 vezes mais lento que o DuckDB em dados que cabem numa máquina. Processamento distribuído se justifica diante de gargalo real, que não existe aqui |
| Streaming, ELT e carga incremental | A fonte é estática e publicada uma vez por ano; a carga completa com hash da fonte é suficiente e mais simples de auditar |
| NoSQL, grafos e bancos vetoriais | Não há padrão de acesso que precise deles: o app lê distribuições inteiras, uma vez |
| Lakehouse (Delta Lake, Iceberg) | Não há atualização, merge nem histórico de versões de tabela; a versão do dado é controlada por hash e manifesto |
| Armazenamento de objetos para os microdados | O RAW e a TRUSTED não saem da máquina da equipe; só os agregados sobem para a nuvem (seção 6.5) |
| Modelos de aprendizado de máquina | O produto não prevê nada: não há variável-alvo nem decisão a automatizar (seção 8.2) |
Fonte: elaborado pela equipe a partir de `docs/stack/README.md` e do Decision Log.
