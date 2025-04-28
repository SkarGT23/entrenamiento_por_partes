from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory
import plotly.graph_objects as go
import plotly.io as pio
import os
import hashlib

app = Flask(__name__)
app.secret_key = 'mi_clave_secreta'  # Necesario para usar la sesión

# Diccionario simple para almacenar usuarios (en una aplicación real usarías una base de datos)
usuarios = {}

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Clase de ejercicio para gestionar los ejercicios de entrenamiento
class Exercise:
    def __init__(self, name, weight, increment, max_reps=12, exercise_type="compound", target_muscle=None, failure_type="controlled"):
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
    # Ejercicios Compuestos
    Exercise("Sentadillas", 50, 2.5, 12, "compound", "piernas", "controlled"),
    Exercise("Peso Muerto", 60, 2.5, 8, "compound", "espalda", "controlled"),
    Exercise("Press de Banca", 40, 2.5, 8, "compound", "pecho", "controlled"),
    Exercise("Remo con Barra", 30, 2.5, 10, "compound", "espalda", "controlled"),
    Exercise("Press Militar con Barra", 20, 2.5, 8, "compound", "hombros", "controlled"),
    
    # Ejercicios de Aislamiento
    Exercise("Curl de Bíceps", 15, 1.0, 12, "isolation", "bíceps", "technical_failure"),
    Exercise("Extensiones de Tríceps", 20, 1.0, 12, "isolation", "tríceps", "technical_failure"),
    Exercise("Elevaciones Laterales", 8, 1.0, 15, "isolation", "hombros", "technical_failure"),
    Exercise("Crunches", 0, 1, 20, "isolation", "abdominales", "failure"),
    
    # Ejercicios con Peso Corporal
    Exercise("Flexiones", 0, 1, 15, "bodyweight", "pecho", "technical_failure"),
    Exercise("Dominadas", 0, 1, 8, "bodyweight", "espalda", "controlled"),
    Exercise("Planchas", 0, 5, 60, "bodyweight", "core", "controlled"),
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

# Ruta para la página de registro
@app.route('/', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        form_type = request.form.get('form_type')
        
        if form_type == 'registro':
            nombre = request.form.get('nombre')
            apellidos = request.form.get('apellidos')
            usuario = request.form.get('usuario')
            password = request.form.get('password')

            if not all([nombre, apellidos, usuario, password]):
                return render_template('registro.html', error="Por favor, completa todos los campos.")
            
            if len(password) < 8:
                return render_template('registro.html', error="La contraseña debe tener al menos 8 caracteres.")
            
            if usuario in usuarios:
                return render_template('registro.html', error="Este nombre de usuario ya está en uso.")
            
            # Guardar usuario
            usuarios[usuario] = {
                'nombre': nombre,
                'apellidos': apellidos,
                'password': hash_password(password)
            }
            
            # Iniciar sesión
            session['usuario'] = usuario
            return redirect(url_for('pagina_principal'))
            
    return render_template('registro.html')

# Ruta para iniciar sesión
@app.route('/login', methods=['POST'])
def login():
    usuario = request.form.get('usuario')
    password = request.form.get('password')
    
    if not usuario or not password:
        return render_template('registro.html', error="Por favor, ingresa usuario y contraseña.")
    
    if usuario in usuarios and usuarios[usuario]['password'] == hash_password(password):
        session['usuario'] = usuario
        return redirect(url_for('pagina_principal'))
    
    return render_template('registro.html', error="Usuario o contraseña incorrectos.")

# Ruta para cerrar sesión
@app.route('/logout')
def logout():
    session.pop('usuario', None)
    return redirect(url_for('registro'))

# Ruta para acceder sin registro
@app.route('/acceder-sin-registro')
def acceder_sin_registro():
    return redirect(url_for('pagina_principal'))

# Ruta para la página principal del entrenamiento
@app.route('/pagina-principal')
def pagina_principal():
    usuario = session.get('usuario', 'Invitado')
    return render_template('index.html', usuario=usuario, exercises=exercises)

# Ruta para mostrar el progreso con gráficos de Plotly
@app.route('/progreso/<int:exercise_id>')
def progreso(exercise_id):
    exercise = exercises[exercise_id]
    
    # Mostrar mensaje en la consola
    print("\n=== IMPORTANTE: INSTRUCCIONES DE PROGRESIÓN ===")
    print("Si no puedes completar las series con el peso programado:")
    print("1. Reduce el peso a los valores de 2 semanas atrás")
    print("2. Mantén ese peso hasta que puedas completar todas las series")
    print("3. Solo entonces intenta progresar nuevamente")
    print("==============================================\n")
    
    progreso_data = calcular_progreso(exercise.weight, exercise.increment, 3, 6, exercise.exercise_type)  # Cálculo del progreso
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

    # Renderizar la plantilla de progreso con el gráfico y el mensaje
    return render_template('progreso.html', 
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

# Ruta para servir archivos estáticos (por ejemplo, imágenes o archivos descargables)
@app.route('/runitas/<path:filename>')
def serve_runitas(filename):
    return send_from_directory(os.path.join(app.root_path, 'static', 'runitas'), filename)

if __name__ == '__main__':
    app.run(debug=True)



