from flask import Flask, render_template_string, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import logging
import os

# Initialize Flask app
app = Flask(__name__)

# ============================================================================
# PRODUCTION CONFIGURATION
# ============================================================================

# Database configuration - supports both PostgreSQL (Render) and SQLite (local)
database_url = os.environ.get('DATABASE_URL')
if database_url:
    # Render uses postgres:// but SQLAlchemy needs postgresql://
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    # Local development with SQLite
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///goals.db'
#--added this due to db issue on 01-09-2025
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,      # Verify connections before using
    'pool_recycle': 300,        # Recycle connections after 5 minutes
    'connect_args': {
        'connect_timeout': 10,  # 10 second timeout
    }
}

# Security configuration
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(24))
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('PRODUCTION', 'False') == 'True'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Initialize database
db = SQLAlchemy()
db.init_app(app)
# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console output for Render logs
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# DATABASE MODELS
# ============================================================================

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    goals = db.relationship('Goal', backref='user', lazy=True, cascade='all, delete-orphan')

class Goal(db.Model):
    __tablename__ = 'goals'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    deadline = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    tasks = db.relationship('Task', backref='goal', lazy=True, cascade='all, delete-orphan')

class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(300), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    position = db.Column(db.Integer, nullable=False)
    goal_id = db.Column(db.Integer, db.ForeignKey('goals.id'), nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# ============================================================================
# HTML TEMPLATES (same as before - keeping them in for completeness)
# ============================================================================

LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Login - Goal Tracker</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Arial, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; justify-content: center; align-items: center; }
        .container { background: white; padding: 40px; border-radius: 10px; box-shadow: 0 10px 40px rgba(0,0,0,0.2); width: 100%; max-width: 400px; }
        h1 { color: #333; margin-bottom: 30px; text-align: center; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 5px; color: #555; font-weight: bold; }
        input { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 5px; font-size: 14px; }
        button { width: 100%; padding: 12px; background: #667eea; color: white; border: none; border-radius: 5px; font-size: 16px; cursor: pointer; font-weight: bold; }
        button:hover { background: #5568d3; }
        .switch { text-align: center; margin-top: 20px; color: #666; }
        .switch a { color: #667eea; text-decoration: none; font-weight: bold; }
        .flash { padding: 10px; margin-bottom: 20px; border-radius: 5px; }
        .flash.error { background: #fee; color: #c33; }
        .flash.success { background: #efe; color: #3c3; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 Goal Tracker</h1>
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="flash {{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        <form method="POST">
            <div class="form-group">
                <label>Username</label>
                <input type="text" name="username" required minlength="3" maxlength="80">
            </div>
            <div class="form-group">
                <label>Password</label>
                <input type="password" name="password" required minlength="6">
            </div>
            <button type="submit">{{ 'Login' if mode == 'login' else 'Register' }}</button>
        </form>
        <div class="switch">
            {% if mode == 'login' %}
                Don't have an account? <a href="{{ url_for('register') }}">Register</a>
            {% else %}
                Already have an account? <a href="{{ url_for('login') }}">Login</a>
            {% endif %}
        </div>
    </div>
</body>
</html>
'''

LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Login - Goal Tracker</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Arial, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; justify-content: center; align-items: center; }
        .container { background: white; padding: 40px; border-radius: 10px; box-shadow: 0 10px 40px rgba(0,0,0,0.2); width: 100%; max-width: 400px; }
        h1 { color: #333; margin-bottom: 30px; text-align: center; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 5px; color: #555; font-weight: bold; }
        input { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 5px; font-size: 14px; }
        button { width: 100%; padding: 12px; background: #667eea; color: white; border: none; border-radius: 5px; font-size: 16px; cursor: pointer; font-weight: bold; }
        button:hover { background: #5568d3; }
        .switch { text-align: center; margin-top: 20px; color: #666; }
        .switch a { color: #667eea; text-decoration: none; font-weight: bold; }
        .flash { padding: 10px; margin-bottom: 20px; border-radius: 5px; }
        .flash.error { background: #fee; color: #c33; }
        .flash.success { background: #efe; color: #3c3; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 Goal Tracker</h1>
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="flash {{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        <form method="POST">
            <div class="form-group">
                <label>Username</label>
                <input type="text" name="username" required minlength="3" maxlength="80">
            </div>
            <div class="form-group">
                <label>Password</label>
                <input type="password" name="password" required minlength="6">
            </div>
            <button type="submit">{{ 'Login' if mode == 'login' else 'Register' }}</button>
        </form>
        <div class="switch">
            {% if mode == 'login' %}
                Don't have an account? <a href="{{ url_for('register') }}">Register</a>
            {% else %}
                Already have an account? <a href="{{ url_for('login') }}">Login</a>
            {% endif %}
        </div>
    </div>
</body>
</html>
'''

DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Dashboard - Goal Tracker</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Arial, sans-serif; background: #f5f5f5; }
        .navbar { background: #667eea; color: white; padding: 20px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; }
        .navbar h1 { font-size: 24px; }
        .navbar a { color: white; text-decoration: none; padding: 10px 20px; background: rgba(255,255,255,0.2); border-radius: 5px; }
        .navbar a:hover { background: rgba(255,255,255,0.3); }
        .container { max-width: 1200px; margin: 40px auto; padding: 0 20px; }
        .welcome { background: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .btn { display: inline-block; padding: 12px 24px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; font-weight: bold; }
        .btn:hover { background: #5568d3; }
        .goals-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
        .goal-card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .goal-card h3 { color: #333; margin-bottom: 10px; }
        .goal-card .deadline { color: #666; font-size: 14px; margin-bottom: 15px; }
        .goal-card .progress { background: #eee; height: 8px; border-radius: 4px; margin-bottom: 15px; overflow: hidden; }
        .goal-card .progress-bar { background: #667eea; height: 100%; transition: width 0.3s; }
        .goal-card .stats { color: #666; font-size: 14px; margin-bottom: 15px; }
        .goal-card .actions { display: flex; gap: 10px; flex-wrap: wrap; }
        .goal-card .actions a { padding: 8px 16px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; font-size: 14px; }
        .goal-card .actions a:hover { background: #5568d3; }
        .goal-card .actions a.delete { background: #e74c3c; }
        .goal-card .actions a.delete:hover { background: #c0392b; }
        .flash { padding: 15px; margin-bottom: 20px; border-radius: 5px; }
        .flash.success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .empty { text-align: center; padding: 60px 20px; color: #999; }
    </style>
</head>
<body>
    <div class="navbar">
        <h1>🎯 Goal Tracker</h1>
        <div>
            <span style="margin-right: 20px;">Welcome, {{ session.username }}!</span>
            <a href="{{ url_for('logout') }}">Logout</a>
        </div>
    </div>
    <div class="container">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="flash {{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        <div class="welcome">
            <h2>Your Goals</h2>
            <p style="color: #666; margin: 10px 0 20px 0;">Track your personal development journey</p>
            <a href="{{ url_for('create_goal') }}" class="btn">+ Create New Goal</a>
        </div>
        {% if goals %}
            <div class="goals-grid">
                {% for goal in goals %}
                <div class="goal-card">
                    <h3>{{ goal.title }}</h3>
                    <div class="deadline">📅 Deadline: {{ goal.deadline }}</div>
                    <div class="progress">
                        <div class="progress-bar" style="width: {{ goal.progress }}%"></div>
                    </div>
                    <div class="stats">{{ goal.completed_tasks }}/{{ goal.total_tasks }} tasks completed</div>
                    <div class="actions">
                        <a href="{{ url_for('view_goal', goal_id=goal.id) }}">View Tasks</a>
                        <a href="{{ url_for('delete_goal', goal_id=goal.id) }}" class="delete" onclick="return confirm('Delete this goal?')">Delete</a>
                    </div>
                </div>
                {% endfor %}
            </div>
        {% else %}
            <div class="empty">
                <h3>No goals yet!</h3>
                <p>Create your first goal to start your personal development journey.</p>
            </div>
        {% endif %}
    </div>
</body>
</html>
'''

CREATE_GOAL_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Create Goal - Goal Tracker</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Arial, sans-serif; background: #f5f5f5; }
        .navbar { background: #667eea; color: white; padding: 20px; display: flex; justify-content: space-between; align-items: center; }
        .navbar h1 { font-size: 24px; }
        .navbar a { color: white; text-decoration: none; padding: 10px 20px; background: rgba(255,255,255,0.2); border-radius: 5px; }
        .navbar a:hover { background: rgba(255,255,255,0.3); }
        .container { max-width: 800px; margin: 40px auto; padding: 0 20px; }
        .form-card { background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h2 { color: #333; margin-bottom: 30px; }
        .form-group { margin-bottom: 25px; }
        label { display: block; margin-bottom: 8px; color: #555; font-weight: bold; }
        input, textarea { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 5px; font-size: 14px; font-family: Arial, sans-serif; }
        textarea { min-height: 150px; resize: vertical; }
        .help-text { font-size: 12px; color: #999; margin-top: 5px; }
        button { width: 100%; padding: 15px; background: #667eea; color: white; border: none; border-radius: 5px; font-size: 16px; cursor: pointer; font-weight: bold; margin-top: 10px; }
        button:hover { background: #5568d3; }
        .step { display: none; }
        .step.active { display: block; }
        .step-indicator { display: flex; justify-content: center; gap: 10px; margin-bottom: 30px; }
        .step-dot { width: 12px; height: 12px; border-radius: 50%; background: #ddd; }
        .step-dot.active { background: #667eea; }
        .task-list { margin-top: 20px; }
        .task-item { background: #f9f9f9; padding: 15px; border-radius: 5px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; border-left: 3px solid #667eea; }
        .task-item .drag-handle { cursor: move; margin-right: 10px; color: #999; }
        .task-item button { width: auto; padding: 5px 15px; background: #e74c3c; margin: 0; }
        .task-item button:hover { background: #c0392b; }
    </style>
</head>
<body>
    <div class="navbar">
        <h1>🎯 Goal Tracker</h1>
        <a href="{{ url_for('dashboard') }}">← Back to Dashboard</a>
    </div>
    <div class="container">
        <div class="form-card">
            <div class="step-indicator">
                <div class="step-dot active" id="dot1"></div>
                <div class="step-dot" id="dot2"></div>
                <div class="step-dot" id="dot3"></div>
            </div>
            
            <form method="POST" id="goalForm">
                <div class="step active" id="step1">
                    <h2>Step 1: Define Your Goal</h2>
                    <div class="form-group">
                        <label>What is your goal?</label>
                        <input type="text" name="goal" id="goalInput" required>
                        <div class="help-text">Be specific and clear about what you want to achieve</div>
                    </div>
                    <button type="button" onclick="nextStep(2)">Next →</button>
                </div>

                <div class="step" id="step2">
                    <h2>Step 2: Set a Deadline</h2>
                    <div class="form-group">
                        <label>When do you want to achieve this goal?</label>
                        <input type="date" name="deadline" id="deadlineInput" required>
                        <div class="help-text">Choose a realistic deadline that motivates you</div>
                    </div>
                    <button type="button" onclick="prevStep(1)">← Previous</button>
                    <button type="button" onclick="nextStep(3)">Next →</button>
                </div>

                <div class="step" id="step3">
                    <h2>Step 3: Break It Down into Tasks</h2>
                    <div class="form-group">
                        <label>List the tasks needed to achieve your goal</label>
                        <textarea id="tasksInput" placeholder="Enter each task on a new line&#10;Example:&#10;Research available courses&#10;Create study schedule&#10;Complete first module"></textarea>
                        <div class="help-text">Enter one task per line. You can reorder them after adding.</div>
                    </div>
                    <button type="button" onclick="addTasks()">Add Tasks</button>
                    <div class="task-list" id="taskList"></div>
                    <input type="hidden" name="tasks" id="tasksHidden">
                    <button type="button" onclick="prevStep(2)">← Previous</button>
                    <button type="submit">Create Goal 🎯</button>
                </div>
            </form>
        </div>
    </div>

    <script>
        let tasks = [];
        let draggedItem = null;

        function nextStep(step) {
            if (step === 2 && !document.getElementById('goalInput').value) {
                alert('Please enter a goal');
                return;
            }
            if (step === 3 && !document.getElementById('deadlineInput').value) {
                alert('Please set a deadline');
                return;
            }
            
            document.querySelectorAll('.step').forEach(s => s.classList.remove('active'));
            document.querySelectorAll('.step-dot').forEach(d => d.classList.remove('active'));
            
            document.getElementById('step' + step).classList.add('active');
            document.getElementById('dot' + step).classList.add('active');
        }

        function prevStep(step) {
            document.querySelectorAll('.step').forEach(s => s.classList.remove('active'));
            document.querySelectorAll('.step-dot').forEach(d => d.classList.remove('active'));
            
            document.getElementById('step' + step).classList.add('active');
            document.getElementById('dot' + step).classList.add('active');
        }

        function addTasks() {
            const input = document.getElementById('tasksInput').value;
            const newTasks = input.split('\\n').filter(t => t.trim());
            
            if (newTasks.length === 0) {
                alert('Please enter at least one task');
                return;
            }
            
            tasks = newTasks.map((t, i) => ({ id: Date.now() + i, text: t.trim() }));
            renderTasks();
            document.getElementById('tasksInput').value = '';
        }

        function renderTasks() {
            const list = document.getElementById('taskList');
            list.innerHTML = tasks.map((task, idx) => `
                <div class="task-item" draggable="true" data-id="${task.id}">
                    <div>
                        <span class="drag-handle">☰</span>
                        <span>${task.text}</span>
                    </div>
                    <button type="button" onclick="removeTask(${task.id})">Remove</button>
                </div>
            `).join('');
            
            document.getElementById('tasksHidden').value = JSON.stringify(tasks.map(t => t.text));
            
            document.querySelectorAll('.task-item').forEach(item => {
                item.addEventListener('dragstart', handleDragStart);
                item.addEventListener('dragover', handleDragOver);
                item.addEventListener('drop', handleDrop);
                item.addEventListener('dragend', handleDragEnd);
            });
        }

        function removeTask(id) {
            tasks = tasks.filter(t => t.id !== id);
            renderTasks();
        }

        function handleDragStart(e) {
            draggedItem = this;
            e.dataTransfer.effectAllowed = 'move';
            this.style.opacity = '0.5';
        }

        function handleDragOver(e) {
            if (e.preventDefault) e.preventDefault();
            e.dataTransfer.dropEffect = 'move';
            return false;
        }

        function handleDrop(e) {
            if (e.stopPropagation) e.stopPropagation();
            
            if (draggedItem !== this) {
                const draggedId = parseInt(draggedItem.dataset.id);
                const targetId = parseInt(this.dataset.id);
                
                const draggedIdx = tasks.findIndex(t => t.id === draggedId);
                const targetIdx = tasks.findIndex(t => t.id === targetId);
                
                tasks.splice(targetIdx, 0, tasks.splice(draggedIdx, 1)[0]);
                renderTasks();
            }
            return false;
        }

        function handleDragEnd(e) {
            this.style.opacity = '1';
        }

        document.getElementById('goalForm').addEventListener('submit', function(e) {
            if (tasks.length === 0) {
                e.preventDefault();
                alert('Please add at least one task');
            }
        });
    </script>
</body>
</html>
'''

VIEW_GOAL_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>{{ goal.title }} - Goal Tracker</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Arial, sans-serif; background: #f5f5f5; }
        .navbar { background: #667eea; color: white; padding: 20px; display: flex; justify-content: space-between; align-items: center; }
        .navbar h1 { font-size: 24px; }
        .navbar a { color: white; text-decoration: none; padding: 10px 20px; background: rgba(255,255,255,0.2); border-radius: 5px; }
        .navbar a:hover { background: rgba(255,255,255,0.3); }
        .container { max-width: 900px; margin: 40px auto; padding: 0 20px; }
        .goal-header { background: white; padding: 40px; border-radius: 10px; margin-bottom: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .goal-header h2 { color: #333; margin-bottom: 15px; font-size: 32px; }
        .goal-info { display: flex; gap: 30px; margin-bottom: 20px; color: #666; flex-wrap: wrap; }
        .progress { background: #eee; height: 20px; border-radius: 10px; margin-top: 20px; overflow: hidden; }
        .progress-bar { background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); height: 100%; transition: width 0.3s; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 12px; }
        .tasks-section { background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .tasks-section h3 { color: #333; margin-bottom: 20px; }
        .task-item { padding: 20px; border-bottom: 1px solid #eee; display: flex; align-items: center; gap: 15px; transition: background 0.2s; }
        .task-item:hover { background: #f9f9f9; }
        .task-item:last-child { border-bottom: none; }
        .task-item input[type="checkbox"] { width: 24px; height: 24px; cursor: pointer; }
        .task-item label { flex: 1; cursor: pointer; font-size: 16px; color: #333; }
        .task-item.completed label { text-decoration: line-through; color: #999; }
        .drag-handle { cursor: move; color: #999; font-size: 20px; }
        .flash { padding: 15px; margin-bottom: 20px; border-radius: 5px; }
        .flash.success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
    </style>
</head>
<body>
    <div class="navbar">
        <h1>🎯 Goal Tracker</h1>
        <a href="{{ url_for('dashboard') }}">← Back to Dashboard</a>
    </div>
    <div class="container">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="flash {{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        
        <div class="goal-header">
            <h2>{{ goal.title }}</h2>
            <div class="goal-info">
                <div>📅 Deadline: {{ goal.deadline }}</div>
                <div>✅ {{ completed_count }}/{{ total_count }} tasks completed</div>
            </div>
            <div class="progress">
                <div class="progress-bar" style="width: {{ progress }}%">{{ progress }}%</div>
            </div>
        </div>

        <div class="tasks-section">
            <h3>Tasks Checklist</h3>
            <div id="taskList">
                {% for task in tasks %}
                <div class="task-item {% if task.completed %}completed{% endif %}" draggable="true" data-id="{{ task.id }}">
                    <span class="drag-handle">☰</span>
                    <input type="checkbox" id="task{{ task.id }}" 
                           {% if task.completed %}checked{% endif %}
                           onchange="toggleTask({{ task.id }})">
                    <label for="task{{ task.id }}">{{ task.description }}</label>
                </div>
                {% endfor %}
            </div>
        </div>
    </div>

    <script>
        let draggedItem = null;

        document.querySelectorAll('.task-item').forEach(item => {
            item.addEventListener('dragstart', handleDragStart);
            item.addEventListener('dragover', handleDragOver);
            item.addEventListener('drop', handleDrop);
            item.addEventListener('dragend', handleDragEnd);
        });

        function handleDragStart(e) {
            draggedItem = this;
            e.dataTransfer.effectAllowed = 'move';
            this.style.opacity = '0.5';
        }

        function handleDragOver(e) {
            if (e.preventDefault) e.preventDefault();
            e.dataTransfer.dropEffect = 'move';
            return false;
        }

        function handleDrop(e) {
            if (e.stopPropagation) e.stopPropagation();
            
            if (draggedItem !== this) {
                const taskId = draggedItem.dataset.id;
                const targetId = this.dataset.id;
                
                fetch('/reorder_task', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ task_id: taskId, target_id: targetId })
                }).then(() => location.reload());
            }
            return false;
        }

        function handleDragEnd(e) {
            this.style.opacity = '1';
        }

        function toggleTask(taskId) {
            fetch('/toggle_task/' + taskId, { method: 'POST' })
                .then(() => location.reload());
        }
    </script>
</body>
</html>
'''

# ============================================================================
# ROUTES
# ============================================================================

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/health')
def health():
    """Health check endpoint for monitoring"""
    try:
        # Test database connection
        db.session.execute(db.text('SELECT 1'))
        return jsonify({'status': 'healthy', 'database': 'connected'}), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Username and password required', 'error')
            return render_template_string(LOGIN_TEMPLATE, mode='login')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            session.permanent = True
            session['user_id'] = user.id
            session['username'] = user.username
            logger.info(f"User logged in: {username}")
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            logger.warning(f"Failed login attempt: {username}")
            flash('Invalid credentials', 'error')
    
    return render_template_string(LOGIN_TEMPLATE, mode='login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Username and password required', 'error')
            return render_template_string(LOGIN_TEMPLATE, mode='register')
        
        if len(username) < 3:
            flash('Username must be at least 3 characters', 'error')
            return render_template_string(LOGIN_TEMPLATE, mode='register')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters', 'error')
            return render_template_string(LOGIN_TEMPLATE, mode='register')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template_string(LOGIN_TEMPLATE, mode='register')
        
        user = User(username=username, password=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        logger.info(f"New user registered: {username}")
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template_string(LOGIN_TEMPLATE, mode='register')

@app.route('/logout')
def logout():
    username = session.get('username')
    logger.info(f"User logged out: {username}")
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    goals = Goal.query.filter_by(user_id=session['user_id']).all()
    goals_data = []
    
    for goal in goals:
        total = len(goal.tasks)
        completed = sum(1 for t in goal.tasks if t.completed)
        progress = (completed / total * 100) if total > 0 else 0
        
        goals_data.append({
            'id': goal.id,
            'title': goal.title,
            'deadline': goal.deadline,
            'total_tasks': total,
            'completed_tasks': completed,
            'progress': int(progress)
        })
    
    return render_template_string(DASHBOARD_TEMPLATE, goals=goals_data)

@app.route('/create_goal', methods=['GET', 'POST'])
def create_goal():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        goal_title = request.form.get('goal', '').strip()
        deadline = request.form.get('deadline', '')
        tasks_json = request.form.get('tasks', '')
        
        if not goal_title or not deadline:
            flash('Goal title and deadline are required', 'error')
            return render_template_string(CREATE_GOAL_TEMPLATE)
        
        try:
            import json
            tasks_list = json.loads(tasks_json) if tasks_json else []
        except json.JSONDecodeError:
            flash('Invalid tasks format', 'error')
            return render_template_string(CREATE_GOAL_TEMPLATE)
        
        if not tasks_list:
            flash('Please add at least one task', 'error')
            return render_template_string(CREATE_GOAL_TEMPLATE)
        
        goal = Goal(title=goal_title, deadline=deadline, user_id=session['user_id'])
        db.session.add(goal)
        db.session.flush()
        
        for idx, task_desc in enumerate(tasks_list):
            task = Task(description=task_desc, position=idx, goal_id=goal.id)
            db.session.add(task)
        
        db.session.commit()
        logger.info(f"Goal created by {session['username']}: {goal_title} with {len(tasks_list)} tasks")
        flash('Goal created successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template_string(CREATE_GOAL_TEMPLATE)

@app.route('/view_goal/<int:goal_id>')
def view_goal(goal_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    goal = Goal.query.get_or_404(goal_id)
    if goal.user_id != session['user_id']:
        flash('Unauthorized access', 'error')
        return redirect(url_for('dashboard'))
    
    tasks = Task.query.filter_by(goal_id=goal_id).order_by(Task.position).all()
    total = len(tasks)
    completed = sum(1 for t in tasks if t.completed)
    progress = (completed / total * 100) if total > 0 else 0
    
    return render_template_string(VIEW_GOAL_TEMPLATE, goal=goal, tasks=tasks, 
                                  total_count=total, completed_count=completed, 
                                  progress=int(progress))

@app.route('/toggle_task/<int:task_id>', methods=['POST'])
def toggle_task(task_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    task = Task.query.get_or_404(task_id)
    if task.goal.user_id != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    task.completed = not task.completed
    db.session.commit()
    logger.info(f"Task toggled by {session['username']}: {task.description} - {'completed' if task.completed else 'incomplete'}")
    return jsonify({'success': True, 'completed': task.completed}), 200

@app.route('/reorder_task', methods=['POST'])
def reorder_task():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    task_id = int(data.get('task_id', 0))
    target_id = int(data.get('target_id', 0))
    
    if not task_id or not target_id:
        return jsonify({'error': 'Invalid data'}), 400
    
    task = Task.query.get_or_404(task_id)
    target = Task.query.get_or_404(target_id)
    
    if task.goal.user_id != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    tasks = Task.query.filter_by(goal_id=task.goal_id).order_by(Task.position).all()
    tasks.remove(task)
    target_idx = tasks.index(target)
    tasks.insert(target_idx, task)
    
    for idx, t in enumerate(tasks):
        t.position = idx
    
    db.session.commit()
    logger.info(f"Tasks reordered by {session['username']} in goal: {task.goal.title}")
    return jsonify({'success': True}), 200

@app.route('/delete_goal/<int:goal_id>')
def delete_goal(goal_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    goal = Goal.query.get_or_404(goal_id)
    if goal.user_id != session['user_id']:
        flash('Unauthorized access', 'error')
        return redirect(url_for('dashboard'))
    
    goal_title = goal.title
    db.session.delete(goal)
    db.session.commit()
    logger.info(f"Goal deleted by {session['username']}: {goal_title}")
    flash('Goal deleted successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.errorhandler(404)
def not_found(e):
    return render_template_string('<h1>404 - Page Not Found</h1>'), 404

@app.errorhandler(500)
def server_error(e):
    logger.error(f"Server error: {e}")
    return render_template_string('<h1>500 - Internal Server Error</h1>'), 500

# ============================================================================
# APPLICATION INITIALIZATION
# ============================================================================

def init_db():
    """Initialize database tables"""
    try : 
        with app.app_context():
            db.create_all()
            logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to init database: {e}")

if __name__ != '__main__':
    init_db()

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)