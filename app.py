import os
from urllib.parse import quote_plus
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_socketio import SocketIO, emit, join_room, leave_room
from datetime import datetime
from werkzeug.utils import secure_filename
from models import db, User, Project, Task, TaskBlock, Note, Attachment, Message, MeetingReport, TaskSectionComment, PushSubscription


from ai_service import generate_task_markdown, reformulate_task_markdown


load_dotenv()

def get_database_uri():
    db_type = os.getenv('DB_TYPE', '').lower()
    db_user = os.getenv('DB_USER', '')
    db_password = os.getenv('DB_PASSWORD', '')
    db_host = os.getenv('DB_HOST', '')
    db_port = os.getenv('DB_PORT', '')
    db_name = os.getenv('DB_NAME', '')

    if db_host and db_name:
        user = quote_plus(db_user) if db_user else ''
        password = f":{quote_plus(db_password)}" if db_password else ''
        auth = f"{user}{password}@" if user else ''
        port = f":{db_port}" if db_port else ''

        if db_type in ['mysql', 'mariadb']:
            return f"mysql+pymysql://{auth}{db_host}{port}/{db_name}"
        elif db_type in ['postgres', 'postgresql']:
            return f"postgresql+psycopg2://{auth}{db_host}{port}/{db_name}"
        elif db_type == 'sqlite':
            return f"sqlite:///{db_name}"
        else:
            return f"{db_type}://{auth}{db_host}{port}/{db_name}"

    db_url = os.getenv('DATABASE_URL')
    if db_url and db_url.strip() and "usuario:senha@host" not in db_url:
        if db_url.startswith("postgres://"):
            return db_url.replace("postgres://", "postgresql://", 1)
        return db_url

    return 'sqlite:///database.db'

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-super-secure')
app.config['SQLALCHEMY_DATABASE_URI'] = get_database_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__name__)), 'uploads')

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)
socketio = SocketIO(app, cors_allowed_origins="*")

@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

def get_current_user():

    user_id = session.get('user_id')
    if user_id:
        user = db.session.get(User, user_id)
        if user and user.is_active:
            return user
    return None

def ensure_master_user():
    master_email = "cristian.sampaio@cosampa.com.br"
    master = User.query.filter(db.func.lower(User.email) == master_email.lower()).first()
    if not master:
        master = User(
            name="Cristian Sampaio",
            email=master_email,
            role="Master",
            is_master=True,
            is_active=True
        )
        db.session.add(master)
        db.session.commit()
    elif not master.is_master or not master.is_active:
        master.is_master = True
        master.role = "Master"
        master.is_active = True
        db.session.commit()

def ensure_schema_updates():
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        columns = [c['name'] for c in inspector.get_columns('task_block')]
        if 'position' not in columns:
            print("Adicionando coluna 'position' na tabela 'task_block'...")
            with db.engine.connect() as conn:
                conn.execute(text("ALTER TABLE task_block ADD COLUMN position INT NOT NULL DEFAULT 0"))
                conn.commit()
    except Exception as e:
        print("Aviso ao verificar/atualizar schema:", str(e))

@app.before_request
def before_request():
    if not hasattr(app, 'db_initialized'):
        db.create_all()
        ensure_master_user()
        ensure_schema_updates()
        app.db_initialized = True


@app.route('/sw.js')
def serve_sw():
    from flask import send_from_directory
    return send_from_directory('static', 'sw.js', mimetype='application/javascript')

@app.route('/login')

def login_page():
    if get_current_user():
        return redirect('/')
    return render_template('login.html')

@app.route('/')
def index():
    user = get_current_user()
    if not user:
        return redirect('/login')
    projects = Project.query.all()
    return render_template('index.html', projects=projects, current_user=user)

# --- Authentication APIs ---
@app.route('/api/login', methods=['POST'])
def login_api():
    data = request.json or {}
    email = data.get('email', '').strip()
    if not email:
        return jsonify({'error': 'Informe o e-mail cadastrado.'}), 400

    user = User.query.filter(db.func.lower(User.email) == email.lower()).first()
    if not user:
        return jsonify({'error': 'E-mail não cadastrado na plataforma. Solicite acesso ao Administrador Master.'}), 401
    
    if not user.is_active:
        return jsonify({'error': 'Acesso desativado. Entre em contato com o Administrador Master.'}), 403

    session['user_id'] = user.id
    return jsonify({
        'message': 'Login realizado com sucesso',
        'user': {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'role': user.role,
            'is_master': user.is_master
        }
    })

