import os
import warnings
import logging
from dotenv import load_dotenv
from google import genai

# Silencia avisos informativos internos da biblioteca da Google
warnings.filterwarnings("ignore", category=UserWarning)
logging.getLogger("google.genai").setLevel(logging.ERROR)

# Carrega variáveis do .env
load_dotenv()


def generate_task_markdown(task_title, blocks, additional_prompt="", existing_markdown="", topic_comments=None):
    """
    Usa o Gemini para gerar/atualizar de forma incremental o Markdown da tarefa
    levando em consideração a ordem de prioridade dos blocos, a documentação existente e comentários por tópico.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "COLE_SUA_CHAVE_AQUI":
        raise ValueError("Chave da API do Gemini não configurada no arquivo .env")
        
    client = genai.Client(api_key=api_key)

    # Montar os blocos ordenados por prioridade (do topo para a base)
    blocks_text_lines = []
    for idx, b in enumerate(blocks, start=1):
        b_type = b.get('type', 'Informação')
        b_content = b.get('content', '')
        prefix = f"[Prioridade #{idx}]"
        if b_type and b_type not in ['Informação', 'Bloco']:
            prefix += f" [{b_type}]"
        blocks_text_lines.append(f"{prefix}: {b_content}")
    
    blocks_text = "\n".join(blocks_text_lines) if blocks_text_lines else "Nenhum bloco adicional fornecido."
    
    existing_doc_prompt = ""
    if existing_markdown and existing_markdown.strip():
        existing_doc_prompt = f"""
DOCUMENTAÇÃO ATUALMENTE EXISTENTE:
{existing_markdown.strip()}

INSTRUÇÃO IMPORTANTE SOBRE O CONTEÚDO EXISTENTE:
- A documentação acima já foi gerada em etapas anteriores. Preserve e enriqueça as seções existentes.
- Incorpore as novas informações e blocos de forma incremental sem apagar o histórico ou descartar detalhes já documentados, a não ser que uma reestruturação seja estritamente necessária para a clareza técnica.
"""

    comments_prompt = ""
    if topic_comments and len(topic_comments) > 0:
        comment_lines = [f"- No tópico/seção '{tc['topic_title']}': \"{tc['comment_text']}\"" for tc in topic_comments]
        comments_prompt = f"""
COMENTÁRIOS E SOLICITAÇÕES DO USUÁRIO EM TÓPICOS ESPECÍFICOS DO DOCUMENTO:
{chr(10).join(comment_lines)}

INSTRUÇÃO SOBRE OS COMENTÁRIOS DOS TÓPICOS:
- Aplique obrigatoriamente as alterações, ajustes e inclusões solicitadas em cada um dos tópicos indicados acima.
"""

    prompt = f"""
Você é um gerente de projetos técnico e especialista em engenharia de requisitos.
Sua missão é compilar e organizar a pilha de blocos de informação de uma tarefa em um documento Markdown profissional, elegante e bem estruturado.

TÍTULO DA TAREFA: {task_title}

{existing_doc_prompt}

{comments_prompt}

PILHA DE BLOCOS DE INFORMAÇÃO (ORDENADA POR PRIORIDADE - DO TOPO PARA A BASE):
{blocks_text}

INSTRUÇÕES EXTRAS DO USUÁRIO:
{additional_prompt if additional_prompt else 'Nenhuma.'}

DIRETRIZES DE PROCESSAMENTO:
1. Respeite a prioridade das informações: os blocos no topo (Prioridade #1, #2...) representam as definições mais importantes.
2. Analise semanticamente o conteúdo e organize o documento em seções claras (Descrição Geral, Regras de Negócio, Requisitos Técnicos, Critérios de Aceite, etc.).
3. Aplique todos os comentários feitos pelo usuário nos tópicos correspondentes.
4. Comece o documento com o título da tarefa em h1 (# {task_title}).
5. Retorne APENAS o texto bruto formatado em Markdown, sem blocos de código (```markdown) em volta do texto final.
"""
    
    models_to_try = ['gemini-3.0-flash', 'gemini-3.5-flash']
    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            return response.text.strip()
        except Exception as e:
            print(f"Erro ao gerar markdown com o modelo {model_name}: {e}")
            continue
            
    raise Exception("Todos os modelos falharam na geração de conteúdo.")


def reformulate_task_markdown(task_title, current_markdown, comment):
    """
    Solicita ao Gemini a reformulação direcionada da documentação com base em um comentário do usuário.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "COLE_SUA_CHAVE_AQUI":
        raise ValueError("Chave da API do Gemini não configurada no arquivo .env")
        
    client = genai.Client(api_key=api_key)

    prompt = f"""
Você é um gerente de projetos técnico e arquiteto de software.
O usuário fez uma solicitação de alteração/comentário sobre a documentação técnica atual de uma tarefa.

TÍTULO DA TAREFA: {task_title}

SOLICITAÇÃO DE ALTERAÇÃO DO USUÁRIO:
"{comment}"

DOCUMENTAÇÃO ATUAL EM MARKDOWN:
{current_markdown if current_markdown else 'Nenhuma documentação existente.'}

DIRETRIZES DE REFORMULAÇÃO:
1. Leia o comentário do usuário atentamente e aplique exatamente as modificações, inclusões ou correções solicitadas.
2. Mantenha a estrutura, o tom técnico e a coerência do restante do documento que não foi afetado pela alteração.
3. Comece com o título da tarefa em h1 (# {task_title}).
4. Retorne APENAS o texto bruto formatado em Markdown, sem blocos de código (```markdown) em volta do texto final.
"""

    models_to_try = ['gemini-3.0-flash', 'gemini-3.5-flash']
    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            return response.text.strip()
        except Exception as e:
            print(f"Erro ao reformular markdown com o modelo {model_name}: {e}")
            continue
            
    raise Exception("Todos os modelos falharam na geração de conteúdo.")


