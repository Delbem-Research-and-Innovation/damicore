# DAMICORE — Especificação Final de Arquitetura e Implementação

**Repositório:** Delbem-Research-and-Innovation/damicore  
**Status:** implementado; contrato normativo da versão 0.1  
**Versão desta especificação:** 1.1  
**Primeira versão de produto:** 0.1.0

---

## 1. Autoridade e linguagem normativa

Este documento é autossuficiente e constitui a referência normativa para implementar a versão 0.1 do DAMICORE. Nenhum contexto externo da conversa é necessário.

Os termos **DEVE**, **NÃO DEVE** e **PODE** são normativos:

- **DEVE** indica requisito obrigatório;
- **NÃO DEVE** indica proibição;
- **PODE** indica comportamento opcional que não altera o contrato obrigatório.

Durante a implementação, a ordem de autoridade é:

1. esta especificação versionada;
2. schemas e modelos públicos derivados dela;
3. testes de contrato e de comportamento;
4. implementação;
5. READMEs, exemplos e notebooks.

Qualquer divergência entre essas fontes é um defeito. O nível inferior NÃO DEVE redefinir silenciosamente o nível superior. Depois do lançamento, mudanças de contrato exigem atualização conjunta desta especificação, dos modelos, dos testes e da documentação pública.

Este documento não duplica o que o repositório já enuncia de forma executável. Onde ele delega uma listagem — assinaturas, campos de modelo, árvore de arquivos — o código é a fonte daquela listagem e um teste a fixa; a regra sobre a listagem continua sendo desta especificação. Delegar não é rebaixar: uma listagem copiada aqui seria uma segunda verdade livre para divergir em silêncio.

---

## 2. Definição do produto

DAMICORE é uma família de bibliotecas Python instaláveis por pip que recebe o caminho local de um CSV do usuário, transforma linhas ou colunas em objetos, calcula distâncias por compressão normalizada, constrói uma árvore filogenética e produz agrupamentos.

O fluxo obrigatório é:

~~~text
CSV local
  -> normalização determinística
  -> matriz NCD
  -> árvore Neighbor Joining
  -> agrupamento FastGreedy
  -> resultado Python e artefatos persistidos
~~~

A instalação e o uso primários são:

~~~python
%pip install damicore

import damicore

result = damicore.run(
    csv_path="/content/dataset.csv",
    split="columns",
)

result.membership
result.clusters
print(result.tree_newick)
result.distance_matrix.head()
~~~

O caso de uso principal é Jupyter Notebook, especialmente Google Colab. A API Python é primária; a CLI é uma interface secundária e fina sobre a mesma API.

---

## 3. Escopo fechado da versão 0.1

### 3.1 Incluído

- entrada por caminho de arquivo CSV local;
- divisão por colunas ou por linhas;
- serialização canônica e reprodutível dos objetos;
- NCD exata com zlib ou gzip;
- matriz float64 persistida em formato NumPy mapeável em disco;
- Neighbor Joining exato e determinístico;
- clusterização FastGreedy por igraph;
- execução paralela local com memória limitada;
- estimativa de recursos, bloqueio preventivo, checkpoints e retomada;
- API de alto nível, APIs independentes por pacote e CLI mínima;
- boa experiência em Jupyter e Colab sem dependências de sistema;
- testes com dados sintéticos gerados internamente;
- build e publicação independentes dos pacotes pip.

### 3.2 Excluído

- corpus legado ou corpus de caracterização;
- uso do gerador sintético na API ou na documentação do usuário;
- entrada por URL, DataFrame, banco de dados, diretório ou arquivo compactado na API principal;
- aproximação, amostragem, redução automática ou algoritmo distribuído;
- CUDA/GPU;
- serviço web, API HTTP, banco de dados ou fila;
- interface gráfica e widgets específicos de notebook;
- detecção automática de encoding ou delimitador;
- suporte a compressores externos;
- portabilidade integral das ferramentas auxiliares do repositório legado;
- descoberta automática de um número de clusters por heurística diferente da modularidade FastGreedy;
- exclusão, sobrescrita recursiva ou limpeza destrutiva de diretórios do usuário.

O código legado serve somente como referência do núcleo algorítmico.

---

## 4. Resultados e invariantes

Uma execução bem-sucedida DEVE produzir:

1. uma matriz NCD simétrica, finita, float64 e com diagonal zero;
2. uma árvore que contenha exatamente uma folha para cada objeto normalizado;
3. uma atribuição de cluster completa e exclusiva para cada folha;
4. um manifesto que permita reconstruir entrada, configuração, versões e estado da execução;
5. artefatos gravados atomicamente e carregáveis sem executar código arbitrário;
6. um objeto DamicoreResult conveniente para notebook.

Invariantes obrigatórios:

- nenhum objeto pode desaparecer ou aparecer duas vezes;
- a ordem dos objetos segue a ordem original de colunas ou linhas;
- a mesma entrada, configuração e fingerprint completo de runtime produz os mesmos bytes normalizados, matriz, árvore e associação de clusters;
- paralelismo não pode alterar o resultado;
- uma etapa não pode declarar sucesso antes de validar sua saída;
- falha, cancelamento ou interrupção não podem marcar um shard ou estágio como concluído;
- nenhum estágio pode carregar o CSV inteiro em memória;
- nenhuma API pode avaliar pickle, código do CSV ou conteúdo de artefato como código.

---

## 5. Drivers e restrições de qualidade

| Prioridade | Propriedade | Cenário verificável |
|---:|---|---|
| 1 | Correção | Fixtures matemáticas validam NCD, Neighbor Joining e associação de folhas. |
| 2 | Memória limitada | Um CSV grande é processado em chunks; matriz e workspace quadráticos ficam em memmap. |
| 3 | Reprodutibilidade | Manifesto registra hash da entrada, configuração, versões e hashes dos artefatos. |
| 4 | DX de notebook | Instalação por pip e uma chamada damicore.run bastam; progresso funciona no Colab. |
| 5 | Recuperação | Execução interrompida retoma apenas shards completos e compatíveis. |
| 6 | Modularidade | Cada estágio pode ser instalado e testado isoladamente; somente o orquestrador depende dos quatro. |
| 7 | Operabilidade | Relatório expõe tempos, contagens, recursos estimados, progresso e falha tipada. |
| 8 | Portabilidade | Python 3.11–3.14, Linux/macOS/Windows, sem binário de sistema obrigatório. |

Restrições duras:

- a implementação DEVE ser Python puro mais wheels das dependências declaradas;
- o resultado exato continua tendo custo quadrático no NCD e cúbico no Neighbor Joining;
- limites de segurança DEVEM impedir trabalho inviável antes de criar milhões de objetos ou pares;
- o sistema NÃO DEVE esconder inviabilidade por meio de amostragem silenciosa.

---

## 6. Arquitetura mínima

~~~mermaid
flowchart TD
    U["Notebook ou CLI"] --> O["damicore: orquestração"]
    O --> N["damicore-normalizer"]
    O --> D["damicore-distance"]
    O --> T["damicore-tree-builder"]
    O --> C["damicore-clusterizer"]
    N --> A["Artefatos versionados"]
    D --> A
    T --> A
    C --> A
~~~

### 6.1 Regra de dependência

- damicore importa e orquestra os quatro pacotes de estágio.
- Um pacote de estágio NÃO DEVE importar outro pacote de estágio.
- synthetic_data NÃO DEVE ser dependência de nenhum pacote publicado.
- O intercâmbio entre estágios DEVE ocorrer por artefatos versionados, tipos da biblioteca padrão e arrays NumPy nas APIs in-memory explicitamente definidas.
- Não será criado um pacote compartilhado damicore-core na versão 0.1. Modelos pequenos e específicos permanecem no pacote proprietário do contrato.