@app.route('/api/logout', methods=['POST'])
def logout_api():
    session.pop('user_id', None)
    return jsonify({'message': 'Desconectado com sucesso'})

@app.route('/api/me')
def me_api():
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Não autenticado'}), 401
    return jsonify({
        'id': user.id,
        'name': user.name,
        'email': user.email,
        'role': user.role,
        'is_master': user.is_master
    })

# --- Admin Master User Management APIs ---
@app.route('/api/admin/users', methods=['GET'])
def list_users_admin():
    user = get_current_user()
    if not user or not user.is_master:
        return jsonify({'error': 'Acesso negado. Apenas o Usuário Master tem permissão.'}), 403

    users = User.query.order_by(User.id.asc()).all()
    return jsonify([{
        'id': u.id,
        'name': u.name,
        'email': u.email,
        'role': u.role or 'Desenvolvedor',
        'is_master': u.is_master,
        'is_active': u.is_active
    } for u in users])

@app.route('/api/admin/users', methods=['POST'])
def create_user_admin():
    user = get_current_user()
    if not user or not user.is_master:
        return jsonify({'error': 'Acesso negado. Apenas o Usuário Master pode adicionar usuários.'}), 403

    data = request.json or {}
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    role = data.get('role', 'Desenvolvedor').strip()
    is_master = bool(data.get('is_master', False))

    if not name or not email:
        return jsonify({'error': 'Nome e E-mail são obrigatórios.'}), 400

    existing = User.query.filter(db.func.lower(User.email) == email.lower()).first()
    if existing:
        return jsonify({'error': 'Este e-mail já está cadastrado.'}), 400

    new_user = User(
        name=name,
        email=email,
        role=role,
        is_master=is_master,
        is_active=True
    )
    db.session.add(new_user)
    db.session.commit()

    return jsonify({
        'id': new_user.id,
        'name': new_user.name,
        'email': new_user.email,
        'role': new_user.role,
        'is_master': new_user.is_master,
        'is_active': new_user.is_active
    }), 201

@app.route('/api/admin/users/<int:target_user_id>', methods=['PUT'])
def update_user_admin(target_user_id):
    user = get_current_user()
    if not user or not user.is_master:
        return jsonify({'error': 'Acesso negado.'}), 403

    target_user = db.session.get(User, target_user_id)
    if not target_user:
        return jsonify({'error': 'Usuário não encontrado.'}), 404

    data = request.json or {}
    if 'is_active' in data:
        target_user.is_active = bool(data['is_active'])
    if 'role' in data:
        target_user.role = data['role']
    if 'is_master' in data:
        target_user.is_master = bool(data['is_master'])

    db.session.commit()
    return jsonify({'message': 'Usuário atualizado com sucesso'})

# --- Project & Task APIs ---
@app.route('/api/projects', methods=['POST'])
def create_project():
    data = request.json
    project = Project(name=data['name'], description=data.get('description', ''))
    db.session.add(project)
    db.session.commit()
    report = MeetingReport(content="# Relatório Inicial\n\nAdicione aqui as definições...", project_id=project.id)
    db.session.add(report)
    db.session.commit()
    return jsonify({'id': project.id, 'name': project.name}), 201

@app.route('/task/<int:task_id>')
def task_page(task_id):
    user = get_current_user()
    if not user:
        return redirect('/login')
    task = Task.query.get_or_404(task_id)
    blocks = TaskBlock.query.filter_by(task_id=task.id).order_by(TaskBlock.position.asc(), TaskBlock.id.asc()).all()
    return render_template('task_page.html', task=task, blocks=blocks, current_user=user)




