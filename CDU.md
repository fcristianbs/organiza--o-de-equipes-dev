# Documento de Especificação de Casos de Uso (CDU)

---

## 1. Visão Geral do Sistema

O sistema é uma plataforma de gestão de projetos e fluxos de trabalho que integra ideação, levantamento de requisitos (funcionais e técnicos), prototipagem, desenvolvimento e testes Q.A. A interface possui navegação baseada em uma barra lateral no estilo Gemini, quadros Kanban (macro e micro), painel de anotações empilhadas, chat entre integrantes e um Mini Drive com renderização nativa de documentos `.md` e `.cdu`.

---

## 2. Mapeamento de Atores

* **Membro da Equipe (Usuário):** Profissional responsável por criar projetos, transitar tarefas no Kanban, registrar atas de reunião, anexar arquivos e utilizar o chat do projeto.
* **Analista / Líder de Requisitos:** Responsável por categorizar e detalhar os Requisitos Funcionais (RF) e Técnicos (RT) no painel de anotações.

---

## 3. Matriz de Casos de Uso

| ID | Nome do Caso de Uso | Objetivo |
| :--- | :--- | :--- |
| **CDU-01** | Navegação Global e Gestão de Projetos | Criar projetos e navegar entre a visão macro (Kanban Global) e a visão micro (Projeto Específico). |
| **CDU-02** | Gestão de Atas e Relatórios de Reunião | Registrar e visualizar diretrizes conceituais em Markdown na aba dedicada do projeto. |
| **CDU-03** | Gerenciamento de Requisitos e Anotações | Registrar observações, solicitações em abas e tarefas no formato TODO (separando RF e RT). |
| **CDU-04** | Gestão do Kanban e Sinalização de Pendências | Mover cards de tarefas, inserir observações críticas e ativar o indicador visual de Sino. |
| **CDU-05** | Mini Drive e Renderização de Arquivos | Fazer upload e organizar anexos por tarefa ou escopo geral, com suporte à renderização de `.md` e `.cdu`. |
| **CDU-06** | Comunicação do Projeto (Chat Integrado) | Enviar mensagens em tempo real no painel inferior do projeto ativo. |

---

## 4. Detalhamento dos Casos de Uso

### CDU-01: Navegação Global e Gestão de Projetos
* **Ator Principal:** Membro da Equipe.
* **Pré-condição:** Usuário autenticado na plataforma via credenciais pré-definidas.
* **Fluxo Principal:**
  1. O usuário acessa a plataforma e visualiza a barra lateral esquerda (contendo acessos recentes e opção de criar projeto) e o **Kanban Global** no centro.
  2. O usuário clica no botão `+ Novo Projeto` na barra lateral.
  3. O sistema abre um formulário solicitando **Nome do Projeto** e **Descrição Simples**.
  4. O usuário confirma a criação; o sistema cadastra o projeto e atualiza o Kanban Global e a lista de recentes na barra lateral.
  5. O usuário clica sobre o card do projeto (no Kanban Global ou na barra lateral).
  6. O sistema redireciona o usuário para o **Kanban Específico** do projeto selecionado.

---

### CDU-02: Gestão de Atas e Relatórios de Reunião
* **Ator Principal:** Membro da Equipe.
* **Pré-condição:** Projeto específico aberto.
* **Fluxo Principal:**
  1. No topo da página do projeto, o usuário clica na aba **"Relatório da Reunião"**.
  2. O sistema exibe a interface de edição/visualização em sintaxe **Markdown**.
  3. O usuário digita ou atualiza as atas conceituais e definições abstratas alinhadas na reunião.
  4. O usuário clica em salvar (ou o sistema efetua o autosave).
  5. O relatório permanece formatado e acessível para todos os membros vinculados ao projeto.

---

### CDU-03: Gerenciamento de Requisitos e Anotações
* **Ator Principal:** Analista / Líder de Requisitos, Membro da Equipe.
* **Pré-condição:** Projeto específico aberto no Kanban de Progresso.
* **Fluxo Principal:**
  1. O usuário visualiza o **Painel de Anotações** localizado entre a barra lateral esquerda e o quadro Kanban.
  2. O usuário digita uma nota ou item no campo de texto localizado na parte inferior do painel.
  3. O usuário define o tipo da anotação (ex: *Requisito Funcional*, *Requisito Técnico*, *Solicitação* ou *TODO*).
  4. Ao enviar, a anotação é empilhada verticalmente acima do campo de texto.
  5. O usuário pode navegar entre as abas internas do painel para filtrar anotações por categorias ou solicitações específicas.

---

### CDU-04: Gestão do Kanban e Sinalização de Pendências
* **Ator Principal:** Membro da Equipe.
* **Pré-condição:** Projeto específico aberto.
* **Fluxo Principal:**
  1. O usuário visualiza o **Kanban de Progresso do Projeto** contendo colunas de status (ex: *Ideação/Requisitos*, *Prototipagem*, *Dev Ativo*, *Q.A. e Testes*).
  2. O usuário arrasta cards entre as colunas para atualizar a fase de desenvolvimento.
  3. O usuário clica em uma tarefa para abrir seu painel de detalhes.
  4. O usuário digita uma observação específica sobre a tarefa e marca a caixa **"Sinalizar Pendência"**.
  5. Ao salvar, o sistema insere um **ícone de Sino (Alerta)** no canto do card correspondente no Kanban.
  6. Ao clicar ou passar o mouse sobre o sino, o sistema exibe o histórico de pendências sinalizadas naquela tarefa.

---

### CDU-05: Mini Drive e Renderização de Arquivos
* **Ator Principal:** Membro da Equipe.
* **Pré-condição:** Projeto específico aberto.

#### Fluxo A: Arquivos da Tarefa
1. O usuário abre o modal de uma tarefa no Kanban.
2. Clica na opção de anexo e faz o upload do arquivo.
3. O usuário seleciona o tipo do arquivo (ex: *Documento*, *CDU/Markdown*, *Imagem*, *Outros*).
4. O arquivo é listado e organizado por categorias dentro da própria aba/modal da tarefa.

#### Fluxo B: Arquivos Gerais do Projeto & Renderização
1. O usuário faz o upload de um arquivo na **Barra Lateral Direita (Anexos do Projeto Geral)**.
2. O arquivo é exibido na lista empilhada de anexos gerais do projeto.
3. O usuário clica sobre um arquivo da lista (ex: `.md`, `.cdu` ou arquivo de imagem).
4. O sistema direciona automaticamente a tela para a aba **"Mini Drive / Visualizador"** no topo da tela.
5. Se for `.md` ou `.cdu`, o sistema renderiza o conteúdo formatado diretamente na plataforma.
6. Se for um arquivo genérico não suportado para visualização, o sistema inicia o download.

---

### CDU-06: Comunicação do Projeto (Chat Integrado)
* **Ator Principal:** Membro da Equipe.
* **Pré-condição:** Projeto específico aberto.
* **Fluxo Principal:**
  1. Na parte inferior da área central (abaixo do quadro Kanban), o usuário visualiza a caixa do **Chat do Projeto**.
  2. O usuário digita uma mensagem e clica em enviar.
  3. A mensagem é exibida no histórico do chat para todos os membros que estão com aquele projeto aberto.
  4. O histórico do chat permanece associado e persistido no escopo do projeto.