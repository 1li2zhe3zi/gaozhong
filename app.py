from flask import Flask, jsonify, request
from flask_cors import CORS
import mysql.connector
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

# 数据库配置
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'yourpassword',
    'database': 'gaozhong_tiku'
}

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def db_conn():
    return mysql.connector.connect(**db_config)

@app.route('/api/tree', methods=['GET'])
def get_tree():
    conn = db_conn()
    cursor = conn.cursor(dictionary=True)
    
    # 获取完整树结构
    tree = []
    cursor.execute("SELECT * FROM subjects")
    subjects = cursor.fetchall()
    
    for subject in subjects:
        subject_node = {
            'id': subject['id'],
            'type': 'subject',
            'name': subject['name'],
            'children': []
        }
        
        cursor.execute("SELECT * FROM books WHERE subject_id = %s", (subject['id'],))
        books = cursor.fetchall()
        
        for book in books:
            book_node = {
                'id': book['id'],
                'type': 'book',
                'name': book['name'],
                'children': []
            }
            
            cursor.execute("SELECT * FROM units WHERE book_id = %s", (book['id'],))
            units = cursor.fetchall()
            
            for unit in units:
                unit_node = {
                    'id': unit['id'],
                    'type': 'unit',
                    'name': unit['name'],
                    'children': []
                }
                
                cursor.execute("SELECT * FROM knowledge WHERE unit_id = %s", (unit['id'],))
                knowledge_points = cursor.fetchall()
                
                for kp in knowledge_points:
                    kp_node = {
                        'id': kp['id'],
                        'type': 'knowledge',
                        'name': kp['name'],
                        'questions': []
                    }
                    unit_node['children'].append(kp_node)
                
                book_node['children'].append(unit_node)
            
            subject_node['children'].append(book_node)
        
        tree.append(subject_node)
    
    cursor.close()
    conn.close()
    return jsonify(tree)

@app.route('/api/questions', methods=['POST'])
def add_question():
    data = request.form
    file = request.files.get('image')
    
    # 保存图片
    filename = None
    if file:
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    
    # 保存到数据库
    conn = db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO questions 
        (knowledge_id, content, answer, image_url)
        VALUES (%s, %s, %s, %s)
    """, (data['knowledge_id'], data['content'], data['answer'], filename))
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(debug=True)
