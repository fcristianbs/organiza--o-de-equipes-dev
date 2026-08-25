import os
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from datetime import datetime
from werkzeug.utils import secure_filename
from models import db, User, Project, Task, TaskBlock, Note, Attachment, Message, MeetingReport
from ai_service import generate_task_markdown

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key-super-secure'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__name__)), 'uploads')

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Mock user function since we don't have login yet
def get_current_user():
    user = User.query.filter_by(username='mockuser').first()
    if not user:
        user = User(username='mockuser', name='Membro da Equipe')
        db.session.add(user)
        db.session.commit()
    return user

@app.before_request
def before_request():
    app.logger.info("Before request hook triggered")
    if not hasattr(app, 'db_initialized'):
        # Ensure db is created inside app context before first request
        db.create_all()
        app.db_initialized = True

@app.route('/')
def index():
    projects = Project.query.all()
    user = get_current_user()
    return render_template('index.html', projects=projects, current_user=user)

# --- APIs ---
@app.route('/api/projects', methods=['POST'])
def create_project():
    data = request.json
    project = Project(name=data['name'], description=data.get('description', ''))
    db.session.add(project)
    db.session.commit()
    # Create initial meeting report
    report = MeetingReport(content="# Relatório Inicial\n\nAdicione aqui as definições...", project_id=project.id)
    db.session.add(report)
    db.session.commit()
    
    return jsonify({'id': project.id, 'name': project.name}), 201

@app.route('/task/<int:task_id>')
def task_page(task_id):
    task = Task.query.get_or_404(task_id)
    blocks = TaskBlock.query.filter_by(task_id=task.id).all()
    return render_template('task_page.html', task=task, blocks=blocks)

@app.route('/api/projects/<int:project_id>')
def get_project(project_id):
    project = Project.query.get_or_404(project_id)
    tasks = Task.query.filter_by(project_id=project.id).all()
    notes = Note.query.filter_by(project_id=project.id).all()
    report = MeetingReport.query.filter_by(project_id=project.id).first()
    
    task_list = []
    for t in tasks:
        current_status = t.status
        if t.status != 'Concluido' and t.deadline and t.deadline < datetime.now():
            current_status = 'Atrasado'
            
        task_list.append({
            'id': t.id, 
            'title': t.title, 
            'phase': t.phase,
            'status': current_status,
            'deadline': t.deadline.strftime('%Y-%m-%d') if t.deadline else None,
            'has_pending_alert': t.has_pending_alert
        })
        
    note_list = [{'id': n.id, 'content': n.content, 'category': n.category} for n in notes]
    
    return jsonify({
        'id': project.id,
        'name': project.name,
        'description': project.description,
        'tasks': task_list,
        'notes': note_list,
        'report': report.content if report else ""
    })

@app.route('/api/users', methods=['GET'])
def get_users():
    users = User.query.all()
    return jsonify([{'id': u.id, 'name': u.name} for u in users])

@app.route('/api/projects/<int:project_id>/tasks', methods=['POST'])
def create_task(project_id):
    data = request.json
    deadline_date = None
    if data.get('deadline'):
        deadline_date = datetime.strptime(data['deadline'], '%Y-%m-%d')

    task = Task(
        title=data['title'],
        description=data.get('description', ''),
        project_id=project_id,
        assignee_id=data.get('assignee_id'),
        deadline=deadline_date,
        phase=data.get('phase', 'Ideação/Requisitos')
    )
    db.session.add(task)
    db.session.commit()
    return jsonify({'id': task.id, 'title': task.title, 'status': task.status}), 201

@app.route('/api/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    t = Task.query.get_or_404(task_id)
    current_status = t.status
    if t.status != 'Concluido' and t.deadline and t.deadline < datetime.now():
        current_status = 'Atrasado'
        
    return jsonify({
        'id': t.id,
        'title': t.title,
        'description': t.description,
        'phase': t.phase,
        'status': current_status,
        'deadline': t.deadline.strftime('%Y-%m-%d') if t.deadline else None,
        'assignee_id': t.assignee_id,
        'assignee_name': t.assignee.name if t.assignee else 'Nenhum',
        'has_pending_alert': t.has_pending_alert
    })

@app.route('/api/tasks/<int:task_id>/status', methods=['POST'])
def update_task_status_endpoint(task_id):
    t = Task.query.get_or_404(task_id)
    data = request.json
    if 'status' in data:
        t.status = data['status']
        db.session.commit()
    return jsonify({'message': 'Success'})

@app.route('/api/tasks/<int:task_id>/blocks', methods=['POST'])
def add_task_block(task_id):
    task = Task.query.get_or_404(task_id)
    data = request.json
    block = TaskBlock(
        task_id=task.id,
        block_type=data['type'],
        content=data['content']
    )
    db.session.add(block)
    db.session.commit()
    return jsonify({'id': block.id, 'type': block.block_type, 'content': block.content}), 201

@app.route('/api/tasks/<int:task_id>/generate', methods=['POST'])
def generate_markdown(task_id):
    task = Task.query.get_or_404(task_id)
    blocks = TaskBlock.query.filter_by(task_id=task.id).all()
    
    blocks_data = [{'type': b.block_type, 'content': b.content} for b in blocks]
    
    data = request.json
    additional_prompt = data.get('prompt', '')
    
    try:
        new_markdown = generate_task_markdown(task.title, blocks_data, additional_prompt)
        task.description = new_markdown
        db.session.commit()
        return jsonify({'message': 'Success', 'markdown': new_markdown})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects/<int:project_id>/notes', methods=['POST'])
def create_note(project_id):
    data = request.json
    note = Note(
        content=data['content'],
        category=data['category'],
        project_id=project_id
    )
    db.session.add(note)
    db.session.commit()
    return jsonify({'id': note.id, 'content': note.content, 'category': note.category}), 201

# --- SocketIO Events ---
@socketio.on('join')
def on_join(data):
    room = data['project_id']
    if room:
        join_room(f"project_{room}")
        emit('status', {'msg': f'Usuário conectou ao projeto {room}.'}, room=f"project_{room}")

@socketio.on('leave')
def on_leave(data):
    room = data['project_id']
    if room:
        leave_room(f"project_{room}")

@socketio.on('send_message')
def handle_send_message(data):
    project_id = data['project_id']
    content = data['message']
    user = get_current_user()
    
    msg = Message(content=content, project_id=project_id, user_id=user.id)
    db.session.add(msg)
    db.session.commit()
    
    emit('receive_message', {
        'user': user.name,
        'message': content,
        'timestamp': msg.created_at.strftime('%H:%M')
    }, room=f"project_{project_id}")

@socketio.on('update_task_status')
def handle_task_status(data):
    task = Task.query.get(data['task_id'])
    if task:
        task.status = data['new_status']
        db.session.commit()
        emit('task_updated', data, room=f"project_{task.project_id}")

@socketio.on('update_task_phase')
def handle_update_task_phase(data):
    task_id = data.get('task_id')
    new_phase = data.get('new_phase')
    
    task = Task.query.get(task_id)
    if task:
        task.phase = new_phase
        db.session.commit()
        # Broadcast the change to the room
        emit('task_phase_updated', {
            'task_id': task_id,
            'new_phase': new_phase
        }, room=f"project_{task.project_id}")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, debug=True)
