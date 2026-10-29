# Sistema Especialista Inteligente para Mapeamento, Compatibilidade e Trilha de Carreira em TI

Projeto desenvolvido para a disciplina de **Inteligência Artificial**, com o objetivo de construir um sistema especialista capaz de mapear o perfil de um usuário, calcular o nível de afinidade e compatibilidade com diferentes áreas da Tecnologia da Informação (TI) e gerar trilhas de carreira e desenvolvimento personalizadas.

---

## 🎯 Objetivo do Projeto

Auxiliar estudantes e profissionais de tecnologia na identificação da área mais adequada ao seu perfil, competências e preferências, por meio de um **motor de inferência baseado em regras com pontuação ponderada e penalidades**. O sistema avalia respostas fornecidas em um questionário estruturado e projeta recomendações detalhadas, habilidades faltantes e um roadmap prático para atingir os objetivos profissionais.

---

## 🧠 Arquitetura e Diretrizes do Sistema Especialista

- **Base de Conhecimento Desacoplada**: 100% das regras, pesos, perguntas, competências (skills) e roadmaps residem no arquivo `regras_carreiras.json`. O código Python atua puramente como motor de execução e interface, sem regras embutidas (*hardcoded*).
- **Motor Próprio de Inferência**: Algoritmo customizado de pontuação ponderada e aplicação de penalidades, operando sem dependência de bibliotecas legadas (como Experta).
- **Interface Interativa (Streamlit)**: Aplicação web organizada em fluxo guiado por etapas (*wizard*), facilitando a experiência do usuário.
- **Trilhas de Carreira Mapeadas (10 áreas)**:
  1. `backend` — Desenvolvimento Back-end
  2. `frontend_ux` — Desenvolvimento Front-end & UX/UI
  3. `cientista_dados` — Ciência de Dados & Machine Learning
  4. `engenheiro_dados` — Engenharia de Dados & Big Data
  5. `ciberseguranca` — Segurança da Informação & Red Team/Blue Team
  6. `devops_sre` — DevOps & Engenharia de Confiabilidade (SRE)
  7. `cloud_architecture` — Arquitetura de Nuvem
  8. `mobile` — Desenvolvimento Mobile (iOS/Android/Multiplataforma)
  9. `qa` — Garantia de Qualidade & Automação de Testes
  10. `product_management` — Gestão de Produtos Digitais (PM/PO)

---

## 📁 Estrutura do Repositório

```text
sistema_carreiras/
├── regras_carreiras.json     # Base de conhecimento declarativa (regras, pesos, trilhas, roadmaps)
├── motor.py                  # Motor de inferência e cálculo de pontuação ponderada
├── roadmap.py                # Gerador e formatador de trilhas de aprendizado personalizadas
├── app.py                    # Interface de usuário interativa em Streamlit (Wizard)
├── tests/
│   └── test_edge_cases.py    # Testes unitários e casos de borda do motor
├── requirements.txt          # Dependências do projeto (streamlit, pandas, plotly, pytest)
├── .gitignore                # Arquivos ignorados pelo controle de versão
└── README.md                 # Documentação e visão geral do projeto
```

---

## 🚀 Instalação e Execução

### Pré-requisitos
- Python 3.10 ou superior

### Passos de Instalação
```bash
# Clone ou acesse a pasta do projeto
cd sistema_carreiras

# Crie e ative um ambiente virtual (opcional, recomendado)
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Instale as dependências
pip install -r requirements.txt
```
