import os
from dotenv import load_dotenv
from google import genai

# Carrega variáveis do .env
load_dotenv()

def generate_task_markdown(task_title, blocks, additional_prompt=""):
    """
    Usa o Gemini para gerar um Markdown bem estruturado da tarefa
    com base nos blocos e no prompt adicional.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "COLE_SUA_CHAVE_AQUI":
        raise ValueError("Chave da API do Gemini não configurada no arquivo .env")
        
    client = genai.Client(api_key=api_key)

    # Montar o conteúdo para a IA
    blocks_text = "\n".join([f"- [{b['type']}] {b['content']}" for b in blocks])
    
    prompt = f"""
Você é um gerente de projetos técnico e assistente de desenvolvimento.
Sua missão é gerar um documento Markdown bem estruturado, limpo e profissional para a seguinte tarefa:

TÍTULO DA TAREFA: {task_title}

BLOCOS DE INFORMAÇÃO ADICIONADOS PELA EQUIPE:
{blocks_text}

INSTRUÇÕES EXTRAS DO USUÁRIO:
{additional_prompt if additional_prompt else 'Nenhuma.'}

REGRAS PARA O MARKDOWN:
1. Comece com o título da tarefa em h1 (#).
2. Organize as informações de forma lógica usando cabeçalhos (##, ###).
3. Agrupe regras de negócios, requisitos técnicos, observações, etc.
4. Se o usuário forneceu "Instruções Extras", aplique as regras/pedidos ali contidos.
5. Retorne APENAS o conteúdo em Markdown, sem blocos genéricos de código (```markdown) em volta de tudo, apenas o texto bruto formatado.
"""
    
    response = client.models.generate_content(
        model='gemini-3.6-flash',
        contents=prompt
    )
    return response.text.strip()