@app.route('/api/projects/<int:project_id>')
def get_project(project_id):
    user = get_current_user()
    project = Project.query.get_or_404(project_id)
    tasks = Task.query.filter_by(project_id=project.id).all()
    notes = Note.query.filter_by(project_id=project.id).all()
    report = MeetingReport.query.filter_by(project_id=project.id).first()
    messages = Message.query.filter_by(project_id=project.id).order_by(Message.created_at.asc()).all()
    
    task_list = []
    for t in tasks:
        current_status = t.status
        if t.status == 'Pendente' and t.deadline and t.deadline < datetime.now():
            current_status = 'Atrasado'
            
        assignees_names = ", ".join([u.name for u in t.assignees]) if t.assignees else (t.assignee.name if t.assignee else 'Nenhum')
        assignees_list = [{'id': u.id, 'name': u.name} for u in t.assignees] if t.assignees else ([{'id': t.assignee.id, 'name': t.assignee.name}] if t.assignee else [])


        task_list.append({
            'id': t.id, 
            'title': t.title,
            'description': t.description,
            'phase': t.phase,
            'status': current_status,
            'deadline': t.deadline.strftime('%Y-%m-%d') if t.deadline else None,
            'assignee_id': t.assignee_id,
            'assignee_name': assignees_names,
            'assignees': assignees_list,
            'has_pending_alert': t.has_pending_alert
        })

        
    note_list = [{'id': n.id, 'content': n.content, 'category': n.category, 'is_completed': n.is_completed} for n in notes]

    
    message_list = [{
        'id': m.id,
        'user_id': m.user_id,
        'user_name': m.user.name if m.user else 'Usuário',
        'user_avatar': m.user.name[:1] if m.user else 'U',
        'message': m.content,
        'timestamp': m.created_at.strftime('%H:%M')
    } for m in messages]

    return jsonify({
        'id': project.id,
        'name': project.name,
        'description': project.description,
        'current_user_id': user.id if user else None,
        'tasks': task_list,
        'notes': note_list,
        'messages': message_list,
        'report': report.content if report else ""
    })


def get_vapid_object():
    """Retorna a instância Vapid carregada de variáveis de ambiente ou arquivo PEM."""
    priv_env = os.getenv("VAPID_PRIVATE_KEY")
    if priv_env and priv_env.strip():
        try:
            from pywebpush import Vapid
            priv_clean = priv_env.replace('\\n', '\n')
            return Vapid.from_pem(priv_clean.encode())
        except Exception as e:
            print("Erro ao carregar VAPID_PRIVATE_KEY do .env:", str(e))
            
    pem_path = os.path.join(app.root_path, 'private_key.pem')
    if os.path.exists(pem_path):
        try:
            from pywebpush import Vapid
            return Vapid.from_file(pem_path)
        except Exception as e:
            print("Erro ao carregar private_key.pem:", str(e))
    return None

def get_vapid_public_key_b64():
    pub_env = os.getenv("VAPID_PUBLIC_KEY")
    if pub_env and pub_env.strip():
        return pub_env.strip()

    v = get_vapid_object()
    if not v:
        return ""
    try:
        import base64
        raw_pub = v.public_key.public_bytes(
            encoding=__import__('cryptography.hazmat.primitives.serialization').hazmat.primitives.serialization.Encoding.X962,
            format=__import__('cryptography.hazmat.primitives.serialization').hazmat.primitives.serialization.PublicFormat.UncompressedPoint
        )
        return base64.urlsafe_b64encode(raw_pub).decode().rstrip('=')
    except Exception as e:
        print("Erro ao formatar chave VAPID publica:", str(e))
        return ""

def send_push_notification_to_all(title, body, url="/"):
    try:
        from pywebpush import webpush, WebPushException
        import json
        
        subscriptions = PushSubscription.query.all()
        if not subscriptions:
            return
            
        payload = json.dumps({
            "title": title,
            "body": body,
            "url": url
        })
        
        vapid_obj = get_vapid_object()
        if not vapid_obj:
            print("Aviso: Nenhuma chave VAPID encontrada para envio de WebPush.")
            return

        for sub in subscriptions:
            try:
                sub_info = json.loads(sub.subscription_json)
                webpush(
                    subscription_info=sub_info,
                    data=payload,
                    vapid_private_key=vapid_obj,
                    vapid_claims={"sub": "mailto:suporte@cosampa.com.br"}
                )
            except WebPushException as ex:
                print("Aviso WebPush:", ex)
                if ex.response is not None and ex.response.status_code in [404, 410]:
                    db.session.delete(sub)
                    db.session.commit()
            except Exception as err:
                print("Erro envio WebPush individual:", str(err))
    except Exception as e:
        print("Erro geral no WebPush:", str(e))


@app.route('/api/vapid-public-key', methods=['GET'])
def get_vapid_key_route():
    return jsonify({'public_key': get_vapid_public_key_b64()})

