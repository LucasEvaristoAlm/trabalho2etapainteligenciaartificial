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


@st.cache_data
def obter_base_conhecimento() -> dict[str, Any]:
    """Carrega e armazena em cache os dados da base declarativa JSON."""
    caminho = diretorio_app / "regras_carreiras.json"
    return carregar_base(caminho)


def inicializar_estado(base: dict[str, Any]) -> None:
    """Garante que todas as chaves necessarias existam no st.session_state."""
    if "passo_atual" not in st.session_state:
        st.session_state.passo_atual = 1

    if "perfil_pessoal" not in st.session_state:
        st.session_state.perfil_pessoal = {
            "nome": "",
            "formacao": "",
            "experiencia": "Nenhuma / Transição",
        }

    if "respostas_afinidade" not in st.session_state:
        # Inicializa respostas com valor mediano (3)
        st.session_state.respostas_afinidade = {
            p["id"]: 3 for p in base.get("perguntas", []) if p.get("passo") == 2
        }

    if "skills_usuario" not in st.session_state:
        # Coleta todas as skills que aparecem em skills_junior de qualquer trilha
        skills_relevantes: set[str] = set()
        for t in base.get("trilhas", {}).values():
            skills_relevantes.update(t.get("skills_junior", {}).keys())

        st.session_state.skills_usuario = {sid: 0 for sid in skills_relevantes}

    if "respostas_objetivos" not in st.session_state:
        st.session_state.respostas_objetivos = {
            p["id"]: 3 for p in base.get("perguntas", []) if p.get("passo") == 3
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
        p["id"]: 3 for p in base.get("perguntas", []) if p.get("passo") == 2
    }
    skills_relevantes: set[str] = set()
    for t in base.get("trilhas", {}).values():
        skills_relevantes.update(t.get("skills_junior", {}).keys())
    st.session_state.skills_usuario = {sid: 0 for sid in skills_relevantes}
    st.session_state.respostas_objetivos = {
        p["id"]: 3 for p in base.get("perguntas", []) if p.get("passo") == 3
    }
    st.session_state.trilha_foco = None
    st.rerun()


def renderizar_cabecalho(passo: int) -> None:
    """Exibe o cabecalho institucional e a barra de progresso do wizard."""
    st.title("Sistema Especialista de Orientacao de Carreiras em TI")
    st.caption(
        "Motor de inferencia baseado em regras ponderadas e analise prescritiva de gaps tecnicos."
    )

    rotulos_passos = [
        "Passo 1: Perfil Pessoal",
        "Passo 2: Afinidades e Habilidades",
        "Passo 3: Objetivos de Carreira",
        "Passo 4: Diagnostico e Roadmap",
    ]

    progresso_pct = int((passo / 4) * 100)
    st.progress(progresso_pct / 100.0, text=f"{rotulos_passos[passo - 1]} ({progresso_pct}%)")
    st.write("---")


def passo_1_perfil_pessoal() -> None:
    """Renderiza o Passo 1: Informacoes basicas do perfil do usuario."""
    st.subheader("Passo 1: Identificacao do Perfil")
    st.write(
        "Informe seus dados basicos para contextualizar o relatorio de recomendacao profissional."
    )

    perfil = st.session_state.perfil_pessoal

    col1, col2 = st.columns(2)
    with col1:
        nome = st.text_input(
            "Nome Completo ou Identificacao:",
            value=perfil.get("nome", ""),
            placeholder="Ex.: Lucas Evaristo",
        )
    with col2:
        formacao = st.text_input(
            "Curso / Formacao Atual:",
            value=perfil.get("formacao", ""),
            placeholder="Ex.: Ciencia da Computacao, Sistemas de Informacao...",
        )

    opcoes_exp = [
        "Nenhuma / Transição de Carreira",
        "Menos de 1 ano (Estagio/Junior iniciante)",
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
        "Tempo de Experiencia Profissional na Area de TI:",
        options=opcoes_exp,
        index=idx_exp,
    )

    st.session_state.perfil_pessoal = {
        "nome": nome.strip(),
        "formacao": formacao.strip(),
        "experiencia": experiencia,
    }

    st.write("")
    col_dir, col_prox = st.columns([8, 2])
    with col_prox:
        if st.button("Proximo: Afinidades ->", type="primary", use_container_width=True):
            st.session_state.passo_atual = 2
            st.rerun()