Essa direção DEVE ser fiscalizada por teste AST no CI, que falha se um pacote de estágio importar outro.

### 6.2 Ownership

| Pacote | Responsabilidade exclusiva | Entrada canônica | Saída canônica |
|---|---|---|---|
| damicore-normalizer | interpretar CSV e serializar objetos | CSV | normalization/manifest.json e objects/ |
| damicore-distance | compressão e cálculo NCD | manifesto de normalização | distance.npy e labels.json |
| damicore-tree-builder | Neighbor Joining e árvore | distance.npy e labels.json | tree.json e tree.nwk |
| damicore-clusterizer | grafo, FastGreedy e memberships | tree.json | membership.csv e clusters.json |
| damicore | preflight, orquestração, progresso, resultado e persistência | caminho CSV | diretório completo de execução |
| synthetic_data | gerar fixtures e datasets de teste | parâmetros de teste | CSV de teste |

---

## 7. Estrutura obrigatória do repositório

O repositório é um workspace uv com packages/ na raiz, mais docs/, notebooks/, tests/ e benchmarks/. São normativos:

- os cinco pacotes publicados e synthetic_data ocupam um diretório cada em packages/, com pyproject.toml, README.md, layout src e tests/ próprios;
- o diretório do código de cada pacote tem exatamente o nome do seu módulo importável;
- módulos são nomeados pelo conceito de domínio que possuem, um conceito por módulo;
- tests/ na raiz guarda somente as suítes que atravessam pacotes: contracts, e2e, notebooks e architecture;
- o pyproject raiz declara o workspace e não gera distribuição.

A árvore concreta de arquivos NÃO É normativa. Ela é legível no próprio repositório, e fixá-la aqui apenas produz uma cópia que se desatualiza a cada módulo novo. Quais pacotes existem e quais podem ser publicados é decidido pelo teste de arquitetura e pela allowlist do Makefile.

Todos os pacotes usam layout src. Os módulos internos NÃO DEVEM ser reexportados por acidente. Cada __init__.py DEVE declarar __all__ com a API pública descrita neste documento.

---

## 8. Empacotamento e dependências

### 8.1 Plataforma

- Python suportado: >=3.11,<3.15.
- Gerenciamento do monorepo e lock: uv workspace.
- Backend de build: hatchling >=1.27,<2.
- Versionamento: SemVer, em lockstep para os cinco pacotes publicados.
- Versão inicial: 0.1.0.
- O pacote synthetic_data é privado ao workspace e NÃO DEVE ser publicado.

### 8.2 Dependências de runtime aprovadas

Somente estas cinco dependências externas são aprovadas em runtime:

| Biblioteca | Faixa pública | Versão inicial no uv.lock | Uso |
|---|---:|---:|---|
| numpy | >=1.26,<3 | 2.5.1 | matriz, memmap e cálculo numérico |
| pandas | >=2.2,<4 | 3.0.5 | leitura CSV em chunks e DataFrames de resultado |
| pydantic | >=2.10,<3 | 2.13.4 | configuração, schemas e validação |
| igraph | >=1.0,<1.1 | 1.0.0 | FastGreedy |
| tqdm | >=4.66,<5 | 4.70.0 | progresso em terminal e notebook |

O uv.lock DEVE fixar versões exatas e hashes. As faixas públicas permitem receber correções compatíveis sem prometer versões principais não testadas.

Distribuição por pacote:

| Pacote | Dependências diretas |
|---|---|
| damicore-normalizer | pandas, pydantic |
| damicore-distance | numpy, pydantic; pandas como extra opcional `[pandas]` |
| damicore-tree-builder | numpy, pydantic |
| damicore-clusterizer | igraph, numpy, pydantic |
| damicore | damicore-normalizer, damicore-distance[pandas], damicore-tree-builder, damicore-clusterizer, pandas, pydantic, tqdm |

damicore DEVE declarar cada pacote irmão como >=0.1.0,<0.2.0. Os pyproject publicados NÃO DEVEM conter referências workspace, paths locais ou sources do uv.

### 8.3 Biblioteca padrão usada

zlib, gzip, csv, json, codecs, pathlib, concurrent.futures, multiprocessing, tempfile, hashlib, shutil, logging, time, os, resource quando disponível, dataclasses e typing.

### 8.4 Dependências não aprovadas

Dask, Ray, PyArrow, Polars, SciPy, scikit-learn, NetworkX, Numba, Zarr, HDF5, Joblib, Typer, Click, psutil, IPython e ipywidgets NÃO DEVEM ser introduzidos na versão 0.1.

### 8.5 Dependências de desenvolvimento

~~~toml
pytest = ">=8,<10"
pytest-cov = ">=6,<8"
hypothesis = ">=6,<7"
ruff = ">=0.15,<0.17"
pyright = ">=1.1,<2"
pandas-stubs = ">=2.2,<4"
build = ">=1.2,<2"
twine = ">=6,<7"
pip-audit = ">=2.9,<3"
nbformat = ">=5.10,<6"
nbclient = ">=0.10,<1"
~~~

O CI NÃO DEVE usar tags latest. Actions, uv e ferramentas DEVEM ter versão fixada.

### 8.6 Contrato de distribuição

| Distribuição PyPI | Import Python | Build | Publicação |
|---|---|---|---|
| damicore-normalizer | damicore_normalizer | hatchling, src layout | pública |
| damicore-distance | damicore_distance | hatchling, src layout | pública |
| damicore-tree-builder | damicore_tree_builder | hatchling, src layout | pública |
| damicore-clusterizer | damicore_clusterizer | hatchling, src layout | pública |
| damicore | damicore | hatchling, src layout | pública |
| synthetic-data | synthetic_data | workspace apenas | nunca publicar |

O pyproject raiz declara workspace members = ["packages/*"] e não gera distribuição. Cada pacote publicado declara requires-python, versão, dependencies, README próprio e build-system. damicore declara o entry point damicore = "damicore.cli:main". O job de release mantém uma allowlist explícita dos cinco diretórios publicáveis; glob irrestrito é proibido.

---

## 9. API pública de alto nível

### 9.1 Assinaturas

damicore expõe exatamente estimate, run e load_result. As assinaturas vivem em damicore/api.py e os nomes públicos são fixados por teste de arquitetura; esta seção define o que uma assinatura não expressa.

csv_path aceita somente arquivo regular local existente. URLs e objetos file-like são rejeitados. split aceita exatamente columns ou rows. delimiter DEVE ter um único caractere Unicode. encoding DEVE ser reconhecido por codecs.lookup e usa errors=strict. compressor aceita exatamente zlib ou gzip. compression_level aceita inteiro de 0 a 9.

num_clusters=None escolhe o corte de maior modularidade fornecido pelo FastGreedy. Um inteiro exige 1 <= num_clusters <= número de folhas e define a quantidade de comunidades no grafo completo da árvore, incluindo nós internos. Comunidades sem folhas não aparecem nos clusters de dados; por isso cluster_count pode ser menor que num_clusters. report expõe ambos os valores.

### 9.2 Configuração de execução

~~~python
class ResourceLimits(BaseModel):
    max_objects: int = 1_000
    max_pairs: int = 500_000
    max_matrix_bytes: int = 536_870_912  # 512 MiB por matriz
    max_working_memory_bytes: int = 536_870_912
    required_free_disk_factor: float = 1.25


class ExecutionConfig(BaseModel):
    workers: int | Literal["auto"] = "auto"
    csv_chunk_rows: int = 50_000
    compression_chunk_bytes: int = 4_194_304  # 4 MiB
    pairs_per_shard: int = 10_000
    resume: bool = True
    reuse_completed: bool = True
    pandas_materialization_limit_bytes: int = 268_435_456
    limits: ResourceLimits = Field(default_factory=ResourceLimits)
