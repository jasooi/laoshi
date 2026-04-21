from app import app
from extensions import db
from models import User

with app.app_context():
    for username in ['jazzy', 'Mobby']:
        user = User.query.filter_by(username=username).first()
        if user:
            db.session.delete(user)
            print(f'Deleted {username} (id={user.id})')
        else:
            print(f'{username} not found')
    db.session.commit()