@app.route('/api/push-subscriptions', methods=['POST'])
def save_push_subscription():
    import json
    data = request.json or {}
    endpoint = data.get('endpoint', '').strip()
    if not endpoint:
        return jsonify({'error': 'Endpoint inválido'}), 400
        
    sub_json = json.dumps(data)
    user = get_current_user()
    
    existing = PushSubscription.query.filter_by(endpoint=endpoint).first()
    if existing:
        existing.subscription_json = sub_json
        if user:
            existing.user_id = user.id
    else:
        new_sub = PushSubscription(
            endpoint=endpoint,
            subscription_json=sub_json,
            user_id=user.id if user else None
        )
        db.session.add(new_sub)
        
    db.session.commit()
    return jsonify({'message': 'Push subscription salva com sucesso'}), 201


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

    initial_desc = data.get('description', '')
    task = Task(
        title=data['title'],
        description=initial_desc,
        project_id=project_id,
        deadline=deadline_date,
        phase=data.get('phase', 'Ideação/Requisitos')
    )
    db.session.add(task)
    
    # Assign multiple members
    raw_ids = data.get('assignee_ids') or ([] if not data.get('assignee_id') else [data.get('assignee_id')])
    assignee_ids = [int(i) for i in raw_ids if str(i).isdigit()]
    if assignee_ids:
        users = User.query.filter(User.id.in_(assignee_ids)).all()
        task.assignees = users
        if users:
            task.assignee_id = users[0].id

    db.session.commit()

    if initial_desc and initial_desc.strip():
        block = TaskBlock(
            task_id=task.id,
            block_type='Descrição Inicial',
            content=initial_desc.strip()
        )
        db.session.add(block)
        db.session.commit()

    # Emitir evento Socket.IO em tempo real para os navegadores abertos
    try:
        socketio.emit('task_created', {
            'task_id': task.id,
            'title': task.title,
            'project_id': project_id
        }, room=f"project_{project_id}")
        
        # Emissão global para notificações da área de trabalho
        socketio.emit('global_task_created', {
            'task_id': task.id,
            'title': task.title,
            'project_id': project_id
        })
    except Exception as e:
        print("Erro ao emitir socket task_created:", str(e))

    # Disparar Web Push Notification para todos os inscritos (mesmo com navegador/aba fechados!)
    try:
        send_push_notification_to_all(
            title="📌 Nova Tarefa Criada!",
            body=f"A tarefa '{task.title}' foi adicionada.",
            url=f"/task/{task.id}"
        )
    except Exception as e:
        print("Erro ao disparar WebPush na criacao de tarefa:", str(e))

    return jsonify({'id': task.id, 'title': task.title, 'status': task.status}), 201



