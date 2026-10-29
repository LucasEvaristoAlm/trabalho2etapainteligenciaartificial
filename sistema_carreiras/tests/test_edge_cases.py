"""Testes automatizados e casos de borda com pytest para o Sistema Especialista.

Cobre os 9 cenarios criticos de avaliacao de regras, motor de inferencia,
analise de gaps, prontidao e integridade da base de conhecimento JSON.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

# Adiciona o diretorio pai ao sys.path para importacao direta dos modulos do sistema
caminho_sistema = Path(__file__).resolve().parent.parent
if str(caminho_sistema) not in sys.path:
    sys.path.insert(0, str(caminho_sistema))

from motor import (
    calcular_compatibilidade,
    carregar_base,
    detectar_empate,
    top_n,
)
from roadmap import (
    analisar_gaps,
    calcular_prontidao,
)


@pytest.fixture(scope="session")
def base_conhecimento() -> dict[str, Any]:
    """Carrega a base de regras uma unica vez para a sessao de testes."""
    caminho_json = caminho_sistema / "regras_carreiras.json"
    return carregar_base(caminho_json)


# ---------------------------------------------------------------------------
# Cenario 1: Perfil dados + web
# ---------------------------------------------------------------------------
def test_perfil_dados_e_web(base_conhecimento: dict[str, Any]) -> None:
    """Perfil com alta afinidade em matematica, dados e programacao web.

    Deve posicionar no Top 3 tanto trilha de dados (cientista ou engenheiro)
    quanto trilha de desenvolvimento (backend ou frontend/web), e detectar empate parcial.
    """
    respostas = {
        "afinidade_matematica_estatistica": 5,
        "afinidade_trabalho_dados": 5,
        "afinidade_programacao_web": 5,
        "afinidade_logica_algoritmos": 4,
        "objetivo_dados_escala": 4,
    }

    resultado = calcular_compatibilidade(respostas, base_conhecimento)
    top_tres = top_n(resultado, n=3)
    ids_top3 = [t[0] for t in top_tres]

    trilhas_dados = {"cientista_dados", "engenheiro_dados"}
    trilhas_dev = {"backend", "frontend_ux"}

    tem_dados = any(tid in trilhas_dados for tid in ids_top3)
    tem_dev = any(tid in trilhas_dev for tid in ids_top3)

    assert tem_dados, f"Top 3 deveria conter trilha de dados, obtido: {ids_top3}"
    assert tem_dev, f"Top 3 deveria conter trilha de desenvolvimento, obtido: {ids_top3}"

    empate = detectar_empate(top_tres, margem=5.0)
    assert len(empate) > 1, f"Deveria sinalizar empate parcial entre as lideres, obtido: {empate}"


# ---------------------------------------------------------------------------
# Cenario 2: Tudo 3 (neutro)
# ---------------------------------------------------------------------------
def test_perfil_neutro_tudo_tres(base_conhecimento: dict[str, Any]) -> None:
    """Todas as perguntas respondidas com valor 3 (neutro).

    Nenhuma trilha deve ultrapassar limiar baixo (ou percentuais minimos),
    sem quebras ou divisoes por zero no sistema.
    """
    respostas = {p["id"]: 3 for p in base_conhecimento["perguntas"]}

    resultado = calcular_compatibilidade(respostas, base_conhecimento)

    for tid, info in resultado.items():
        assert info["pct"] <= 10.0, f"Trilha '{tid}' com pct elevado ({info['pct']}%) em perfil neutro"
        assert info["bruto"] == 0.0, f"Trilha '{tid}' com pontuacao bruta nao nula: {info['bruto']}"


# ---------------------------------------------------------------------------
# Cenario 3: Tudo 5 (maximo em tudo)
# ---------------------------------------------------------------------------
def test_limite_superior_tudo_cinco(base_conhecimento: dict[str, Any]) -> None:
    """Todas as perguntas com valor maximo 5.

    Nenhuma trilha pode ultrapassar 100% de compatibilidade.
    """
    respostas = {p["id"]: 5 for p in base_conhecimento["perguntas"]}

    resultado = calcular_compatibilidade(respostas, base_conhecimento)

    for tid, info in resultado.items():
        assert info["pct"] <= 100.0, f"Trilha '{tid}' ultrapassou 100%: {info['pct']}%"
        assert info["pct"] >= 0.0, f"Trilha '{tid}' com pct negativo: {info['pct']}%"


# ---------------------------------------------------------------------------
# Cenario 4: Tudo 1 (minimo em tudo)
# ---------------------------------------------------------------------------
def test_limite_inferior_tudo_um(base_conhecimento: dict[str, Any]) -> None:
    """Todas as perguntas com valor minimo 1.

    Nenhum percentual pode ser inferior a 0%.
    """
    respostas = {p["id"]: 1 for p in base_conhecimento["perguntas"]}

    resultado = calcular_compatibilidade(respostas, base_conhecimento)

    for tid, info in resultado.items():
        assert info["pct"] >= 0.0, f"Trilha '{tid}' com pct inferior a 0%: {info['pct']}%"
        assert info["pct"] <= 100.0, f"Trilha '{tid}' com pct invalido: {info['pct']}%"


# ---------------------------------------------------------------------------
# Cenario 5: Perfil conflitante
# ---------------------------------------------------------------------------
def test_perfil_conflitante_design_vs_infra_logica(base_conhecimento: dict[str, Any]) -> None:
    """Usuario adora design visual e experiencia do usuario, mas rejeita logica e infraestrutura.

    frontend_ux ou product_management deve liderar, e penalidades devem
    aparecer nos motivos de trilhas tecnicas como ciberseguranca ou devops_sre.
    """
    respostas = {
        "afinidade_design_visual": 5,
        "afinidade_experiencia_usuario": 5,
        "objetivo_interfaces_usuarios": 5,
        "afinidade_gestao_pessoas_produto": 4,
        "afinidade_logica_algoritmos": 1,
        "afinidade_infraestrutura_servidores": 1,
        "afinidade_seguranca_sistemas": 1,
        "afinidade_automacao": 1,
    }

    resultado = calcular_compatibilidade(respostas, base_conhecimento)
    top_tres = top_n(resultado, n=3)
    lider = top_tres[0][0]

    assert lider in (
        "frontend_ux",
        "product_management",
    ), f"Lider inesperado para perfil de design/produto: '{lider}'"

    # Verificar se trilhas tecnicas registraram penalidades em penalidades_aplicadas
    penalidades_tecnicas: list[str] = []
    for tid in ("ciberseguranca", "devops_sre", "backend"):
        penalidades_tecnicas.extend(resultado[tid].get("penalidades_aplicadas", []))

    assert len(penalidades_tecnicas) > 0, "Trilhas tecnicas deveriam ter sofrido penalidades por conflito."


# ---------------------------------------------------------------------------
# Cenario 6: Respostas parciais
# ---------------------------------------------------------------------------
def test_respostas_parciais_sem_excecao(base_conhecimento: dict[str, Any]) -> None:
    """Usuario respondeu apenas metade das perguntas cadastradas.

    O motor deve processar normalmente, desconsiderando as omissas sem gerar erros.
    """
    todas_perguntas = base_conhecimento["perguntas"]
    metade = todas_perguntas[: len(todas_perguntas) // 2]
    respostas_parciais = {p["id"]: 4 for p in metade}

    resultado = calcular_compatibilidade(respostas_parciais, base_conhecimento)

    assert len(resultado) == 10, "Todas as 10 trilhas devem estar presentes no resultado."
    for tid, info in resultado.items():
        assert "pct" in info and 0.0 <= info["pct"] <= 100.0


# ---------------------------------------------------------------------------
# Cenario 7: Valor invalido (fora da escala 1 a 5)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("valor_invalido", [0, 6, -1, 10])
def test_valor_invalido_lanca_value_error(
    base_conhecimento: dict[str, Any], valor_invalido: int
) -> None:
    """Respostas fora do intervalo 1-5 devem levantar ValueError com explicacao."""
    respostas = {"afinidade_automacao": valor_invalido}

    with pytest.raises(ValueError) as excinfo:
        calcular_compatibilidade(respostas, base_conhecimento)

    assert "1 e 5" in str(excinfo.value)


# ---------------------------------------------------------------------------
# Cenario 8: Usuario que atende todos os skills Junior
# ---------------------------------------------------------------------------
def test_usuario_atende_todos_skills_junior(base_conhecimento: dict[str, Any]) -> None:
    """Usuario possui nivel de competencia igual ou superior ao exigido na trilha.

    Deve resultar em lista de gaps vazia e prontidao 100.0%.
    """
    trilha_id = "backend"
    skills_exigidas = base_conhecimento["trilhas"][trilha_id]["skills_junior"]

    # Cria perfil de usuario que domina ou supera todos os requisitos
    skills_usuario = {sid: nivel + 1 for sid, nivel in skills_exigidas.items()}

    gaps = analisar_gaps(trilha_id, skills_usuario, base_conhecimento)
    prontidao = calcular_prontidao(trilha_id, skills_usuario, base_conhecimento)

    assert len(gaps) == 0, f"Lista de gaps deveria estar vazia, obtido: {gaps}"
    assert prontidao == 100.0, f"Prontidao deveria ser 100.0%, obtido: {prontidao}%"


# ---------------------------------------------------------------------------
# Cenario 9: Integridade estrutural e referencial da base
# ---------------------------------------------------------------------------
def test_integridade_base_conhecimento(base_conhecimento: dict[str, Any]) -> None:
    """Garante que todas as 10 trilhas possuem pesos, skills_junior e roadmap validos,

    e que todos os IDs referenciados cruzam perfeitamente com os catalogos de perguntas e skills.
    """
    trilhas_esperadas = {
        "backend", "frontend_ux", "cientista_dados", "engenheiro_dados",
        "ciberseguranca", "devops_sre", "cloud_architecture", "mobile",
        "qa", "product_management"
    }

    trilhas = base_conhecimento.get("trilhas", {})
    assert set(trilhas.keys()) == trilhas_esperadas, "Divergencia nos IDs das 10 trilhas do contrato."

    ids_perguntas = {p["id"] for p in base_conhecimento.get("perguntas", [])}
    ids_skills = set(base_conhecimento.get("skills_catalogo", {}).keys())

    for tid, tinfo in trilhas.items():
        # Validacao dos pesos
        pesos = tinfo.get("pesos", {})
        assert 5 <= len(pesos) <= 9, f"Trilha '{tid}' tem quantidade de pesos fora de [5, 9]: {len(pesos)}"
        assert any(peso < 0 for peso in pesos.values()), f"Trilha '{tid}' nao possui peso negativo."
        for qid, peso in pesos.items():
            assert qid in ids_perguntas, f"Trilha '{tid}' referencia pergunta inexistente: '{qid}'"
            assert -1.0 <= peso <= 1.0, f"Trilha '{tid}', peso '{qid}' fora de [-1, 1]: {peso}"

        # Validacao de skills junior
        skills_jr = tinfo.get("skills_junior", {})
        assert 5 <= len(skills_jr) <= 8, f"Trilha '{tid}' com skills_junior fora de [5, 8]: {len(skills_jr)}"
        for sid, nivel in skills_jr.items():
            assert sid in ids_skills, f"Trilha '{tid}' referencia skill inexistente: '{sid}'"
            assert nivel in (1, 2, 3), f"Trilha '{tid}', nivel invalido para '{sid}': {nivel}"

        # Validacao de roadmap
        roadmap = tinfo.get("roadmap", {})
        assert len(roadmap.get("tecnologias", [])) > 0, f"Trilha '{tid}' sem tecnologias no roadmap"
        assert 2 <= len(roadmap.get("certificacoes", [])) <= 3, f"Trilha '{tid}' certificacoes fora de [2, 3]"
        assert len(roadmap.get("projeto", "").strip()) >= 20, f"Trilha '{tid}' projeto muito curto ou vazio"

    # Validacao das regras de conflito
    regras_conflito = base_conhecimento.get("regras_conflito", [])
    assert len(regras_conflito) >= 8, f"Esperado ao menos 8 regras de conflito, obtido: {len(regras_conflito)}"
    for idx, regra in enumerate(regras_conflito):
        assert regra.get("trilha") in trilhas_esperadas, f"Regra #{idx} com trilha desconhecida"
        assert 0.10 <= regra.get("penalidade", 0.0) <= 0.25, f"Regra #{idx} com penalidade fora de [0.10, 0.25]"
        for qid in regra.get("se", {}).keys():
            assert qid in ids_perguntas, f"Regra #{idx} referencia pergunta inexistente: '{qid}'"
