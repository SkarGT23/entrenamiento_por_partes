from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellidos = db.Column(db.String(100), nullable=False)
    usuario = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Medidas corporales
    peso = db.Column(db.Float)
    altura = db.Column(db.Float)
    cintura = db.Column(db.Float)
    cadera = db.Column(db.Float)
    brazo = db.Column(db.Float)
    pierna = db.Column(db.Float)
    
    # Preferencias
    sistema_unidades = db.Column(db.String(10), default='metrico')
    idioma = db.Column(db.String(2), default='es')
    notificaciones_email = db.Column(db.Boolean, default=True)
    notificaciones_push = db.Column(db.Boolean, default=True)
    
    # Relaciones
    fotos = db.relationship('Foto', backref='usuario', lazy=True)
    objetivos = db.relationship('Objetivo', backref='usuario', lazy=True)
    seguimientos = db.relationship('Seguimiento', backref='usuario', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def verificar_password(self, password):
        return check_password_hash(self.password_hash, password)

class Foto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    ruta = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text)
    categoria = db.Column(db.String(50))

class Objetivo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    tipo = db.Column(db.String(50), nullable=False)
    objetivo = db.Column(db.String(200), nullable=False)
    fecha_limite = db.Column(db.DateTime, nullable=False)
    completado = db.Column(db.Boolean, default=False)
    tiempo_estimado = db.Column(db.String(100))
    nivel = db.Column(db.String(20))
    incremento_semanal = db.Column(db.Float)
    factor_dificultad = db.Column(db.Float)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    ultima_actualizacion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Seguimiento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    ejercicio = db.Column(db.String(100), nullable=False)
    peso = db.Column(db.Float)
    repeticiones = db.Column(db.Integer)
    peso_levantado = db.Column(db.Float)
    notas = db.Column(db.Text)

class Configuracion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    tema = db.Column(db.String(20), default='oscuro')
    zona_horaria = db.Column(db.String(50), default='UTC')
    formato_fecha = db.Column(db.String(20), default='DD/MM/YYYY')
    dias_entrenamiento = db.Column(db.String(100), default='lunes,miercoles,viernes')
    hora_entrenamiento = db.Column(db.String(5), default='09:00')
    duracion_entrenamiento = db.Column(db.Integer, default=60)
    nivel_entrenamiento = db.Column(db.String(20), default='intermedio')
    notificaciones_email = db.Column(db.String(100), default='recordatorio,progreso')
    notificaciones_push = db.Column(db.String(100), default='recordatorio')
    hora_notificaciones = db.Column(db.String(5), default='08:00')
    perfil_publico = db.Column(db.Boolean, default=False)
    mostrar_progreso = db.Column(db.String(100), default='peso,objetivos')
    mostrar_galeria = db.Column(db.String(100), default='antes_despues')

def init_db(app):
    db.init_app(app)
    with app.app_context():
        # Crear todas las tablas si no existen
        db.create_all()
        print("Base de datos inicializada correctamente")

def add_user(usuario, password, nombre, apellidos):
    try:
        # Verificar si el usuario ya existe
        if Usuario.query.filter_by(usuario=usuario).first():
            print(f"El usuario {usuario} ya existe")
            return False
            
        # Crear hash de la contraseña
        hashed_password = generate_password_hash(password)
        
        # Crear nuevo usuario
        nuevo_usuario = Usuario(
            usuario=usuario,
            password_hash=hashed_password,
            nombre=nombre,
            apellidos=apellidos
        )
        
        # Añadir a la base de datos
        db.session.add(nuevo_usuario)
        db.session.commit()
        print(f"Usuario {usuario} creado correctamente")
        return True
    except Exception as e:
        print(f"Error al añadir usuario: {e}")
        db.session.rollback()
        return False

def verify_user(usuario, password):
    try:
        # Buscar usuario
        user = Usuario.query.filter_by(usuario=usuario).first()
        
        # Verificar contraseña
        if user and user.verificar_password(password):
            print(f"Usuario {usuario} verificado correctamente")
            return user
        print(f"Usuario {usuario} no encontrado o contraseña incorrecta")
        return None
    except Exception as e:
        print(f"Error al verificar usuario: {e}")
        return None

def get_user_info(usuario):
    try:
        user = Usuario.query.filter_by(usuario=usuario).first()
        if user:
            print(f"Información del usuario {usuario} recuperada correctamente")
            return {
                'id': user.id,
                'usuario': user.usuario,
                'nombre': user.nombre,
                'apellidos': user.apellidos
            }
        return None
    except Exception as e:
        print(f"Error al obtener información del usuario: {e}")
        return None

def add_objetivo(usuario, tipo, objetivo, fecha_limite):
    try:
        nuevo_objetivo = Objetivo(
            tipo=tipo,
            objetivo=objetivo,
            fecha_limite=fecha_limite,
            usuario_id=usuario.id
        )
        db.session.add(nuevo_objetivo)
        db.session.commit()
        print(f"Objetivo para {tipo} creado correctamente")
        return nuevo_objetivo
    except Exception as e:
        print(f"Error al crear objetivo: {str(e)}")
        db.session.rollback()
        return None

