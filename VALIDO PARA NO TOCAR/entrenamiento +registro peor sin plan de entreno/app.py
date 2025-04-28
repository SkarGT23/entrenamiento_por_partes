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
    semana_actual = 1
    semanas_hasta_deload = 0
    factor_fatiga = 1.0

    for i in range(total_dias):
        mes = (i // 28) + 1
        semana = (i // 7) + 1
        dia_semana = i % 7 + 1

        # Resetear contador de días si es necesario
        if dia_contador > dias_entrenamiento:
            dia_contador = 1

        # Gestión de deload cada 4-6 semanas
        if semana != semana_actual:
            semana_actual = semana
            semanas_hasta_deload += 1
            if semanas_hasta_deload >= 4:
                peso_actual = peso_actual * 0.9  # Reducción del 10% para deload
                semanas_hasta_deload = 0
                factor_fatiga = 1.0  # Reset del factor de fatiga
            else:
                factor_fatiga *= 0.95  # Reducción gradual del progreso por fatiga

        # Determinar si es día de descanso
        es_descanso = dia_semana > dias_entrenamiento

        if es_descanso:
            progreso.append((mes, semana, dia_semana, "Descanso", peso_actual))
        else:
            # Calcular incremento ajustado por fatiga
            incremento_ajustado = incremento * factor_fatiga
            peso_sesion = round(peso_actual, 1)  # Redondear a 1 decimal
            progreso.append((mes, semana, dia_semana, 
                           f"Entreno: {peso_sesion} kg (Intensidad: {int(factor_fatiga*100)}%)", 
                           peso_sesion))
            
            # Solo incrementamos peso en días de entrenamiento
            if dia_contador <= dias_entrenamiento:
                peso_actual += incremento_ajustado

        dia_contador += 1

    return progreso

# Ruta para la página de registro
@app.route('/', methods=['GET', 'POST'])
def registro():
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
    indice_progreso = 0
    
    # Procesar todos los días del progreso
    for progreso in progreso_data:
        mes, semana, dia, estado, peso = progreso
        es_descanso = "Descanso" in estado
        
        plan.append({
            'mes': mes,
            'semana': f'Semana {semana}',
            'dia': f'Día {dia}',
            'ejercicio': ejercicio,
            'peso': peso,
            'estado': 'Descanso' if es_descanso else 'Entreno'
        })

    # Estimación de tiempo para alcanzar el peso deseado
    peso_actual = selected_exercise.weight * 0.5
    
    # Definir factores de progresión según el ejercicio y nivel
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

    # Determinar nivel basado en el peso actual vs peso objetivo y experiencia
    diferencia_peso = peso_deseado - peso_actual
    if diferencia_peso > 50:
        nivel = "avanzado"
    elif diferencia_peso > 25:
        nivel = "intermedio"
    else:
        nivel = "principiante"

    # Obtener factores específicos para el ejercicio y nivel
    factores = factores_progresion.get(ejercicio, {
        "principiante": {"incremento": 1.25, "frecuencia": 3, "factor_dificultad": 1.0},
        "intermedio": {"incremento": 0.625, "frecuencia": 3, "factor_dificultad": 1.5},
        "avanzado": {"incremento": 0.3125, "frecuencia": 3, "factor_dificultad": 2.0}
    })[nivel]

    # Calcular incremento semanal realista
    incremento_semanal = factores["incremento"] * (factores["frecuencia"] / 3)  # Normalizado a 3 días/semana
    factor_dificultad = factores["factor_dificultad"]

    # Ajustar por la diferencia de peso
    factor_diferencia = 1 + (diferencia_peso / 100)  # Aumenta la dificultad cuanto mayor es la diferencia

    # Calcular semanas necesarias considerando todos los factores
    semanas_base = diferencia_peso / incremento_semanal
    semanas_ajustadas = semanas_base * factor_dificultad * factor_diferencia

    # Añadir tiempo extra para deloads y estancamientos
    semanas_extra = int(semanas_ajustadas / 4)  # Un deload cada 4 semanas
    semanas_totales = semanas_ajustadas + semanas_extra

    # Convertir a meses y días
    meses_estimados = int(semanas_totales / 4)
    semanas_restantes = semanas_totales % 4
    dias_adicionales = int(semanas_restantes * 7)

    # Calcular rango de tiempo estimado (±20%)
    rango_inferior = int(semanas_totales * 0.8)
    rango_superior = int(semanas_totales * 1.2)
    
    meses_inferior = rango_inferior // 4
    semanas_inferior = rango_inferior % 4
    meses_superior = rango_superior // 4
    semanas_superior = rango_superior % 4

    # Preparamos el mensaje de estimación con formato HTML
    mensaje_estimacion = f"""
    <div class="estimation-container">
        <h3 class="estimation-title">📊 Estimación de Progreso</h3>
        
        <div class="estimation-header">
            <p class="exercise-name">Ejercicio: <strong>{ejercicio}</strong></p>
            <p class="target-weight">Peso objetivo: <strong>{peso_deseado} kg</strong></p>
            <p class="current-level">Nivel: <strong>{nivel.capitalize()}</strong></p>
        </div>

        <div class="time-estimate">
            <h4>⏱️ Tiempo Estimado</h4>
            <p>Tiempo estimado: {meses_estimados} meses{f' y {dias_adicionales} días' if dias_adicionales > 0 else ''}</p>
            <p class="time-range">Rango probable: {meses_inferior} meses{f' y {semanas_inferior} semanas' if semanas_inferior > 0 else ''} - {meses_superior} meses{f' y {semanas_superior} semanas' if semanas_superior > 0 else ''}</p>
        </div>

        <div class="considerations">
            <h4>⚠️ Factores Considerados</h4>
            <ul>
                <li>Diferencia de peso: {diferencia_peso:.1f} kg</li>
                <li>Factor de dificultad del ejercicio: {factor_dificultad:.1f}x</li>
                <li>Frecuencia de entrenamiento: {factores['frecuencia']} días/semana</li>
                <li>Incremento semanal base: {incremento_semanal:.1f} kg</li>
            </ul>
        </div>

        <div class="warning-box">
            <h4>🔄 Protocolo de Estancamiento</h4>
            <p>Si no puedes completar el peso programado en una sesión:</p>
            <ol>
                <li>Retrocede 2 semanas en tu plan de progresión</li>
                <li>Asegúrate de mejorar tu recuperación y nutrición</li>
                <li>Revisa tu técnica con un profesional si es necesario</li>
                <li>Continúa progresando desde ese punto más bajo</li>
            </ol>
        </div>

        <div class="reminder">
            <p><strong>💪 Recuerda:</strong> La progresión sostenible es mejor que la progresión rápida</p>
        </div>
    </div>
    
    <style>
    .estimation-container {
        max-width: 800px;
        margin: 20px auto;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 0 10px rgba(0,0,0,0.1);
    }
    .estimation-title {
        color: #2c3e50;
        text-align: center;
        margin-bottom: 20px;
    }
    .time-range {
        color: #666;
        font-style: italic;
    }
    .considerations ul {
        list-style-type: none;
        padding-left: 0;
    }
    .considerations li {
        margin: 10px 0;
        padding: 5px;
        background-color: #f8f9fa;
        border-radius: 5px;
    }
    </style>
    """

    # Crear tabla HTML con el plan de entrenamiento
    tabla_html = f"""
    <div class="plan-container">
        <h3 class="plan-title">📋 Plan de Entrenamiento</h3>
        <div class="table-responsive">
            <table class="training-table">
                <thead>
                    <tr>
                        <th>Mes</th>
                        <th>Semana</th>
                        <th>Día</th>
                        <th>Estado</th>
                        <th>Peso (kg)</th>
                        <th>Notas</th>
                    </tr>
                </thead>
                <tbody>
    """

    for entrada in plan:
        # Determinar si es semana de deload
        es_deload = entrada['semana'].split()[1] in ['4', '8', '12', '16', '20', '24']
        es_descanso = entrada['estado'] == 'Descanso'
        
        # Determinar clase y estilo
        clase_fila = 'deload-week' if es_deload else ('rest-day' if es_descanso else '')
        
        tabla_html += f"""
                    <tr class="{clase_fila}">
                        <td>{entrada['mes']}</td>
                        <td>{entrada['semana']}</td>
                        <td>{entrada['dia']}</td>
                        <td>{entrada['estado']}</td>
                        <td>{round(entrada['peso'], 1) if not es_descanso else '-'}</td>
                        <td>{
                            '🔄 Semana de deload' if es_deload else 
                            '😴 Día de descanso' if es_descanso else 
                            '💪 Entreno normal'
                        }</td>
                    </tr>
        """

    tabla_html += """
                </tbody>
            </table>
        </div>
    </div>

    <style>
    .plan-container {
        max-width: 1000px;
        margin: 20px auto;
        padding: 20px;
        background-color: white;
        border-radius: 10px;
        box-shadow: 0 0 10px rgba(0,0,0,0.1);
    }
    .plan-title {
        color: #2c3e50;
        text-align: center;
        margin-bottom: 20px;
    }
    .table-responsive {
        overflow-x: auto;
    }
    .training-table {
        width: 100%;
        border-collapse: collapse;
        margin: 20px 0;
        font-size: 0.9em;
        border-radius: 8px;
        overflow: hidden;
    }
    .training-table thead tr {
        background-color: #2c3e50;
        color: white;
        text-align: left;
    }
    .training-table th,
    .training-table td {
        padding: 12px 15px;
        border-bottom: 1px solid #dddddd;
    }
    .training-table tbody tr {
        border-bottom: 1px solid #dddddd;
    }
    .training-table tbody tr:nth-of-type(even) {
        background-color: #f8f9fa;
    }
    .rest-day {
        background-color: #f5f5f5 !important;
        color: #757575;
    }
    .deload-week {
        background-color: #fff3e0 !important;
    }
    .deload-week td {
        color: #ff5722;
    }
    </style>
    """

    return jsonify({
        'plan': plan, 
        'mensaje_estimacion': mensaje_estimacion,
        'tabla_html': tabla_html
    })

# Ruta para servir archivos estáticos (por ejemplo, imágenes o archivos descargables)
@app.route('/runitas/<path:filename>')
def serve_runitas(filename):
    return send_from_directory(os.path.join(app.root_path, 'static', 'runitas'), filename)

if __name__ == '__main__':
    app.run(debug=True)



