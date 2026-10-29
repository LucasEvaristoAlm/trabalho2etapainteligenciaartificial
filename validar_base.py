"""Script de validacao da base de conhecimento regras_carreiras.json."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def validar_base_conhecimento(caminho_json: Path) -> list[str]:
    """Carrega o JSON e valida todas as restricoes da Fase 1."""
    erros: list[str] = []

    if not caminho_json.exists():
        return [f"Arquivo nao encontrado: {caminho_json}"]

    try:
        with open(caminho_json, "r", encoding="utf-8") as f:
            dados = json.load(f)
    except Exception as e:
        return [f"Erro ao ler JSON: {e}"]

    # 1. Validacao de chaves raiz
    chaves_esperadas = {"niveis_resposta", "perguntas", "skills_catalogo", "trilhas", "regras_conflito"}
    chaves_presentes = set(dados.keys())
    if not chaves_esperadas.issubset(chaves_presentes):
        erros.append(f"Chaves raiz faltantes: {chaves_esperadas - chaves_presentes}")

    # 2. Catalogo de perguntas
    perguntas = dados.get("perguntas", [])
    ids_perguntas: set[str] = set()
    for idx, p in enumerate(perguntas):
        pid = p.get("id")
        if not pid:
            erros.append(f"Pergunta no indice {idx} sem campo 'id'")
        elif pid in ids_perguntas:
            erros.append(f"ID de pergunta duplicado: {pid}")
        else:
            ids_perguntas.add(pid)

        if not p.get("texto"):
            erros.append(f"Pergunta '{pid}' sem 'texto'")
        if p.get("passo") not in (2, 3):
            erros.append(f"Pergunta '{pid}' com passo invalido: {p.get('passo')} (esperado 2 ou 3)")

    # 3. Catalogo de skills
    skills_catalogo = dados.get("skills_catalogo", {})
    if not isinstance(skills_catalogo, dict):
        erros.append("skills_catalogo deve ser um dicionario")
    elif len(skills_catalogo) < 30 or len(skills_catalogo) > 40:
        erros.append(f"skills_catalogo deve ter entre 30 e 40 itens, encontrado: {len(skills_catalogo)}")
    ids_skills = set(skills_catalogo.keys())

    # 4. Trilhas
    trilhas_esperadas = {
        "backend", "frontend_ux", "cientista_dados", "engenheiro_dados",
        "ciberseguranca", "devops_sre", "cloud_architecture", "mobile",
        "qa", "product_management"
    }
    trilhas = dados.get("trilhas", {})
    if not isinstance(trilhas, dict):
        erros.append("trilhas deve ser um dicionario")
    else:
        trilhas_chaves = set(trilhas.keys())
        if trilhas_chaves != trilhas_esperadas:
            erros.append(f"IDs de trilhas divergem do contrato. Diferenca: {trilhas_chaves ^ trilhas_esperadas}")

        for tid, tinfo in trilhas.items():
            # Nome e descricao
            if not tinfo.get("nome"):
                erros.append(f"Trilha '{tid}' sem campo 'nome'")
            if not tinfo.get("descricao"):
                erros.append(f"Trilha '{tid}' sem campo 'descricao'")

            # Pesos
            pesos = tinfo.get("pesos")
            if not isinstance(pesos, dict):
                erros.append(f"Trilha '{tid}' deve conter dicionario 'pesos'")
            else:
                if not (5 <= len(pesos) <= 9):
                    erros.append(f"Trilha '{tid}' tem {len(pesos)} pesos (deve ter entre 5 e 9)")
                tem_negativo = False
                for qid, peso in pesos.items():
                    if qid not in ids_perguntas:
                        erros.append(f"Trilha '{tid}' referencia pergunta inexistente nos pesos: '{qid}'")
                    if not isinstance(peso, (int, float)):
                        erros.append(f"Trilha '{tid}', peso para '{qid}' nao e numerico: {peso}")
                    else:
                        if peso < -1.0 or peso > 1.0:
                            erros.append(f"Trilha '{tid}', peso para '{qid}' ({peso}) fora de [-1.0, 1.0]")
                        if peso < 0:
                            tem_negativo = True
                if not tem_negativo:
                    erros.append(f"Trilha '{tid}' deve ter ao menos 1 peso negativo")

            # Skills junior
            skills_junior = tinfo.get("skills_junior")
            if not isinstance(skills_junior, dict):
                erros.append(f"Trilha '{tid}' deve conter dicionario 'skills_junior'")
            else:
                if not (5 <= len(skills_junior) <= 8):
                    erros.append(f"Trilha '{tid}' tem {len(skills_junior)} skills_junior (deve ter entre 5 e 8)")
                for sid, nivel in skills_junior.items():
                    if sid not in ids_skills:
                        erros.append(f"Trilha '{tid}' referencia skill inexistente em skills_junior: '{sid}'")
                    if nivel not in (1, 2, 3):
                        erros.append(f"Trilha '{tid}', nivel para '{sid}' ({nivel}) deve ser 1, 2 ou 3")

            # Roadmap
            roadmap = tinfo.get("roadmap")
            if not isinstance(roadmap, dict):
                erros.append(f"Trilha '{tid}' deve conter dicionario 'roadmap'")
            else:
                tecs = roadmap.get("tecnologias", [])
                certs = roadmap.get("certificacoes", [])
                proj = roadmap.get("projeto", "")

                if not isinstance(tecs, list) or len(tecs) == 0:
                    erros.append(f"Trilha '{tid}' roadmap.tecnologias deve ser lista nao vazia")
                if not isinstance(certs, list) or not (2 <= len(certs) <= 3):
                    erros.append(f"Trilha '{tid}' roadmap.certificacoes deve ter 2 ou 3 certificacoes (possui {len(certs)})")
                if not isinstance(proj, str) or len(proj.strip()) < 15:
                    erros.append(f"Trilha '{tid}' roadmap.projeto deve ser uma descricao detalhada")

    # 5. Regras de conflito
    regras_conflito = dados.get("regras_conflito", [])
    if not isinstance(regras_conflito, list):
        erros.append("regras_conflito deve ser uma lista")
    elif len(regras_conflito) < 8:
        erros.append(f"regras_conflito deve ter ao menos 8 regras (possui {len(regras_conflito)})")
    else:
        regex_condicao = re.compile(r"^(<=|>=|<|>|==)[1-5]$")
        for idx, regra in enumerate(regras_conflito):
            se = regra.get("se")
            trilha = regra.get("trilha")
            penalidade = regra.get("penalidade")
            motivo = regra.get("motivo")

            if not isinstance(se, dict) or len(se) == 0:
                erros.append(f"Regra de conflito #{idx} com campo 'se' invalido")
            else:
                for qid, cond in se.items():
                    if qid not in ids_perguntas:
                        erros.append(f"Regra de conflito #{idx} referencia pergunta inexistente: '{qid}'")
                    if not isinstance(cond, str) or not regex_condicao.match(cond):
                        erros.append(f"Regra de conflito #{idx} condicao invalida '{cond}' para '{qid}'")

            if trilha not in trilhas_esperadas:
                erros.append(f"Regra de conflito #{idx} referencia trilha desconhecida: '{trilha}'")

            if not isinstance(penalidade, (int, float)) or not (0.10 <= penalidade <= 0.25):
                erros.append(f"Regra de conflito #{idx} penalidade ({penalidade}) fora do intervalo [0.10, 0.25]")

            if not isinstance(motivo, str) or len(motivo.strip()) < 10:
                erros.append(f"Regra de conflito #{idx} motivo vazio ou curto demais")

    return erros


def main() -> None:
    caminho = Path("sistema_carreiras/regras_carreiras.json")
    print(f"Validando arquivo: {caminho.resolve()} ...")
    erros = validar_base_conhecimento(caminho)

    if erros:
        print("\n[ERRO] Foram encontrados os seguintes problemas:")
        for e in erros:
            print(f" - {e}")
        sys.exit(1)
    else:
        print("\n[OK] Base de conhecimento perfeitamente validada!")
        print(" - Todas as 10 trilhas possuem pesos, skills_junior e roadmap completos.")
        print(" - Todos os IDs de perguntas e skills referenciados existem no catalogo.")
        print(" - Todos os pesos estao no intervalo [-1.0, 1.0] com ao menos 1 negativo por trilha.")
        print(" - Regras de conflito validadas com sucesso (conjuncao 'se', trilha, penalidade e motivo).")
        sys.exit(0)


if __name__ == "__main__":
    main()
