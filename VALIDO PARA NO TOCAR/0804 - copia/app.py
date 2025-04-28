from flask import Flask, request, jsonify, session, redirect, url_for, flash, render_template
from datetime import datetime
from flask_login import login_required
import os
from plotly import graph_objs as go
import plotly.io as pio
from bs4 import BeautifulSoup

app = Flask(__name__)

# Función para manejar errores
def handle_error(e):
    db.session.rollback()
    return jsonify({'success': False, 'message': str(e)}), 400

# Función para construir respuestas JSON
def response_json(success, message, data=None):
    return jsonify({'success': success, 'message': message, 'data': data})

# Función para actualizar los datos del usuario
def actualizar_usuario_info(usuario, datos):
    try:
        for key, value in datos.items():
            if hasattr(usuario, key):
                setattr(usuario, key, value)
        db.session.commit()
        return response_json(True, 'Actualización exitosa')
    except Exception as e:
        db.session.rollback()
        return handle_error(e)

# Función para calcular la biometría
def calcular_biometria(altura, peso, edad, sexo, actividad):
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

    # Calcular grasa corporal
    grasa_corporal = (1.2 * imc) + (0.23 * edad) - (3.8 if sexo == "masculino" else 5.4)
    
    # Calcular masa muscular
    masa_muscular = peso * (1 - grasa_corporal / 100)

    # Calcular calorías diarias
    tmb = 10 * peso + 6.25 * (altura * 100) - 5 * edad + (5 if sexo == "masculino" else -161)
    factor_actividad = {
        "sedentario": 1.2, "ligero": 1.375, "moderado": 1.55, "activo": 1.725, "muy_activo": 1.9
    }
    calorias_diarias = tmb * factor_actividad.get(actividad, 1.2)

    return {
        'imc': round(imc, 2),
        'categoria_imc': categoria_imc,
        'grasa_corporal': round(grasa_corporal, 2),
        'masa_muscular': round(masa_muscular, 2),
        'calorias_diarias': round(calorias_diarias)
    }

# Función para formato de seguimiento
def formato_seguimiento(seguimiento):
    return {
        'id': seguimiento.id,
        'fecha': seguimiento.fecha.strftime('%Y-%m-%d %H:%M'),
        'peso': seguimiento.peso,
        'repeticiones': seguimiento.repeticiones
    }

@app.route('/registrar_seguimiento', methods=['POST'])
@login_required
def registrar_seguimiento():
    try:
        data = request.get_json()
        seguimiento = add_seguimiento(
            usuario=session['usuario'],
            ejercicio=data['ejercicio'],
            peso=data['peso'],
            repeticiones=data['repeticiones'],
            fecha=datetime.now()
        )

        return jsonify({
            'success': True,
            'message': 'Entrenamiento registrado correctamente',
            'seguimiento': formato_seguimiento(seguimiento)
        })
    except Exception as e:
        return handle_error(e)

@app.route('/actualizar_objetivo', methods=['POST'])
@login_required
def actualizar_objetivo():
    try:
        data = request.get_json()
        objetivo = Objetivo.query.get_or_404(data['id'])
        
        if objetivo.usuario == session['usuario']:
            objetivo.progreso = data['progreso']
            db.session.commit()
            return response_json(True, 'Objetivo actualizado correctamente')
        
        return response_json(False, 'No autorizado')
    except Exception as e:
        return handle_error(e)

@app.route('/actualizar_perfil', methods=['POST'])
@login_required
def actualizar_perfil():
    try:
        usuario = Usuario.query.filter_by(usuario=session['usuario']).first()
        if not usuario:
            return response_json(False, 'Usuario no encontrado')

        datos = {
            'nombre': request.form.get('nombre'),
            'apellidos': request.form.get('apellidos')
        }
        return actualizar_usuario_info(usuario, datos)
    except Exception as e:
        return handle_error(e)

@app.route('/calcular_biometrico', methods=['POST'])
def calcular_biometrico():
    try:
        altura = float(request.form.get('altura')) / 100
        peso = float(request.form.get('peso'))
        edad = int(request.form.get('edad'))
        sexo = request.form.get('sexo')
        actividad = request.form.get('actividad')

        biometria = calcular_biometria(altura, peso, edad, sexo, actividad)

        return jsonify(biometria)
    except Exception as e:
        return handle_error(e)

