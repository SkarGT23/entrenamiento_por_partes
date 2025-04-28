from flask import Flask, render_template, request, redirect, url_for, session
import plotly.graph_objects as go
import plotly.io as pio

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
    semana_contador = 1

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

if __name__ == '__main__':
    app.run(debug=True)