~~~

Validações:

- workers inteiro deve ser >=1;
- auto resolve para min(4, max(1, cpu_count - 1));
- csv_chunk_rows, compression_chunk_bytes e pairs_per_shard devem ser positivos;
- todos os limites devem ser positivos;
- required_free_disk_factor deve ser >=1.0;
- configuração inválida falha antes de ler o conteúdo do CSV.

Para aceitar um problema maior, o usuário precisa fornecer limites maiores explicitamente. Não existe flag que desabilite todos os limites. Espaço em disco insuficiente nunca pode ser ignorado.

### 9.3 Resultado

DamicoreResult expõe membership, clusters, tree_newick, distance_matrix, report e artifacts, mais save e close. Os campos de RunReport e ArtifactPaths são o schema de report.json e dos paths que a CLI imprime; a lista exata é fixada por teste de arquitetura, e alterá-la é mudança de contrato.

No DamicoreResult retornado por run ou load_result, report.status é sempre completed. Reports failed/interrupted existem no disco para diagnóstico e retomada, mas load_result os rejeita.

Os campos csv_chunk_rows, compression_chunk_bytes e pairs_per_shard são os chunks e shards que a seção 18.6 exige em report.json; eles constam aqui porque RunReport é o modelo desse artefato.

membership possui, nesta ordem, as colunas object_id, label e cluster. cluster é int64; as demais são strings. A ordem das linhas é a ordem original dos objetos.

clusters mapeia IDs inteiros contíguos a listas de labels na ordem original. tree_newick termina com ponto e vírgula.

DistanceMatrixView DEVE oferecer:

- shape, dtype, labels e path;
- indexação NumPy somente leitura;
- head(n=5) retornando DataFrame n por n;
- to_pandas(force=False).

head e to_pandas são os únicos pontos do pacote que usam pandas, declarado como extra `[pandas]`. Quando o extra não está instalado, ambos DEVEM falhar com erro tipado nomeando o extra a instalar; o restante da view (shape, dtype, labels, path e indexação NumPy) permanece disponível sem ele. damicore depende de damicore-distance[pandas], então o pipeline agregado sempre os tem.

to_pandas falha com MaterializationError quando os bytes da matriz excedem pandas_materialization_limit_bytes, salvo force=True. A mensagem DEVE informar tamanho estimado e sugerir head ou acesso por fatias.

save copia somente artefatos concluídos para um destino inexistente ou vazio. Destino não vazio causa OutputDirectoryConflictError. A biblioteca nunca apaga o destino.

close fecha o memmap e demais handles. membership, clusters, tree_newick, report e paths continuam legíveis; qualquer novo acesso à matriz após close levanta ValueError com mensagem para recarregar via load_result.

### 9.4 Exports públicos

| Import | Símbolos em __all__ |
|---|---|
| damicore | run, estimate, load_result, DamicoreResult, DistanceMatrixView, ExecutionConfig, ResourceLimits, ResourceEstimate, RunReport, ArtifactPaths e exceções da seção 19 |
| damicore_normalizer | normalize_csv, NormalizationConfig, NormalizationResult, ObjectDescriptor, NormalizerError |
| damicore_distance | compute_distance_matrix, DistanceConfig, DistanceResult, DistanceMatrixView, DistanceError |
| damicore_tree_builder | build_tree, neighbor_joining, TreeBuildConfig, TreeBuildResult, Tree, TreeNode, TreeEdge, TreeBuilderError |
| damicore_clusterizer | cluster_tree, ClusterConfig, ClusterResult, ClusterizerError |

Nenhum outro nome é API pública na versão 0.1.

---

## 10. Contrato do CSV

### 10.1 Parsing

A leitura DEVE usar pandas.read_csv com:

~~~python
pd.read_csv(
    path,
    sep=delimiter,
    encoding=encoding,
    dtype=str,
    keep_default_na=False,
    na_filter=False,
    skip_blank_lines=False,
    chunksize=execution.csv_chunk_rows,
    on_bad_lines="error",
)
~~~

quotechar é aspas duplas, doublequote é verdadeiro e comment é None. Todos os valores são tratados como texto. O sistema NÃO DEVE inferir tipos, converter datas, remover espaços, normalizar Unicode ou substituir strings vazias por nulos.

O cabeçalho é obrigatório. Nomes vazios ou duplicados são rejeitados antes da normalização. Em columns, o CSV precisa conter ao menos duas colunas e uma linha de dados. Em rows, precisa conter ao menos duas linhas de dados. Linhas malformadas e erro de decoding causam CSVFormatError com número da etapa e mensagem original encadeada.

### 10.2 IDs e labels

- columns: object_id column_000001, column_000002, ...; label é o cabeçalho original.
- rows: object_id e label row_000001, row_000002, ...; a numeração ignora o cabeçalho.

IDs são baseados em posição, têm seis dígitos no mínimo e aumentam a largura quando necessário. Eles são usados em matriz, árvore e contratos. Labels são somente apresentação.

### 10.3 Serialização canônica

Todo objeto é escrito em UTF-8 sem BOM e com newline LF.

- columns: cada célula, em ordem de linha, vira um JSON string por linha;
- rows: cada linha vira um JSON array de strings, na ordem do cabeçalho, seguido por LF.

json.dumps DEVE usar ensure_ascii=False e separators=(",", ":"). O conteúdo decodificado é preservado; apenas a representação JSON fornece escaping. Todo arquivo de objeto termina com LF.

Exemplo:

~~~text
CSV: nome,idade
     Ana,31
     Bia,

column_000001.jsonl:
"Ana"
"Bia"

row_000002.jsonl:
["Bia",""]
~~~

O normalizador DEVE escrever progressivamente. Em columns, um pool LRU limita a 64 os arquivos abertos. Em rows, cada arquivo é criado e fechado imediatamente. Nenhum objeto completo é acumulado em RAM.

---

## 11. Preflight e estimativa de recursos

estimate e run DEVEM executar o mesmo preflight. run NÃO PODE pular essa etapa.

### 11.1 Passos

1. resolver o caminho sem seguir para URL e validar arquivo regular legível;
2. obter size e mtime_ns;
3. calcular SHA-256 dos bytes do CSV por streaming;
4. validar cabeçalho e estrutura em chunks e executar a serialização canônica em modo de contagem;
5. contar exatamente objetos, pares, bytes normalizados e maior chunk serializado;
6. calcular matrizes, workspace, memória e disco necessários;
7. comparar com ResourceLimits e espaço livre real;
8. retornar ResourceEstimate ou levantar ResourceLimitError.

No modo rows, o preflight faz uma passagem completa de contagem antes de criar arquivos por linha. Isso é obrigatório mesmo que implique uma passagem adicional sobre um CSV grande. No modo columns, o número de objetos vem do cabeçalho, mas a passagem completa de hash, validação e contagem de bytes continua obrigatória. O preflight não grava objetos; a normalização faz uma segunda passagem de parsing. Os bytes normalizados calculados pelas duas passagens DEVEM coincidir.

size e mtime_ns são conferidos antes e depois de cada passagem. Se mudarem entre preflight e normalização, run falha com InputValidationError de code input_drift e não prossegue para NCD. O hash do preflight é a identidade forte usada em retomadas.

### 11.2 Fórmulas

Para n objetos:

~~~text
pairs = n * (n - 1) / 2
matrix_bytes = n * n * 8
tree_workspace_bytes = matrix_bytes
checkpoint_bytes = ceil(pairs / pairs_per_shard) * 256
final_metadata_bytes = 1_048_576 + n * 4_096 + 8 * label_bytes_total
diagnostic_bytes = 0, se save_diagnostics=False
diagnostic_bytes = n * n * 32 + pairs * 96 + 2 * label_bytes_total, se save_diagnostics=True
estimated_artifact_bytes = normalized_bytes + 2 * matrix_bytes + checkpoint_bytes + final_metadata_bytes + diagnostic_bytes
required_free_disk_bytes = ceil(estimated_artifact_bytes * required_free_disk_factor)
working_memory_bytes = max(
    6 * max_serialized_chunk_bytes,
    workers * 2 * compression_chunk_bytes + pairs_per_shard * 24
)
~~~

normalized_bytes é exato porque o preflight executa o mesmo serializer em modo de contagem. O multiplicador de memória seis cobre DataFrame, strings Python, índices e buffers temporários; ele é um limite conservador, não uma previsão de RSS. Um único campo que exceda max_working_memory_bytes é rejeitado. keep_normalized altera somente a retenção final, não o pico de disco, pois os objetos sempre existem durante o NCD.

ResourceEstimate contém:

~~~python
class ResourceEstimate(BaseModel):
    csv_path: Path
    input_sha256: str
    input_size_bytes: int
    split: Literal["columns", "rows"]
    object_count: int
    pair_count: int
    effective_workers: int
    matrix_bytes: int
    tree_workspace_bytes: int
    normalized_bytes: int
    max_serialized_chunk_bytes: int
    estimated_working_memory_bytes: int
    estimated_final_metadata_bytes: int
    estimated_diagnostic_bytes: int
    estimated_artifact_bytes: int
    required_free_disk_bytes: int
    available_free_disk_bytes: int
    within_limits: bool
    violations: list[str]
~~~

estimate sempre retorna o modelo, inclusive quando há violações. run levanta ResourceLimitError se within_limits for falso. A exceção DEVE carregar o ResourceEstimate.

violations é ordenada por: max_objects, max_pairs, max_matrix_bytes, max_working_memory_bytes e free_disk. within_limits é verdadeiro somente se nenhuma violação existir. Erro de path, parsing ou encoding levanta sua exceção própria e não produz estimate parcial.

Os limites padrão fazem rows rejeitar datasets com mais de 1.000 linhas. Isso é intencional: o algoritmo exato não é apropriado para milhões de linhas.

### 11.3 Complexidade e capacidade real

Se S é a soma dos bytes dos objetos normalizados:

| Etapa | Tempo/I/O assintótico | RAM principal | Disco principal |
|---|---|---|---|
| preflight | O(tamanho do CSV) | O(chunk) | O(1) |
| normalização | O(tamanho do CSV) | O(chunk) | O(S) |
| C(x) | O(S) | O(chunk) | O(n) |
| pares NCD | O((n-1) * S) bytes comprimidos | O(workers * chunk + shard) | O(n²) |
| Neighbor Joining | O(n³) | O(n + bloco) | O(n²) adicional temporário |
| FastGreedy na árvore | dependente do igraph, sobre grafo O(n) | O(n) | O(n) |

Um CSV de vários gigabytes com dezenas ou centenas de colunas é um caso suportado porque n permanece moderado. O mesmo CSV em rows pode criar milhões de objetos e é rejeitado pelo preflight. Streaming e memmap evitam estouro de RAM, mas não eliminam o trabalho quadrático/cúbico. Essa distinção DEVE aparecer no README e em ResourceLimitError.

---

## 12. Diretório de execução, identidade e retomada

### 12.1 Identidade

config_hash é SHA-256 do JSON canônico com: split, delimiter, encoding, compressor, compression_level, num_clusters, keep_normalized, save_diagnostics, workers efetivos, csv_chunk_rows, compression_chunk_bytes, pairs_per_shard, pandas_materialization_limit_bytes e todos os ResourceLimits. Excluem-se csv_path, output_dir, progress, resume e reuse_completed. run_id são os 16 primeiros caracteres hexadecimais de SHA-256(input_sha256 + config_hash + schema_version). O manifesto armazena os hashes completos; o prefixo serve somente como nome legível do diretório.

Quando output_dir=None, o diretório é:

~~~text
./damicore-results/<run_id>/
~~~

Em Colab isso normalmente fica em /content/damicore-results. O README DEVE recomendar processamento e cache no disco local de /content e cópia final para o Drive; a biblioteca NÃO DEVE importar google.colab nem detectar o Drive.

### 12.2 Regras para diretório existente

- inexistente: criar;
- vazio: usar;
- manifesto compatível e status completed, com reuse_completed=True: verificar hashes e carregar;
- manifesto compatível e incompleto, com resume=True: verificar checkpoints e retomar;
- qualquer outra condição: levantar OutputDirectoryConflictError.

Compatível significa igualdade de input_sha256, config_hash e schema_version. Retomar uma execução incompleta exige também igualdade de damicore, Python, NumPy, igraph e versões build/runtime do zlib registradas no checkpoint. Uma execução completed com schema suportado pode ser carregada em runtime mais novo, pois nenhum algoritmo será retomado. A biblioteca NÃO DEVE apagar ou sobrescrever recursivamente diretórios incompatíveis.

Se um artefato de uma execução completed falhar na verificação, run e load_result levantam ArtifactValidationError; não há recomputação silenciosa. Se resume=False encontrar execução incompleta, a condição é conflito de saída. O espaço livre é medido no filesystem do output_dir ou, antes de sua criação, no ancestral existente mais próximo.

### 12.3 Estrutura final

~~~text
<run>/
├── manifest.json
├── report.json
├── distance.npy
├── labels.json
├── tree.json
├── tree.nwk
├── membership.csv
├── clusters.json
├── checkpoints/
│   ├── pipeline.json
│   ├── compressed-sizes.json
│   └── distance-shards.json
├── diagnostics/              # somente save_diagnostics=True
│   ├── distance.csv
│   └── ncd-pairs.csv
└── normalization/            # mantido somente keep_normalized=True
    ├── manifest.json
    └── objects/
~~~

Durante a execução, normalization existe sempre. Após sucesso ela é removida somente quando keep_normalized=False; essa remoção é limitada ao diretório gerenciado da execução e ocorre depois de validar todos os artefatos finais.

Todos os JSON usam UTF-8, indentação de duas posições, chaves ordenadas, allow_nan=False e LF final. Escritas de manifesto, checkpoint e resultados pequenos usam arquivo temporário no mesmo diretório, fsync e os.replace.

### 12.4 Estados

O manifesto usa exatamente:

~~~text
created -> preflighted -> normalizing -> distancing -> tree_building
        -> clusterizing -> verifying -> completed
~~~

failed e interrupted são estados recuperáveis alcançáveis a partir de qualquer etapa em execução. Uma falha registra failed_stage, error_type e error_message no report, mas não converte checkpoint incompleto em completo. Uma retomada válida sai de failed, interrupted ou do último estado não terminal. completed é o único sucesso terminal.

---

## 13. Manifesto de normalização

Schema obrigatório:

~~~json
{
  "schema_version": 1,
  "input": {
    "path": "/content/dataset.csv",
    "sha256": "...",
    "size_bytes": 1234,
    "delimiter": ",",
    "encoding": "utf-8",
    "split": "columns"
  },
  "objects": [
    {
      "object_id": "column_000001",
      "label": "sensor_a",
      "relative_path": "objects/column_000001.jsonl",
      "size_bytes": 456,
      "sha256": "..."
    }
  ]
}
~~~

relative_path DEVE ser relativo POSIX e não pode conter .., caminho absoluto ou symlink externo. Objetos ficam ordenados. O normalizador valida contagem, tamanho e SHA-256 antes de concluir.

API pública do pacote:

~~~python
def normalize_csv(
    csv_path: str | Path,
    output_dir: str | Path,
    *,
    config: NormalizationConfig | None = None,
) -> NormalizationResult: ...
~~~

NormalizationConfig é:

~~~python
class NormalizationConfig(BaseModel):
    split: Literal["columns", "rows"] = "columns"
    delimiter: str = ","
    encoding: str = "utf-8"
    chunk_rows: int = 50_000
    max_open_files: int = 64
~~~

NormalizationResult contém manifest_path, object_count, total_bytes e objects. A função exige output_dir inexistente ou vazio. O resultado total_bytes DEVE ser igual a normalized_bytes calculado no preflight.

---

## 14. Distância NCD

### 14.1 Definição

Para objetos x e y:

~~~text
NCD(x, y) = (C(xy) - min(C(x), C(y))) / max(C(x), C(y))
~~~

C é o tamanho em bytes da saída finalizada do compressor. xy é concatenação direta dos bytes canônicos de x seguidos pelos de y. Não há separador adicional. A ordem x depois y é determinada por i < j. O resultado NÃO DEVE ser truncado, arredondado, normalizado ou limitado ao intervalo 0..1.

zlib é o padrão, nível 6. Cada C(x), C(y) ou C(xy) usa uma instância nova de zlib.compressobj. gzip usa zlib.compressobj com wbits=31 e cabeçalho determinístico. O manifesto DEVE registrar zlib.ZLIB_VERSION e zlib.ZLIB_RUNTIME_VERSION. A identidade bit a bit é exigida para o mesmo fingerprint de runtime; o CI entre versões Python valida invariantes e contratos, não promete bytes iguais entre implementações diferentes do zlib.

O compressor recebe chunks de no máximo compression_chunk_bytes. C(xy) alimenta todos os chunks de x e depois todos os de y na mesma instância. xy nunca é materializado.

### 14.2 Cache e pares

- C(x) é calculado uma vez por objeto e persistido em compressed-sizes.json.
- Apenas o triângulo superior i < j é calculado.
- Cada valor é escrito em [i,j] e [j,i].
- A diagonal é 0.0.
- A matriz é float64 C-order em distance.npy.
- Células ainda não calculadas são NaN.

Se o denominador for zero, DistanceComputationError é levantado. Na prática, um stream de compressor finalizado deve produzir overhead positivo até para objeto vazio; o teste desse caso é obrigatório.

### 14.3 Sharding e paralelismo

Os pares são enumerados lexicograficamente por i e j e particionados em shards contíguos de pairs_per_shard. ProcessPoolExecutor usa multiprocessing.get_context("spawn").

Com workers > 1 os processos spawnados reimportam o módulo do chamador. Uma chamada em nível de módulo em script .py DEVE estar sob `if __name__ == "__main__":`; notebook e REPL já satisfazem a condição. A ausência da guarda mata o pool, e essa falha DEVE ser reportada como DistanceComputationError nomeando a guarda e a alternativa workers=1, nunca como BrokenProcessPool cru.

Cada worker:

1. recebe IDs, paths, tamanhos comprimidos e pares de um shard;
2. calcula somente seus pares em artefatos previamente validados pelo coordenador;
3. retorna três arrays contíguos ao coordenador: i int64, j int64 e ncd float64.

Somente o processo coordenador escreve no memmap e checkpoints. Depois de escrever e flushar todos os valores, ele valida finitude e simetria do shard e o marca como concluído atomicamente. Falha de worker cancela os shards pendentes e mantém o atual incompleto.

O progresso é atualizado por pares concluídos, usando tqdm.auto. progress=False desativa apenas a apresentação, nunca o checkpoint.

### 14.4 Verificação final

Antes de concluir a etapa, a biblioteca DEVE verificar por blocos:

- shape n por n;
- dtype float64;
- ausência de NaN e infinito;
- diagonal exatamente zero;
- simetria bit a bit;
- labels na mesma ordem do manifesto.

API pública:

~~~python
def compute_distance_matrix(
    normalization_manifest: str | Path,
    output_dir: str | Path,
    *,
    config: DistanceConfig | None = None,
    progress: ProgressCallback | None = None,
) -> DistanceResult: ...
~~~

DistanceResult contém matrix_path, labels_path, object_count, pair_count e timing. CSV da matriz e lista de pares são diagnósticos opcionais e nunca a fonte canônica.

DistanceConfig é:

~~~python
class DistanceConfig(BaseModel):
    compressor: Literal["zlib", "gzip"] = "zlib"
    compression_level: int = 6
    compression_chunk_bytes: int = 4_194_304
    workers: int | Literal["auto"] = "auto"
    pairs_per_shard: int = 10_000
    resume: bool = True
    save_diagnostics: bool = False
~~~

ProgressCallback é um protocolo callable com argumentos completed: int, total: int e message: str. O callback é chamado somente pelo coordenador.

---

## 15. Neighbor Joining

### 15.1 Entrada

tree-builder recebe distance.npy e labels.json, abre a matriz com numpy.load(..., mmap_mode="r", allow_pickle=False) e repete todas as validações essenciais. Labels devem ser únicos e ter mesmo tamanho da matriz.

### 15.2 Algoritmo normativo

Com r clusters ativos e somas R_i:

~~~text
Q(i,j) = (r - 2) * d(i,j) - R_i - R_j
delta = (R_i - R_j) / (r - 2)
L(i,u) = 0.5 * (d(i,j) + delta)
L(j,u) = d(i,j) - L(i,u)
d(u,k) = 0.5 * (d(i,k) + d(j,k) - d(i,j))
~~~

Enquanto r > 2, selecionar o menor Q fora da diagonal. A varredura de blocos segue a ordem dos IDs ativos.

Dois valores de Q cujo módulo da diferença não excede `1e-9 * max(1, |Q_min|)` constituem um empate, e o empate é resolvido pelo menor par lexicográfico de IDs ativos. A tolerância é relativa e normativa: comparação por igualdade float64 exata NÃO é aceitável aqui. Cada d(i,j) é razão entre tamanhos comprimidos inteiros, de modo que a precisão significativa do dado se esgota muito antes do 16º dígito; além disso, os empates que a regra existe para resolver são exatamente os que o arredondamento destrói. Com r = 4, por exemplo, Q(i,j) e Q(k,l) de pares complementares são algebricamente iguais para qualquer matriz, e ainda assim float64 só detecta essa igualdade em cerca de 60% dos casos — nenhuma estratégia de somatório corrige isso, porque o cancelamento ocorre na subtração final e não nas somas.

Ao final, criar um root com os dois clusters restantes e comprimentos iguais a metade da distância entre eles.

Após unir i e j em u, o slot de i passa a representar u e o slot de j fica inativo.

As somas R são recalculadas a partir da matriz no início de cada iteração:

~~~text
R_i = soma de d(i,k) para todos os k ativos diferentes de i
~~~

A forma incremental `R'_k = R_k - d(k,i) - d(k,j) + d(k,u)` NÃO deve ser usada: ela acumula erro a cada união, e o custo do recálculo é O(r²), já pago pela varredura de Q, portanto não altera a complexidade.

A diagonal do slot reutilizado volta a zero. A lista de ativos é mantida ordenada por ID estável para a resolução de empates.

Comprimentos negativos são preservados no tree.json e Newick; não serão truncados. Valores não finitos são proibidos.

### 15.3 Estratégia de memória

- O distance.npy original é somente leitura.
- Um tree-work.npy temporário, n por n float64, recebe a cópia de trabalho.
- Slots removidos são reutilizados para clusters internos; não se cria matriz 2n por 2n.
- Q é avaliada em blocos e nunca materializada inteira.
- Somas de linhas são mantidas em vetor O(n) e atualizadas a cada junção.
- RAM adicional permanece O(n + tamanho_do_bloco); disco adicional é O(n²).
- tree-work.npy é removido somente após validar tree.json e tree.nwk.

