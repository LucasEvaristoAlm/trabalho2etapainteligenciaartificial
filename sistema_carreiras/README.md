# Sistema Especialista Inteligente para Mapeamento, Compatibilidade e Trilha de Carreira em TI

Projeto desenvolvido para a disciplina de **Inteligencia Artificial** com o objetivo de construir
um sistema especialista capaz de mapear o perfil de um usuario, calcular compatibilidade com 10
areas da Tecnologia da Informacao e gerar trilhas de carreira e planos de desenvolvimento personalizados.

---

## Objetivo

Auxiliar estudantes e profissionais de tecnologia a identificar a area mais alinhada ao seu perfil
por meio de um **motor de inferencia baseado em regras com pontuacao ponderada e penalidades**.
O sistema avalia respostas fornecidas em um questionario estruturado (escala Likert 1-5) e produz:

- Ranking de compatibilidade com as 10 trilhas de carreira.
- Justificativa explicavel citando as perguntas mais determinantes.
- Deteccao de empate tecnico e perfil hibrido.
- Diagnostico de gaps tecnicos e percentual de prontidao para o nivel Junior.
- Plano de estudos personalizado com certificacoes, tecnologias e projeto para portfolio.

---

## Arquitetura do Sistema

```
+-------------------------------+
|   regras_carreiras.json        |  <- Base de conhecimento declarativa (UNICA fonte de verdade)
|  perguntas | skills | trilhas  |
|  pesos | roadmaps | conflitos  |
+---------------+---------------+
                |
     carregado por st.cache_data
                |
     +----------v----------+
     |      motor.py        |
     | calcular_compatibili-|
     | dade()               |
     | - normaliza respostas|  c = (resp - 3) / 2
     | - aplica pesos       |  contrib = c * peso
     | - aplica penalidades |  pen = penalidade * maximo
     | - gera justificativa |
     +----------+----------+
                |
     +----------v----------+
     |     roadmap.py       |
     | analisar_gaps()      |
     | calcular_prontidao() |
     | gerar_roadmap()      |
     | formatar_markdown()  |
     +----------+----------+
                |
     +----------v----------+
     |       app.py         |  <- Streamlit: wizard 4 etapas
     | Passo 1: Perfil      |
     | Passo 2: Afinidades  |
     | Passo 3: Objetivos   |
     | Passo 4: Resultados  |
     |  - metricas Top 3    |
     |  - radar + barras    |
     |  - gaps + roadmap    |
     +---------------------+
```

---

## Formula de Pontuacao e Penalidades

### 1. Normalizacao da Resposta Likert

Cada resposta `r` (de 1 a 5) e convertida para a escala `[-1.0, +1.0]`:

```
c = (r - 3) / 2
```

| Resposta | c      |
|----------|--------|
| 1        | -1.0   |
| 2        | -0.5   |
| 3        |  0.0   |
| 4        | +0.5   |
| 5        | +1.0   |

### 2. Calculo da Pontuacao Bruta

Para cada pergunta respondida que possui peso na trilha:

```
contribuicao(q) = c(q) * peso(q)
bruto           = SOMA[ contribuicao(q) para todas as q respondidas ]
maximo          = SOMA[ |peso(q)| para todas as q respondidas ]
```

### 3. Aplicacao de Penalidades por Conflito

Para cada regra de conflito cujas condicoes (conjuncao AND) sao satisfeitas:

```
penalidade_acumulada += penalidade_regra * maximo
```

### 4. Percentual Final

```
pct = max(0, (bruto - penalidade_acumulada) / maximo) * 100
pct = min(100, pct)                    # limitado a [0, 100]
pct = round(pct, 1)                    # 1 casa decimal
Se maximo == 0: pct = 0.0             # sem perguntas respondidas com peso
```

### Exemplo Numerico Completo

Perfil DevOps simulado respondendo 3 das perguntas com peso na trilha `devops_sre`:

| Pergunta                            | Resposta (r) | c      | Peso   | Contribuicao |
|-------------------------------------|:------------:|:------:|:------:|:------------:|
| afinidade_automacao                 | 5            | +1.0   | +0.95  | +0.950       |
| afinidade_infraestrutura_servidores | 5            | +1.0   | +0.90  | +0.900       |
| afinidade_design_visual             | 1            | -1.0   | -0.80  | +0.800       |

