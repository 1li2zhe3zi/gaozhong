from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

# 配置
app.config.update({
    'DATABASE': os.path.join(app.root_path, 'database.db'),
    'UPLOAD_FOLDER': os.path.join(app.root_path, 'static', 'uploads'),
    'ALLOWED_EXTENSIONS': {'png', 'jpg', 'jpeg', 'gif'}
})

# 数据库连接
def get_db():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

# 初始化数据库（首次运行）
def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/tree')
def get_tree():
    db = get_db()
    tree = []
    
    # 获取科目
    subjects = db.execute('SELECT * FROM subjects ORDER BY id').fetchall()
    for subject in subjects:
        subject_node = {
            'id': subject['id'],
            'type': 'subject',
            'name': subject['name'],
            'children': []
        }
        
        # 获取书本
        books = db.execute(
            'SELECT * FROM books WHERE subject_id = ? ORDER BY id',
            (subject['id'],)
        ).fetchall()
        
        for book in books:
            book_node = {
                'id': book['id'],
                'type': 'book',
                'name': book['name'],
                'children': []
            }
            
            # 获取单元
            units = db.execute(
                'SELECT * FROM units WHERE book_id = ? ORDER BY id',
                (book['id'],)
            ).fetchall()
            
            for unit in units:
                unit_node = {
                    'id': unit['id'],
                    'type': 'unit',
                    'name': unit['name'],
                    'children': []
                }
                
                # 获取知识点
                knowledge_points = db.execute('''
                    SELECT k.*, COUNT(q.id) as question_count 
                    FROM knowledge k LEFT JOIN questions q 
                    ON k.id = q.knowledge_id 
                    WHERE unit_id = ? 
                    GROUP BY k.id 
                    ORDER BY k.id
                ''', (unit['id'],)).fetchall()
                
                unit_node['children'] = [dict(kp) for kp in knowledge_points]
                book_node['children'].append(unit_node)
            
            subject_node['children'].append(book_node)
        
        tree.append(subject_node)
    
    return jsonify(tree)

@app.route('/api/questions', methods=['GET', 'POST'])
def handle_questions():
    db = get_db()
    
    if request.method == 'GET':
        knowledge_id = request.args.get('knowledge_id')
        questions = db.execute('''
            SELECT q.*, k.name as knowledge_name 
            FROM questions q JOIN knowledge k 
            ON q.knowledge_id = k.id 
            WHERE q.knowledge_id = ?
        ''', (knowledge_id,)).fetchall()
        return jsonify([dict(q) for q in questions])
    
    elif request.method == 'POST':
        data = request.form
        file = request.files.get('image')
        
        filename = None
        if file and allowed_file(file.filename):
            filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{secure_filename(file.filename)}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        db.execute('''
            INSERT INTO questions (knowledge_id, content, answer, image_url)
            VALUES (?, ?, ?, ?)
        ''', (data['knowledge_id'], data['content'], data['answer'], filename))
        db.commit()
        
        return jsonify({'success': True})

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)