O tempo continua O(n³). A documentação NÃO DEVE prometer escala linear ou tratar memmap como redução de complexidade computacional.

### 15.4 IDs e artefato

Folhas usam object_id. Nós internos usam nj_000001, nj_000002, ... em ordem de criação; a raiz usa nj_root. tree.json:

~~~json
{
  "schema_version": 1,
  "root_id": "nj_root",
  "nodes": [
    {"id": "column_000001", "kind": "leaf", "label": "sensor_a"},
    {"id": "nj_000001", "kind": "internal", "label": null}
  ],
  "edges": [
    {"source": "nj_000001", "target": "column_000001", "length": 0.123}
  ]
}
~~~

Nodes seguem ordem folhas, internos e raiz. Edges são ordenadas por source e target. O Newick usa IDs, escapa conforme o formato, imprime float com repr Python e termina em ;.

API pública:

~~~python
def build_tree(
    matrix_path: str | Path,
    labels_path: str | Path,
    output_dir: str | Path,
    *,
    config: TreeBuildConfig | None = None,
) -> TreeBuildResult: ...


def neighbor_joining(
    matrix: numpy.ndarray,
    labels: Sequence[str],
) -> Tree: ...
~~~

A API in-memory é destinada a matrizes pequenas e copia a entrada. A API por paths é a usada pelo orquestrador.

TreeBuildConfig é:

~~~python
class TreeBuildConfig(BaseModel):
    q_block_size: int = 512
~~~

q_block_size deve ser positivo e controla somente RAM e velocidade; não altera o resultado.

---

## 16. Clusterização FastGreedy

### 16.1 Conversão em grafo não enraizado

clusterizer lê tree.json; não importa tree-builder. Se a raiz tiver exatamente dois filhos, ela é removida e os filhos são conectados por uma aresta cujo comprimento é a soma dos dois comprimentos. Qualquer outra topologia de raiz é TreeFormatError.

Todos os nós internos e folhas participam da detecção de comunidades. Apenas folhas aparecem no resultado público.

Para cada comprimento l:

~~~text
w_bruto = 1 / l
desvio  = desvio-padrão populacional de w_bruto sobre todas as arestas
weight  = 1 + (w_bruto - min(w_bruto)) / desvio
~~~

O deslocamento é aplicado sobre os recíprocos, não sobre os comprimentos. Isso mantém weight >= 1, dá à branch negativa o menor peso em vez do maior, e limita a razão entre pesos à dispersão dos dados. A modularidade é uma soma ponderada, então um peso ilimitado decidiria a partição sozinho: como o recíproco cresce sem limite quando o comprimento se aproxima de zero, deslocar do lado dos comprimentos deixaria a partição ser escolhida pela menor branch, e não pela estrutura do grafo. O resultado é invariante a reescalar todos os comprimentos.

Comprimento exatamente zero, e comprimento cujo recíproco não é finito, são TreeFormatError: qualquer reparo reintroduziria o peso ilimitado que a fórmula existe para evitar. Se o desvio for zero, todos os comprimentos são iguais e todo weight é 1.

### 16.2 Comunidades

Usar igraph.Graph.community_fastgreedy(weights="weight").

- num_clusters=None: dendrogram.as_clustering() no corte de maior modularidade do igraph.
- num_clusters=k: dendrogram.as_clustering(n=k).

Comunidades sem folhas são descartadas da saída de dados, mas contam em community_count e no parâmetro num_clusters. As restantes são reidentificadas como 0..cluster_count-1 ordenando-as pela tupla dos object_ids de folhas em ordem lexicográfica. Em seguida, as folhas em membership voltam à ordem original de labels.json. Isso torna IDs determinísticos e independentes dos IDs internos do igraph.

Validações finais:

- cada folha aparece exatamente uma vez;
- nenhum object_id desconhecido aparece;
- nenhum cluster de saída é vazio;
- IDs de cluster são inteiros contíguos começando em zero.

API pública:

~~~python
def cluster_tree(
    tree_path: str | Path,
    output_dir: str | Path,
    *,
    config: ClusterConfig | None = None,
) -> ClusterResult: ...
~~~

ClusterConfig é:

~~~python
class ClusterConfig(BaseModel):
    num_clusters: int | None = None
~~~

ClusterResult contém membership_path, clusters_path, community_count, cluster_count e modularity.

---

## 17. Orquestração

damicore.run DEVE executar estas transições:

1. validar argumentos e construir configuração imutável;
2. executar preflight e aplicar limites;
3. criar ou validar o diretório de execução;
4. normalizar;
5. calcular a matriz;
6. construir a árvore;
7. clusterizar;
8. verificar todos os invariantes cruzados;
9. remover objetos normalizados se configurado e registrar cleanup_completed;
10. escrever report e manifest como completed, por último;
11. retornar DamicoreResult carregado dos artefatos finais.

Cada estágio recebe apenas caminhos já validados e produz uma receipt no checkpoints/pipeline.json com started_at, finished_at, status, versões, entradas, saídas, hashes e métricas. Um estágio é skipped somente ao retomar e depois de revalidar a receipt e os hashes de saída.

A verificação cruzada da etapa 8 compara obrigatoriamente:

- object_ids e labels do manifesto de normalização com labels.json;
- tamanho de labels.json com shape da matriz;
- object_ids de labels.json com as folhas de tree.json;
- folhas de tree.json com as linhas de membership.csv;
- membership.csv com clusters.json nos dois sentidos;
- cluster_count com IDs contíguos e community_count com num_clusters solicitado, quando definido;
- hashes, tamanhos e paths de todos os artefatos declarados.

Não há fallback entre algoritmos. Uma falha de etapa encerra a chamada com exceção tipada e preserva o diretório para diagnóstico ou retomada.

Cada API de estágio possui uma allowlist de paths. Ela pode escrever somente seus artefatos e temporários com prefixo próprio, recusa substituir saída concluída sem receipt compatível e ignora arquivos não pertencentes ao estágio. O normalizador recebe especificamente o diretório <run>/normalization; os outros três recebem <run>. Nenhum estágio remove arquivo pertencente a outro.

---

## 18. Schemas dos artefatos finais

### 18.1 labels.json

~~~json
{
  "schema_version": 1,
  "object_ids": ["column_000001", "column_000002"],
  "labels": ["sensor_a", "sensor_b"]
}
~~~

### 18.2 membership.csv

~~~csv
object_id,label,cluster
column_000001,sensor_a,0
column_000002,sensor_b,1
~~~

Escrita UTF-8, delimitador vírgula, quoting mínimo e LF. Labels com vírgula, aspas ou newline são escapados pelo módulo csv.

### 18.3 clusters.json

~~~json
{
  "schema_version": 1,
  "clusters": [
    {
      "cluster": 0,
      "object_ids": ["column_000001"],
      "labels": ["sensor_a"]
    }
  ]
}
~~~

### 18.4 Diagnósticos opcionais

distance.csv usa a primeira célula de cabeçalho object_id, IDs nas colunas e na primeira coluna, e valores float64 com repr Python. ncd-pairs.csv usa as colunas i, j, object_id_x, object_id_y e ncd, em ordem lexicográfica de pares. Ambos são produzidos por streaming depois da validação de distance.npy; não são carregados em DataFrame nem usados por etapas seguintes.

### 18.5 manifest.json

Campos obrigatórios:

- schema_version, damicore_version, run_id e status;
- created_at, updated_at e completed_at em UTC ISO 8601;
- input com path resolvido, size, mtime_ns e SHA-256;
- config completo e config_hash;
- objects com object_id, label, size_bytes e SHA-256 copiados do manifesto de normalização, mesmo quando os arquivos normalizados forem removidos;
- versões Python, plataforma e dependências runtime;
- estimate;
- stages e receipts;
- artifacts com path relativo, size e SHA-256;
- warnings.