def add_seguimiento(usuario, ejercicio, peso, repeticiones, fecha=None, notas=None):
    try:
        nuevo_seguimiento = Seguimiento(
            ejercicio=ejercicio,
            peso=peso,
            repeticiones=repeticiones,
            fecha=fecha or datetime.utcnow(),
            notas=notas,
            usuario_id=usuario.id
        )
        db.session.add(nuevo_seguimiento)
        db.session.commit()
        print(f"Seguimiento registrado correctamente")
        return nuevo_seguimiento
    except Exception as e:
        print(f"Error al registrar seguimiento: {str(e)}")
        db.session.rollback()
        return None

def get_seguimientos_usuario(usuario_id, ejercicio=None):
    query = Seguimiento.query.filter_by(usuario_id=usuario_id)
    if ejercicio:
        query = query.filter_by(ejercicio=ejercicio)
    return query.order_by(Seguimiento.fecha.desc()).all()

def get_objetivos_usuario(usuario_id):
    try:
        objetivos = Objetivo.query.filter_by(usuario_id=usuario_id).order_by(Objetivo.fecha_limite).all()
        print(f"Objetivos del usuario {usuario_id} recuperados correctamente")
        return objetivos
    except Exception as e:
        print(f"Error al obtener objetivos: {str(e)}")
        return []

def get_fotos_usuario(usuario_id, categoria=None):
    query = Foto.query.filter_by(usuario_id=usuario_id)
    if categoria:
        query = query.filter_by(categoria=categoria)
    return query.order_by(Foto.fecha.desc()).all()

def get_configuracion_usuario(usuario_id):
    try:
        config = Configuracion.query.filter_by(usuario_id=usuario_id).first()
        if not config:
            # Crear configuración por defecto si no existe
            config = Configuracion(usuario_id=usuario_id)
            db.session.add(config)
            db.session.commit()
        
        return {
            'tema': config.tema,
            'zona_horaria': config.zona_horaria,
            'formato_fecha': config.formato_fecha,
            'dias_entrenamiento': config.dias_entrenamiento.split(','),
            'hora_entrenamiento': config.hora_entrenamiento,
            'duracion_entrenamiento': config.duracion_entrenamiento,
            'nivel_entrenamiento': config.nivel_entrenamiento,
            'notificaciones_email': config.notificaciones_email.split(','),
            'notificaciones_push': config.notificaciones_push.split(','),
            'hora_notificaciones': config.hora_notificaciones,
            'perfil_publico': config.perfil_publico,
            'mostrar_progreso': config.mostrar_progreso.split(','),
            'mostrar_galeria': config.mostrar_galeria.split(',')
        }
    except Exception as e:
        print(f"Error al obtener configuración: {str(e)}")
        return None

def actualizar_configuracion_general(usuario_id, tema, zona_horaria, formato_fecha):
    try:
        config = Configuracion.query.filter_by(usuario_id=usuario_id).first()
        if not config:
            config = Configuracion(usuario_id=usuario_id)
            db.session.add(config)
        
        config.tema = tema
        config.zona_horaria = zona_horaria
        config.formato_fecha = formato_fecha
        
        db.session.commit()
        return True
    except Exception as e:
        print(f"Error al actualizar configuración general: {str(e)}")
        db.session.rollback()
        return False

def actualizar_configuracion_entrenamiento(usuario_id, dias_entrenamiento, hora_entrenamiento, 
                                         duracion_entrenamiento, nivel_entrenamiento):
    try:
        config = Configuracion.query.filter_by(usuario_id=usuario_id).first()
        if not config:
            config = Configuracion(usuario_id=usuario_id)
            db.session.add(config)
        
        config.dias_entrenamiento = ','.join(dias_entrenamiento)
        config.hora_entrenamiento = hora_entrenamiento
        config.duracion_entrenamiento = int(duracion_entrenamiento)
        config.nivel_entrenamiento = nivel_entrenamiento
        
        db.session.commit()
        return True
    except Exception as e:
        print(f"Error al actualizar configuración de entrenamiento: {str(e)}")
        db.session.rollback()
        return False

def actualizar_configuracion_notificaciones(usuario_id, notificaciones_email, notificaciones_push, 
                                          hora_notificaciones):
    try:
        config = Configuracion.query.filter_by(usuario_id=usuario_id).first()
        if not config:
            config = Configuracion(usuario_id=usuario_id)
            db.session.add(config)
        
        config.notificaciones_email = ','.join(notificaciones_email)
        config.notificaciones_push = ','.join(notificaciones_push)
        config.hora_notificaciones = hora_notificaciones
        
        db.session.commit()
        return True
    except Exception as e:
        print(f"Error al actualizar configuración de notificaciones: {str(e)}")
        db.session.rollback()
        return False

def actualizar_configuracion_privacidad(usuario_id, perfil_publico, mostrar_progreso, mostrar_galeria):
    try:
        config = Configuracion.query.filter_by(usuario_id=usuario_id).first()
        if not config:
            config = Configuracion(usuario_id=usuario_id)
            db.session.add(config)
        
        config.perfil_publico = perfil_publico
        config.mostrar_progreso = ','.join(mostrar_progreso)
        config.mostrar_galeria = ','.join(mostrar_galeria)
        
        db.session.commit()
        return True
    except Exception as e:
        print(f"Error al actualizar configuración de privacidad: {str(e)}")
        db.session.rollback()
        return False 