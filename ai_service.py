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

    # Montar o conteúdo dos blocos para a IA
    blocks_text = "\n".join([
        f"- [{b['type']}] {b['content']}" if b['type'] not in ['Informação', 'Bloco', ''] else f"- {b['content']}"
        for b in blocks
    ])
    
    prompt = f"""
Você é um gerente de projetos técnico e especialista em engenharia de requisitos.
Sua missão é compilar e organizar os blocos de informação brutos de uma tarefa em um documento Markdown profissional, elegante e bem estruturado.

TÍTULO DA TAREFA: {task_title}

BLOCO(S) DE INFORMAÇÃO FORNECIDO(S):
{blocks_text}

INSTRUÇÕES EXTRAS DO USUÁRIO:
{additional_prompt if additional_prompt else 'Nenhuma.'}

DIRETRIZES DE ORGANIZAÇÃO E PROCESSAMENTO:
1. Analise semanticamente o conteúdo de cada bloco de informação. Identifique automaticamente os tópicos pertinentes (como Descrição Geral, Regras de Negócio, Requisitos Técnicos, Critérios de Aceite, Observações ou Próximos Passos), organizando cada informação na seção mais adequada.
2. Não exija ou dependa de rótulos padronizados nos blocos; use sua capacidade de inferência contextual para criar a estrutura do documento. Caso um bloco especifique um tópico explicitamente, respeite essa indicação.
3. Comece o documento com o título da tarefa em h1 (# {task_title}).
4. Utilize uma hierarquia de cabeçalhos limpos (##, ###) e listas/marcadores de fácil leitura.
5. Se houver Instruções Extras do Usuário, aplique-as com prioridade no estilo e na estrutura final.
6. Retorne APENAS o texto bruto formatado em Markdown, sem blocos de código (```markdown) em volta de todo o documento.
"""
    
    response = client.models.generate_content(
        model='gemini-3.6-flash',
        contents=prompt
    )
    return response.text.strip()