Paths absolutos aparecem somente para input e run_dir; artefatos internos são relativos. Timestamps e paths não participam do config_hash.

### 18.6 report.json

Campos obrigatórios:

- status e failed_stage quando aplicável;
- contagens de objetos, pares, comunidades do grafo e clusters de folhas;
- segundos por estágio e total;
- workers efetivos, chunks e shards;
- matriz e disco em bytes;
- pico de RSS quando a plataforma oferecer resource.getrusage, senão null;
- modularidade;
- NCD mínimo, máximo e quantidade fora de 0..1;
- quantidade de branches negativas;
- avisos e erro tipado;
- resultado de cada verificação final.

---

## 19. Falhas públicas

Na API de alto nível, todas as exceções derivam de DamicoreError:

~~~text
DamicoreError
├── ConfigurationError
├── InputValidationError
│   └── CSVFormatError
├── ResourceLimitError
├── OutputDirectoryConflictError
├── CheckpointMismatchError
├── NormalizationError
├── CompressionError
├── DistanceComputationError
├── DistanceMatrixValidationError
├── TreeBuildError
│   └── TreeFormatError
├── ClusterizationError
├── ArtifactValidationError
└── MaterializationError
~~~

Os pacotes independentes usam suas próprias bases NormalizerError, DistanceError, TreeBuilderError e ClusterizerError. Eles não importam damicore. O orquestrador captura essas falhas e levanta a subclasse DamicoreError correspondente usando encadeamento explícito. Assim, usuários do pacote agregado recebem uma hierarquia única sem violar a direção de dependências.

Cada exceção pública DEVE possuir code estável em snake_case, message acionável e context sem dados volumosos. O code padrão é o nome completo da classe convertido para snake_case, incluindo o sufixo error: CSVFormatError resulta em csv_format_error. input_drift é o único code especializado da versão 0.1. Exceções internas são encadeadas com raise ... from original. A CLI traduz códigos em exit status:

| Exit | Categoria |
|---:|---|
| 0 | sucesso |
| 2 | configuração, input ou CSV |
| 3 | limite de recursos |
| 4 | falha algorítmica ou artefato inválido |
| 5 | conflito de saída ou checkpoint |
| 130 | interrupção pelo usuário |

KeyboardInterrupt fecha workers, flushes seguros e reporta a etapa como interrompida sem imprimir traceback pela CLI. Na API Python, KeyboardInterrupt é propagado.

---

## 20. CLI

Implementar com argparse da biblioteca padrão:

~~~text
damicore estimate CSV [--split columns|rows] [--delimiter CHAR]
                         [--encoding NAME] [--workers N]
                         [--max-objects N] [--max-pairs N]
                         [--max-matrix-bytes N] [--max-working-memory-bytes N]
                         [--keep-normalized] [--save-diagnostics] [--json]

damicore run CSV [--split columns|rows] [--delimiter CHAR]
                 [--encoding NAME] [--compressor zlib|gzip]
                 [--compression-level 0..9] [--clusters N]
                 [--output-dir PATH] [--workers N]
                 [--max-objects N] [--max-pairs N]
                 [--max-matrix-bytes N] [--max-working-memory-bytes N]
                 [--keep-normalized] [--save-diagnostics]
                 [--no-progress]
~~~

A CLI chama estimate/run; não duplica lógica. Saída humana vai para stderr durante progresso e resumo; --json escreve um único JSON em stdout. Caminhos dos artefatos são impressos no sucesso.

---

## 21. Segurança e integridade local

- Somente caminhos locais regulares são aceitos como entrada.
- O conteúdo do CSV é dado, nunca instrução.
- numpy.load usa allow_pickle=False.
- JSON é validado por schema Pydantic antes de uso.
- Paths relativos de manifesto são resolvidos e confirmados dentro do run_dir.
- Symlinks que escapem do run_dir são rejeitados.
- Arquivos internos têm nomes gerados, nunca derivados diretamente de label.
- O subprocesso de compressor externo é proibido; zlib/gzip são in-process.
- Não há rede, telemetria remota ou upload automático.
- Logs não incluem conteúdo de células; somente paths, hashes, tamanhos e contagens.
- Erros não devem despejar linhas completas do CSV.

---

## 22. DX para Jupyter e Google Colab

O quickstart obrigatório tem somente:

1. %pip install damicore;
2. upload ou mount feito pelo próprio usuário;
3. variável csv_path;
4. damicore.estimate para inspeção opcional;
5. damicore.run;
6. visualização de membership, clusters, árvore e head da matriz;
7. result.save para destino final opcional.

Exemplo avançado:

~~~python
from damicore import ExecutionConfig, ResourceLimits, estimate, run

csv_path = "/content/dataset.csv"

preview = estimate(csv_path, split="columns")
display(preview.model_dump())

result = run(
    csv_path,
    split="columns",
    delimiter=",",
    encoding="utf-8",
    compressor="zlib",
    compression_level=6,
    output_dir="/content/damicore-run",
    execution=ExecutionConfig(
        workers="auto",
        limits=ResourceLimits(),
    ),
)

display(result.membership)
display(result.distance_matrix.head(10))
~~~

O notebook NÃO DEVE instalar apt, clonar o repositório, alterar sys.path, usar shell para chamar cada estágio ou expor synthetic_data ao usuário.

---

## 23. Dados sintéticos: uso estritamente interno

synthetic_data existe somente para testes, benchmarks e smoke tests de wheel. API interna:

~~~python
def generate_csv(
    path: str | Path,
    *,
    rows: int,
    columns: int,
    clusters: int,
    seed: int,
    delimiter: str = ",",
) -> Path: ...
~~~

O gerador DEVE:

- ser determinístico por seed;
- produzir CSV válido UTF-8;
- gerar grupos controláveis de colunas e de linhas;
- aceitar volume total para stress sem montar tudo em RAM;
- registrar parâmetros em retorno de teste, não no CSV do usuário;
- não ser importado por código runtime;
- não aparecer no quickstart público.

Fixture e2e padrão: 24 linhas, 8 colunas, 2 clusters, seed 42. Testes de correção algorítmica usam fixtures mínimas construídas no próprio teste; não usam corpus legado.

---

## 24. Estratégia de testes

### 24.1 Unitários e propriedades

Normalizer:

- cabeçalhos vazios/duplicados, delimitadores, encodings e CSV malformado;
- strings vazias, aspas, vírgulas, Unicode e newline em célula;
- bytes canônicos iguais entre chunks diferentes;
- ordem, IDs, hashes e manifestos;
- memória não proporcional ao CSV inteiro.

Distance:

- tamanhos do compressor contra implementação direta pequena;
- fórmula NCD sem clamp;
- diagonal, simetria, dtype e ordem;
- serial igual a paralelo bit a bit;
- retomada após cada boundary de shard;
- corrupção de objeto, checkpoint e matriz;
- propriedades Hypothesis para pares aleatórios pequenos.

Tree:

- matrizes conhecidas com topologia esperada;
- fórmula de branch lengths;
- empates determinísticos;
- comprimentos negativos preservados;
- matriz não finita, assimétrica ou com diagonal inválida;
- API memmap igual à API in-memory;
- todas as folhas exatamente uma vez.

Clusterizer:

- remoção correta da raiz de grau dois;
- pesos limitados e partição estável para comprimento próximo de zero ou negativo;
- corte ótimo e corte k;
- IDs determinísticos;
- comunidades internas sem folhas;
- membership completa e exclusiva.

### 24.2 Contrato e integração

- schemas JSON são compatíveis entre produtor e consumidor;
- nenhum pacote de estágio importa outro;
- cada wheel instala e roda seus testes de smoke isoladamente;
- instalar damicore traz exatamente os quatro estágios;
- pyproject publicado não contém path/workspace source;
- execução completa em columns e rows;
- result.save e load_result;
- diretório concluído reutilizado;
- execução interrompida retomada;
- erro não gera falso completed.

