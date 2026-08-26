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
    const sidebarLeft = document.getElementById('sidebar-left');
    const kanbanBoard = document.getElementById('kanban-board');
    
    // --- Sidebar Toggle Logic ---
    const btnToggleLeft = document.getElementById('btn-toggle-left-sidebar');
    if (btnToggleLeft && sidebarLeft) {
        btnToggleLeft.addEventListener('click', () => {
            sidebarLeft.classList.toggle('collapsed');
            if (sidebarLeft.classList.contains('collapsed')) {
                btnToggleLeft.textContent = '▶';
                btnToggleLeft.title = 'Expandir Projetos';
            } else {
                btnToggleLeft.textContent = '◀';
                btnToggleLeft.title = 'Recolher Projetos';
            }
        });
    }

    const btnToggleNotes = document.getElementById('btn-toggle-notes-panel');
    if (btnToggleNotes && notesPanel) {
        btnToggleNotes.addEventListener('click', () => {
            notesPanel.classList.toggle('collapsed');
            if (notesPanel.classList.contains('collapsed')) {
                btnToggleNotes.textContent = '▶';
                btnToggleNotes.title = 'Expandir Anotações';
            } else {
                btnToggleNotes.textContent = '◀';
                btnToggleNotes.title = 'Recolher Anotações';
            }
        });
    }

    const btnToggleRight = document.getElementById('btn-toggle-right-sidebar');
    if (btnToggleRight && sidebarRight) {
        btnToggleRight.addEventListener('click', () => {
            sidebarRight.classList.toggle('collapsed');
            if (sidebarRight.classList.contains('collapsed')) {
                btnToggleRight.textContent = '◀';
                btnToggleRight.title = 'Expandir Mini Drive';
            } else {
                btnToggleRight.textContent = '▶';
                btnToggleRight.title = 'Recolher Mini Drive';
            }
        });
    }

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
        if (!projectList) return;
        const li = document.createElement('li');
        li.className = 'project-item';
        li.dataset.projectId = project.id;
        li.textContent = project.name;
        projectList.appendChild(li);
    }

    // Global Event Delegation for clicking any project item
    document.addEventListener('click', (e) => {
        const item = e.target.closest('.project-item');
        if (item) {
            const pId = item.getAttribute('data-project-id') || (item.dataset ? item.dataset.projectId : null);
            if (pId) {
                openProject(pId);
            }
        }
    });


    async function openProject(id) {
        if (!id) return;
        try {
            // Leave old socket room
            if (currentProjectId) {
                socket.emit('leave', { project_id: currentProjectId });
            }
            
            currentProjectId = id;
            
            // Highlight active sidebar item
            document.querySelectorAll('.project-item').forEach(el => el.classList.remove('active'));
            const activeItem = document.querySelector(`.project-item[data-project-id="${id}"]`);
            if (activeItem) {
                activeItem.classList.add('active');
            }

            // Fetch project data (cache buster added)
            const res = await fetch(`/api/projects/${id}?_t=${Date.now()}`);

            if (!res.ok) {
                console.error("Erro ao buscar dados do projeto:", res.status);
                return;
            }
            const data = await res.json();
            
            currentUserId = data.current_user_id;
            if (currentViewTitle) {
                currentViewTitle.textContent = data.name;
            }
            
            // Show project specific panels
            if (projectToggles) projectToggles.classList.remove('hidden');
            const btnNewTask = document.getElementById('btn-new-task');
            if (btnNewTask) btnNewTask.classList.remove('hidden');
            if (notesPanel) notesPanel.classList.remove('hidden');
            if (chatPanel) chatPanel.classList.remove('hidden');
            if (sidebarRight) sidebarRight.classList.remove('hidden');

            // Ensure Kanban board is visible and report view is hidden
            const kanbanBoardEl = document.getElementById('kanban-board');
            const reportViewEl = document.getElementById('report-view');
            if (kanbanBoardEl) kanbanBoardEl.classList.remove('hidden');
            if (reportViewEl) reportViewEl.classList.add('hidden');

            document.querySelectorAll('.view-toggles .tab-btn').forEach(b => {
                if (b.dataset.view === 'kanban') b.classList.add('active');
                else b.classList.remove('active');
            });
            
            // Join socket room
            socket.emit('join', { project_id: id });
            
            renderKanban(data.tasks);
            renderNotes(data.notes);
            renderChatMessages(data.messages, currentUserId);
            
            // Fetch users for assignment dropdown
            fetchUsers();
        } catch (err) {
            console.error("Erro ao abrir o projeto:", err);
        }
    }

    let cachedUsers = [];

    async function fetchUsers() {
        const res = await fetch('/api/users');
        cachedUsers = await res.json();
        renderNewTaskAssigneesCheckboxes();
    }

    function renderNewTaskAssigneesCheckboxes() {
        const container = document.getElementById('new-task-assignees-container');
        if (!container) return;
        container.innerHTML = cachedUsers.map(u => `
            <label style="display: flex; align-items: center; gap: 0.4rem; font-size: 0.85rem; cursor: pointer;">
                <input type="checkbox" class="new-task-assignee-checkbox" value="${u.id}" style="width: auto;">
                <span>${escapeHtml(u.name)}</span>
            </label>
        `).join('');
    }
    
    function renderKanban(tasks) {
        const columns = Array.from(document.querySelectorAll('.kanban-column'));
        columns.forEach(col => {
            const container = col.querySelector('.kanban-cards-container');
            if (container) container.innerHTML = '';
        });
        
        if (!tasks) return;
        
        const defaultContainer = columns[0] ? columns[0].querySelector('.kanban-cards-container') : null;

        tasks.forEach(task => {
            let targetCol = columns.find(c => c.getAttribute('data-phase') === task.phase);
            let container = targetCol ? targetCol.querySelector('.kanban-cards-container') : defaultContainer;

            if (container) {
                const card = document.createElement('div');
                const statusSlug = (task.status || 'Pendente').toLowerCase().replace(/\s+/g, '-');
                card.className = `kanban-card status-${statusSlug}`;
                card.draggable = true;
                card.dataset.taskId = task.id;
                card.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 0.5rem;">
                        <h4 style="font-size: 0.95rem; font-weight: 600; line-height: 1.3; margin: 0; color: white;">${escapeHtml(task.title)}</h4>
                        ${task.has_pending_alert ? '<div class="alert-bell" style="position: static;">🔔</div>' : ''}
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 0.75rem; gap: 0.5rem; flex-wrap: wrap;">
                        <span class="status-badge status-${statusSlug}">${escapeHtml(task.status || 'Pendente')}</span>
                        ${task.assignee_name && task.assignee_name !== 'Nenhum' ? `<span style="font-size: 0.75rem; color: var(--text-muted); font-weight: 500;">👤 ${escapeHtml(task.assignee_name)}</span>` : ''}
                    </div>
                `;

                // Click to open quick task details
                card.addEventListener('click', async () => {
                    const res = await fetch(`/api/tasks/${task.id}`);
                    const taskData = await res.json();
                    
                    document.getElementById('quick-task-title-input').value = taskData.title || '';
                    const quickStatusSelect = document.getElementById('quick-task-status-select');
                    if (quickStatusSelect) {
                        quickStatusSelect.value = taskData.status || 'Pendente';
                    }
                    document.getElementById('quick-task-desc-input').value = taskData.description || '';


                    const assigneesContainer = document.getElementById('quick-task-assignees-container');
                    if (assigneesContainer) {
                        const assignedIds = taskData.assignee_ids || [];
                        assigneesContainer.innerHTML = cachedUsers.map(u => `
                            <label style="display: flex; align-items: center; gap: 0.35rem; font-size: 0.8rem; cursor: pointer;">
                                <input type="checkbox" class="quick-task-assignee-checkbox" value="${u.id}" ${assignedIds.includes(u.id) ? 'checked' : ''} style="width: auto;">
                                <span>${escapeHtml(u.name)}</span>
                            </label>
                        `).join('');
                    }

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
                
                container.appendChild(card);
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
            const newPhase = col.getAttribute('data-phase');
            
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

    function renderChatMessages(messages, currentUserId) {
        if (!msgContainer) return;
        msgContainer.innerHTML = '';
        if (!messages) return;
        messages.forEach(msg => appendChatMessage(msg, currentUserId));
        msgContainer.scrollTop = msgContainer.scrollHeight;
    }

    function appendChatMessage(data, currentUserId) {
        if (!msgContainer) return;
        const isSelf = (data.user_id === currentUserId);
        const msgEl = document.createElement('div');
        msgEl.className = `chat-msg ${isSelf ? 'self' : 'other'}`;

        const safeText = escapeHtml(data.message);
        msgEl.innerHTML = `
            ${!isSelf ? `<div class="chat-msg-header">${escapeHtml(data.user_name || 'Usuário')}</div>` : ''}
            <div class="chat-msg-text">${safeText}</div>
            <div class="chat-msg-time">${data.timestamp || ''}</div>
        `;
        msgContainer.appendChild(msgEl);
        msgContainer.scrollTop = msgContainer.scrollHeight;
    }

    function escapeHtml(text) {
        if (!text) return '';
        return text.replace(/&/g, "&amp;")
                   .replace(/</g, "&lt;")
                   .replace(/>/g, "&gt;")
                   .replace(/"/g, "&quot;")
                   .replace(/'/g, "&#039;");
    }

    socket.on('receive_message', (data) => {
        appendChatMessage(data, currentUserId);
    });

    socket.on('task_updated', (data) => {
        if (currentProjectId) {
            openProject(currentProjectId);
        }
    });

    socket.on('task_phase_updated', (data) => {
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
        renderNewTaskAssigneesCheckboxes();
        modalNewTask.classList.add('active');
    });
    
    document.getElementById('btn-cancel-task').addEventListener('click', () => {
        modalNewTask.classList.remove('active');
    });
    
    document.getElementById('btn-save-task').addEventListener('click', async () => {
        const title = document.getElementById('new-task-title').value.trim();
        const desc = document.getElementById('new-task-desc').value.trim();
        const deadline = document.getElementById('new-task-deadline').value;
        const selectedAssigneeIds = Array.from(document.querySelectorAll('.new-task-assignee-checkbox:checked')).map(cb => parseInt(cb.value));

        if (!title) return alert('Título da tarefa é obrigatório');
        
        const res = await fetch(`/api/projects/${currentProjectId}/tasks`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                title, 
                description: desc, 
                assignee_ids: selectedAssigneeIds,
                deadline: deadline || null
            })
        });
        
        if (res.ok) {
            modalNewTask.classList.remove('active');
            document.getElementById('new-task-title').value = '';
            document.getElementById('new-task-desc').value = '';
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
        window.open(`/task/${taskId}`, '_blank');
    });

    const btnSaveQuickTask = document.getElementById('btn-save-quick-task');
    if (btnSaveQuickTask) {
        btnSaveQuickTask.addEventListener('click', async () => {
            const taskId = document.getElementById('modal-quick-task').dataset.taskId;
            if (!taskId) return;

            const title = document.getElementById('quick-task-title-input').value.trim();
            const desc = document.getElementById('quick-task-desc-input').value.trim();
            const quickStatusEl = document.getElementById('quick-task-status-select');
            const statusVal = quickStatusEl ? quickStatusEl.value : 'Pendente';
            const assigneeIds = Array.from(document.querySelectorAll('.quick-task-assignee-checkbox:checked')).map(cb => parseInt(cb.value));

            if (!title) return alert("O título da tarefa não pode ficar em branco.");

            try {
                const res = await fetch(`/api/tasks/${taskId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ title, description: desc, status: statusVal, assignee_ids: assigneeIds })
                });


                if (res.ok) {
                    document.getElementById('modal-quick-task').classList.remove('active');
                    if (currentProjectId) {
                        openProject(currentProjectId);
                    }
                } else {
                    alert("Erro ao salvar alterações da tarefa.");
                }
            } catch(err) {
                alert("Erro de conexão ao salvar tarefa.");
            }
        });
    }

    let isDeletingQuickTask = false;
    let deleteQuickTaskTimer = null;

    const btnDeleteQuickTask = document.getElementById('btn-delete-quick-task');
    if (btnDeleteQuickTask) {
        btnDeleteQuickTask.addEventListener('click', async () => {
            const taskId = document.getElementById('modal-quick-task').dataset.taskId;
            if (!taskId) return alert("Erro: ID da tarefa não encontrado.");

            if (!isDeletingQuickTask) {
                isDeletingQuickTask = true;
                btnDeleteQuickTask.textContent = "⚠️ Confirmar Exclusão?";
                btnDeleteQuickTask.style.background = "#ef4444";
                btnDeleteQuickTask.style.color = "#ffffff";
                
                clearTimeout(deleteQuickTaskTimer);
                deleteQuickTaskTimer = setTimeout(() => {
                    isDeletingQuickTask = false;
                    btnDeleteQuickTask.textContent = "🗑️ Excluir";
                    btnDeleteQuickTask.style.background = "rgba(239, 68, 68, 0.2)";
                    btnDeleteQuickTask.style.color = "#fca5a5";
                }, 4000);
                return;
            }

            clearTimeout(deleteQuickTaskTimer);
            isDeletingQuickTask = false;
            btnDeleteQuickTask.disabled = true;
            btnDeleteQuickTask.textContent = "Excluindo...";

            try {
                const res = await fetch(`/api/tasks/${taskId}`, { method: 'DELETE' });
                if (res.ok) {
                    document.getElementById('modal-quick-task').classList.remove('active');
                    if (currentProjectId) {
                        openProject(currentProjectId);
                    }
                } else {
                    const errData = await res.json().catch(() => ({}));
                    alert("Erro ao excluir tarefa: " + (errData.error || res.statusText));
                }
            } catch(err) {
                alert("Erro de conexão ao excluir tarefa.");
            } finally {
                btnDeleteQuickTask.disabled = false;
                btnDeleteQuickTask.textContent = "🗑️ Excluir";
                btnDeleteQuickTask.style.background = "rgba(239, 68, 68, 0.2)";
                btnDeleteQuickTask.style.color = "#fca5a5";
            }
        });
    }



    socket.on('task_deleted', (data) => {
        const card = document.querySelector(`.kanban-card[data-task-id="${data.task_id}"]`);
        if (card) card.remove();
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

    // --- Notes Logic & Tabs ---
    let currentNoteTab = 'all';
    let cachedNotes = [];

    document.querySelectorAll('.note-tabs .tab-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.note-tabs .tab-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            currentNoteTab = e.target.dataset.tab.toLowerCase();
            renderNotes(cachedNotes);
        });
    });

    function renderNotes(notes) {
        cachedNotes = notes || [];
        const list = document.getElementById('notes-list');
        list.innerHTML = '';
        if (!cachedNotes) return;

        let filtered = cachedNotes.filter(n => {
            if (currentNoteTab === 'done') {
                return n.is_completed === true;
            } else {
                if (n.is_completed) return false;
                if (currentNoteTab === 'all') return true;
                const catLower = (n.category || '').toLowerCase();
                if (currentNoteTab === 'rf') return catLower.includes('funcional') || catLower === 'rf';
                if (currentNoteTab === 'rt') return catLower.includes('técnico') || catLower === 'rt';
                if (currentNoteTab === 'todo') return catLower.includes('todo') || catLower === 'solicitação';
                return true;
            }
        });


        if (filtered.length === 0) {
            list.innerHTML = `<p style="font-size: 0.85rem; color: var(--text-muted); text-align: center; margin-top: 1rem;">Nenhuma anotação nesta aba.</p>`;
            return;
        }

        filtered.forEach(note => {
            const div = document.createElement('div');
            let catClass = 'rf';
            if ((note.category || '').includes('Técnico') || note.category === 'RT') catClass = 'rt';
            if ((note.category || '').includes('TODO') || note.category === 'Solicitação') catClass = 'todo';
            if (note.is_completed) catClass += ' completed';

            div.className = `note-item ${catClass}`;
            div.innerHTML = `
                <div class="note-item-header">
                    <strong>${escapeHtml(note.category)}</strong>
                    <div class="note-item-actions">
                        <button class="note-action-btn" onclick="toggleNoteComplete(${note.id}, ${!note.is_completed})" title="${note.is_completed ? 'Reabrir anotação' : 'Marcar como Conforme'}">
                            ${note.is_completed ? '↩️' : '✔️'}
                        </button>
                        <button class="note-action-btn" onclick="deleteNote(${note.id})" title="Excluir anotação">
                            🗑️
                        </button>
                    </div>
                </div>
                <p style="margin-top: 0.2rem; font-size: 0.85rem; line-height: 1.35;">${escapeHtml(note.content)}</p>
            `;
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
                openProject(currentProjectId);
            }
        }
    });

    window.toggleNoteComplete = async function(noteId, newStatus) {
        try {
            const res = await fetch(`/api/notes/${noteId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ is_completed: newStatus })
            });
            if (res.ok && currentProjectId) {
                openProject(currentProjectId);
            }
        } catch(err) {
            alert("Erro ao atualizar anotação.");
        }
    };

    window.deleteNote = async function(noteId) {
        if (!confirm("Tem certeza que deseja excluir esta anotação?")) return;
        try {
            const res = await fetch(`/api/notes/${noteId}`, { method: 'DELETE' });
            if (res.ok && currentProjectId) {
                openProject(currentProjectId);
            }
        } catch(err) {
            alert("Erro ao excluir anotação.");
        }
    };


    // --- Logout Logic ---
    const btnLogout = document.getElementById('btn-logout');
    if (btnLogout) {
        btnLogout.addEventListener('click', async () => {
            const res = await fetch('/api/logout', { method: 'POST' });
            if (res.ok) {
                window.location.href = '/login';
            }
        });
    }

    // --- Master User Management Modal ---
    const btnManageUsers = document.getElementById('btn-manage-users');
    const modalManageUsers = document.getElementById('modal-manage-users');
    const btnCloseManageUsers = document.getElementById('btn-close-manage-users');
    const btnAdminAddUser = document.getElementById('btn-admin-add-user');

    if (btnManageUsers && modalManageUsers) {
        btnManageUsers.addEventListener('click', () => {
            modalManageUsers.classList.add('active');
            loadAdminUsers();
        });

        if (btnCloseManageUsers) {
            btnCloseManageUsers.addEventListener('click', () => {
                modalManageUsers.classList.remove('active');
            });
        }

        if (btnAdminAddUser) {
            btnAdminAddUser.addEventListener('click', async () => {
                const name = document.getElementById('admin-new-user-name').value.trim();
                const email = document.getElementById('admin-new-user-email').value.trim();
                const role = document.getElementById('admin-new-user-role').value;
                const isMaster = document.getElementById('admin-new-user-master').checked;

                if (!name || !email) return alert('Preencha Nome e E-mail.');

                try {
                    const res = await fetch('/api/admin/users', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ name, email, role, is_master: isMaster })
                    });
                    const data = await res.json();
                    if (res.ok) {
                        document.getElementById('admin-new-user-name').value = '';
                        document.getElementById('admin-new-user-email').value = '';
                        document.getElementById('admin-new-user-master').checked = false;
                        loadAdminUsers();
                    } else {
                        alert('Erro: ' + (data.error || 'Não foi possível cadastrar o usuário.'));
                    }
                } catch (err) {
                    alert('Erro ao conectar com o servidor.');
                }
            });
        }
    }

    async function loadAdminUsers() {
        const listEl = document.getElementById('admin-users-list');
        if (!listEl) return;
        try {
            const res = await fetch('/api/admin/users');
            if (res.ok) {
                const users = await res.json();
                listEl.innerHTML = users.map(u => `
                    <div style="background: rgba(0,0,0,0.25); padding: 0.75rem; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; gap: 0.5rem; border: 1px solid var(--border-color);">
                        <div>
                            <div style="font-weight: 600; font-size: 0.9rem;">
                                ${u.name} ${u.is_master ? '<span style="background: #818cf8; color: white; padding: 0.1rem 0.4rem; border-radius: 99px; font-size: 0.7rem; font-weight: 700; margin-left: 0.3rem;">MASTER</span>' : ''}
                            </div>
                            <div style="font-size: 0.8rem; color: var(--text-muted);">${u.email} • <em>${u.role}</em></div>
                        </div>
                        <div>
                            <button onclick="toggleUserActive(${u.id}, ${!u.is_active})" style="background: ${u.is_active ? 'rgba(239,68,68,0.2)' : 'rgba(16,185,129,0.2)'}; color: ${u.is_active ? '#fca5a5' : '#6ee7b7'}; border: 1px solid ${u.is_active ? '#ef4444' : '#10b981'}; padding: 0.35rem 0.7rem; font-size: 0.8rem; border-radius: 6px; cursor: pointer;">
                                ${u.is_active ? 'Desativar' : 'Ativar'}
                            </button>
                        </div>
                    </div>
                `).join('');
            }
        } catch(err) {
            listEl.innerHTML = '<p style="color: red;">Erro ao carregar usuários.</p>';
        }
    }

    window.toggleUserActive = async function(userId, newActiveState) {
        try {
            const res = await fetch(`/api/admin/users/${userId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ is_active: newActiveState })
            });
            if (res.ok) {
                loadAdminUsers();
            } else {
                alert('Erro ao alterar status do usuário.');
            }
        } catch(err) {
            alert('Erro ao conectar com o servidor.');
        }
    };

    // Check URL parameters for project to open, or open the first project by default
    const urlParams = new URLSearchParams(window.location.search);
    const targetProjectId = urlParams.get('project');
    if (targetProjectId) {
        openProject(targetProjectId);
    } else {
        const firstProject = document.querySelector('.project-item');
        if (firstProject) {
            const pId = firstProject.getAttribute('data-project-id') || (firstProject.dataset ? firstProject.dataset.projectId : null);
            if (pId) openProject(pId);
        }
    }
});



