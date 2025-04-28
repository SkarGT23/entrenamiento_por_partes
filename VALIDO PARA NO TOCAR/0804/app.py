from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory, flash
import plotly.graph_objects as go
import plotly.io as pio
import os
import hashlib
import secrets
from database import db, Usuario, Foto, Objetivo, Seguimiento, Configuracion
from functools import wraps
from werkzeug.utils import secure_filename
from datetime import datetime
import time
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from bs4 import BeautifulSoup

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv('SECRET_KEY', 'mi_clave_secreta')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # Registrar Blueprints
    from app.routes import auth, ejercicios, objetivos, progreso, rutinas, configuracion, galeria
    app.register_blueprint(auth.bp)
    app.register_blueprint(ejercicios.bp)
    app.register_blueprint(objetivos.bp)
    app.register_blueprint(progreso.bp)
    app.register_blueprint(rutinas.bp)
    app.register_blueprint(configuracion.bp)
    app.register_blueprint(galeria.bp)

    return app

app = create_app()

# Diccionario simple para almacenar usuarios (en una aplicación real usarías una base de datos)
usuarios = {}

# Decorador para proteger rutas que requieren autenticación
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            flash('Por favor, inicia sesión para acceder a esta página.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Clase de ejercicio para gestionar los ejercicios de entrenamiento
class Exercise:
    _next_id = 1  # Variable de clase para generar IDs únicos
    
    def __init__(self, name, weight, increment, max_reps=12, exercise_type="compound", target_muscle=None, failure_type="controlled"):
        self.id = Exercise._next_id
        Exercise._next_id += 1
        self.name = name
        self.weight = weight
        self.increment = increment
        self.max_reps = max_reps
        self.exercise_type = exercise_type  # compound, isolation, bodyweight
        self.target_muscle = target_muscle
        self.failure_type = failure_type  # controlled, failure, technical_failure
        self.one_rm = self.calculate_one_rm()
        self.intensity = self.get_initial_intensity()
        self.volume = self.get_initial_volume()
        self.reps = self.get_initial_reps()
        self.rest_days = self.get_rest_days()
        self.warmup_sets = self.get_warmup_sets()
        self.rest_between_sets = self.get_rest_between_sets()

    def get_warmup_sets(self):
        if self.exercise_type == "compound":
            return [
                {"weight": self.one_rm * 0.4, "reps": 12},
                {"weight": self.one_rm * 0.5, "reps": 8},
                {"weight": self.one_rm * 0.6, "reps": 5}
            ]
        else:
            return [
                {"weight": self.one_rm * 0.5, "reps": 12},
                {"weight": self.one_rm * 0.6, "reps": 8}
            ]

    def get_rest_between_sets(self):
        if self.exercise_type == "compound":
            return 180  # 3 minutos para ejercicios compuestos
        elif self.exercise_type == "isolation":
            return 90   # 1.5 minutos para ejercicios de aislamiento
        else:
            return 60   # 1 minuto para ejercicios con peso corporal

    def calculate_one_rm(self):
        if self.exercise_type == "bodyweight":
            return self.weight
        return self.weight * (36 / (37 - self.max_reps))

    def get_initial_intensity(self):
        if self.exercise_type == "bodyweight":
            return 1.0
        elif self.exercise_type == "compound":
            return 0.6
        else:
            return 0.7

    def get_initial_volume(self):
        if self.exercise_type == "bodyweight":
            return 4
        elif self.exercise_type == "compound":
            return 3
        else:
            return 4

    def get_initial_reps(self):
        if self.exercise_type == "bodyweight":
            return 15
        elif self.exercise_type == "compound":
            return 8
        else:
            return 12

    def get_rest_days(self):
        if self.exercise_type == "compound":
            return 2
        else:
            return 1

    def adjust_intensity(self, week_number):
        if self.exercise_type == "bodyweight":
            if week_number % 4 == 0:  # Semana de descarga
                return self.intensity * 0.8
            elif week_number % 4 == 3:  # Semana de intensidad máxima
                return min(self.intensity * 1.2, 1.2)
        else:
            if week_number % 4 == 0:  # Semana de descarga
                return self.intensity * 0.8
            elif week_number % 4 == 3:  # Semana de intensidad máxima
                return min(self.intensity * 1.1, 0.9)
        return self.intensity

    def calculate_working_weight(self, week_number):
        intensity = self.adjust_intensity(week_number)
        if self.exercise_type == "bodyweight":
            return self.weight * intensity
        return self.one_rm * intensity

    def get_series_structure(self, week_number):
        working_weight = self.calculate_working_weight(week_number)
        series = []
        
        # Añadir series de calentamiento
        for warmup in self.warmup_sets:
            series.append({
                "weight": warmup["weight"],
                "reps": warmup["reps"],
                "type": "warmup",
                "rest": 60
            })
        
        # Añadir series de trabajo
        for i in range(self.volume):
            series.append({
                "weight": working_weight,
                "reps": self.reps,
                "type": "working",
                "rest": self.rest_between_sets,
                "failure": self.failure_type
            })
        
        return series

# Lista de ejercicios con sus características específicas
exercises = [
    # PIERNAS
    Exercise("Sentadillas", 50, 2.5, 12, "compound", "piernas", "controlled"),
    Exercise("Prensa de Piernas", 80, 2.5, 12, "compound", "piernas", "controlled"),
    Exercise("Extensiones de Cuádriceps", 30, 1.0, 15, "isolation", "piernas", "technical_failure"),
    Exercise("Curl de Isquiotibiales", 25, 1.0, 15, "isolation", "piernas", "technical_failure"),
    Exercise("Elevaciones de Gemelos", 40, 1.0, 20, "isolation", "piernas", "technical_failure"),
    Exercise("Peso Muerto Rumano", 40, 2.0, 12, "compound", "piernas", "controlled"),
    Exercise("Zancadas", 30, 1.0, 12, "compound", "piernas", "controlled"),
    Exercise("Sentadilla Búlgara", 20, 1.0, 12, "compound", "piernas", "controlled"),
    Exercise("Hip Thrust", 60, 2.5, 12, "compound", "piernas", "controlled"),
    Exercise("Peso Muerto Sumo", 50, 2.5, 10, "compound", "piernas", "controlled"),
    Exercise("Prensa de Gemelos", 50, 2.0, 15, "isolation", "piernas", "technical_failure"),
    Exercise("Aductores en Máquina", 35, 1.0, 15, "isolation", "piernas", "technical_failure"),
    Exercise("Abductores en Máquina", 35, 1.0, 15, "isolation", "piernas", "technical_failure"),
    
    # ESPALDA
    Exercise("Peso Muerto", 60, 2.5, 8, "compound", "espalda", "controlled"),
    Exercise("Remo con Barra", 30, 2.5, 10, "compound", "espalda", "controlled"),
    Exercise("Dominadas", 0, 1, 8, "bodyweight", "espalda", "controlled"),
    Exercise("Remo con Mancuerna", 20, 1.0, 12, "compound", "espalda", "controlled"),
    Exercise("Pull-down Lat", 40, 1.5, 12, "compound", "espalda", "controlled"),
    Exercise("Remo en Máquina", 35, 1.5, 12, "compound", "espalda", "controlled"),
    Exercise("Hiperextensiones", 0, 1.0, 15, "isolation", "espalda", "technical_failure"),
    Exercise("Remo Meadows", 25, 1.0, 12, "compound", "espalda", "controlled"),
    Exercise("Pull-down con Agarre Cerrado", 35, 1.5, 12, "compound", "espalda", "controlled"),
    Exercise("Dominadas con Agarre Neutro", 0, 1, 8, "bodyweight", "espalda", "controlled"),
    Exercise("Remo Pendlay", 40, 2.0, 8, "compound", "espalda", "controlled"),
    Exercise("Jalón al Pecho", 35, 1.5, 12, "compound", "espalda", "controlled"),
    Exercise("Remo a una Mano con Polea", 20, 1.0, 12, "compound", "espalda", "controlled"),
    Exercise("Face Pull Alto", 15, 1.0, 15, "isolation", "espalda", "technical_failure"),
    
    # PECHO
    Exercise("Press de Banca", 40, 2.5, 8, "compound", "pecho", "controlled"),
    Exercise("Flexiones", 0, 1, 15, "bodyweight", "pecho", "technical_failure"),
    Exercise("Press Inclinado", 35, 2.0, 10, "compound", "pecho", "controlled"),
    Exercise("Press Declinado", 35, 2.0, 10, "compound", "pecho", "controlled"),
    Exercise("Aperturas con Mancuernas", 12, 1.0, 15, "isolation", "pecho", "technical_failure"),
    Exercise("Crossover en Poleas", 15, 1.0, 15, "isolation", "pecho", "technical_failure"),
    Exercise("Press con Mancuernas", 16, 1.0, 12, "compound", "pecho", "controlled"),
    Exercise("Press Inclinado con Mancuernas", 14, 1.0, 12, "compound", "pecho", "controlled"),
    Exercise("Flexiones Declinadas", 0, 1, 12, "bodyweight", "pecho", "technical_failure"),
    Exercise("Aperturas Inclinadas", 10, 1.0, 15, "isolation", "pecho", "technical_failure"),
    Exercise("Press en Máquina Smith", 30, 2.0, 12, "compound", "pecho", "controlled"),
    Exercise("Fondos en Paralelas", 0, 1, 12, "bodyweight", "pecho", "controlled"),
    
    # HOMBROS
    Exercise("Press Militar con Barra", 20, 2.5, 8, "compound", "hombros", "controlled"),
    Exercise("Elevaciones Laterales", 8, 1.0, 15, "isolation", "hombros", "technical_failure"),
    Exercise("Press Arnold", 14, 1.0, 12, "compound", "hombros", "controlled"),
    Exercise("Elevaciones Frontales", 8, 1.0, 15, "isolation", "hombros", "technical_failure"),
    Exercise("Remo al Mentón", 25, 1.0, 12, "compound", "hombros", "controlled"),
    Exercise("Face Pull", 15, 1.0, 15, "isolation", "hombros", "technical_failure"),
    Exercise("Press Militar con Mancuernas", 16, 1.0, 12, "compound", "hombros", "controlled"),
    Exercise("Press Viking", 30, 1.5, 12, "compound", "hombros", "controlled"),
    Exercise("Elevaciones Laterales en Polea", 10, 0.5, 15, "isolation", "hombros", "technical_failure"),
    Exercise("Press en Máquina Smith", 25, 1.5, 12, "compound", "hombros", "controlled"),
    Exercise("Elevaciones Posteriores", 6, 0.5, 15, "isolation", "hombros", "technical_failure"),
    Exercise("Press Bradford", 20, 1.0, 12, "compound", "hombros", "controlled"),
    
    # BÍCEPS
    Exercise("Curl de Bíceps con Barra", 15, 1.0, 12, "isolation", "biceps", "technical_failure"),
    Exercise("Curl Martillo", 14, 1.0, 12, "isolation", "biceps", "technical_failure"),
    Exercise("Curl con Barra Z", 20, 1.0, 12, "isolation", "biceps", "technical_failure"),
    Exercise("Curl de Predicador", 15, 1.0, 12, "isolation", "biceps", "technical_failure"),
    Exercise("Curl Concentrado", 10, 0.5, 12, "isolation", "biceps", "technical_failure"),
    Exercise("Curl 21s", 12, 1.0, 21, "isolation", "biceps", "technical_failure"),
    Exercise("Curl Araña", 12, 1.0, 12, "isolation", "biceps", "technical_failure"),
    Exercise("Curl en Polea Baja", 15, 1.0, 15, "isolation", "biceps", "technical_failure"),
    Exercise("Curl Alternado con Mancuernas", 12, 1.0, 12, "isolation", "biceps", "technical_failure"),
    Exercise("Curl en Banco Inclinado", 10, 1.0, 12, "isolation", "biceps", "technical_failure"),
    
    # TRÍCEPS
    Exercise("Extensiones de Tríceps con Barra", 20, 1.0, 12, "isolation", "triceps", "technical_failure"),
    Exercise("Extensiones en Polea Alta", 25, 1.0, 15, "isolation", "triceps", "technical_failure"),
    Exercise("Press Francés", 18, 1.0, 12, "isolation", "triceps", "technical_failure"),
    Exercise("Extensiones con Mancuerna", 8, 0.5, 15, "isolation", "triceps", "technical_failure"),
    Exercise("Press Cerrado", 30, 2.0, 12, "compound", "triceps", "controlled"),
    Exercise("Extensiones en Polea con Cuerda", 20, 1.0, 15, "isolation", "triceps", "technical_failure"),
    Exercise("Extensiones Tumbado", 12, 1.0, 12, "isolation", "triceps", "technical_failure"),
    Exercise("Patada de Tríceps", 8, 0.5, 15, "isolation", "triceps", "technical_failure"),
    Exercise("Press de Banca Agarre Cerrado", 35, 2.0, 12, "compound", "triceps", "controlled"),
    Exercise("Extensiones en Máquina", 25, 1.0, 15, "isolation", "triceps", "technical_failure"),
    
    # ABDOMINALES/CORE
    Exercise("Crunches", 0, 1, 20, "isolation", "abdominales", "failure"),
    Exercise("Planchas", 0, 5, 60, "bodyweight", "core", "controlled"),
    Exercise("Russian Twist", 10, 1.0, 20, "isolation", "abdominales", "technical_failure"),
    Exercise("Mountain Climbers", 0, 1, 30, "bodyweight", "core", "technical_failure"),
    Exercise("Leg Raises", 0, 1, 15, "bodyweight", "abdominales", "technical_failure"),
    Exercise("Plank to Downward Dog", 0, 1, 10, "bodyweight", "core", "controlled"),
    Exercise("Side Plank", 0, 5, 30, "bodyweight", "core", "controlled"),
    Exercise("Bicycle Crunches", 0, 1, 20, "isolation", "abdominales", "technical_failure"),
    Exercise("Hollow Body Hold", 0, 5, 30, "bodyweight", "core", "controlled"),
    Exercise("Dead Bug", 0, 1, 20, "bodyweight", "core", "controlled")
]

# Función para calcular el progreso y devolver un calendario de entrenamiento
def calcular_progreso(peso_maximo, incremento, dias_entrenamiento, meses, exercise_type="compound"):
    progreso = []
    peso_actual = peso_maximo * 0.6
    total_dias = meses * 28
    dia_contador = 1
    semana_actual = 1
    fatiga_acumulada = 0
    peso_anterior = peso_actual

    # Mensaje de advertencia inicial
    print("\n=== IMPORTANTE: INSTRUCCIONES DE PROGRESIÓN ===")
    print("Si no puedes completar las series con el peso programado:")
    print("1. Reduce el peso a los valores de 2 semanas atrás")
    print("2. Mantén ese peso hasta que puedas completar todas las series")
    print("3. Solo entonces intenta progresar nuevamente")
    print("==============================================\n")

    for i in range(total_dias):
        mes = (i // 28) + 1
        semana = (i // 7) + 1
        dia_semana = i % 7 + 1
        
        dia_descanso = "Descanso" if dia_semana > dias_entrenamiento else None
        peso_trabajo = peso_actual
        
        if not dia_descanso:
            # Ajustar el peso según el tipo de ejercicio y la semana
            if exercise_type == "bodyweight":
                if semana % 4 == 0:  # Semana de descarga
                    peso_trabajo *= 0.8
                    fatiga_acumulada = 0
                elif semana % 4 == 3:  # Semana de intensidad máxima
                    peso_trabajo *= 1.2
            else:
                if semana % 4 == 0:  # Semana de descarga
                    peso_trabajo *= 0.8
                    fatiga_acumulada = 0
                elif semana % 4 == 3:  # Semana de intensidad máxima
                    peso_trabajo *= 1.1
                
                # Ajustar peso según fatiga acumulada
                if fatiga_acumulada > 0.8:  # Alta fatiga
                    peso_trabajo *= 0.9
                    fatiga_acumulada = 0
            
            # Aumentar el peso base según el tipo de ejercicio
            if semana_actual % 4 == 0:
                peso_anterior = peso_actual  # Guardar el peso anterior
                if exercise_type == "compound":
                    peso_actual += incremento
                elif exercise_type == "isolation":
                    peso_actual += incremento * 0.8
            
            # Aumentar fatiga acumulada
            fatiga_acumulada += 0.2
            
            progreso.append((mes, semana, dia_semana, 
                           f"Entreno: {peso_trabajo:.1f} kg", 
                           peso_trabajo))
        else:
            # Reducir fatiga en días de descanso
            fatiga_acumulada = max(0, fatiga_acumulada - 0.3)
            progreso.append((mes, semana, dia_semana, "Descanso", peso_actual))

        dia_contador += 1
        if dia_contador > dias_entrenamiento:
            dia_contador = 1
            semana_actual += 1

    return progreso

# Ruta para la página principal
@app.route('/')
def index():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

# Ruta para la página de registro
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        try:
            usuario = request.form['usuario']
            password = request.form['password']
            nombre = request.form['nombre']
            apellidos = request.form['apellidos']
            
            # Verificar si el usuario ya existe
            if Usuario.query.filter_by(usuario=usuario).first():
                flash('El usuario ya existe', 'error')
                return redirect(url_for('registro'))
            
            # Crear nuevo usuario
            nuevo_usuario = Usuario(
                usuario=usuario,
                nombre=nombre,
                apellidos=apellidos
            )
            nuevo_usuario.set_password(password)
            
            db.session.add(nuevo_usuario)
            db.session.commit()
            
            # Iniciar sesión automáticamente después del registro
            session['usuario'] = usuario
            flash('Usuario registrado correctamente', 'success')
            return redirect(url_for('index'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al registrar el usuario: {str(e)}', 'error')
            return redirect(url_for('registro'))
    
    return render_template('registro.html')

# Ruta para iniciar sesión
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            usuario = request.form['usuario']
            password = request.form['password']
            
            user = Usuario.query.filter_by(usuario=usuario).first()
            
            if user and user.verificar_password(password):
                session['usuario'] = usuario
                flash('Has iniciado sesión correctamente', 'success')
                return redirect(url_for('index'))
            else:
                flash('Usuario o contraseña incorrectos', 'error')
                return redirect(url_for('login'))
                
        except Exception as e:
            flash(f'Error al iniciar sesión: {str(e)}', 'error')
            return redirect(url_for('login'))
    
    return render_template('login.html')

# Ruta para cerrar sesión
@app.route('/logout')
def logout():
    session.pop('usuario', None)
    flash('Has cerrado sesión correctamente', 'success')
    return redirect(url_for('registro'))

# Ruta para acceder sin registro
@app.route('/acceder-sin-registro')
def acceder_sin_registro():
    session['usuario'] = 'Invitado'
    flash('Has accedido como invitado', 'info')
    return redirect(url_for('index'))

# Ruta para mostrar el progreso con gráficos de Plotly
@app.route('/progreso')
@login_required
def progreso():
    """Página de progreso general"""
    return render_template('progreso.html', usuario=session['usuario'], exercises=exercises)

@app.route('/progreso/ejercicio/<int:exercise_id>')
@login_required
def progreso_ejercicio(exercise_id):
    """Página de progreso específico de un ejercicio"""
    exercise = exercises[exercise_id]
    
    # Mostrar mensaje en la consola
    print("\n=== IMPORTANTE: INSTRUCCIONES DE PROGRESIÓN ===")
    print("Si no puedes completar las series con el peso programado:")
    print("1. Reduce el peso a los valores de 2 semanas atrás")
    print("2. Mantén ese peso hasta que puedas completar todas las series")
    print("3. Solo entonces intenta progresar nuevamente")
    print("==============================================\n")
    
    progreso_data = calcular_progreso(exercise.weight, exercise.increment, 3, 6, exercise.exercise_type)
    meses_data = [f"Mes {p[0]}" for p in progreso_data]
    semanas_data = [f"Semana {p[1]}" for p in progreso_data]
    dias_data = [f"Día {p[2]}" for p in progreso_data]
    status_data = [p[3] for p in progreso_data]
    pesos = [p[4] for p in progreso_data]

    # Crear gráfico con Plotly
    fig = go.Figure(data=[go.Scatter(x=meses_data, y=pesos, mode='lines+markers')])
    fig.update_layout(title=f'Progreso de {exercise.name}', xaxis_title='Meses', yaxis_title='Peso (kg)')
    graph_html = pio.to_html(fig, full_html=False)

    # Mensaje de advertencia
    mensaje_advertencia = {
        'titulo': 'IMPORTANTE: INSTRUCCIONES DE PROGRESIÓN',
        'instrucciones': [
            'Si no puedes completar las series con el peso programado:',
            '1. Reduce el peso a los valores de 2 semanas atrás',
            '2. Mantén ese peso hasta que puedas completar todas las series',
            '3. Solo entonces intenta progresar nuevamente'
        ]
    }

    return render_template('progreso_ejercicio.html', 
                         graph=graph_html, 
                         exercise=exercise,
                         mensaje_advertencia=mensaje_advertencia,
                         progreso_data=zip(meses_data, semanas_data, dias_data, status_data, pesos))

# Ruta para obtener el plan de entrenamiento con estimación de tiempo
@app.route('/plan_entrenamiento', methods=['POST'])
def plan_entrenamiento():
    peso_deseado = float(request.form.get('peso_deseado'))
    repeticion_maxima = float(request.form.get('repeticion_maxima'))
    dias_entrenamiento = int(request.form.get('dias_entrenamiento'))
    meses = int(request.form.get('meses'))
    ejercicio = request.form.get('ejercicio')

    selected_exercise = None
    for ex in exercises:
        if ex.name == ejercicio:
            selected_exercise = ex
            break

    progreso_data = calcular_progreso(selected_exercise.weight, selected_exercise.increment, dias_entrenamiento, meses, selected_exercise.exercise_type)

    plan = []
    for mes in range(1, meses + 1):
        for semana in range(1, 5):
            for dia in range(1, dias_entrenamiento + 1):
                if progreso_data:
                    progreso = progreso_data.pop(0)
                    if progreso[2] != "Descanso":
                        plan.append({
                            'mes': mes,
                            'semana': f'Semana {semana}',
                            'dia': f'Día {dia}',
                            'ejercicio': ejercicio,
                            'peso': progreso[4]
                        })

    # Estimación de tiempo para alcanzar el peso deseado
    peso_actual = selected_exercise.weight * 0.5
    tiempo_estimado_dias = 0
    while peso_actual < peso_deseado:
        peso_actual += selected_exercise.increment
        tiempo_estimado_dias += 1

    # Calcular meses y días restantes
    dias_entrenamiento_por_mes = dias_entrenamiento * 4
    dias_restantes = tiempo_estimado_dias % dias_entrenamiento_por_mes
    meses_estimados = tiempo_estimado_dias // dias_entrenamiento_por_mes
    dias_restantes_en_meses = dias_restantes / 30.4

    meses_estimados += round(dias_restantes_en_meses)

    mensaje_estimacion = f"Se estima que alcanzarás {peso_deseado} kg en aproximadamente "
    if meses_estimados > 0:
        mensaje_estimacion += f"{meses_estimados} mes(es) "
    if dias_restantes > 0:
        mensaje_estimacion += f"{dias_restantes} día(s)."

    return jsonify({'plan': plan, 'mensaje_estimacion': mensaje_estimacion})

# Ruta para la configuración
@app.route('/configuracion')
def configuracion():
    try:
        usuario = session.get('usuario')
        if not usuario:
            return redirect(url_for('registro'))
            
        configuracion = usuarios.get(usuario, {})
        return render_template('configuracion.html', configuracion=configuracion)
    except Exception as e:
        flash(f'Error al cargar la configuración: {str(e)}', 'error')
        return redirect(url_for('pagina_principal'))

@app.route('/actualizar_configuracion_general', methods=['POST'])
def actualizar_configuracion_general():
    try:
        usuario = session.get('usuario')
        if not usuario:
            return jsonify({'success': False, 'message': 'Usuario no encontrado'})
            
        tema = request.form.get('tema')
        zona_horaria = request.form.get('zona_horaria')
        formato_fecha = request.form.get('formato_fecha')
        
        if usuario in usuarios:
            usuarios[usuario].update({
                'tema': tema,
                'zona_horaria': zona_horaria,
                'formato_fecha': formato_fecha
            })
            return jsonify({'success': True})
        return jsonify({'success': False, 'message': 'Usuario no encontrado'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/actualizar_configuracion_entrenamiento', methods=['POST'])
def actualizar_configuracion_entrenamiento():
    try:
        usuario = session.get('usuario')
        if not usuario:
            return jsonify({'success': False, 'message': 'Usuario no encontrado'})
            
        dias_entrenamiento = request.form.get('dias_entrenamiento')
        hora_entrenamiento = request.form.get('hora_entrenamiento')
        duracion_entrenamiento = request.form.get('duracion_entrenamiento')
        nivel_entrenamiento = request.form.get('nivel_entrenamiento')
        
        if usuario in usuarios:
            usuarios[usuario].update({
                'dias_entrenamiento': dias_entrenamiento,
                'hora_entrenamiento': hora_entrenamiento,
                'duracion_entrenamiento': duracion_entrenamiento,
                'nivel_entrenamiento': nivel_entrenamiento
            })
            return jsonify({'success': True})
        return jsonify({'success': False, 'message': 'Usuario no encontrado'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/actualizar_configuracion_notificaciones', methods=['POST'])
def actualizar_configuracion_notificaciones():
    try:
        usuario = session.get('usuario')
        if not usuario:
            return jsonify({'success': False, 'message': 'Usuario no encontrado'})
            
        notificaciones_email = request.form.get('notificaciones_email') == 'true'
        notificaciones_push = request.form.get('notificaciones_push') == 'true'
        hora_notificaciones = request.form.get('hora_notificaciones')
        
        if usuario in usuarios:
            usuarios[usuario].update({
                'notificaciones_email': notificaciones_email,
                'notificaciones_push': notificaciones_push,
                'hora_notificaciones': hora_notificaciones
            })
            return jsonify({'success': True})
        return jsonify({'success': False, 'message': 'Usuario no encontrado'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/actualizar_configuracion_privacidad', methods=['POST'])
def actualizar_configuracion_privacidad():
    try:
        usuario = session.get('usuario')
        if not usuario:
            return jsonify({'success': False, 'message': 'Usuario no encontrado'})
            
        perfil_publico = request.form.get('perfil_publico') == 'true'
        mostrar_progreso = request.form.get('mostrar_progreso') == 'true'
        mostrar_galeria = request.form.get('mostrar_galeria') == 'true'
        
        if usuario in usuarios:
            usuarios[usuario].update({
                'perfil_publico': perfil_publico,
                'mostrar_progreso': mostrar_progreso,
                'mostrar_galeria': mostrar_galeria
            })
            return jsonify({'success': True})
        return jsonify({'success': False, 'message': 'Usuario no encontrado'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# Ruta para servir archivos estáticos
@app.route('/runitas/<path:filename>')
def serve_runitas(filename):
    return send_from_directory(os.path.join(app.root_path, 'static', 'runitas'), filename)

# Ruta para el temporizador Tabata
@app.route('/tabata')
@login_required
def tabata():
    """Página del temporizador Tabata"""
    return render_template('tabata.html', usuario=session['usuario'])

# Ruta para la galería
@app.route('/galeria')
@login_required
def galeria():
    try:
        usuario = Usuario.query.filter_by(usuario=session['usuario']).first()
        fotos = get_fotos_usuario(usuario.id)
        categorias = db.session.query(Foto.categoria).distinct().all()
        categorias = [c[0] for c in categorias if c[0]]
        
        return render_template('galeria.html',
                             fotos=fotos,
                             categorias=categorias)
                             
    except Exception as e:
        flash(f'Error al cargar la galería: {str(e)}', 'error')
        return redirect(url_for('index'))

# Función para verificar formato de archivo permitido
def formato_permitido(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

# Ruta para subir fotos
@app.route('/subir_foto', methods=['POST'])
@login_required
def subir_foto():
    if 'foto' not in request.files:
        return jsonify({'success': False, 'error': 'No se ha seleccionado ningún archivo'})
    
    file = request.files['foto']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No se ha seleccionado ningún archivo'})
    
    if file and formato_permitido(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Guardar en la base de datos
        try:
            foto = Foto(
                usuario=session['usuario'],
                ruta=filename,
                fecha=datetime.now()
            )
            db.session.add(foto)
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    return jsonify({'success': False, 'error': 'Formato de archivo no permitido'})

# Ruta para eliminar fotos
@app.route('/eliminar_foto/<int:foto_id>', methods=['POST'])
@login_required
def eliminar_foto(foto_id):
    try:
        foto = Foto.query.get_or_404(foto_id)
        if foto.usuario == session['usuario']:
            # Eliminar archivo físico
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], foto.ruta)
            if os.path.exists(filepath):
                os.remove(filepath)
            
            # Eliminar de la base de datos
            db.session.delete(foto)
            db.session.commit()
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'No autorizado'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Ruta para objetivos
@app.route('/objetivos')
@login_required
def objetivos():
    try:
        usuario = Usuario.query.filter_by(usuario=session['usuario']).first()
        objetivos = get_objetivos_usuario(usuario.id)
        
        # Obtener seguimientos recientes para cada objetivo
        for objetivo in objetivos:
            seguimientos = get_seguimientos_usuario(usuario.id, objetivo.tipo)
            if seguimientos:
                objetivo.ultimo_seguimiento = seguimientos[0]
        
        # Obtener ejercicios de fuerza
        ejercicios_fuerza = [e for e in exercises if e.exercise_type == "compound"]
        
        return render_template('objetivos.html',
                             objetivos=objetivos,
                             exercises=exercises,
                             ejercicios_fuerza=ejercicios_fuerza)
                             
    except Exception as e:
        flash(f'Error al cargar los objetivos: {str(e)}', 'error')
        return redirect(url_for('index'))

# Ruta para añadir objetivos
@app.route('/añadir_objetivo', methods=['POST'])
@login_required
def añadir_objetivo():
    try:
        data = request.get_json()
        
        # Verificar si es un objetivo de fuerza
        if data.get('tipo') == 'fuerza':
            # Calcular el peso objetivo basado en el 1RM
            ejercicio = next((e for e in exercises if e.name == data['ejercicio']), None)
            if ejercicio:
                # Determinar nivel basado en el peso actual vs peso objetivo
                peso_actual = float(data.get('peso_actual', ejercicio.weight))
                peso_objetivo = float(data.get('peso_objetivo', ejercicio.weight * 1.1))
                diferencia_peso = peso_objetivo - peso_actual
                
                if diferencia_peso > 50:
                    nivel = "avanzado"
                elif diferencia_peso > 25:
                    nivel = "intermedio"
                else:
                    nivel = "principiante"
                
                # Calcular tiempo estimado
                factores_progresion = {
                    "Press de Banca": {
                        "principiante": {"incremento": 2.5, "frecuencia": 3, "factor_dificultad": 1.0},
                        "intermedio": {"incremento": 1.25, "frecuencia": 3, "factor_dificultad": 1.5},
                        "avanzado": {"incremento": 0.625, "frecuencia": 3, "factor_dificultad": 2.0}
                    },
                    "Remo con Barra": {
                        "principiante": {"incremento": 2.5, "frecuencia": 3, "factor_dificultad": 1.0},
                        "intermedio": {"incremento": 1.25, "frecuencia": 3, "factor_dificultad": 1.5},
                        "avanzado": {"incremento": 0.625, "frecuencia": 3, "factor_dificultad": 2.0}
                    },
                    "Peso Muerto": {
                        "principiante": {"incremento": 5.0, "frecuencia": 2, "factor_dificultad": 1.2},
                        "intermedio": {"incremento": 2.5, "frecuencia": 2, "factor_dificultad": 1.8},
                        "avanzado": {"incremento": 1.25, "frecuencia": 2, "factor_dificultad": 2.5}
                    },
                    "Sentadillas": {
                        "principiante": {"incremento": 5.0, "frecuencia": 2, "factor_dificultad": 1.2},
                        "intermedio": {"incremento": 2.5, "frecuencia": 2, "factor_dificultad": 1.8},
                        "avanzado": {"incremento": 1.25, "frecuencia": 2, "factor_dificultad": 2.5}
                    },
                    "Press Militar con Barra": {
                        "principiante": {"incremento": 2.5, "frecuencia": 3, "factor_dificultad": 1.3},
                        "intermedio": {"incremento": 1.25, "frecuencia": 3, "factor_dificultad": 1.8},
                        "avanzado": {"incremento": 0.625, "frecuencia": 3, "factor_dificultad": 2.2}
                    }
                }
                
                factores = factores_progresion.get(ejercicio.name, {
                    "principiante": {"incremento": 1.25, "frecuencia": 3, "factor_dificultad": 1.0},
                    "intermedio": {"incremento": 0.625, "frecuencia": 3, "factor_dificultad": 1.5},
                    "avanzado": {"incremento": 0.3125, "frecuencia": 3, "factor_dificultad": 2.0}
                })[nivel]
                
                # Calcular tiempo estimado
                incremento_semanal = factores["incremento"] * (factores["frecuencia"] / 3)
                factor_dificultad = factores["factor_dificultad"]
                factor_diferencia = 1 + (diferencia_peso / 100)
                
                semanas_base = diferencia_peso / incremento_semanal
                semanas_ajustadas = semanas_base * factor_dificultad * factor_diferencia
                semanas_extra = int(semanas_ajustadas / 4)
                semanas_totales = semanas_ajustadas + semanas_extra
                
                meses_estimados = int(semanas_totales / 4)
                semanas_restantes = semanas_totales % 4
                dias_adicionales = int(semanas_restantes * 7)
                
                # Crear el objetivo con la información detallada
                data['objetivo'] = f"Alcanzar {peso_objetivo:.1f} kg en {ejercicio.name} (Nivel: {nivel})"
                data['tiempo_estimado'] = f"{meses_estimados} meses{f' y {dias_adicionales} días' if dias_adicionales > 0 else ''}"
                data['nivel'] = nivel
                data['incremento_semanal'] = incremento_semanal
                data['factor_dificultad'] = factor_dificultad
        
        objetivo = add_objetivo(
            usuario=session['usuario'],
            tipo=data['tipo'],
            objetivo=data['objetivo'],
            fecha_limite=datetime.strptime(data['fecha_limite'], '%Y-%m-%d'),
            tiempo_estimado=data.get('tiempo_estimado'),
            nivel=data.get('nivel'),
            incremento_semanal=data.get('incremento_semanal'),
            factor_dificultad=data.get('factor_dificultad')
        )
        return jsonify({'success': True, 'objetivo': objetivo})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Ruta para registrar entrenamiento
@app.route('/registrar_entrenamiento', methods=['POST'])
@login_required
def registrar_entrenamiento():
    try:
        data = request.get_json()
        usuario = Usuario.query.filter_by(usuario=session['usuario']).first()
        
        seguimiento = add_seguimiento(
            usuario=usuario,
            ejercicio=data['ejercicio'],
            peso=float(data['peso']),
            repeticiones=int(data['repeticiones']),
            notas=data.get('notas')
        )
        
        if seguimiento:
            return jsonify({
                'success': True,
                'message': 'Entrenamiento registrado correctamente',
                'seguimiento': {
                    'id': seguimiento.id,
                    'fecha': seguimiento.fecha.strftime('%Y-%m-%d %H:%M'),
                    'peso': seguimiento.peso,
                    'repeticiones': seguimiento.repeticiones
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Error al registrar el entrenamiento'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        })

# Ruta para actualizar objetivo
@app.route('/actualizar_objetivo', methods=['POST'])
@login_required
def actualizar_objetivo():
    try:
        data = request.get_json()
        objetivo = Objetivo.query.get_or_404(data['id'])
        if objetivo.usuario == session['usuario']:
            objetivo.progreso = data['progreso']
            db.session.commit()
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'No autorizado'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Ruta para actualizar peso de ejercicio
@app.route('/actualizar_peso_ejercicio', methods=['POST'])
@login_required
def actualizar_peso_ejercicio():
    try:
        data = request.get_json()
        seguimiento = add_seguimiento(
            usuario=session['usuario'],
            ejercicio=data['ejercicio'],
            peso=data['peso'],
            repeticiones=data['repeticiones'],
            fecha=datetime.now()
        )
        return jsonify({'success': True, 'seguimiento': seguimiento})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/calcular_biometrico', methods=['POST'])
def calcular_biometrico():
    try:
        altura = float(request.form.get('altura')) / 100  # Convertir a metros
        peso = float(request.form.get('peso'))
        edad = int(request.form.get('edad'))
        sexo = request.form.get('sexo')
        actividad = request.form.get('actividad')

        # Calcular IMC
        imc = peso / (altura * altura)
        categoria_imc = ""
        if imc < 18.5:
            categoria_imc = "Bajo peso"
        elif imc < 25:
            categoria_imc = "Peso normal"
        elif imc < 30:
            categoria_imc = "Sobrepeso"
        else:
            categoria_imc = "Obesidad"

        # Calcular grasa corporal (fórmula aproximada)
        if sexo == "masculino":
            grasa_corporal = (1.2 * imc) + (0.23 * edad) - 3.8
        else:
            grasa_corporal = (1.2 * imc) + (0.23 * edad) - 5.4

        # Calcular masa muscular (aproximado)
        masa_muscular = peso * (1 - grasa_corporal/100)

        # Calcular calorías diarias (aproximado)
        tmb = 10 * peso + 6.25 * (altura * 100) - 5 * edad
        if sexo == "masculino":
            tmb += 5
        else:
            tmb -= 161

        factor_actividad = {
            "sedentario": 1.2,
            "ligero": 1.375,
            "moderado": 1.55,
            "activo": 1.725,
            "muy_activo": 1.9
        }

        calorias_diarias = tmb * factor_actividad[actividad]

        # Crear gráfico de composición corporal
        fig = go.Figure(data=[
            go.Pie(
                labels=['Masa Muscular', 'Grasa Corporal', 'Otros'],
                values=[masa_muscular, peso * (grasa_corporal/100), peso - masa_muscular - peso * (grasa_corporal/100)],
                hole=0.4,
                marker=dict(colors=['#00ff00', '#ff0000', '#808080'])
            )
        ])

        fig.update_layout(
            title=dict(
                text='Composición Corporal',
                font=dict(size=24, color='#ffffff')
            ),
            template='plotly_dark',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0.1)',
            font=dict(color='#ffffff'),
            showlegend=True,
            legend=dict(
                bgcolor='rgba(0,0,0,0.3)',
                bordercolor='#ff4d00'
            )
        )

        graph_html = pio.to_html(fig, full_html=False)

        return jsonify({
            'imc': round(imc, 2),
            'categoria_imc': categoria_imc,
            'grasa_corporal': round(grasa_corporal, 2),
            'categoria_grasa': 'Normal' if (grasa_corporal < 25 and sexo == 'masculino') or (grasa_corporal < 32 and sexo == 'femenino') else 'Alta',
            'masa_muscular': round(masa_muscular, 2),
            'calorias_diarias': round(calorias_diarias),
            'graph': graph_html
        })

    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 400

@app.route('/perfil')
@login_required
def perfil():
    try:
        usuario = Usuario.query.filter_by(usuario=session['usuario']).first()
        if not usuario:
            flash('Error al cargar el perfil', 'error')
            return redirect(url_for('index'))
            
        return render_template('perfil.html', usuario=usuario)
    except Exception as e:
        flash('Error al cargar el perfil', 'error')
        return redirect(url_for('index'))

@app.route('/actualizar_perfil', methods=['POST'])
@login_required
def actualizar_perfil():
    try:
        usuario = Usuario.query.filter_by(usuario=session['usuario']).first()
        if not usuario:
            return jsonify({'success': False, 'message': 'Usuario no encontrado'})

        usuario.nombre = request.form.get('nombre')
        usuario.apellidos = request.form.get('apellidos')
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Perfil actualizado correctamente'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/actualizar_password', methods=['POST'])
@login_required
def actualizar_password():
    try:
        usuario = Usuario.query.filter_by(usuario=session['usuario']).first()
        if not usuario:
            return jsonify({'success': False, 'message': 'Usuario no encontrado'})

        password_actual = request.form.get('password_actual')
        nuevo_password = request.form.get('nuevo_password')
        confirmar_password = request.form.get('confirmar_password')

        if not usuario.verificar_password(password_actual):
            return jsonify({'success': False, 'message': 'Contraseña actual incorrecta'})

        if nuevo_password != confirmar_password:
            return jsonify({'success': False, 'message': 'Las contraseñas no coinciden'})

        usuario.set_password(nuevo_password)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Contraseña actualizada correctamente'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/actualizar_medidas', methods=['POST'])
@login_required
def actualizar_medidas():
    try:
        usuario = Usuario.query.filter_by(usuario=session['usuario']).first()
        if not usuario:
            return jsonify({'success': False, 'message': 'Usuario no encontrado'})

        usuario.peso = float(request.form.get('peso'))
        usuario.altura = float(request.form.get('altura'))
        usuario.cintura = float(request.form.get('cintura')) if request.form.get('cintura') else None
        usuario.cadera = float(request.form.get('cadera')) if request.form.get('cadera') else None
        usuario.brazo = float(request.form.get('brazo')) if request.form.get('brazo') else None
        usuario.pierna = float(request.form.get('pierna')) if request.form.get('pierna') else None
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Medidas actualizadas correctamente'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/actualizar_preferencias', methods=['POST'])
@login_required
def actualizar_preferencias():
    try:
        usuario = Usuario.query.filter_by(usuario=session['usuario']).first()
        if not usuario:
            return jsonify({'success': False, 'message': 'Usuario no encontrado'})

        usuario.sistema_unidades = request.form.get('sistema_unidades')
        usuario.idioma = request.form.get('idioma')
        usuario.notificaciones_email = bool(request.form.get('notificaciones_email'))
        usuario.notificaciones_push = bool(request.form.get('notificaciones_push'))
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Preferencias actualizadas correctamente'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/rutinas')
def rutinas():
    """Página de rutinas complementarias"""
    if 'usuario' not in session:
        return redirect(url_for('registro'))
    
    rutinas = [
        {
            'id': 'arnold',
            'nombre': 'Rutina Arnold',
            'descripcion': 'Rutina clásica de Arnold Schwarzenegger para hipertrofia',
            'icono': 'fas fa-dumbbell',
            'tipo': 'hipertrofia'
        },
        {
            'id': 'weider',
            'nombre': 'Rutina Weider',
            'descripcion': 'Sistema de entrenamiento para principiantes',
            'icono': 'fas fa-dumbbell',
            'tipo': 'principiante'
        },
        {
            'id': 'hiit',
            'nombre': 'Rutina HIIT',
            'descripcion': 'Entrenamiento de alta intensidad para quemar grasa',
            'icono': 'fas fa-running',
            'tipo': 'cardio'
        },
        {
            'id': 'fuerza',
            'nombre': 'Rutina de Fuerza',
            'descripcion': 'Programa enfocado en el desarrollo de fuerza máxima',
            'icono': 'fas fa-weight-hanging',
            'tipo': 'fuerza'
        },
        {
            'id': 'full-body',
            'nombre': 'Rutina Full Body',
            'descripcion': 'Entrenamiento completo que trabaja todo el cuerpo en cada sesión',
            'icono': 'fas fa-user',
            'tipo': 'full-body'
        },
        {
            'id': 'push-pull',
            'nombre': 'Rutina Push-Pull',
            'descripcion': 'Sistema de entrenamiento que divide los ejercicios en empuje y tracción',
            'icono': 'fas fa-exchange-alt',
            'tipo': 'push-pull'
        },
        {
            'id': 'hipertrofia',
            'nombre': 'Rutina de Hipertrofia',
            'descripcion': 'Programa específico para el desarrollo muscular',
            'icono': 'fas fa-dumbbell',
            'tipo': 'hipertrofia'
        }
    ]
    
    return render_template('rutinas.html', rutinas=rutinas)

@app.route('/rutina/<tipo>')
def rutina_especifica(tipo):
    """Página de rutina específica"""
    if 'usuario' not in session:
        return redirect(url_for('registro'))
    
    # Obtener la ruta del archivo de la rutina
    rutina_path = os.path.join('static', 'rutinas', 'rutina complementaria', f'{tipo}.html')
    
    if not os.path.exists(rutina_path):
        return redirect(url_for('rutinas'))
    
    # Leer el contenido del archivo HTML
    with open(rutina_path, 'r', encoding='utf-8') as file:
        contenido = file.read()
    
    # Extraer solo el contenido del body
    soup = BeautifulSoup(contenido, 'html.parser')
    
    # Obtener el título y el contenido
    titulo = soup.find('h2').text if soup.find('h2') else 'Rutina de Entrenamiento'
    body_content = soup.find('body')
    
    if (body_content):
        # Extraer el contenido del body sin el body tag
        contenido = ''.join(str(child) for child in body_content.children)
    
    return render_template('rutina_especifica.html', 
                         titulo=titulo,
                         contenido=contenido)

if __name__ == '__main__':
    app.run(debug=True)



