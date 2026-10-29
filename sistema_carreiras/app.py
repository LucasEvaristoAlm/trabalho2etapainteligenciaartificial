"""Interface interativa em Streamlit (Wizard em 4 etapas).

Sistema Especialista Inteligente para Mapeamento, Compatibilidade e Trilha de Carreira em TI.
Totalmente orientado a dados a partir de regras_carreiras.json.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Garante que o diretorio atual esteja no sys.path para importacao dos modulos locais
diretorio_app = Path(__file__).resolve().parent
if str(diretorio_app) not in sys.path:
    sys.path.insert(0, str(diretorio_app))

from motor import (
    calcular_compatibilidade,
    carregar_base,
    detectar_empate,
    gerar_justificativa,
    top_n,
)
from roadmap import (
    analisar_gaps,
    calcular_prontidao,
    formatar_roadmap_markdown,
    gerar_roadmap,
)

LIKERT_VALORES = (1, 2, 3, 4, 5)


def perguntas_nao_respondidas(
    perguntas: list[dict[str, Any]], respostas: dict[str, Any]
) -> list[dict[str, Any]]:
    """Retorna as perguntas sem resposta Likert inteira válida."""
    return [
        pergunta
        for pergunta in perguntas
        if type(respostas.get(pergunta["id"])) is not int
        or respostas[pergunta["id"]] not in LIKERT_VALORES
    ]


@st.cache_data
def obter_base_conhecimento() -> dict[str, Any]:
    """Carrega e armazena em cache os dados da base declarativa JSON."""
    caminho = diretorio_app / "regras_carreiras.json"
    return carregar_base(caminho)


def inicializar_estado(base: dict[str, Any]) -> None:
    """Garante que todas as chaves necessarias existam no st.session_state."""
    perguntas = base.get("perguntas", [])
    if st.session_state.get("versao_questionario") != 2:
        st.session_state.respostas_afinidade = {
            p["id"]: None for p in perguntas if p.get("passo") == 2
        }
        st.session_state.respostas_objetivos = {
            p["id"]: None for p in perguntas if p.get("passo") == 3
        }
        st.session_state.versao_questionario = 2

    if "passo_atual" not in st.session_state:
        st.session_state.passo_atual = 1

    if "perfil_pessoal" not in st.session_state:
        st.session_state.perfil_pessoal = {
            "nome": "",
            "formacao": "",
            "experiencia": "Nenhuma / Transição",
        }

    if "respostas_afinidade" not in st.session_state:
        st.session_state.respostas_afinidade = {
            p["id"]: None for p in perguntas if p.get("passo") == 2
        }

    if "skills_usuario" not in st.session_state:
        # Coleta todas as skills que aparecem em skills_junior de qualquer trilha
        skills_relevantes: set[str] = set()
        for t in base.get("trilhas", {}).values():
            skills_relevantes.update(t.get("skills_junior", {}).keys())

        st.session_state.skills_usuario = {sid: 0 for sid in skills_relevantes}

    if "respostas_objetivos" not in st.session_state:
        st.session_state.respostas_objetivos = {
            p["id"]: None for p in perguntas if p.get("passo") == 3
        }

    if "trilha_foco" not in st.session_state:
        st.session_state.trilha_foco = None


def reiniciar_aplicacao(base: dict[str, Any]) -> None:
    """Limpa o estado da sessao e retorna ao primeiro passo."""
    st.session_state.passo_atual = 1
    st.session_state.perfil_pessoal = {
        "nome": "",
        "formacao": "",
        "experiencia": "Nenhuma / Transição",
    }
    st.session_state.respostas_afinidade = {
        p["id"]: None for p in base.get("perguntas", []) if p.get("passo") == 2
    }
    for pergunta in base.get("perguntas", []):
        if pergunta.get("passo") == 2:
            st.session_state.pop(f"resposta_afinidade_{pergunta['id']}", None)
    skills_relevantes: set[str] = set()
    for t in base.get("trilhas", {}).values():
        skills_relevantes.update(t.get("skills_junior", {}).keys())
    st.session_state.skills_usuario = {sid: 0 for sid in skills_relevantes}
    st.session_state.respostas_objetivos = {
        p["id"]: None for p in base.get("perguntas", []) if p.get("passo") == 3
    }
    for pergunta in base.get("perguntas", []):
        if pergunta.get("passo") == 3:
            st.session_state.pop(f"resposta_objetivo_{pergunta['id']}", None)
    st.session_state.trilha_foco = None
    st.rerun()


def aplicar_estilos_profissionais() -> None:
    """Aplica identidade visual consistente sem depender de assets externos."""
    st.markdown(
        """
        <style>
        :root {
            color-scheme: light !important;
        }
        html,
        body,
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"],
        [data-testid="stHeader"],
        .stApp {
            background-color: #f5f7fb !important;
            color: #17243a !important;
        }
        [data-testid="stAppViewContainer"] .main .block-container {
            max-width: 1440px;
            padding-top: 2rem;
            padding-bottom: 3rem;
        }
        [data-testid="stWidgetLabel"],
        [data-testid="stWidgetLabel"] label,
        [data-testid="stMarkdownContainer"],
        [data-testid="stCaptionContainer"] {
            color: #17243a;
        }
        [data-testid="stTextInput"] [data-baseweb="base-input"],
        [data-testid="stTextInput"] [data-baseweb="input"] > div,
        [data-testid="stTextArea"] [data-baseweb="textarea"] > div,
        [data-testid="stNumberInput"] [data-baseweb="input"] > div,
        [data-testid="stSelectbox"] [data-baseweb="select"] > div,
        [data-testid="stTextInputRootElement"],
        [data-testid="stTextAreaRootElement"],
        [data-testid="stNumberInputRootElement"],
        [data-testid="stSelectbox"] [role="group"] {
            background-color: #ffffff !important;
            border: 1px solid #cbd6e2 !important;
            border-radius: 9px !important;
            box-shadow: none !important;
        }
        .stTextInput input,
        .stTextArea textarea,
        .stNumberInput input,
        [data-baseweb="input"] input,
        [data-baseweb="textarea"] textarea {
            background-color: #ffffff !important;
            color: #17243a !important;
            -webkit-text-fill-color: #17243a !important;
            caret-color: #174f88 !important;
            color-scheme: light !important;
        }
        .stTextInput input::placeholder,
        .stTextArea textarea::placeholder {
            color: #77869a !important;
            -webkit-text-fill-color: #77869a !important;
        }
        [data-baseweb="input"]:focus-within > div,
        [data-baseweb="select"]:focus-within > div,
        [data-baseweb="textarea"]:focus-within > div {
            border-color: #4f9d8f !important;
            box-shadow: 0 0 0 2px rgba(79, 157, 143, .18) !important;
        }
        [data-testid="stSelectbox"] [data-baseweb="select"],
        [data-testid="stSelectbox"] [data-baseweb="select"] * {
            color: #17243a !important;
        }
        [data-testid="stSelectbox"] input,
        [data-testid="stSelectbox"] button,
        [data-testid="stSelectbox"] svg {
            color: #52647a !important;
            -webkit-text-fill-color: #17243a !important;
            fill: #52647a !important;
        }
        [data-testid="stProgressBarTrack"] {
            background-color: #dce5ef !important;
        }
        [data-testid="stProgressBarTrack"] > div {
            background-color: #4f9d8f !important;
        }
        [data-testid="stExpander"] details {
            overflow: hidden;
            border: 1px solid #dce5ef !important;
            border-radius: 12px !important;
            background-color: #ffffff !important;
        }
        [data-testid="stExpander"] details > summary,
        [data-testid="stExpander"] details > summary * {
            background-color: #ffffff !important;
            color: #17243a !important;
            -webkit-text-fill-color: #17243a !important;
        }
        [data-testid="stExpander"] details > summary {
            padding: .75rem 1rem !important;
        }
        [data-testid="stExpander"] details > summary:hover {
            background-color: #f0f6fb !important;
        }
        [data-testid="stExpander"] details[open] > summary {
            border-bottom: 1px solid #e6edf4 !important;
        }
        [data-baseweb="popover"],
        [data-baseweb="popover"] > div,
        [data-baseweb="menu"],
        [role="listbox"] {
            background-color: #ffffff !important;
            color: #17243a !important;
            color-scheme: light !important;
            border-color: #dce5ef !important;
        }
        [role="option"],
        [role="option"] * {
            background-color: #ffffff !important;
            color: #17243a !important;
            -webkit-text-fill-color: #17243a !important;
        }
        [role="option"]:hover,
        [role="option"][aria-selected="true"] {
            background-color: #edf5ff !important;
        }
        [data-testid="stSlider"] [data-baseweb="slider"] > div:first-child {
            background-color: #dce5ef !important;
        }
        [data-testid="stSlider"] [data-baseweb="slider"] [role="slider"] {
            background-color: #4f9d8f !important;
            border: 2px solid #ffffff !important;
            box-shadow: 0 0 0 1px #3d8276 !important;
        }
        [data-testid="stSlider"] [data-rac][data-orientation="horizontal"] > div:first-child,
        [data-testid="stSelectSlider"] [data-rac][data-orientation="horizontal"] > div:first-child {
            background-color: #dce5ef !important;
        }
        [data-testid="stSlider"] [data-rac][data-orientation="horizontal"] > div:first-child > div,
        [data-testid="stSelectSlider"] [data-rac][data-orientation="horizontal"] > div:first-child > div {
            filter: hue-rotate(145deg) saturate(.75);
        }
        [data-testid="stSlider"] [data-rac][style*="position: absolute"],
        [data-testid="stSelectSlider"] [data-rac][style*="position: absolute"] {
            background-color: #4f9d8f !important;
            border-color: #3d8276 !important;
            box-shadow: 0 0 0 2px #ffffff !important;
        }
        [data-testid="stSlider"] input[type="range"],
        [data-testid="stSelectSlider"] input[type="range"] {
            background: transparent !important;
            color-scheme: light !important;
        }
        [data-testid="stSelectSlider"] [data-baseweb="slider"] {
            color: #17243a !important;
        }
        [data-testid="stSelectSlider"] [data-baseweb="slider"] [role="slider"] {
            background-color: #4f9d8f !important;
            border-color: #3d8276 !important;
        }
        .career-hero {
            padding: 1.8rem 2rem;
            margin-bottom: 1.5rem;
            border: 1px solid #dce5f0;
            border-radius: 18px;
            background: linear-gradient(120deg, #ffffff 20%, #edf5ff 100%);
            box-shadow: 0 8px 24px rgba(21, 43, 74, 0.06);
        }
        .career-hero .eyebrow {
            margin: 0 0 .45rem;
            color: #2363a6;
            font-size: .76rem;
            font-weight: 700;
            letter-spacing: .12em;
            text-transform: uppercase;
        }
        .career-hero h1 {
            margin: 0;
            color: #14243a;
            font-size: clamp(1.7rem, 3vw, 2.45rem);
            line-height: 1.15;
        }
        .career-hero .hero-copy {
            max-width: 850px;
            margin: .7rem 0 0;
            color: #52647a;
            font-size: 1rem;
            line-height: 1.6;
        }
        .career-hero .hero-tags {
            display: flex;
            flex-wrap: wrap;
            gap: .55rem;
            margin-top: 1rem;
        }
        .career-hero .hero-tag {
            padding: .3rem .65rem;
            border: 1px solid #d7e5f4;
            border-radius: 999px;
            background: #fff;
            color: #38536f;
            font-size: .8rem;
            font-weight: 600;
        }
        .career-stepper {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: .7rem;
            margin: 0 0 1.1rem;
        }
        .career-step {
            display: flex;
            align-items: center;
            gap: .65rem;
            min-height: 54px;
            padding: .65rem .8rem;
            border: 1px solid #e0e7f0;
            border-radius: 12px;
            background: #fff;
            color: #66758a;
            font-size: .88rem;
            font-weight: 600;
        }
        .career-step .step-number {
            display: grid;
            width: 28px;
            height: 28px;
            flex: 0 0 28px;
            place-items: center;
            border-radius: 50%;
            background: #edf1f6;
            color: #53647a;
            font-size: .78rem;
        }
        .career-step.is-active {
            border-color: #9dc2eb;
            background: #edf5ff;
            color: #174f88;
        }
        .career-step.is-active .step-number,
        .career-step.is-done .step-number {
            background: #1d5f9e;
            color: #fff;
        }
        .career-step.is-done {
            color: #38536f;
        }
        [data-testid="stMetric"] {
            padding: 1rem 1.1rem;
            border: 1px solid #e0e7f0;
            border-radius: 14px;
            background: #fff;
            box-shadow: 0 4px 14px rgba(21, 43, 74, 0.04);
        }
        [data-testid="stMetricLabel"] {
            color: #52647a;
        }
        [data-testid="stExpander"] {
            border-color: #e0e7f0;
            border-radius: 12px;
            background: #fff;
        }
        .stButton > button {
            border: 1px solid #cbd6e2 !important;
            border-radius: 9px !important;
            background-color: #ffffff !important;
            color: #36536e !important;
            -webkit-text-fill-color: #36536e !important;
        }
        .stButton > button:hover {
            border-color: #91b8b0 !important;
            background-color: #f0f7f5 !important;
            color: #244e48 !important;
            -webkit-text-fill-color: #244e48 !important;
        }
        .stButton > button[kind="primary"] {
            border: 1px solid #174f88 !important;
            background: #174f88 !important;
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
        }
        .stButton > button[kind="primary"]:hover {
            border-color: #103c6b;
            background: #103c6b;
        }
        @media (max-width: 700px) {
            .career-hero {
                padding: 1.25rem;
            }
            .career-stepper {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
            .career-step {
                font-size: .78rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def renderizar_cabecalho(passo: int) -> None:
    """Exibe a identidade visual e a navegacao do wizard."""
    st.markdown(
        """
        <section class="career-hero">
            <p class="eyebrow">Orientação profissional em tecnologia</p>
            <h1>Construa seu próximo passo em TI</h1>
            <p class="hero-copy">
                Explore áreas compatíveis com seus interesses, identifique competências
                para desenvolver e receba um plano inicial de evolução profissional.
            </p>
            <div class="hero-tags">
                <span class="hero-tag">10 trilhas de carreira</span>
                <span class="hero-tag">Análise explicável</span>
                <span class="hero-tag">Plano por competências</span>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    rotulos_passos = [
        "Perfil",
        "Interesses e competências",
        "Objetivos",
        "Recomendações",
    ]
    etapas = []
    for indice, rotulo in enumerate(rotulos_passos, start=1):
        estado = "is-active" if indice == passo else "is-done" if indice < passo else ""
        aria_atual = 'aria-current="step"' if indice == passo else ""
        etapas.append(
            f'<div class="career-step {estado}" {aria_atual}>'
            f'<span class="step-number">{indice:02d}</span><span>{rotulo}</span></div>'
        )
    st.markdown(
        f'<div class="career-stepper">{"".join(etapas)}</div>',
        unsafe_allow_html=True,
    )
    st.progress(
        (passo - 1) / (len(rotulos_passos) - 1),
        text=f"Etapa {passo} de {len(rotulos_passos)} · {rotulos_passos[passo - 1]}",
    )


def passo_1_perfil_pessoal() -> None:
    """Renderiza o Passo 1: Informacoes basicas do perfil do usuario."""
    st.subheader("Passo 1: Identificacao do Perfil")
    st.write(
        "Compartilhe algumas informações para personalizar o relatório. Os campos são opcionais."
    )

    perfil = st.session_state.perfil_pessoal

    col1, col2 = st.columns(2)
    with col1:
        nome = st.text_input(
            "Nome (opcional):",
            value=perfil.get("nome", ""),
            placeholder="Ex.: Maria Silva",
        )
    with col2:
        formacao = st.text_input(
            "Curso ou formação (opcional):",
            value=perfil.get("formacao", ""),
            placeholder="Ex.: Ciência da Computação",
        )

    opcoes_exp = [
        "Nenhuma / Transição de Carreira",
        "Menos de 1 ano (estágio / início de carreira)",
        "1 a 2 anos",
        "3 a 5 anos",
        "Mais de 5 anos",
    ]
    idx_exp = (
        opcoes_exp.index(perfil.get("experiencia"))
        if perfil.get("experiencia") in opcoes_exp
        else 0
    )
    experiencia = st.selectbox(
        "Experiência profissional em TI:",
        options=opcoes_exp,
        index=idx_exp,
    )

    st.session_state.perfil_pessoal = {
        "nome": nome.strip(),
        "formacao": formacao.strip(),
        "experiencia": experiencia,
    }
    st.caption(
        "Os dados de perfil ficam apenas nesta sessão e não alteram a pontuação das trilhas."
    )

    st.write("")
    col_dir, col_prox = st.columns([8, 2])
    with col_prox:
        if st.button("Proximo: Afinidades ->", type="primary", use_container_width=True):
            st.session_state.passo_atual = 2
            st.rerun()


def passo_2_afinidades_e_skills(base: dict[str, Any]) -> None:
    """Renderiza o Passo 2: Afinidades tecnicas e autoavaliacao de habilidades."""
    st.subheader("Passo 2: Interesses e competências")
    st.write(
        "Reflita sobre situações reais de estudo, projetos e trabalho. Respostas honestas ajudam a tornar as recomendações mais úteis."
    )

    niveis_resposta = base.get("niveis_resposta", {})
    perguntas_passo2 = [p for p in base.get("perguntas", []) if p.get("passo") == 2]

    # Aba 1: Afinidades (Likert 1-5)
    with st.expander("Parte A: Interesses profissionais (escala de 1 a 5)", expanded=True):
        st.info(
            "Use a escala de 1 (discordo totalmente / pouca afinidade) a 5 "
            "(concordo totalmente / muita afinidade). O valor 3 representa uma posição neutra."
        )

        st.caption("Selecione uma opção em cada pergunta. A escala completa vai de 1 a 5.")
        col1, col2 = st.columns(2)
        for idx, p in enumerate(perguntas_passo2):
            col_alvo = col1 if idx % 2 == 0 else col2
            with col_alvo:
                qid = p["id"]
                rotulo_pergunta = f"**{idx + 1}. {p['texto']}**"
                st.markdown(rotulo_pergunta)
                novo_val = st.radio(
                    "Resposta (1 a 5)",
                    options=LIKERT_VALORES,
                    index=None,
                    horizontal=True,
                    key=f"resposta_afinidade_{qid}",
                    help="1 = pouca afinidade · 3 = neutro · 5 = muita afinidade",
                )
                if novo_val is None:
                    st.caption("Ainda sem resposta")
                else:
                    st.caption(
                        f"Nível: **{novo_val} - "
                        f"{niveis_resposta.get(str(novo_val), '')}**"
                    )
                st.session_state.respostas_afinidade[qid] = novo_val

    # Aba 2: Autoavaliacao de skills tecnicas (0-3)
    catalogo_skills = base.get("skills_catalogo", {})
    skills_relevantes: list[str] = sorted(list(st.session_state.skills_usuario.keys()))

    with st.expander(
        "Parte B: Autoavaliação de competências (escala de 0 a 3)", expanded=True
    ):
        st.info(
            "Indique seu nível atual nas competências técnicas avaliadas:\n"
            "- **0**: Não conheço\n"
            "- **1**: Básico (conheço conceitos ou fiz tutoriais)\n"
            "- **2**: Intermediário (já apliquei em projetos práticos)\n"
            "- **3**: Avançado (aplico com autonomia e consigo explicar minhas decisões)\n\n"
            "Considere evidências práticas, como exercícios, projetos ou experiências profissionais; "
            "não é necessário marcar um nível alto apenas por conhecer a teoria."
        )

        mapa_rotulos_skill = {
            0: "0 - Não conheço",
            1: "1 - Básico",
            2: "2 - Intermediário",
            3: "3 - Avançado",
        }

        col_s1, col_s2 = st.columns(2)
        for idx, sid in enumerate(skills_relevantes):
            col_alvo = col_s1 if idx % 2 == 0 else col_s2
            nome_exibicao = catalogo_skills.get(sid, sid)
            val_skill = int(st.session_state.skills_usuario.get(sid, 0))

            with col_alvo:
                novo_val_skill = st.select_slider(
                    f"{nome_exibicao}",
                    options=[0, 1, 2, 3],
                    value=val_skill,
                    format_func=lambda x: mapa_rotulos_skill.get(x, str(x)),
                    key=f"skill_slider_{sid}",
                )
                st.session_state.skills_usuario[sid] = novo_val_skill

    # Navegacao
    pendentes = perguntas_nao_respondidas(
        perguntas_passo2, st.session_state.respostas_afinidade
    )
    if pendentes:
        st.warning(
            f"Responda às {len(pendentes)} pergunta(s) de interesse que faltam para avançar."
        )

    st.write("")
    col_voltar, col_espaco, col_prox = st.columns([2, 6, 2])
    with col_voltar:
        if st.button("<- Voltar ao Passo 1", use_container_width=True):
            st.session_state.passo_atual = 1
            st.rerun()
    with col_prox:
        if st.button(
            "Proximo: Objetivos ->",
            type="primary",
            use_container_width=True,
            disabled=bool(pendentes),
        ):
            st.session_state.passo_atual = 3
            st.rerun()


def passo_3_objetivos_carreira(base: dict[str, Any]) -> None:
    """Renderiza o Passo 3: Objetivos e aspiracoes de carreira."""
    st.subheader("Passo 3: Objetivos de carreira")
    st.write(
        "Indique o que você busca no próximo passo da carreira. Essas respostas complementam o perfil de interesses."
    )

    niveis_resposta = base.get("niveis_resposta", {})
    perguntas_passo3 = [p for p in base.get("perguntas", []) if p.get("passo") == 3]

    for idx, p in enumerate(perguntas_passo3):
        qid = p["id"]
        st.markdown(f"**{idx + 1}. {p['texto']}**")
        novo_val = st.radio(
            "Nível de alinhamento (1 a 5)",
            options=LIKERT_VALORES,
            index=None,
            horizontal=True,
            key=f"resposta_objetivo_{qid}",
            help="1 = pouco alinhado · 3 = neutro · 5 = muito alinhado",
        )
        if novo_val is None:
            st.caption("Ainda sem resposta")
        else:
            st.caption(
                f"Alinhamento: **{novo_val} - "
                f"{niveis_resposta.get(str(novo_val), '')}**"
            )
        st.session_state.respostas_objetivos[qid] = novo_val
        st.write("")

    # Navegacao
    pendentes = perguntas_nao_respondidas(
        perguntas_passo3, st.session_state.respostas_objetivos
    )
    if pendentes:
        st.warning(
            f"Responda às {len(pendentes)} pergunta(s) de objetivo que faltam para gerar o resultado."
        )

    col_voltar, col_espaco, col_calc = st.columns([2, 5, 3])
    with col_voltar:
        if st.button("<- Voltar ao Passo 2", use_container_width=True):
            st.session_state.passo_atual = 2
            st.rerun()
    with col_calc:
        if st.button(
            "Calcular Resultados e Roadmap",
            type="primary",
            use_container_width=True,
            disabled=bool(pendentes),
        ):
            st.session_state.passo_atual = 4
            st.rerun()


def passo_4_resultados_e_roadmap(base: dict[str, Any]) -> None:
    """Renderiza o Passo 4: Apresentacao analitica e diagnostica dos resultados."""
    st.subheader("Recomendações e plano de desenvolvimento")

    # Consolida as respostas de todos os passos
    todas_respostas = {
        **st.session_state.respostas_afinidade,
        **st.session_state.respostas_objetivos,
    }

    resultado = calcular_compatibilidade(todas_respostas, base)
    top_tres = top_n(resultado, n=3)
    empates = detectar_empate(top_tres, margem=5.0)

    # Tratamento de perfil indefinido / neutro
    todos_pcts = [item["pct"] for item in resultado.values()]
    max_pct = max(todos_pcts) if todos_pcts else 0.0
    min_pct = min(todos_pcts) if todos_pcts else 0.0
    amplitude = max_pct - min_pct

    if max_pct < 35.0 or (amplitude < 10.0 and max_pct < 55.0):
        st.warning(
            "Seu perfil ainda não aponta uma direção claramente dominante. Considere revisar as "
            "respostas de afinidade e objetivos para refletir melhor suas preferências atuais."
        )

    # Identificacao do usuario
    perfil = st.session_state.perfil_pessoal
    nome_usuario = perfil.get("nome") or "Profissional em Avaliacao"
    formacao_usuario = perfil.get("formacao")
    experiencia_usuario = perfil.get("experiencia")
    contexto_perfil = " · ".join(
        valor for valor in (formacao_usuario, experiencia_usuario) if valor
    )
    st.markdown(
        f"#### Síntese para **{nome_usuario}**"
        + (f" · {contexto_perfil}" if contexto_perfil else "")
    )
    st.caption(
        "As recomendações são indicativas: representam aderência às respostas e aos critérios "
        "desta base, não probabilidade de contratação nem garantia de empregabilidade. "
        "A análise usa uma base local e não consulta vagas ou salários em tempo real."
    )

    # (a) Metricas do Top 3
    col1, col2, col3 = st.columns(3)
    colunas_metricas = [col1, col2, col3]

    for idx, (tid, info) in enumerate(top_tres):
        nome_trilha = base["trilhas"].get(tid, {}).get("nome", tid)
        with colunas_metricas[idx]:
            st.metric(
                label=f"{idx + 1}ª recomendação · {nome_trilha}",
                value=f"{info['pct']}%",
            )

    # (d) Aviso de Empate Tecnico / Perfil Hibrido
    if len(empates) > 1:
        nomes_empate = [base["trilhas"].get(t, {}).get("nome", t) for t in empates]
        st.info(
            f"Perfil híbrido: {', '.join(nomes_empate)} tiveram resultados próximos pelo critério "
            "adotado. Vale explorar as atividades e competências de cada trilha antes de escolher."
        )

    # (c) Justificativa da Trilha Vencedora
    trilha_vencedora_id = top_tres[0][0]
    with st.expander(
        f"Por que esta trilha foi recomendada: {base['trilhas'][trilha_vencedora_id]['nome']}",
        expanded=True,
    ):
        texto_justificativa = gerar_justificativa(trilha_vencedora_id, resultado, base)
        st.markdown(texto_justificativa.replace("\n", "  \n"))

    # (b) Visualizacoes Graficas (Radar Chart e Barras Ordenadas)
    st.write("---")
    st.subheader("Comparativo entre as trilhas")

    df_todas = pd.DataFrame(
        [
            {
                "Trilha": base["trilhas"].get(tid, {}).get("nome", tid),
                "Compatibilidade (%)": info["pct"],
                "ID": tid,
            }
            for tid, info in resultado.items()
        ]
    ).sort_values(by="Compatibilidade (%)", ascending=False)

    col_radar, col_barras = st.columns(2)

    with col_radar:
        st.markdown("**Visão geral por trilha**")
        # Grafico Radar usando plotly.graph_objects
        categorias = df_todas["Trilha"].tolist()
        valores = df_todas["Compatibilidade (%)"].tolist()
        # Fecha o poligono do radar
        categorias_fechadas = categorias + [categorias[0]]
        valores_fechados = valores + [valores[0]]

        fig_radar = go.Figure()
        fig_radar.add_trace(
            go.Scatterpolar(
                r=valores_fechados,
                theta=categorias_fechadas,
                fill="toself",
                fillcolor="rgba(29, 95, 158, 0.18)",
                line=dict(color="#1d5f9e", width=2),
                name="Aderência",
            )
        )
        fig_radar.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 100], tickfont=dict(size=10)),
            ),
            showlegend=False,
            template="plotly_white",
            margin=dict(l=40, r=40, t=20, b=20),
            height=380,
        )
        st.plotly_chart(fig_radar, use_container_width=True)

    with col_barras:
        st.markdown("**Ranking de aderência**")
        fig_barras = px.bar(
            df_todas,
            x="Compatibilidade (%)",
            y="Trilha",
            orientation="h",
            color_discrete_sequence=["#4F9D8F"],
            text="Compatibilidade (%)",
        )
        fig_barras.update_layout(
            yaxis=dict(autorange="reversed"),
            margin=dict(l=20, r=20, t=20, b=20),
            height=380,
            coloraxis_showscale=False,
            template="plotly_white",
        )
        fig_barras.update_traces(
            marker_color="#4F9D8F",
            marker_line_color="#3D8276",
            marker_line_width=0.5,
            texttemplate="%{text:.1f}%",
            textposition="outside",
            textfont=dict(color="#263746"),
        )
        st.plotly_chart(fig_barras, use_container_width=True)

    # (g) Seletor de Trilha para Exploracao Detalhada
    st.write("---")
    st.subheader("Plano de desenvolvimento")
    st.caption(
        "A prontidão compara sua autoavaliação aos requisitos Júnior cadastrados para a trilha; "
        "não substitui a análise de vagas ou processos seletivos."
    )

    opcoes_trilha = [t[0] for t in top_tres]
    if (
        st.session_state.trilha_foco is None
        or st.session_state.trilha_foco not in opcoes_trilha
    ):
        st.session_state.trilha_foco = opcoes_trilha[0]

    idx_selecao = opcoes_trilha.index(st.session_state.trilha_foco)
    trilha_selecionada = st.selectbox(
        "Selecione uma trilha do Top 3 para inspecionar os gaps tecnicos e o plano de estudos:",
        options=opcoes_trilha,
        index=idx_selecao,
        format_func=lambda tid: f"{base['trilhas'][tid]['nome']} (Compatibilidade: {resultado[tid]['pct']}%)",
    )
    st.session_state.trilha_foco = trilha_selecionada

    # (e) e (f) Diagnostico de Gaps e Roadmap da Trilha Selecionada
    gaps_trilha = analisar_gaps(
        trilha_selecionada, st.session_state.skills_usuario, base
    )
    prontidao_trilha = calcular_prontidao(
        trilha_selecionada, st.session_state.skills_usuario, base
    )
    roadmap_trilha = gerar_roadmap(trilha_selecionada, gaps_trilha, base)

    st.write("")
    st.markdown(
        f"### Diagnostico de Prontidao para Junior: **{base['trilhas'][trilha_selecionada]['nome']}**"
    )
    st.progress(
        prontidao_trilha / 100.0,
        text=f"Nivel de Prontidao Atual: {prontidao_trilha}%",
    )

    if gaps_trilha:
        st.markdown("#### Tabela de Gaps Tecnicos Identificados:")
        df_gaps = pd.DataFrame(
            [
                {
                    "Habilidade": g["skill"],
                    "Nivel Atual": g["atual"],
                    "Exigido (Junior)": g["exigido"],
                    "Lacuna (Niveis a Evoluir)": f"+{g['gap']}",
                }
                for g in gaps_trilha
            ]
        )
        st.dataframe(df_gaps, use_container_width=True, hide_index=True)
    else:
        st.success("Voce atende ou supera todas as habilidades tecnicas minimas desta trilha!")

    # Formatacao do Roadmap em Markdown
    st.write("")
    markdown_roadmap = formatar_roadmap_markdown(
        roadmap_trilha, gaps_trilha, prontidao_trilha
    )
    st.markdown(markdown_roadmap)

    # Botoes de acao finais
    st.write("---")
    col_v, col_esp, col_refazer = st.columns([3, 5, 2])
    with col_v:
        if st.button("<- Voltar ao Passo 3 para Ajustar", use_container_width=True):
            st.session_state.passo_atual = 3
            st.rerun()
    with col_refazer:
        if st.button("Refazer Avaliacao Completa", type="secondary", use_container_width=True):
            reiniciar_aplicacao(base)


def main() -> None:
    """Ponto de entrada principal da aplicacao Streamlit."""
    st.set_page_config(
        page_title="Sistema Especialista de Carreiras em TI",
        page_icon="💼",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    aplicar_estilos_profissionais()

    base = obter_base_conhecimento()
    inicializar_estado(base)

    passo = st.session_state.passo_atual
    renderizar_cabecalho(passo)

    if passo == 1:
        passo_1_perfil_pessoal()
    elif passo == 2:
        passo_2_afinidades_e_skills(base)
    elif passo == 3:
        passo_3_objetivos_carreira(base)
    elif passo == 4:
        passo_4_resultados_e_roadmap(base)


if __name__ == "__main__":
    main()