```
bruto   = 0.95 + 0.90 + 0.80 = 2.65
maximo  = |0.95| + |0.90| + |-0.80| = 2.65

Nenhuma regra de conflito acionada -> penalidade_acumulada = 0

pct = max(0, (2.65 - 0) / 2.65) * 100 = 100.0%
```

Se adicionarmos `afinidade_design_visual = 5` (conflito com ciberseguranca):

```
Regra de conflito acionada: penalidade = 0.20
penalidade_acumulada = 0.20 * maximo

bruto   = -0.95   (design_visual com peso -0.80 e c=+1.0)
maximo  = 0.80
pct antes da penalidade = max(0, (-0.95 - 0.20 * 0.80) / 0.80) * 100 = 0.0%  (clamped)
```

---

## Estrutura do Repositorio

```
sistema_carreiras/
├── regras_carreiras.json       <- Base de conhecimento (EDITAVEL pelo usuario)
├── motor.py                    <- Motor de inferencia e pontuacao ponderada
├── roadmap.py                  <- Gerador de gaps e planos de estudo
├── app.py                      <- Interface Streamlit (wizard 4 passos)
├── tests/
│   └── test_edge_cases.py      <- 16 testes automatizados com pytest
├── requirements.txt            <- Dependencias: streamlit, pandas, plotly, pytest
└── README.md                   <- Esta documentacao
validar_base.py                 <- Script de validacao estrutural do JSON
```

---

## Instalacao e Execucao

### Pre-requisitos

- Python 3.10 ou superior

### Passos

```bash
# Acesse o diretorio do projeto
cd sistema_carreiras

# Crie e ative ambiente virtual (recomendado)
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
# .venv\Scripts\activate         # Windows

# Instale as dependencias
pip install -r requirements.txt

# Valide a integridade da base de conhecimento
python ../validar_base.py

# Execute a aplicacao
streamlit run app.py
```

A interface estara disponivel em `http://localhost:8501`.

### Executar os Testes

```bash
# Na raiz do projeto (fora de sistema_carreiras/)
python -m pytest sistema_carreiras/tests/ -v
```

---

## Como Adicionar uma Nova Trilha ou Pergunta (Apenas Editando o JSON)

O sistema e **100% orientado a dados**. Nenhum codigo Python precisa ser alterado.

### Adicionar uma Nova Pergunta de Afinidade

Abra `regras_carreiras.json` e adicione um novo objeto na lista `"perguntas"`:

```json
{
  "id": "afinidade_blockchain",
  "texto": "Tenho interesse em tecnologias de ledger distribuido e contratos inteligentes.",
  "passo": 2,
  "categoria": "blockchain"
}
```

Depois, referencie o novo `id` nos `"pesos"` das trilhas relevantes.

### Adicionar uma Nova Trilha

1. Adicione uma entrada em `"trilhas"` com o novo `id` em snake_case:

```json
"blockchain_web3": {
  "nome": "Desenvolvimento Blockchain & Web3",
  "descricao": "Criacao de contratos inteligentes e aplicacoes descentralizadas. ...",
  "pesos": {
    "afinidade_blockchain": 0.95,
    "afinidade_logica_algoritmos": 0.80,
    "afinidade_design_visual": -0.50
  },
  "skills_junior": {
    "python": 2,
    "git": 2,
    "sql": 1
  },
  "roadmap": {
    "tecnologias": ["Fundamentos de Criptografia", "Solidity e EVM", "Hardhat / Foundry"],
    "certificacoes": ["Certified Blockchain Developer - Ethereum (CBDE)"],
    "projeto": "Contrato inteligente de leilao descentralizado com testes no Hardhat."
  }
}
```

2. Opcionalmente adicione regras de conflito referenciando o novo `id` em `"regras_conflito"`.
3. Execute `python validar_base.py` para garantir a integridade antes de rodar a aplicacao.

### Adicionar uma Nova Skill ao Catalogo

Adicione uma entrada em `"skills_catalogo"`:

```json
"solidity": "Solidity e Contratos Inteligentes"
```

Depois referencie `"solidity"` em `skills_junior` da trilha desejada.

---

## Resultados dos Testes de Casos Limite

Suíte completa em `sistema_carreiras/tests/test_edge_cases.py` — **16/16 testes aprovados**.