@app.route('/api/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    t = Task.query.get_or_404(task_id)
    current_status = t.status
    if t.status != 'Concluido' and t.deadline and t.deadline < datetime.now():
        current_status = 'Atrasado'
        
    assignees_names = ", ".join([u.name for u in t.assignees]) if t.assignees else (t.assignee.name if t.assignee else 'Nenhum')
    assignees_list = [{'id': u.id, 'name': u.name} for u in t.assignees] if t.assignees else ([{'id': t.assignee.id, 'name': t.assignee.name}] if t.assignee else [])
    assignee_ids = [u.id for u in t.assignees] if t.assignees else ([t.assignee_id] if t.assignee_id else [])

    return jsonify({
        'id': t.id,
        'title': t.title,
        'description': t.description,
        'generated_markdown': t.generated_markdown,
        'phase': t.phase,
        'status': current_status,
        'deadline': t.deadline.strftime('%Y-%m-%d') if t.deadline else None,
        'assignee_id': t.assignee_id,
        'assignee_ids': assignee_ids,
        'assignee_name': assignees_names,
        'assignees': assignees_list,
        'has_pending_alert': t.has_pending_alert
    })

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    t = Task.query.get_or_404(task_id)
    data = request.json or {}
    
    if 'title' in data and data['title'].strip():
        t.title = data['title'].strip()
    if 'description' in data:
        t.description = data['description'].strip()
    if 'status' in data:
        t.status = data['status']
    if 'deadline' in data:
        t.deadline = datetime.strptime(data['deadline'], '%Y-%m-%d') if data['deadline'] else None
        
    if 'assignee_ids' in data:
        raw_ids = data['assignee_ids'] or []
        assignee_ids = [int(i) for i in raw_ids if str(i).isdigit()]
        users = User.query.filter(User.id.in_(assignee_ids)).all() if assignee_ids else []
        t.assignees = users
        t.assignee_id = users[0].id if users else None

    db.session.commit()
    
    socketio.emit('task_updated', {
        'task_id': t.id,
        'title': t.title,
        'status': t.status
    }, room=f"project_{t.project_id}")
    
    return jsonify({'message': 'Tarefa atualizada com sucesso'})


@app.route('/api/tasks/<int:task_id>/status', methods=['POST'])
def update_task_status_endpoint(task_id):
    t = Task.query.get_or_404(task_id)
    data = request.json or {}
    if 'status' in data:
        t.status = data['status']
        db.session.commit()
        socketio.emit('task_updated', {
            'task_id': t.id,
            'title': t.title,
            'status': t.status
        }, room=f"project_{t.project_id}")
    return jsonify({'message': 'Success', 'status': t.status})


@app.route('/api/tasks/<int:task_id>/blocks', methods=['POST'])
def add_task_block(task_id):
    task = Task.query.get_or_404(task_id)
    data = request.json or {}
    block_type = data.get('type', 'Informação')
    content = data.get('content', '')
    if not content:
        return jsonify({'error': 'Conteúdo do bloco é obrigatório'}), 400
        
    max_pos = db.session.query(db.func.max(TaskBlock.position)).filter_by(task_id=task.id).scalar() or 0

    block = TaskBlock(
        task_id=task.id,
        block_type=block_type,
        content=content,
        position=max_pos + 1
    )
    db.session.add(block)
    db.session.commit()
    return jsonify({'id': block.id, 'type': block.block_type, 'content': block.content, 'position': block.position}), 201

@app.route('/api/blocks/<int:block_id>', methods=['PUT'])
def edit_task_block(block_id):
    block = TaskBlock.query.get_or_404(block_id)
    data = request.json or {}
    if 'content' in data:
        block.content = data['content'].strip()
    if 'type' in data:
        block.block_type = data['type'].strip()
    db.session.commit()
    return jsonify({'id': block.id, 'type': block.block_type, 'content': block.content, 'position': block.position})

@app.route('/api/blocks/<int:block_id>', methods=['DELETE'])
def delete_task_block(block_id):
    block = TaskBlock.query.get_or_404(block_id)
    db.session.delete(block)
    db.session.commit()
    return jsonify({'message': 'Bloco removido com sucesso'})

@app.route('/api/tasks/<int:task_id>/blocks/reorder', methods=['POST'])
def reorder_task_blocks(task_id):
    task = Task.query.get_or_404(task_id)
    data = request.json or {}
    order_ids = data.get('block_ids', [])
    
    for idx, block_id in enumerate(order_ids, start=1):
        TaskBlock.query.filter_by(id=block_id, task_id=task.id).update({'position': idx})
    
    db.session.commit()
    return jsonify({'message': 'Ordem dos blocos atualizada com sucesso'})


@app.route('/api/tasks/<int:task_id>/comments', methods=['GET'])
def get_task_section_comments(task_id):
    task = Task.query.get_or_404(task_id)
    comments = TaskSectionComment.query.filter_by(task_id=task.id).order_by(TaskSectionComment.created_at.asc()).all()
    return jsonify([{
        'id': c.id,
        'topic_title': c.topic_title,
        'comment_text': c.comment_text,
        'created_at': c.created_at.isoformat()
    } for c in comments])

@app.route('/api/tasks/<int:task_id>/comments', methods=['POST'])
def add_task_section_comment(task_id):
    task = Task.query.get_or_404(task_id)
    data = request.json or {}
    topic_title = data.get('topic_title', '').strip()
    comment_text = data.get('comment_text', '').strip()
    if not topic_title or not comment_text:
        return jsonify({'error': 'Tópico e comentário são obrigatórios'}), 400

    comment = TaskSectionComment(
        task_id=task.id,
        topic_title=topic_title,
        comment_text=comment_text
    )
    db.session.add(comment)
    db.session.commit()
    return jsonify({
        'id': comment.id,
        'topic_title': comment.topic_title,
        'comment_text': comment.comment_text,
        'created_at': comment.created_at.isoformat()
    }), 201

@app.route('/api/comments/<int:comment_id>', methods=['DELETE'])
def delete_task_section_comment(comment_id):
    comment = TaskSectionComment.query.get_or_404(comment_id)
    db.session.delete(comment)
    db.session.commit()
    return jsonify({'message': 'Comentário removido com sucesso'})


@app.route('/api/tasks/<int:task_id>/generate', methods=['POST'])
def generate_markdown(task_id):
    task = Task.query.get_or_404(task_id)
    blocks = TaskBlock.query.filter_by(task_id=task.id).order_by(TaskBlock.position.asc(), TaskBlock.id.asc()).all()
    
    blocks_data = [{'type': b.block_type, 'content': b.content, 'position': b.position} for b in blocks]
    
    comments = TaskSectionComment.query.filter_by(task_id=task.id).all()
    topic_comments = [{'topic_title': c.topic_title, 'comment_text': c.comment_text} for c in comments]

    data = request.json or {}
    additional_prompt = data.get('prompt', '')
    
    try:
        new_markdown = generate_task_markdown(
            task_title=task.title,
            blocks=blocks_data,
            additional_prompt=additional_prompt,
            existing_markdown=task.generated_markdown or "",
            topic_comments=topic_comments
        )
        task.generated_markdown = new_markdown
        db.session.commit()
        return jsonify({'message': 'Success', 'markdown': new_markdown})
    except Exception as e:
        print("Erro Gemini:", str(e))
        return jsonify({'error': str(e)}), 500


@app.route('/api/tasks/<int:task_id>/reformulate', methods=['POST'])
def reformulate_markdown(task_id):
    task = Task.query.get_or_404(task_id)
    data = request.json or {}
    comment = data.get('comment', '').strip()
    if not comment:
        return jsonify({'error': 'Comentário é obrigatório'}), 400

    try:
        new_markdown = reformulate_task_markdown(
            task_title=task.title,
            current_markdown=task.generated_markdown or "",
            comment=comment
        )
        task.generated_markdown = new_markdown
        db.session.commit()
        return jsonify({'message': 'Success', 'markdown': new_markdown})
    except Exception as e:
        print("Erro Gemini na reformulação:", str(e))
        return jsonify({'error': str(e)}), 500




@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    project_id = task.project_id

    # 1. Delete associated TaskBlock entries from db session
    TaskBlock.query.filter_by(task_id=task.id).delete(synchronize_session=False)
    
    # 2. Delete associated Attachment entries from db session
    Attachment.query.filter_by(task_id=task.id).delete(synchronize_session=False)
    
    # 3. Clear assignees relationship to prevent FK integrity errors
    task.assignees = []
    
    # 4. Delete task
    db.session.delete(task)
    db.session.commit()
    
    # Broadcast task deletion to room
    socketio.emit('task_deleted', {'task_id': task_id}, room=f"project_{project_id}")
    return jsonify({'message': 'Tarefa excluída com sucesso'})



@app.route('/api/projects/<int:project_id>/notes', methods=['POST'])
def create_note(project_id):
    data = request.json
    note = Note(
        content=data['content'],
        category=data['category'],
        project_id=project_id,
        is_completed=False
    )
    db.session.add(note)
    db.session.commit()
    return jsonify({'id': note.id, 'content': note.content, 'category': note.category, 'is_completed': note.is_completed}), 201


@app.route('/api/notes/<int:note_id>', methods=['PUT'])
def update_note(note_id):
    note = Note.query.get_or_404(note_id)
    data = request.json or {}
    if 'is_completed' in data:
        note.is_completed = bool(data['is_completed'])
    if 'content' in data:
        note.content = data['content']
    if 'category' in data:
        note.category = data['category']
    db.session.commit()
    return jsonify({'id': note.id, 'content': note.content, 'category': note.category, 'is_completed': note.is_completed})


@app.route('/api/notes/<int:note_id>', methods=['DELETE'])
def delete_note(note_id):
    note = Note.query.get_or_404(note_id)
    db.session.delete(note)
    db.session.commit()
    return jsonify({'message': 'Anotação excluída com sucesso'})


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
    project_id = data.get('project_id')
    content = data.get('message', '').strip()
    if not project_id or not content:
        return
        
    user = get_current_user()
    if not user:
        return
    
    msg = Message(content=content, project_id=project_id, user_id=user.id)
    db.session.add(msg)
    db.session.commit()
    
    emit('receive_message', {
        'id': msg.id,
        'user_id': user.id,
        'user_name': user.name,
        'user_avatar': user.name[:1],
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
