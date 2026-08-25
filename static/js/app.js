document.addEventListener('DOMContentLoaded', () => {
    // Connect to Socket.IO
    const socket = io();
    
    let currentProjectId = null;

    // --- DOM Elements ---
    const btnNewProject = document.getElementById('btn-new-project');
    const modalNewProject = document.getElementById('modal-new-project');
    const btnCancelProject = document.getElementById('btn-cancel-project');
    const btnSaveProject = document.getElementById('btn-save-project');
    
    const projectList = document.getElementById('project-list').querySelector('ul');
    const currentViewTitle = document.getElementById('current-view-title');
    const projectToggles = document.getElementById('project-toggles');
    
    const notesPanel = document.getElementById('notes-panel');
    const chatPanel = document.getElementById('chat-panel');
    const sidebarRight = document.getElementById('sidebar-right');
    const kanbanBoard = document.getElementById('kanban-board');
    
    // --- Modals ---
    btnNewProject.addEventListener('click', () => {
        modalNewProject.classList.add('active');
    });
    
    btnCancelProject.addEventListener('click', () => {
        modalNewProject.classList.remove('active');
    });

    btnSaveProject.addEventListener('click', async () => {
        const name = document.getElementById('new-project-name').value;
        const desc = document.getElementById('new-project-desc').value;
        
        if (!name) return alert('Nome é obrigatório');
        
        const res = await fetch('/api/projects', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, description: desc })
        });
        
        if (res.ok) {
            const data = await res.json();
            modalNewProject.classList.remove('active');
            addProjectToSidebar(data);
            openProject(data.id);
        }
    });

    // --- Sidebar Projects ---
    function addProjectToSidebar(project) {
        const li = document.createElement('li');
        li.className = 'project-item';
        li.dataset.projectId = project.id;
        li.textContent = project.name;
        li.addEventListener('click', () => openProject(project.id));
        projectList.appendChild(li);
    }

    document.querySelectorAll('.project-item').forEach(item => {
        item.addEventListener('click', (e) => openProject(e.target.dataset.projectId));
    });

    async function openProject(id) {
        // Leave old socket room
        if (currentProjectId) {
            socket.emit('leave', { project_id: currentProjectId });
        }
        
        currentProjectId = id;
        
        // Highlight active sidebar item
        document.querySelectorAll('.project-item').forEach(el => el.classList.remove('active'));
        document.querySelector(`.project-item[data-project-id="${id}"]`).classList.add('active');

        // Fetch project data
        const res = await fetch(`/api/projects/${id}`);
        const data = await res.json();
        
        currentViewTitle.textContent = data.name;
        
        // Show project specific panels
        projectToggles.classList.remove('hidden');
        document.getElementById('btn-new-task').classList.remove('hidden');
        notesPanel.classList.remove('hidden');
        chatPanel.classList.remove('hidden');
        sidebarRight.classList.remove('hidden');
        
        // Join socket room
        socket.emit('join', { project_id: id });
        
        renderKanban(data.tasks);
        renderNotes(data.notes);
        
        // Fetch users for assignment dropdown
        fetchUsers();
    }
    
    async function fetchUsers() {
        const res = await fetch('/api/users');
        const users = await res.json();
        const select = document.getElementById('new-task-assignee');
        select.innerHTML = '<option value="">Atribuir a um membro...</option>';
        users.forEach(u => {
            select.innerHTML += `<option value="${u.id}">${u.name}</option>`;
        });
    }
    
    function renderKanban(tasks) {
        // Clear columns
        document.querySelectorAll('.kanban-cards-container').forEach(col => col.innerHTML = '');
        
        if (!tasks) return;
        
        tasks.forEach(task => {
            const col = document.querySelector(`.kanban-column[data-phase="${task.phase}"] .kanban-cards-container`);
            if (col) {
                const card = document.createElement('div');
                card.className = `kanban-card status-${task.status.toLowerCase().replace(' ', '-')}`;
                card.draggable = true;
                card.dataset.taskId = task.id;
                card.innerHTML = `
                    <h4>${task.title}</h4>
                    ${task.has_pending_alert ? '<div class="alert-bell">🔔</div>' : ''}
                `;
                
                // Click to open quick task details
                card.addEventListener('click', async () => {
                    const res = await fetch(`/api/tasks/${task.id}`);
                    const taskData = await res.json();
                    
                    document.getElementById('quick-task-title').textContent = taskData.title;
                    document.getElementById('quick-task-assignee').textContent = taskData.assignee_name;
                    document.getElementById('quick-task-status').textContent = taskData.status;
                    document.getElementById('quick-task-desc').textContent = taskData.description || 'Sem descrição.';
                    
                    const quickModal = document.getElementById('modal-quick-task');
                    quickModal.dataset.taskId = task.id;
                    quickModal.classList.add('active');
                });
                
                // Drag events
                card.addEventListener('dragstart', (e) => {
                    card.classList.add('dragging');
                    e.dataTransfer.setData('text/plain', task.id);
                });
                
                card.addEventListener('dragend', () => {
                    card.classList.remove('dragging');
                });
                
                col.appendChild(card);
            }
        });
    }

    // --- Drag and Drop Logic ---
    const columns = document.querySelectorAll('.kanban-column');
    columns.forEach(col => {
        col.addEventListener('dragover', e => {
            e.preventDefault(); // Allow drop
        });
        
        col.addEventListener('drop', e => {
            e.preventDefault();
            const taskId = e.dataTransfer.getData('text/plain');
            const newPhase = col.dataset.phase;
            
            const card = document.querySelector(`.kanban-card[data-task-id="${taskId}"]`);
            if (card) {
                col.querySelector('.kanban-cards-container').appendChild(card);
                
                // Emit socket event to update phase
                socket.emit('update_task_phase', {
                    task_id: taskId,
                    new_phase: newPhase
                });
            }
        });
    });

    // --- Chat Logic ---
    const btnSendMsg = document.getElementById('btn-send-message');
    const inputMsg = document.getElementById('chat-input');
    const msgContainer = document.getElementById('chat-messages');

    btnSendMsg.addEventListener('click', sendMessage);
    inputMsg.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    function sendMessage() {
        const msg = inputMsg.value.trim();
        if (msg && currentProjectId) {
            socket.emit('send_message', {
                project_id: currentProjectId,
                message: msg
            });
            inputMsg.value = '';
        }
    }

    socket.on('receive_message', (data) => {
        const msgEl = document.createElement('div');
        msgEl.className = 'chat-msg';
        msgEl.innerHTML = `<strong>${data.user}</strong>: ${data.message}`;
        msgContainer.appendChild(msgEl);
        msgContainer.scrollTop = msgContainer.scrollHeight;
    });

    socket.on('task_phase_updated', (data) => {
        // When another user updates a task phase
        const card = document.querySelector(`.kanban-card[data-task-id="${data.task_id}"]`);
        const col = document.querySelector(`.kanban-column[data-phase="${data.new_phase}"] .kanban-cards-container`);
        if (card && col && card.parentElement !== col) {
            col.appendChild(card);
        }
    });

    // --- Task Creation Logic ---
    const btnNewTask = document.getElementById('btn-new-task');
    const modalNewTask = document.getElementById('modal-new-task');
    
    btnNewTask.addEventListener('click', () => {
        if (!currentProjectId) return alert('Selecione um projeto primeiro.');
        modalNewTask.classList.add('active');
    });
    
    document.getElementById('btn-cancel-task').addEventListener('click', () => {
        modalNewTask.classList.remove('active');
    });
    
    document.getElementById('btn-save-task').addEventListener('click', async () => {
        const title = document.getElementById('new-task-title').value;
        const desc = document.getElementById('new-task-desc').value;
        const assigneeId = document.getElementById('new-task-assignee').value;
        const deadline = document.getElementById('new-task-deadline').value;
        
        if (!title) return alert('Título da tarefa é obrigatório');
        
        const res = await fetch(`/api/projects/${currentProjectId}/tasks`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                title, 
                description: desc, 
                assignee_id: assigneeId || null,
                deadline: deadline || null
            })
        });
        
        if (res.ok) {
            modalNewTask.classList.remove('active');
            // Refresh kanban (lazy way, re-open project)
            openProject(currentProjectId);
        }
    });

    // --- Quick Task Modal & Task View ---
    document.getElementById('btn-close-quick-task').addEventListener('click', () => {
        document.getElementById('modal-quick-task').classList.remove('active');
    });
    
    document.getElementById('btn-open-task-full').addEventListener('click', () => {
        const taskId = document.getElementById('modal-quick-task').dataset.taskId;
        document.getElementById('modal-quick-task').classList.remove('active');
        
        // Abre em uma nova aba do navegador
        window.open(`/task/${taskId}`, '_blank');
    });
    
    // View toggles logic
    document.querySelectorAll('.view-toggles .tab-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.view-toggles .tab-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            
            document.querySelectorAll('.view-container > div').forEach(div => div.classList.add('hidden'));
            document.getElementById(e.target.dataset.view).classList.remove('hidden');
        });
    });

    // --- Notes Logic ---
    function renderNotes(notes) {
        const list = document.getElementById('notes-list');
        list.innerHTML = '';
        if (!notes) return;
        notes.forEach(note => {
            const div = document.createElement('div');
            let catClass = 'rf';
            if (note.category === 'Requisito Técnico') catClass = 'rt';
            if (note.category === 'TODO') catClass = 'todo';
            div.className = `note-item ${catClass}`;
            div.innerHTML = `<strong>${note.category}</strong><p>${note.content}</p>`;
            list.appendChild(div);
        });
    }

    document.getElementById('btn-add-note').addEventListener('click', async () => {
        const input = document.getElementById('note-input');
        const cat = document.getElementById('note-category').value;
        const content = input.value.trim();
        
        if (content && currentProjectId) {
            const res = await fetch(`/api/projects/${currentProjectId}/notes`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content, category: cat })
            });
            if (res.ok) {
                input.value = '';
                openProject(currentProjectId); // Refresh to get notes
            }
        }
    });

});
