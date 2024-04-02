from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from urllib.parse import quote
from werkzeug.security import generate_password_hash, check_password_hash
import requests


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///notes.db'
app.config['JWT_SECRET_KEY'] = 'your-secret-key'  # Change this to your secret key
db = SQLAlchemy(app)
jwt = JWTManager(app)

# Database model for users
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Database model for notes
class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref='notes')

# Database model for chats
class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    note_id = db.Column(db.Integer, db.ForeignKey('note.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_user_request = db.Column(db.Boolean, nullable=False)

# Routes for user authentication
@app.route('/auth/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'message': 'Missing username or password'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'message': 'Username already exists'}), 400

    user = User(username=username)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return jsonify({'message': 'User registered successfully'}), 201

@app.route('/auth/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'message': 'Missing username or password'}), 400

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({'message': 'Invalid username or password'}), 401

    access_token = create_access_token(identity=user.id)
    return jsonify({'access_token': access_token}), 200

# Routes for CRUD operations on notes
@app.route('/notes', methods=['GET'])
@jwt_required()
def get_notes():
    current_user_id = get_jwt_identity()
    notes = Note.query.filter_by(user_id=current_user_id).all()
    return jsonify([{'id': note.id, 'content': note.content} for note in notes])

@app.route('/notes', methods=['POST'])
@jwt_required()
def create_note():
    current_user_id = get_jwt_identity()
    content = request.json.get('content')
    if not content:
        return jsonify({'message': 'Missing content'}), 400

    new_note = Note(content=content, user_id=current_user_id)
    db.session.add(new_note)
    db.session.commit()
    return jsonify({'message': 'Note created successfully', 'id': new_note.id}), 201

@app.route('/notes/<int:id>', methods=['GET'])
@jwt_required()
def get_note(id):
    current_user_id = get_jwt_identity()
    note = Note.query.filter_by(id=id, user_id=current_user_id).first()
    if not note:
        return jsonify({'message': 'Note not found'}), 404
    return jsonify({'id': note.id, 'content': note.content})

@app.route('/notes/<int:id>', methods=['PUT'])
@jwt_required()
def update_note(id):
    current_user_id = get_jwt_identity()
    note = Note.query.filter_by(id=id, user_id=current_user_id).first()
    if not note:
        return jsonify({'message': 'Note not found'}), 404

    content = request.json.get('content')
    if not content:
        return jsonify({'message': 'Missing content'}), 400

    note.content = content
    db.session.commit()
    return jsonify({'message': 'Note updated successfully'})

@app.route('/notes/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_note(id):
    current_user_id = get_jwt_identity()
    note = Note.query.filter_by(id=id, user_id=current_user_id).first()
    if not note:
        return jsonify({'message': 'Note not found'}), 404

    db.session.delete(note)
    db.session.commit()
    return jsonify({'message': 'Note deleted successfully'})


# Chat routes
@app.route('/notes/<int:id>/chats', methods=['GET'])
@jwt_required()
def get_chats(id):
    current_user_id = get_jwt_identity()
    note = Note.query.filter_by(id=id, user_id=current_user_id).first()
    if not note:
        return jsonify({'message': 'Note not found'}), 404

    chats = Chat.query.filter_by(note_id=id).all()
    return jsonify([{'id': chat.id, 'message': chat.message, 'is_user_request': chat.is_user_request} for chat in chats])

@app.route('/notes/<int:id>/chats', methods=['POST'])
@jwt_required()
def create_chat(id):
    current_user_id = get_jwt_identity()
    note = Note.query.filter_by(id=id, user_id=current_user_id).first()
    if not note:
        return jsonify({'message': 'Note not found'}), 404

    message = request.json.get('message')
    if not message:
        return jsonify({'message': 'Missing message'}), 400

    # Assume first message is always user request
    is_user_request = True

    # Call OpenAI API for response
    response = requests.post('http://localhost:5000/openai/chat', json={'message': message}).json()

    # Store user request
    new_chat = Chat(note_id=id, message=message, is_user_request=is_user_request)
    db.session.add(new_chat)

    # Store OpenAI response
    response_message = response.get('message')
    if response_message:
        is_user_request = False
        new_chat = Chat(note_id=id, message=response_message, is_user_request=is_user_request)
        db.session.add(new_chat)

    db.session.commit()
    return jsonify({'message': 'Chat created successfully'}), 201



if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
