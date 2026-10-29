"""Modulo de analise de gaps de competencias e geracao de roadmaps personalizados.

100% orientado a dados: consome todas as regras, habilidades e estruturas
diretamente da base de conhecimento JSON.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def carregar_base(caminho: str | Path = "regras_carreiras.json") -> dict[str, Any]:
    """Carrega a base de conhecimento declarativa em formato JSON."""
    caminho_p = Path(caminho)
    if not caminho_p.exists():
        caminho_alt = Path(__file__).parent / caminho_p.name
        if caminho_alt.exists():
            caminho_p = caminho_alt
        else:
            raise FileNotFoundError(f"Base de regras nao encontrada: {caminho}")

    with open(caminho_p, "r", encoding="utf-8") as f:
        return json.load(f)


def analisar_gaps(
    trilha_id: str, skills_usuario: dict[str, int], base: dict[str, Any]
) -> list[dict[str, Any]]:
    """Identifica e ordena as lacunas tecnicas do usuario em relacao ao nivel Junior.

    Retorna apenas skills em que atual < exigido, ordenadas por gap decrescente.
    O desempate e feito pela ordem em que a tecnologia aparece no roadmap da trilha.

    Args:
        trilha_id: Identificador da trilha (ex.: 'devops_sre').
        skills_usuario: Dicionario {id_skill: nivel_atual (0-3)}.
        base: Dicionario da base de regras_carreiras.json.

    Returns:
        Lista de dicionarios com {skill_id, skill, atual, exigido, gap}.
    """
    trilhas = base.get("trilhas", {})
    if trilha_id not in trilhas:
        raise KeyError(f"Trilha '{trilha_id}' nao encontrada na base de conhecimento.")

    trilha = trilhas[trilha_id]
    skills_junior: dict[str, int] = trilha.get("skills_junior", {})
    catalogo: dict[str, str] = base.get("skills_catalogo", {})
    tecnologias_roadmap: list[str] = trilha.get("roadmap", {}).get("tecnologias", [])

    def _posicao_no_roadmap(sid: str, nome: str) -> int:
        """Determina a ordem de aparicao no roadmap para desempate."""
        sid_l = sid.lower()
        nome_l = nome.lower()
        for idx, tec in enumerate(tecnologias_roadmap):
            tec_l = tec.lower()
            if sid_l in tec_l or any(p in tec_l for p in nome_l.split() if len(p) >= 4):
                return idx
        return 9999

    gaps_brutos: list[tuple[int, int, dict[str, Any]]] = []

    for sid, exigido in skills_junior.items():
        atual = int(skills_usuario.get(sid, 0))
        if atual < exigido:
            gap = exigido - atual
            nome_exibicao = catalogo.get(sid, sid)
            ordem_tec = _posicao_no_roadmap(sid, nome_exibicao)
            item = {
                "skill_id": sid,
                "skill": nome_exibicao,
                "atual": atual,
                "exigido": exigido,
                "gap": gap,
            }
            # Tupla para ordenacao: (-gap para decrescente, ordem_tec crescente)
            gaps_brutos.append((-gap, ordem_tec, item))

    gaps_brutos.sort(key=lambda t: (t[0], t[1]))
    return [t[2] for t in gaps_brutos]


def calcular_prontidao(
    trilha_id: str, skills_usuario: dict[str, int], base: dict[str, Any]
) -> float:
    """Calcula o percentual (0.0 a 100.0) de prontidao do usuario para o nivel Junior.

    Formula: (soma dos min(atual, exigido) / soma dos exigidos) * 100.

    Args:
        trilha_id: Identificador da trilha avaliada.
        skills_usuario: Dicionario {id_skill: nivel_atual}.
        base: Dicionario da base de regras.

    Returns:
        Percentual de prontidao arredondado a 1 casa decimal.
    """
    trilhas = base.get("trilhas", {})
    if trilha_id not in trilhas:
        raise KeyError(f"Trilha '{trilha_id}' nao encontrada na base de conhecimento.")

    skills_junior: dict[str, int] = trilhas[trilha_id].get("skills_junior", {})
    if not skills_junior:
        return 100.0

    soma_atingida = sum(
        min(int(skills_usuario.get(sid, 0)), int(exigido))
        for sid, exigido in skills_junior.items()
    )
    soma_exigida = sum(int(exigido) for exigido in skills_junior.values())

    if soma_exigida == 0:
        return 100.0

    pct = (soma_atingida / soma_exigida) * 100.0
    return round(min(100.0, max(0.0, pct)), 1)


def gerar_roadmap(
    trilha_id: str, gaps: list[dict[str, Any]], base: dict[str, Any]
) -> dict[str, Any]:
    """Elabora o plano estruturado de evolucao personalizado para a trilha.

    Args:
        trilha_id: Identificador da trilha avaliada.
        gaps: Lista gerada por analisar_gaps.
        base: Dicionario da base de regras.

    Returns:
        Dicionario contendo:
          - estudar_primeiro: ate 3 skills com maiores gaps
          - depois: demais tecnologias do roadmap nao presentes em estudar_primeiro
          - certificacoes: lista do JSON
          - projeto_github: descricao com recomendacao adaptada
          - mensagem: orientacao contextual sobre o estagio do usuario
    """
    trilhas = base.get("trilhas", {})
    if trilha_id not in trilhas:
        raise KeyError(f"Trilha '{trilha_id}' nao encontrada na base de conhecimento.")

    trilha = trilhas[trilha_id]
    roadmap_base = trilha.get("roadmap", {})
    tecnologias: list[str] = roadmap_base.get("tecnologias", [])
    certificacoes: list[str] = roadmap_base.get("certificacoes", [])
    projeto_base: str = roadmap_base.get("projeto", "")

    # Ate 3 skills com maiores gaps
    estudar_primeiro = [g["skill"] for g in gaps[:3]]

    # Demais tecnologias do roadmap que nao estao contempladas no bloco imediato
    depois: list[str] = []
    for tec in tecnologias:
        tec_l = tec.lower()
        ja_coberto = False
        for s in estudar_primeiro:
            palavras = [p.lower() for p in s.split() if len(p) >= 4]
            if any(p in tec_l for p in palavras):
                ja_coberto = True
                break
        if not ja_coberto:
            depois.append(tec)

    # Adaptacao do projeto de portfolio
    if gaps:
        skills_destaque = ", ".join(f"**{g['skill']}**" for g in gaps[:2])
        projeto_github = (
            f"{projeto_base} "
            f"Foco pratico recomendado: aplique especialmente {skills_destaque} "
            "ao longo do desenvolvimento deste projeto para consolidar seu aprendizado."
        )
        mensagem = (
            f"Voce possui {len(gaps)} lacuna(s) tecnica(s) identificada(s) para atuar como Junior. "
            "Foque nas habilidades prioritarias para acelerar sua entrada no mercado."
        )
    else:
        projeto_github = (
            f"{projeto_base} "
            "Como voce ja domina as bases necessarias, utilize este projeto para demonstrar "
            "excelencia arquitetural, testes e boas praticas de engenharia."
        )
        mensagem = (
            "Parabens! Voce ja possui todas as competencias tecnicas minimas esperadas para o "
            "nivel Junior nesta trilha. Recomendamos partir diretamente para o projeto de portfolio "
            "e a obtencao das certificacoes sugeridas."
        )

    return {
        "trilha": trilha_id,
        "estudar_primeiro": estudar_primeiro,
        "depois": depois,
        "certificacoes": certificacoes,
        "projeto_github": projeto_github,
        "mensagem": mensagem,
    }


def formatar_roadmap_markdown(
    roadmap: dict[str, Any], gaps: list[dict[str, Any]], prontidao: float
) -> str:
    """Formata o plano de aprendizado em Markdown estruturado para exibicao no Streamlit.

    Args:
        roadmap: Dicionario retornado por gerar_roadmap.
        gaps: Lista retornada por analisar_gaps.
        prontidao: Percentual retornado por calcular_prontidao.

    Returns:
        String formatada em GitHub-Flavored Markdown.
    """
    mapa_niveis = {
        0: "0 (Nao conheco)",
        1: "1 (Basico)",
        2: "2 (Intermediario)",
        3: "3 (Avancado)",
    }

    linhas: list[str] = []
    linhas.append("## Plano de Desenvolvimento e Roadmap de Carreira")
    linhas.append("")
    linhas.append(f"### Nivel de Prontidao para Junior: **{prontidao}%**")
    linhas.append(f"> {roadmap.get('mensagem', '')}")
    linhas.append("")

    # Tabela de Gaps
    if gaps:
        linhas.append("### Diagnostico de Habilidades (Gaps Tecnicos)")
        linhas.append("| Habilidade | Nivel Atual | Minimo Exigido (Junior) | Lacuna (Gap) |")
        linhas.append("| :--- | :---: | :---: | :---: |")
        for g in gaps:
            atual_str = mapa_niveis.get(g["atual"], str(g["atual"]))
            exigido_str = mapa_niveis.get(g["exigido"], str(g["exigido"]))
            linhas.append(
                f"| **{g['skill']}** | {atual_str} | {exigido_str} | **+{g['gap']} nivel(is)** |"
            )
        linhas.append("")
    else:
        linhas.append("### Diagnostico de Habilidades")
        linhas.append("Nenhum gap tecnico detectado para o nivel Junior.")
        linhas.append("")

    # Etapas de Estudo
    linhas.append("### Trilha de Aprendizado Recomendada")
    if roadmap.get("estudar_primeiro"):
        linhas.append("#### 1. Estudar Primeiro (Prioridades Criticas)")
        for item in roadmap["estudar_primeiro"]:
            linhas.append(f"- **{item}**")
        linhas.append("")

    if roadmap.get("depois"):
        linhas.append("#### 2. Na Sequencia (Evolucao e Aprofundamento)")
        for item in roadmap["depois"]:
            linhas.append(f"- {item}")
        linhas.append("")

    # Certificacoes
    if roadmap.get("certificacoes"):
        linhas.append("### Certificacoes Valorizadas pelo Mercado")
        for cert in roadmap["certificacoes"]:
            linhas.append(f"- {cert}")
        linhas.append("")

    # Projeto Pratico de Portfolio
    if roadmap.get("projeto_github"):
        linhas.append("### Projeto Pratico para Portfolio (GitHub)")
        linhas.append(f"{roadmap['projeto_github']}")
        linhas.append("")

    return "\n".join(linhas)


if __name__ == "__main__":
    base_dados = carregar_base(Path(__file__).parent / "regras_carreiras.json")
    trilha_exemplo = "devops_sre"

    # Perfil simulado: usuario com algumas skills parciais para DevOps
    # Exigencias de devops_sre: linux: 2, docker: 2, git: 2, ci_cd: 2, monitoramento: 1, cloud: 1 (Total = 10 niveis)
    skills_usuario_exemplo = {
        "git": 2,  # atende (2/2)
        "linux": 1,  # gap de 1 nivel (1/2)
        "docker": 0,  # gap de 2 niveis (0/2)
        "ci_cd": 0,  # gap de 2 niveis (0/2)
        "monitoramento_observabilidade": 1,  # atende (1/1)
        "cloud_aws_azure_gcp": 0,  # gap de 1 nivel (0/1)
    }

    gaps_identificados = analisar_gaps(trilha_exemplo, skills_usuario_exemplo, base_dados)
    prontidao_calculada = calcular_prontidao(
        trilha_exemplo, skills_usuario_exemplo, base_dados
    )
    roadmap_gerado = gerar_roadmap(trilha_exemplo, gaps_identificados, base_dados)
    relatorio_md = formatar_roadmap_markdown(
        roadmap_gerado, gaps_identificados, prontidao_calculada
    )

    print("=" * 70)
    print("SIMULACAO DO MODULO ROADMAP.PY - TRILHA DEVOPS_SRE")
    print("=" * 70)
    print(f"Prontidao Calculada: {prontidao_calculada}%")
    print(f"Total de Gaps: {len(gaps_identificados)}")
    print("\nRelatorio Formatado em Markdown:\n")
    print(relatorio_md)
    print("=" * 70)