@app.route('/actualizar_medidas', methods=['POST'])
@login_required
def actualizar_medidas():
    try:
        usuario = Usuario.query.filter_by(usuario=session['usuario']).first()
        if not usuario:
            return response_json(False, 'Usuario no encontrado')

        medidas = {
            'peso': float(request.form.get('peso')),
            'altura': float(request.form.get('altura')),
            'cintura': float(request.form.get('cintura') or 0),
            'cadera': float(request.form.get('cadera') or 0),
            'brazo': float(request.form.get('brazo') or 0),
            'pierna': float(request.form.get('pierna') or 0)
        }

        return actualizar_usuario_info(usuario, medidas)
    except Exception as e:
        return handle_error(e)

@app.route('/actualizar_preferencias', methods=['POST'])
@login_required
def actualizar_preferencias():
    try:
        usuario = Usuario.query.filter_by(usuario=session['usuario']).first()
        if not usuario:
            return response_json(False, 'Usuario no encontrado')

        preferencias = {
            'sistema_unidades': request.form.get('sistema_unidades'),
            'idioma': request.form.get('idioma'),
            'notificaciones_email': bool(request.form.get('notificaciones_email')),
            'notificaciones_push': bool(request.form.get('notificaciones_push'))
        }

        return actualizar_usuario_info(usuario, preferencias)
    except Exception as e:
        return handle_error(e)

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

@app.route('/rutinas')
def rutinas():
    if 'usuario' not in session:
        return redirect(url_for('registro'))

    rutinas = [
        {'id': 'arnold', 'nombre': 'Rutina Arnold', 'descripcion': 'Rutina clásica de Arnold Schwarzenegger para hipertrofia', 'icono': 'fas fa-dumbbell', 'tipo': 'hipertrofia'},
        {'id': 'weider', 'nombre': 'Rutina Weider', 'descripcion': 'Sistema de entrenamiento para principiantes', 'icono': 'fas fa-dumbbell', 'tipo': 'principiante'},
        {'id': 'hiit', 'nombre': 'Rutina HIIT', 'descripcion': 'Entrenamiento de alta intensidad para quemar grasa', 'icono': 'fas fa-running', 'tipo': 'cardio'},
        {'id': 'fuerza', 'nombre': 'Rutina de Fuerza', 'descripcion': 'Programa enfocado en el desarrollo de fuerza máxima', 'icono': 'fas fa-weight-hanging', 'tipo': 'fuerza'},
        {'id': 'full-body', 'nombre': 'Rutina Full Body', 'descripcion': 'Entrenamiento completo que trabaja todo el cuerpo en cada sesión', 'icono': 'fas fa-user', 'tipo': 'full-body'},
        {'id': 'push-pull', 'nombre': 'Rutina Push-Pull', 'descripcion': 'Sistema de entrenamiento que divide los ejercicios en empuje y tracción', 'icono': 'fas fa-exchange-alt', 'tipo': 'push-pull'},
        {'id': 'hipertrofia', 'nombre': 'Rutina de Hipertrofia', 'descripcion': 'Programa específico para el desarrollo muscular', 'icono': 'fas fa-dumbbell', 'tipo': 'hipertrofia'}
    ]

    return render_template('rutinas.html', rutinas=rutinas)

@app.route('/rutina/<tipo>')
def rutina_especifica(tipo):
    if 'usuario' not in session:
        return redirect(url_for('registro'))
    
    rutina_path = os.path.join('static', 'rutinas', 'rutina complementaria', f'{tipo}.html')
    
    if not os.path.exists(rutina_path):
        return redirect(url_for('rutinas'))
    
    with open(rutina_path, 'r', encoding='utf-8') as file:
        contenido = file.read()
    
    # Extraer el contenido del HTML
    soup = BeautifulSoup(contenido, 'html.parser')
    rutina_contenido = soup.get_text()
    
    return render_template('rutina.html', rutina=contenido)