def passo_2_afinidades_e_skills(base: dict[str, Any]) -> None:
    """Renderiza o Passo 2: Afinidades tecnicas e autoavaliacao de habilidades."""
    st.subheader("Passo 2: Afinidades Tecnicas e Autoavaliacao de Habilidades")
    st.write(
        "Responda ao questionario de afinidades e avalie seu nivel de dominio atual nas principais tecnologias."
    )

    niveis_resposta = base.get("niveis_resposta", {})
    perguntas_passo2 = [p for p in base.get("perguntas", []) if p.get("passo") == 2]

    # Aba 1: Afinidades (Likert 1-5)
    with st.expander("Parte A: Questionario de Afinidades Tecnicas (Likert 1 a 5)", expanded=True):
        st.info("Classifique de 1 (Nenhuma afinidade) a 5 (Afinidade muito alta) cada declaracao.")

        col1, col2 = st.columns(2)
        for idx, p in enumerate(perguntas_passo2):
            col_alvo = col1 if idx % 2 == 0 else col2
            with col_alvo:
                qid = p["id"]
                val_atual = int(st.session_state.respostas_afinidade.get(qid, 3))
                rotulo_pergunta = f"**{idx + 1}. {p['texto']}**"
                novo_val = st.slider(
                    rotulo_pergunta,
                    min_value=1,
                    max_value=5,
                    value=val_atual,
                    format="%d",
                    key=f"slider_{qid}",
                    help=f"Classificacao: {niveis_resposta.get(str(val_atual), '')}",
                )
                st.caption(f"Nivel: **{novo_val} - {niveis_resposta.get(str(novo_val), '')}**")
                st.session_state.respostas_afinidade[qid] = novo_val

    # Aba 2: Autoavaliacao de skills tecnicas (0-3)
    catalogo_skills = base.get("skills_catalogo", {})
    skills_relevantes: list[str] = sorted(list(st.session_state.skills_usuario.keys()))

    with st.expander(
        "Parte B: Autoavaliacao de Habilidades Tecnicas (Escala 0 a 3)", expanded=True
    ):
        st.info(
            "Indique seu grau de conhecimento atual nas competencias tecnicas avaliadas:\n"
            "- **0**: Desconheco completamente\n"
            "- **1**: Basico (conheco conceitos / fiz tutoriais)\n"
            "- **2**: Intermediario (ja utilizei em projetos praticos)\n"
            "- **3**: Avancado (domino com seguranca e autonomia)"
        )

        mapa_rotulos_skill = {
            0: "0 - Desconheco",
            1: "1 - Basico",
            2: "2 - Intermediario",
            3: "3 - Avancado",
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
    st.write("")
    col_voltar, col_espaco, col_prox = st.columns([2, 6, 2])
    with col_voltar:
        if st.button("<- Voltar ao Passo 1", use_container_width=True):
            st.session_state.passo_atual = 1
            st.rerun()
    with col_prox:
        if st.button("Proximo: Objetivos ->", type="primary", use_container_width=True):
            st.session_state.passo_atual = 3
            st.rerun()


def passo_3_objetivos_carreira(base: dict[str, Any]) -> None:
    """Renderiza o Passo 3: Objetivos e aspiracoes de carreira."""
    st.subheader("Passo 3: Objetivos e Aspiracoes de Carreira")
    st.write(
        "Para refinar ainda mais o direcionamento do sistema especialista, indique seus objetivos profissionais."
    )

    niveis_resposta = base.get("niveis_resposta", {})
    perguntas_passo3 = [p for p in base.get("perguntas", []) if p.get("passo") == 3]

    for idx, p in enumerate(perguntas_passo3):
        qid = p["id"]
        val_atual = int(st.session_state.respostas_objetivos.get(qid, 3))
        st.markdown(f"**{idx + 1}. {p['texto']}**")
        novo_val = st.slider(
            "Nivel de alinhamento com seu objetivo:",
            min_value=1,
            max_value=5,
            value=val_atual,
            key=f"obj_slider_{qid}",
            label_visibility="collapsed",
        )
        st.caption(f"Alinhamento: **{novo_val} - {niveis_resposta.get(str(novo_val), '')}**")
        st.session_state.respostas_objetivos[qid] = novo_val
        st.write("")

    # Navegacao
    col_voltar, col_espaco, col_calc = st.columns([2, 5, 3])
    with col_voltar:
        if st.button("<- Voltar ao Passo 2", use_container_width=True):
            st.session_state.passo_atual = 2
            st.rerun()
    with col_calc:
        if st.button("Calcular Resultados e Roadmap", type="primary", use_container_width=True):
            st.session_state.passo_atual = 4
            st.rerun()


def passo_4_resultados_e_roadmap(base: dict[str, Any]) -> None:
    """Renderiza o Passo 4: Apresentacao analitica e diagnostica dos resultados."""
    st.subheader("Passo 4: Diagnostico de Compatibilidade e Plano de Carreira")

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
            "Aviso de Perfil Indefinido: As respostas registradas geraram pontuacoes baixas ou "
            "muito homogeneas entre todas as 10 areas avaliadas. Recomendamos refazer a avaliacao "
            "expressando gostos e rejeicoes mais nitidos para obter um direcionamento mais seguro."
        )

    # Identificacao do usuario
    perfil = st.session_state.perfil_pessoal
    nome_usuario = perfil.get("nome") or "Profissional em Avaliacao"
    formacao_usuario = perfil.get("formacao") or "Area Tecnica"
    st.markdown(f"#### Relatorio Gerado para: **{nome_usuario}** ({formacao_usuario})")

    # (a) Metricas do Top 3
    col1, col2, col3 = st.columns(3)
    colunas_metricas = [col1, col2, col3]

    for idx, (tid, info) in enumerate(top_tres):
        nome_trilha = base["trilhas"].get(tid, {}).get("nome", tid)
        with colunas_metricas[idx]:
            st.metric(
                label=f"#{idx + 1} Lugar: {nome_trilha}",
                value=f"{info['pct']}%",
                delta=f"Bruto: {info['bruto']:.2f} pts",
            )

    # (d) Aviso de Empate Tecnico / Perfil Hibrido
    if len(empates) > 1:
        nomes_empate = [base["trilhas"].get(t, {}).get("nome", t) for t in empates]
        st.info(
            f"Perfil Hibrido / Empate Tecnico Detectado: As trilhas {', '.join(nomes_empate)} "
            "apresentam compatibilidade estatisticamente muito proxima (diferenca inferior a 5%). "
            "Isso sinaliza versatilidade para atuar em cargos com perfil interdisciplinar."
        )

    # (c) Justificativa da Trilha Vencedora
    trilha_vencedora_id = top_tres[0][0]
    with st.expander(
        f"Ver Explicabilidade da Trilha Lider: {base['trilhas'][trilha_vencedora_id]['nome']}",
        expanded=True,
    ):
        texto_justificativa = gerar_justificativa(trilha_vencedora_id, resultado, base)
        st.text(texto_justificativa)

    # (b) Visualizacoes Graficas (Radar Chart e Barras Ordenadas)
    st.write("---")
    st.subheader("Panorama Comparativo de Compatibilidade (10 Trilhas)")

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
        st.markdown("**Grafico Radar de Competencias:**")
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
                fillcolor="rgba(33, 150, 243, 0.25)",
                line=dict(color="#1976D2", width=2),
                name="Afinidade",
            )
        )
        fig_radar.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 100], tickfont=dict(size=10)),
            ),
            showlegend=False,
            margin=dict(l=40, r=40, t=20, b=20),
            height=380,
        )
        st.plotly_chart(fig_radar, use_container_width=True)

    with col_barras:
        st.markdown("**Ranking Geral de Compatibilidade:**")
        fig_barras = px.bar(
            df_todas,
            x="Compatibilidade (%)",
            y="Trilha",
            orientation="h",
            color="Compatibilidade (%)",
            color_continuous_scale="Viridis",
            text="Compatibilidade (%)",
        )
        fig_barras.update_layout(
            yaxis=dict(autorange="reversed"),
            margin=dict(l=20, r=20, t=20, b=20),
            height=380,
            coloraxis_showscale=False,
        )
        fig_barras.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        st.plotly_chart(fig_barras, use_container_width=True)

    # (g) Seletor de Trilha para Exploracao Detalhada
    st.write("---")
    st.subheader("Exploracao Detalhada de Gaps e Roadmap")

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
        layout="wide",
        initial_sidebar_state="collapsed",
    )

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
