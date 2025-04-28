from app import app, db
from database import Usuario, Foto, Objetivo, Seguimiento, Configuracion

def init_database():
    with app.app_context():
        # Crear todas las tablas
        db.create_all()
        print("Base de datos inicializada correctamente")

if __name__ == '__main__':
    init_database() 