### 24.3 Notebook

O CI constrói wheels, cria ambiente limpo, instala o wheel damicore, executa notebooks/colab_quickstart.ipynb via nbclient com CSV sintético e valida todas as células. O notebook não pode depender do checkout.

### 24.4 Stress e desempenho

Dois benchmarks obrigatórios, ambos executados por benchmark.yml. O primeiro:

- CSV sintético de 2 GiB, 64 colunas, split=columns;
- execução de normalização em runner Linux com 8 GiB RAM;
- pico RSS durante normalização <=1,5 GiB;
- nenhuma leitura única maior que csv_chunk_rows;
- matriz aberta por memmap e to_pandas bloqueado conforme limite;
- execução DEVE interromper após a normalização, que é a última etapa coberta pelo teto.

O segundo mede NCD e Neighbor Joining para n=100, 250, 500 e 1.000 e registra tempo, disco, RSS e pares/segundo.

O benchmark de 2 GiB é gate de release: release.yml o executa no commit da tag e o estouro do teto reprova a publicação. O segundo não tem threshold de tempo portável na versão 0.1 e roda por workflow_dispatch; regressão acima de 25% contra a mediana dos três últimos runs no mesmo runner gera alerta, não bloqueio automático. Ambos publicam as medições como artefato do run, que é a única série disponível para essa comparação, e as escrevem antes de reprovar, para que os números da falha sobrevivam.

### 24.5 Cobertura

- cobertura total mínima: 90%;
- módulos serializer.py, ncd.py, neighbor_joining.py e fastgreedy.py: 95%;
- cobertura não substitui invariantes nem fixtures matemáticas.

---

## 25. CI, build e publicação

### 25.1 ci.yml — bloqueante em PR

Jobs:

1. ruff check .;
2. ruff format --check .;
3. pyright;
4. pytest unit/contract/e2e com cobertura em Python 3.11, 3.12, 3.13 e 3.14 no Linux;
5. lane de versões mínimas compatíveis em Python 3.11;
6. teste de arquitetura de imports;
7. notebook smoke usando wheels.

### 25.2 build.yml — bloqueante

- construir sdist e wheel de cada um dos cinco pacotes publicados;
- twine check em todos;
- inspecionar metadata e conteúdo;
- instalar cada wheel em ambiente limpo;
- executar import e smoke da API pública;
- instalar apenas damicore e executar e2e;
- construir novamente e comparar conteúdo lógico do wheel, ignorando metadados ZIP inevitáveis.

### 25.3 Atualização de dependências

Não existe lane agendada. As atualizações chegam pelo Dependabot, configurado em .github/dependabot.yml para os ecossistemas uv e github-actions:

- alertas e correções de segurança são disparados pela publicação do advisory, não por um intervalo;
- cada atualização chega como pull request e passa pelos mesmos gates bloqueantes de 25.1 e 25.2, incluindo pip-audit, de modo que a falha é atribuída a um bump específico;
- o lock NÃO DEVE ser atualizado automaticamente no branch principal; o merge é decisão humana;
- as faixas declaradas nos pacotes publicados são contrato da seção 8.2. Um pull request que as altere é reprovado pelo teste de arquitetura, não mergeado.

### 25.4 release.yml

Disparo por tag vX.Y.Z. Ordem:

1. confirmar que versões dos cinco pacotes e tag são iguais;
2. executar CI e build do commit da tag;
3. publicar primeiro no TestPyPI por Trusted Publishing;
4. instalar do TestPyPI em ambiente limpo e executar smoke;
5. publicar no PyPI por Trusted Publishing;
6. criar GitHub Release com changelog e hashes.

Tokens PyPI persistentes NÃO DEVEM ser armazenados. Artefatos publicados devem ser exatamente os aprovados pelo job de build, sem rebuild entre TestPyPI e PyPI.

O commit da tag é a definição de pronto da versão. Nenhum critério desta especificação é dado por cumprido por inspeção informal: o que reprova qualquer lane de 24.4, 25.1, 25.2 ou deste job não é publicado.

---

## 26. Versionamento e compatibilidade

- Os cinco pacotes publicados usam a mesma versão.
- Durante 0.x, mudança incompatível incrementa minor; correção compatível incrementa patch.
- A partir de 1.0, SemVer padrão.
- Símbolos em __all__, assinaturas, schemas e nomes de artefato são API pública.
- Mudança incompatível em schema exige novo schema_version e leitor compatível com ao menos a versão anterior.
- Remoção de API pública requer aviso DeprecationWarning por ao menos uma minor antes da remoção.
- O uv.lock é atualizado somente por PR com CI completo.

---

## 27. Observabilidade e logs

Usar logging da biblioteca padrão com logger por pacote. Bibliotecas NÃO configuram handler global e NÃO chamam basicConfig. O orquestrador e a CLI configuram apresentação somente em seus entry points.

Eventos mínimos:

- run_started, preflight_completed;
- stage_started, stage_completed, stage_failed;
- shard_completed;
- resume_started, artifact_reused;
- verification_completed;
- run_completed, run_failed.

Cada evento inclui run_id, stage e métricas escalares. Conteúdo do CSV e dos objetos nunca é logado. tqdm e logging não podem corromper stdout JSON da CLI.

---

## 28. Rastreabilidade de decisões

| Objetivo | Decisão | Enforcement | Evidência |
|---|---|---|---|
| CSV de gigabytes | chunks + escrita progressiva | config e normalizer | teste de 2 GiB/RSS |
| evitar estouro quadrático | preflight e limites explícitos | ResourceLimitError | testes de boundary |
| matriz grande | float64 .npy memmap | MatrixView e validators | teste sem materialização |
| NCD correta | fórmula exata, sem clamp | ncd.py | fixtures e Hypothesis |
| reprodutibilidade | bytes canônicos, hashes, tie-break | schemas e algoritmos | serial/paralelo idênticos |
| recuperação | shards e receipts atômicos | state machine | fault-injection |
| libs independentes | nenhum import lateral | teste AST | instalação de wheels isolados |
| DX Colab | uma API, tqdm.auto, sem apt | notebook oficial | nbclient em wheel limpo |
| resultado confiável | verificação cruzada antes de completed | pipeline | testes de corrupção |
| supply chain simples | cinco deps runtime, lock e audit | pyproject/uv.lock/CI | build e pip-audit |

---

## 29. Decisões conscientemente adiadas

As decisões abaixo não estão indefinidas; estão explicitamente fora da versão 0.1:

| Tema | Decisão atual | Condição objetiva para reabrir |
|---|---|---|
| Aproximação | não implementar | demanda validada para rows >1.000 aceitando erro mensurável e API separada |
| Dask/Ray | não usar | benchmark provar que paralelismo local é o gargalo dominante e houver ambiente distribuído alvo |
| PyArrow/Polars | não usar | benchmark reproduzível demonstrar redução material de RSS/tempo sem piorar instalação Colab |
| GPU | não usar | existir algoritmo e workload com ganho comprovado, não somente disponibilidade de GPU |
| Novo compressor | não usar | caso científico exigir e houver implementação portátil/reprodutível |
| DataFrame/stream como input | não aceitar | contrato de CSV estabilizado e demanda justificar nova API sem ambiguidade de fingerprint |
| Formato Parquet | não usar | necessidade de I/O tabular pós-processamento justificar dependência adicional |
| Serviço remoto | não construir | requisitos multiusuário, isolamento e operação surgirem de produto real |

Até uma condição ser satisfeita e uma decisão versionada ser aprovada, a implementação DEVE seguir a decisão atual.
