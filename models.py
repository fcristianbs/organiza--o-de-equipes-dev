from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50), default='Desenvolvedor')
    is_master = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    tasks = db.relationship('Task', backref='project', lazy=True)
    meeting_reports = db.relationship('MeetingReport', backref='project', lazy=True)
    notes = db.relationship('Note', backref='project', lazy=True)
    attachments = db.relationship('Attachment', backref='project', lazy=True)
    messages = db.relationship('Message', backref='project', lazy=True)
task_assignees = db.Table('task_assignees',
    db.Column('task_id', db.Integer, db.ForeignKey('task.id', ondelete='CASCADE'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), primary_key=True)
)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    generated_markdown = db.Column(db.Text, nullable=True)
    phase = db.Column(db.String(50), default='Ideação/Requisitos')

    status = db.Column(db.String(50), default='Pendente')
    deadline = db.Column(db.DateTime, nullable=True)
    has_pending_alert = db.Column(db.Boolean, default=False)
    pending_alert_history = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    assignee_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    assignee = db.relationship('User', backref='assigned_tasks', lazy=True)
    assignees = db.relationship('User', secondary=task_assignees, backref=db.backref('tasks_assigned_many', lazy=True))
    attachments = db.relationship('Attachment', backref='task', lazy=True)

    blocks = db.relationship('TaskBlock', backref='task', lazy=True)

class TaskBlock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    block_type = db.Column(db.String(50), nullable=False) # Ex: Regra, Requisito, Obs
    content = db.Column(db.Text, nullable=False)
    position = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class MeetingReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False) # Markdown content
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False) # Requisito Funcional, Requisito Técnico, Solicitação, TODO
    is_completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)


class Attachment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50), nullable=False) # Documento, CDU/Markdown, Imagem, Outros
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=True)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    user = db.relationship('User', backref='messages', lazy=True)


class TaskSectionComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    topic_title = db.Column(db.String(255), nullable=False)
    comment_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


