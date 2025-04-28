// Función para iniciar entrenamiento
function iniciarEntrenamiento(id) {
    window.location.href = `/entrenamiento/${id}`;
}

// Manejo del formulario biométrico
document.addEventListener('DOMContentLoaded', function() {
    const biometricForm = document.getElementById('biometric-form');
    const results = document.getElementById('results');

    if (biometricForm) {
        biometricForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Obtener valores del formulario
            const peso = parseFloat(document.getElementById('peso').value);
            const altura = parseFloat(document.getElementById('altura').value);
            const edad = parseInt(document.getElementById('edad').value);
            const genero = document.getElementById('genero').value;
            const nivel = document.getElementById('nivel').value;

            // Calcular TMB (Tasa Metabólica Basal)
            let tmb;
            if (genero === 'masculino') {
                tmb = 88.362 + (13.397 * peso) + (4.799 * altura) - (5.677 * edad);
            } else {
                tmb = 447.593 + (9.247 * peso) + (3.098 * altura) - (4.330 * edad);
            }

            // Calcular calorías diarias según nivel de actividad
            const factoresActividad = {
                sedentario: 1.2,
                ligero: 1.375,
                moderado: 1.55,
                activo: 1.725,
                muy_activo: 1.9
            };
            const calorias = tmb * factoresActividad[nivel];

            // Calcular IMC
            const alturaMetros = altura / 100;
            const imc = peso / (alturaMetros * alturaMetros);

            // Mostrar resultados
            document.getElementById('tmb-result').textContent = Math.round(tmb) + ' kcal';
            document.getElementById('calorias-result').textContent = Math.round(calorias) + ' kcal';
            document.getElementById('imc-result').textContent = imc.toFixed(1);
            
            results.style.display = 'block';
        });
    }
}); 