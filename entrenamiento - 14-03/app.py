from flask import Flask, render_template, request, jsonify, send_from_directory
import plotly.graph_objects as go
import plotly.io as pio
import os

app = Flask(__name__)

class Exercise:
    def __init__(self, name, weight, increment):
        self.name = name
        self.weight = weight
        self.increment = increment

    def progress(self):
        self.weight += self.increment
        return self.weight

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

def calcular_progreso(peso_maximo, incremento, dias_entrenamiento, meses):
    progreso = []
    peso_actual = peso_maximo * 0.5
    total_dias = meses * 28
    dia_contador = 1
    semana_contador = 1

    for i in range(total_dias):
        mes = (i // 28) + 1
        semana = (i // 7) + 1
        dia_semana = i % 7 + 1
        
        if dia_semana <= dias_entrenamiento:
            progreso.append((mes, semana, dia_contador, peso_actual))
            peso_actual += incremento
        else:
            progreso.append((mes, semana, "Descanso", peso_actual))

        dia_contador += 1
        if dia_contador > dias_entrenamiento:
            dia_contador = 1

    return progreso

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/progreso')
def progreso():
    progreso_data = calcular_progreso(50, 2.5, 3, 6)
    meses_data = [p[0] for p in progreso_data]
    pesos = [p[3] for p in progreso_data]

    fig = go.Figure(data=[go.Scatter(x=meses_data, y=pesos, mode='lines+markers')])
    fig.update_layout(title='Progreso de Entrenamiento', xaxis_title='Meses', yaxis_title='Peso (kg)')
    graph_html = pio.to_html(fig, full_html=False)

    return jsonify({'graph': graph_html})

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
                            'peso': progreso[3]
                        })

    # Estimación de tiempo para alcanzar el peso deseado
    peso_actual = selected_exercise.weight * 0.5
    tiempo_estimado_dias = 0  # Días totales de entrenamiento incluyendo descanso
    while peso_actual < peso_deseado:
        peso_actual += selected_exercise.increment
        tiempo_estimado_dias += 1  # Cada incremento representa un día de entrenamiento

    # Calcular meses y días restantes
    dias_entrenamiento_por_mes = dias_entrenamiento * 4  # 4 semanas por mes de entrenamiento
    dias_restantes = tiempo_estimado_dias % dias_entrenamiento_por_mes
    meses_estimados = tiempo_estimado_dias // dias_entrenamiento_por_mes

    # Convertir los días restantes en un valor más realista (promedio de 30.4 días por mes)
    dias_restantes_en_meses = dias_restantes / 30.4

    # Redondear el tiempo estimado en meses
    meses_estimados += round(dias_restantes_en_meses)

    # Mensaje de estimación
    mensaje_estimacion = f"Se estima que alcanzarás {peso_deseado} kg en aproximadamente "
    if meses_estimados > 0:
        mensaje_estimacion += f"{meses_estimados} mes(es) "

    if dias_restantes > 0:
        mensaje_estimacion += f"{dias_restantes} día(s)."

    return jsonify({'plan': plan, 'mensaje_estimacion': mensaje_estimacion})

@app.route('/runitas/<path:filename>')
def serve_runitas(filename):
    return send_from_directory(os.path.join(app.root_path, 'static', 'runitas'), filename)

if __name__ == '__main__':
    app.run(debug=True)


