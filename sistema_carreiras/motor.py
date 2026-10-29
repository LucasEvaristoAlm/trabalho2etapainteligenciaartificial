"""Motor de inferencia para mapeamento e calculo de compatibilidade de carreiras em TI.

Implementa pontuacao ponderada com penalidades e explicabilidade,
sem nenhuma regra, peso ou pergunta hardcoded (100% orientado pela base de conhecimento).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def carregar_base(caminho: str | Path = "regras_carreiras.json") -> dict[str, Any]:
    """Carrega a base de conhecimento declarativa em formato JSON.

    Args:
        caminho: Caminho relativo ou absoluto para o arquivo JSON.

    Returns:
        Dicionario contendo perguntas, catalogo de skills, trilhas e regras.

    Raises:
        FileNotFoundError: Se o arquivo nao existir.
        ValueError: Se o arquivo nao contiver um JSON valido.
    """
    caminho_p = Path(caminho)
    if not caminho_p.exists():
        # Tenta buscar relativo ao diretorio do proprio motor.py se necessario
        caminho_alt = Path(__file__).parent / caminho_p.name
        if caminho_alt.exists():
            caminho_p = caminho_alt
        else:
            raise FileNotFoundError(f"Arquivo de regras nao encontrado: {caminho}")

    try:
        with open(caminho_p, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Erro ao decodificar JSON de regras em '{caminho_p}': {e}") from e


def avaliar_condicao(valor: int, condicao: str) -> bool:
    """Avalia uma expressao condicional numerica simples sobre a resposta Likert.

    Suporta os operadores: '<=', '>=', '<', '>', '=='.

    Args:
        valor: Valor inteiro informado pelo usuario (1 a 5).
        condicao: String de comparacao, ex.: '<=2', '>=4', '<3', '>3', '==5'.

    Returns:
        True se o valor satisfaz a condicao, False caso contrario.

    Raises:
        ValueError: Se o operador for desconhecido ou o formato for invalido.
    """
    cond = condicao.strip()
    try:
        if cond.startswith("<="):
            return valor <= float(cond[2:].strip())
        elif cond.startswith(">="):
            return valor >= float(cond[2:].strip())
        elif cond.startswith("<"):
            return valor < float(cond[1:].strip())
        elif cond.startswith(">"):
            return valor > float(cond[1:].strip())
        elif cond.startswith("=="):
            return valor == float(cond[2:].strip())
        else:
            raise ValueError(f"Operador condicional nao suportado: '{condicao}'")
    except ValueError as e:
        if "could not convert" in str(e):
            raise ValueError(f"Valor numerico invalido na condicao: '{condicao}'") from e
        raise


def calcular_compatibilidade(
    respostas: dict[str, int], base: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    """Calcula a compatibilidade do perfil do usuario para cada trilha da base.

    Algoritmo:
      1. Normaliza cada resposta: c = (resposta - 3) / 2 (escala de -1.0 a +1.0).
      2. contribuicao = c * peso; bruto = soma(contribuicoes); maximo = soma(|pesos| respondidos).
      3. Para cada regra de conflito satisfeita (AND), penalidade_total += penalidade * maximo.
      4. pct = max(0.0, (bruto - penalidade_total) / maximo) * 100, limitado a 100.0 e arredondado a 1 casa.

    Args:
        respostas: Dicionario {id_pergunta: valor_likert (1-5)}.
        base: Dicionario carregado de regras_carreiras.json.

    Returns:
        Dicionario mapeando id_trilha para:
          - pct: float (0.0 a 100.0)
          - bruto: float
          - penalidades_aplicadas: list[str] (motivos)
          - contribuicoes: list[tuple[str, float]] ordenada por valor decrescente
          - trilha: str (id da trilha)

    Raises:
        ValueError: Se alguma resposta estiver fora da escala 1 a 5.
    """
    # Validacao de robustez dos valores fornecidos
    for qid, val in respostas.items():
        if not isinstance(val, (int, float)) or int(val) < 1 or int(val) > 5:
            raise ValueError(
                f"Valor de resposta invalido para a pergunta '{qid}': {val}. "
                "As respostas devem ser inteiros entre 1 e 5."
            )

    trilhas = base.get("trilhas", {})
    regras_conflito = base.get("regras_conflito", [])
    resultado: dict[str, dict[str, Any]] = {}

    for trilha_id, trilha_info in trilhas.items():
        pesos: dict[str, float] = trilha_info.get("pesos", {})

        contribuicoes: list[tuple[str, float]] = []
        bruto = 0.0
        maximo = 0.0

        for qid, peso in pesos.items():
            if qid in respostas:
                resp = int(respostas[qid])
                c = (resp - 3) / 2.0  # varia de -1.0 a +1.0
                contrib = c * float(peso)
                contribuicoes.append((qid, round(contrib, 3)))
                bruto += contrib
                maximo += abs(float(peso))

        # Ordenar contribuicoes da maior para a menor
        contribuicoes.sort(key=lambda item: item[1], reverse=True)

        # Avaliacao das regras de conflito (conjuncao AND)
        penalidades_aplicadas: list[str] = []
        penalidade_acumulada = 0.0

        for regra in regras_conflito:
            if regra.get("trilha") == trilha_id:
                condicoes = regra.get("se", {})
                # Todas as condicoes do "se" precisam estar nas respostas e ser verdadeiras
                todas_satisfeitas = True
                if not condicoes:
                    todas_satisfeitas = False

                for q_cond_id, cond_expr in condicoes.items():
                    if q_cond_id not in respostas:
                        todas_satisfeitas = False
                        break
                    if not avaliar_condicao(int(respostas[q_cond_id]), cond_expr):
                        todas_satisfeitas = False
                        break

                if todas_satisfeitas:
                    fator_penalidade = float(regra.get("penalidade", 0.0))
                    penalidade_acumulada += fator_penalidade * maximo
                    motivo = regra.get("motivo", "Regra de conflito acionada.")
                    penalidades_aplicadas.append(motivo)

        # Calculo do percentual final
        if maximo == 0.0:
            pct = 0.0
        else:
            pct_calculado = ((bruto - penalidade_acumulada) / maximo) * 100.0
            pct = max(0.0, min(100.0, pct_calculado))

        resultado[trilha_id] = {
            "trilha": trilha_id,
            "pct": round(pct, 1),
            "bruto": round(bruto, 3),
            "penalidades_aplicadas": penalidades_aplicadas,
            "contribuicoes": contribuicoes,
        }

    return resultado


def top_n(resultado: dict[str, dict[str, Any]], n: int = 3) -> list[tuple[str, dict[str, Any]]]:
    """Retorna as N trilhas com maior percentual de compatibilidade.

    Args:
        resultado: Dicionario retornado por calcular_compatibilidade.
        n: Quantidade de trilhas a retornar.

    Returns:
        Lista ordenada de tuplas (id_trilha, dados_trilha) do maior para o menor pct.
    """
    itens = list(resultado.items())
    itens.sort(key=lambda item: (item[1].get("pct", 0.0), item[1].get("bruto", 0.0)), reverse=True)
    return itens[:n]


def detectar_empate(top: list[Any], margem: float = 5.0) -> list[str]:
    """Identifica trilhas no topo cuja diferenca para a 1ª seja menor que a margem.

    Suporta listas de tuplas (id_trilha, dados) ou dicionarios contendo 'pct'.

    Args:
        top: Lista das principais trilhas (tipicamente resultado de top_n).
        margem: Diferenca percentual maxima em relacao a primeira colocada.

    Returns:
        Lista com os IDs das trilhas que estao dentro da margem de empate da lider.
    """
    if not top:
        return []

    def _extrair(item: Any) -> tuple[str, float]:
        if isinstance(item, tuple) and len(item) == 2:
            tid = str(item[0])
            pct = float(item[1].get("pct", 0.0)) if isinstance(item[1], dict) else float(item[1])
            return tid, pct
        elif isinstance(item, dict):
            tid = str(item.get("trilha", ""))
            pct = float(item.get("pct", 0.0))
            return tid, pct
        raise ValueError(f"Formato de item nao suportado em detectar_empate: {type(item)}")

    primeiro_id, primeiro_pct = _extrair(top[0])
    empatadas: list[str] = [primeiro_id]

    for item in top[1:]:
        tid, pct = _extrair(item)
        if (primeiro_pct - pct) < margem:
            empatadas.append(tid)

    return empatadas


def gerar_justificativa(
    trilha_id: str, resultado: dict[str, dict[str, Any]], base: dict[str, Any]
) -> str:
    """Gera texto explicativo em portugues sobre a compatibilidade calculada para uma trilha.

    Cita as 2 ou 3 perguntas que mais impulsionaram a pontuacao e as penalidades
    que eventualmente tenham sido aplicadas por regras de conflito.

    Args:
        trilha_id: ID da trilha a justificar.
        resultado: Dicionario de resultados de calcular_compatibilidade.
        base: Dicionario da base de regras.

    Returns:
        String formatada em linguagem natural explicando o resultado.
    """
    if trilha_id not in resultado:
        return f"Trilha '{trilha_id}' nao encontrada nos resultados calculados."

    dados = resultado[trilha_id]
    pct = dados.get("pct", 0.0)

    trilhas_info = base.get("trilhas", {})
    nome_trilha = trilhas_info.get(trilha_id, {}).get("nome", trilha_id)

    # Mapeamento rapido de id_pergunta para texto amigavel
    mapa_perguntas = {p["id"]: p.get("texto", p["id"]) for p in base.get("perguntas", [])}

    contribuicoes = dados.get("contribuicoes", [])
    # Selecionar ate 3 maiores contribuicoes positivas
    positivas = [c for c in contribuicoes if c[1] > 0][:3]
    if not positivas and contribuicoes:
        positivas = contribuicoes[:2]

    linhas: list[str] = []
    linhas.append(f"Compatibilidade de {pct}% com a trilha de {nome_trilha}:")

    if positivas:
        linhas.append("Principais fatores que impulsionaram seu encaixe:")
        for qid, valor in positivas:
            texto_p = mapa_perguntas.get(qid, qid)
            linhas.append(f"  - (+{valor:.2f}) \"{texto_p}\"")
    else:
        linhas.append("Nao houve respostas com contribuicao positiva expressiva para esta trilha.")

    penalidades = dados.get("penalidades_aplicadas", [])
    if penalidades:
        linhas.append("Penalidades aplicadas por conflito de perfil:")
        for motivo in penalidades:
            linhas.append(f"  - {motivo}")

    return "\n".join(linhas)


if __name__ == "__main__":
    # Teste de demonstracao com perfil com alta afinidade para DevOps / SRE
    base_conhecimento = carregar_base(Path(__file__).parent / "regras_carreiras.json")

    perfil_devops = {
        "afinidade_automacao": 5,
        "afinidade_infraestrutura_servidores": 5,
        "afinidade_resolucao_problemas_pressao": 5,
        "afinidade_computacao_nuvem": 4,
        "afinidade_seguranca_sistemas": 4,
        "afinidade_design_visual": 1,
        "objetivo_interfaces_usuarios": 1,
        "objetivo_liderar_equipes": 2,
        "afinidade_logica_algoritmos": 4,
        "afinidade_programacao_web": 3,
        "afinidade_trabalho_dados": 3,
    }

    resultado_simulacao = calcular_compatibilidade(perfil_devops, base_conhecimento)
    melhores = top_n(resultado_simulacao, n=3)
    empates = detectar_empate(melhores, margem=5.0)

    print("=" * 70)
    print("SIMULACAO DE MOTOR DE INFERENCIA - PERFIL DEVOPS/SRE")
    print("=" * 70)

    for posicao, (tid, info) in enumerate(melhores, start=1):
        nome = base_conhecimento["trilhas"].get(tid, {}).get("nome", tid)
        print(f"\n#{posicao} - {nome} ({tid}): {info['pct']}% (Bruto: {info['bruto']})")
        justificativa = gerar_justificativa(tid, resultado_simulacao, base_conhecimento)
        print(justificativa)

    print("\n" + "-" * 70)
    if len(empates) > 1:
        print(f"Empate tecnico detectado (diferenca < 5% da 1ª): {empates}")
    else:
        print(f"Lider isolado: {empates[0]}")
    print("=" * 70)
