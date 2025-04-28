from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory
import plotly.graph_objects as go
import plotly.io as pio
import os

app = Flask(__name__)
app.secret_key = 'mi_clave_secreta'  # Necesario para usar la sesión

# Clase de ejercicio para gestionar los ejercicios de entrenamiento
class Exercise:
    def __init__(self, name, weight, increment):
        self.name = name
        self.weight = weight
        self.increment = increment

    def progress(self):
        self.weight += self.increment
        return self.weight

# Lista de ejercicios
exercises = [
    Exercise("Sentadillas", 50, 2.5),
    Exercise("Flexiones", 0, 1),
    Exercise("Dominadas", 0, 1),
    Exercise("Peso Muerto", 60, 2.5),
    Exercise("Press de Banca", 40, 2.5),
    Exercise("Remo con Barra", 30, 2.5),
    Exercise("Planchas", 0, 5),
    Exercise("Press Militar con Barra", 20, 2.5),
]

# Función para calcular el progreso y devolver un calendario de entrenamiento
def calcular_progreso(peso_maximo, incremento, dias_entrenamiento, meses):
    progreso = []
    peso_actual = peso_maximo * 0.5
    total_dias = meses * 28
    dia_contador = 1

    for i in range(total_dias):
        mes = (i // 28) + 1
        semana = (i // 7) + 1
        dia_semana = i % 7 + 1
        dia_descanso = "Descanso" if dia_semana > dias_entrenamiento else None

        # Si el día es de descanso, no aumentamos el peso
        if dia_descanso:
            progreso.append((mes, semana, dia_semana, "Descanso", peso_actual))
        else:
            progreso.append((mes, semana, dia_semana, f"Entreno: {peso_actual} kg", peso_actual))
            peso_actual += incremento

        dia_contador += 1
        if dia_contador > dias_entrenamiento:
            dia_contador = 1

    return progreso

# Ruta para la página de registro
@app.route('/', methods=['GET', 'POST'])
def registro():
    # Si el usuario ya está registrado o es invitado, redirigir a la página principal
    if 'usuario' in session:
        return redirect(url_for('pagina_principal'))
        
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        apellidos = request.form.get('apellidos')

        if nombre and apellidos:
            usuario = f"{nombre.lower()}{apellidos.lower().split(' ')[0]}"
            # Guardar usuario en la sesión
            session['usuario'] = usuario
            return redirect(url_for('pagina_principal'))
        else:
            return render_template('registro.html', error="Por favor, ingresa todos los datos correctamente.")
    
    return render_template('registro.html')

# Ruta para acceder sin registro
@app.route('/acceder-sin-registro')
def acceder_sin_registro():
    session['usuario'] = 'Invitado'
    return redirect(url_for('pagina_principal'))

# Ruta para cerrar sesión
@app.route('/logout')
def logout():
    session.pop('usuario', None)
    return redirect(url_for('registro'))

# Ruta para la página principal del entrenamiento
@app.route('/pagina-principal')
def pagina_principal():
    usuario = session.get('usuario', 'Invitado')
    return render_template('index.html', usuario=usuario, exercises=exercises)

# Ruta para mostrar el progreso con gráficos de Plotly
@app.route('/progreso/<int:exercise_id>')
def progreso(exercise_id):
    exercise = exercises[exercise_id]
    progreso_data = calcular_progreso(exercise.weight, exercise.increment, 3, 6)  # Cálculo del progreso
    meses_data = [f"Mes {p[0]}" for p in progreso_data]
    semanas_data = [f"Semana {p[1]}" for p in progreso_data]
    dias_data = [f"Día {p[2]}" for p in progreso_data]
    status_data = [p[3] for p in progreso_data]
    pesos = [p[4] for p in progreso_data]

    # Crear gráfico con Plotly
    fig = go.Figure(data=[go.Scatter(x=meses_data, y=pesos, mode='lines+markers')])
    fig.update_layout(title=f'Progreso de {exercise.name}', xaxis_title='Meses', yaxis_title='Peso (kg)')
    graph_html = pio.to_html(fig, full_html=False)

    # Renderizar la plantilla de progreso con el gráfico
    return render_template('progreso.html', graph=graph_html, exercise=exercise,
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

    progreso_data = calcular_progreso(selected_exercise.weight, selected_exercise.increment, dias_entrenamiento, meses)

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