| # | Cenario | Validacao | Resultado |
|---|---------|-----------|-----------|
| 1 | **Perfil dados + web** (matematica=5, dados=5, web=5) | Top 3 contem trilha de dados E desenvolvimento; empate tecnico detectado | PASSOU |
| 2 | **Tudo 3 (neutro)** | Todas as trilhas com pct <= 10% e bruto == 0.0; sem excecoes | PASSOU |
| 3 | **Tudo 5 (maximo)** | Nenhuma trilha ultrapassa 100% | PASSOU |
| 4 | **Tudo 1 (minimo)** | Nenhuma trilha com pct abaixo de 0% | PASSOU |
| 5 | **Perfil conflitante** (design=5, logica=1, infra=1) | `frontend_ux` lidera; penalidades registradas em `ciberseguranca` e `devops_sre` | PASSOU |
| 6 | **Respostas parciais** (9 de 18 perguntas) | 10 trilhas retornadas sem excecao; perguntas omissas ignoradas | PASSOU |
| 7 | **Valor invalido** (fora da faixa, fracionario, tipo incorreto ou booleano) | `ValueError` para respostas que nao sejam inteiros entre 1 e 5 | PASSOU (8 parametrizados) |
| 8 | **Atende todos skills junior** | `gaps == []` e `prontidao == 100.0%` | PASSOU |
| 9 | **Integridade da base** | 10 trilhas do contrato; pesos em [-1,1]; IDs de perguntas e skills validos; roadmaps completos | PASSOU |

---

## Limitacoes Conhecidas

1. **Escala Likert sem granularidade fracional**: o usuario avalia com valores inteiros de 1 a 5;
   respostas mais nuancadas (ex.: 3.5) nao sao suportadas sem alterar o JSON e o motor.

2. **Skills de autoavaliacao sujeitas a vies de percepcao**: a acuracia do diagnostico de gaps
   depende da honestidade e calibragem do usuario ao autoavaliar seu nivel tecnico.

3. **Base de conhecimento estatica**: os pesos, perguntas e roadmaps refletem o estado do
   mercado no momento de criacao. Novos frameworks ou tendencias exigem atualizacao manual do JSON.

4. **Sem persistencia de sessao**: ao fechar o navegador ou recarregar a pagina, o estado do
   wizard e zerado (limitacao do Streamlit sem backend de autenticacao).

5. **Mercado regional nao considerado**: os pesos e certificacoes refletem tendencias globais;
   demandas especificas de mercados locais podem divergir do modelo atual.

6. **Sem aprendizado adaptativo**: o sistema nao aprende com os dados coletados; a base de
   regras nao e atualizada automaticamente a partir do historico de usuarios.

---

## Sugestoes de Mensagens de Commit por Fase

```
feat: estrutura inicial do projeto, requirements e .gitignore

docs: remocao de emojis da documentacao README

feat(base): criacao de regras_carreiras.json com perguntas, skills e trilhas

feat(base): conclusao dos pesos, skills_junior, roadmaps e regras de conflito

feat(motor): implementacao do motor de inferencia ponderada com penalidades

feat(roadmap): implementacao do modulo de gaps, prontidao e roadmaps em markdown

feat(app): interface Streamlit com wizard em 4 etapas, radar chart e roadmap integrado

test: suite de 16 testes de casos de borda com pytest - 16/16 aprovados

docs: README completo com arquitetura, formulas, exemplos e instrucoes de extensao
```

---

## Tecnologias Utilizadas

| Biblioteca  | Uso |
|-------------|-----|
| `streamlit` | Interface web interativa em modo wizard |
| `plotly`    | Graficos de radar e barras para visualizacao das trilhas |
| `pandas`    | Estruturacao da tabela de gaps tecnicos |
| `pytest`    | Suíte de testes automatizados e casos de borda |

---

## Como Executar o Validador da Base

```bash
# Na raiz do repositorio (fora de sistema_carreiras/)
python validar_base.py
```

Saida esperada:
```
Validando arquivo: .../sistema_carreiras/regras_carreiras.json ...

[OK] Base de conhecimento perfeitamente validada!
 - Todas as 10 trilhas possuem pesos, skills_junior e roadmap completos.
 - Todos os IDs de perguntas e skills referenciados existem no catalogo.
 - Todos os pesos estao no intervalo [-1.0, 1.0] com ao menos 1 negativo por trilha.
 - Regras de conflito validadas com sucesso (conjuncao 'se', trilha, penalidade e motivo).
```
