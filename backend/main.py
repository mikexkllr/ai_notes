from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import openai

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///notes.db'
db = SQLAlchemy(app)

# Database model for notes
class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text)
    chats = db.relationship('Chat', backref='note', lazy=True)

# Database model for chats
class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    note_id = db.Column(db.Integer, db.ForeignKey('note.id'), nullable=False)
    message = db.Column(db.Text)
    response = db.Column(db.Text)

# Flask routes for CRUD operations on notes
@app.route('/notes', methods=['GET'])
def get_notes():
    notes = Note.query.all()
    return jsonify([{'id': note.id, 'content': note.content} for note in notes])

@app.route('/notes', methods=['POST'])
def create_note():
    content = request.json.get('content')
    new_note = Note(content=content)
    db.session.add(new_note)
    db.session.commit()
    return jsonify({'message': 'Note created successfully', 'id': new_note.id}), 201

@app.route('/notes/<int:id>', methods=['GET'])
def get_note(id):
    note = Note.query.get_or_404(id)
    return jsonify({'id': note.id, 'content': note.content})

@app.route('/notes/<int:id>', methods=['PUT'])
def update_note(id):
    note = Note.query.get_or_404(id)
    content = request.json.get('content')
    note.content = content
    db.session.commit()
    return jsonify({'message': 'Note updated successfully'})

@app.route('/notes/<int:id>', methods=['DELETE'])
def delete_note(id):
    note = Note.query.get_or_404(id)
    db.session.delete(note)
    db.session.commit()
    return jsonify({'message': 'Note deleted successfully'})

# API endpoint for chat interactions with OpenAI GPT
@app.route('/notes/<int:id>/chat', methods=['POST'])
def chat_with_openai(id):
    note = Note.query.get_or_404(id)
    message = request.json.get('message')

    # Integrate OpenAI API here and get response
    # response = openai.Completion.create(model="text-davinci-003", prompt=message, ...)
    response = "Response from OpenAI GPT"

    new_chat = Chat(note_id=id, message=message, response=response)
    db.session.add(new_chat)
    db.session.commit()

    return jsonify({'message': 'Chat created successfully', 'id': new_chat.id, 'response': response})

if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)
