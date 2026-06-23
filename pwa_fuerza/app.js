// app.js - Controlador Principal Fuerza365 v2.0 (Fuego Metálico, CrossFit y Rutinas Propias)

const db = window.dbManager;
const algo = window.ExerciseManager;

// Variables de Gráficos (Instancias de Chart.js)
let rmChartInstance = null;
let weightChartInstance = null;
let bodyCompChartInstance = null;

// Temporizador Tabata (Estado)
let tabataInterval = null;
let tabataTimeLeft = 0;
let tabataState = "prep"; // prep, work, rest
let tabataRound = 1;
let tabataIsPaused = false;
let tabataSettings = {};

// Creador de Rutinas (Ejercicios seleccionados en memoria antes de guardar)
let builderSelectedExercises = []; 
let builderActiveFilter = "todos"; // todos, libre, maquina, corporal

// Tracker de Entrenamiento Activo (Memoria de la sesión en curso)
let activeSessionRoutine = null;
let activeSessionLogs = {}; // Almacena series completadas: { exerciseName: [ { peso, reps, completado } ] }

// ==========================================
// INICIALIZACIÓN DE LA APLICACIÓN
// ==========================================

document.addEventListener("DOMContentLoaded", () => {
  // 1. Cargar datos del perfil en la UI
  actualizarInfoPerfilUI();

  // 2. Poblar selectores de ejercicios
  poblarSelectoresEjercicios();

  // 3. Registrar Listeners de Formularios y Botones
  registrarEventListeners();

  // 4. Renderizar datos del Dashboard
  actualizarDashboardUI();

  // 5. Cargar Rutinas Clásicas preconfiguradas
  cargarRutinasClasicas();

  // 6. Cargar Rutinas Propias del usuario
  poblarCustomRoutinesList();

  // 7. Precargar Calculadora Biométrica desde el Perfil
  precargarDatosBiometricos();
  
  console.log("Fuerza365 PWA v2.0 inicializada con soporte de Retos y Creador de Rutinas.");
});

// ==========================================
// SPA ROUTING (NAVEGACIÓN)
// ==========================================

function switchTab(tabId) {
  // Ocultar todas las páginas
  document.querySelectorAll(".tab-page").forEach(page => {
    page.classList.remove("active");
  });

  // Mostrar página seleccionada
  const targetPage = document.getElementById(`tab-${tabId}`);
  if (targetPage) {
    targetPage.classList.add("active");
  }

  // Actualizar barra de navegación inferior
  document.querySelectorAll(".nav-item").forEach(item => {
    item.classList.remove("active");
  });

  const navBtn = Array.from(document.querySelectorAll(".nav-item")).find(btn => 
    btn.getAttribute("onclick").includes(`'${tabId}'`)
  );
  if (navBtn) {
    navBtn.classList.add("active");
  }

  // Acciones específicas por pestaña
  if (tabId === "dashboard") {
    actualizarDashboardUI();
  } else if (tabId === "entreno") {
    poblarCustomRoutinesList();
  } else if (tabId === "retos") {
    actualizarRetosUI();
  } else if (tabId === "progreso") {
    renderProgressCharts();
    actualizarTablaHistorial();
  } else if (tabId === "galeria") {
    actualizarGaleriaUI();
  } else if (tabId === "ajustes") {
    actualizarAjustesUI();
  }
}

// Sub-pestañas dentro de Entrenar
function switchSubTab(subTabId) {
  document.querySelectorAll(".sub-tab-content").forEach(content => {
    content.classList.remove("active");
  });
  document.querySelectorAll(".sub-tab-btn").forEach(btn => {
    btn.classList.remove("active");
  });

  document.getElementById(subTabId).classList.add("active");
  
  const activeBtn = Array.from(document.querySelectorAll(".sub-tab-btn")).find(btn => 
    btn.getAttribute("onclick").includes(`'${subTabId}'`)
  );
  if (activeBtn) activeBtn.classList.add("active");

  if (subTabId === "sub-logger") {
    actualizarLoggerRecientes();
  } else if (subTabId === "sub-custom-workout") {
    poblarCustomRoutinesList();
    showRoutineBuilder(false);
  }
}

// Sub-pestañas dentro de Retos
function switchRetosSubTab(subTabId) {
  const tabRetos = document.getElementById("tab-retos");
  tabRetos.querySelectorAll(".sub-tab-content").forEach(content => {
    content.classList.remove("active");
  });
  tabRetos.querySelectorAll(".sub-tab-btn").forEach(btn => {
    btn.classList.remove("active");
  });

  document.getElementById(subTabId).classList.add("active");
  
  const activeBtn = Array.from(tabRetos.querySelectorAll(".sub-tab-btn")).find(btn => 
    btn.getAttribute("onclick").includes(`'${subTabId}'`)
  );
  if (activeBtn) activeBtn.classList.add("active");
}

// ==========================================
// CONFIGURACIÓN DE ELEMENTOS DINÁMICOS
// ==========================================

function actualizarInfoPerfilUI() {
  const perfil = db.getPerfil();
  document.getElementById("header-user").textContent = perfil.nombre;
  document.getElementById("welcome-name").textContent = perfil.nombre;
}

function poblarSelectoresEjercicios() {
  const genSelect = document.getElementById("gen-exercise");
  const progressSelect = document.getElementById("progress-exercise-select");
  const logExerciseSelect = document.getElementById("log-exercise");
  const logMuscleSelect = document.getElementById("log-muscle");
  
  if (!genSelect) return;

  genSelect.innerHTML = "";
  progressSelect.innerHTML = "";
  logMuscleSelect.innerHTML = "";

  const musculos = [...new Set(algo.DEFAULT_EXERCISES.map(e => e.targetMuscle))];
  
  logMuscleSelect.innerHTML = `<option value="todos">Todos los músculos</option>`;
  musculos.forEach(m => {
    logMuscleSelect.innerHTML += `<option value="${m}">${capitalizar(m)}</option>`;
  });

  const ordenados = [...algo.DEFAULT_EXERCISES].sort((a, b) => a.name.localeCompare(b.name));

  ordenados.forEach(ex => {
    genSelect.innerHTML += `<option value="${ex.name}">${ex.name} (${capitalizar(ex.targetMuscle)})</option>`;
    progressSelect.innerHTML += `<option value="${ex.name}">${ex.name}</option>`;
  });

  filterLogExercises();
}

function filterLogExercises() {
  const logMuscleSelect = document.getElementById("log-muscle");
  const logExerciseSelect = document.getElementById("log-exercise");
  const selectedMuscle = logMuscleSelect.value;

  logExerciseSelect.innerHTML = "";

  const filtered = algo.DEFAULT_EXERCISES.filter(ex => 
    selectedMuscle === "todos" || ex.targetMuscle === selectedMuscle
  ).sort((a, b) => a.name.localeCompare(b.name));

  filtered.forEach(ex => {
    logExerciseSelect.innerHTML += `<option value="${ex.name}">${ex.name} (${capitalizar(ex.equipmentType)})</option>`;
  });
}

// Helper para capitalizar texto
function capitalizar(string) {
  if (!string) return "";
  return string.charAt(0).toUpperCase() + string.slice(1);
}

// ==========================================
// REGISTRO DE EVENTOS (LISTENERS)
// ==========================================

function registrarEventListeners() {
  // 1. Formulario del Generador del Plan de Fuerza
  document.getElementById("generator-form").addEventListener("submit", (e) => {
    e.preventDefault();
    generarPlanFuerzaAnual();
  });

  // 2. Formulario del Logger de Entrenamientos (Series Rápidas)
  document.getElementById("logger-form").addEventListener("submit", (e) => {
    e.preventDefault();
    registrarSerieEntrenamiento();
  });

  // 3. Formulario de la Calculadora Biométrica
  document.getElementById("biometric-form").addEventListener("submit", (e) => {
    e.preventDefault();
    ejecutarCalculosBiometricos();
  });

  // 4. Formulario de Subida de Fotos en Galería
  document.getElementById("gallery-form").addEventListener("submit", (e) => {
    e.preventDefault();
    subirFotoProgreso();
  });

  // 5. Formulario de Guardado de Perfil General
  document.getElementById("profile-form").addEventListener("submit", (e) => {
    e.preventDefault();
    guardarPerfilGeneral();
  });

  // 6. Formulario de Medidas Corporales
  document.getElementById("measures-form").addEventListener("submit", (e) => {
    e.preventDefault();
    guardarMedidasMusculares();
  });

  // 7. Formulario de Creación de Objetivos
  document.getElementById("goal-modal-form").addEventListener("submit", (e) => {
    e.preventDefault();
    crearNuevoObjetivo();
  });

  // 8. Formulario de Creación de Rutinas Personalizadas
  document.getElementById("routine-builder-form").addEventListener("submit", (e) => {
    e.preventDefault();
    guardarRutinaCreada();
  });

  // 9. Formulario del Modal de Retos / WODs
  document.getElementById("challenge-modal-form").addEventListener("submit", (e) => {
    e.preventDefault();
    guardarMarcaRetoLogueada();
  });
}

// ==========================================
// DASHBOARD VIEW LOGIC
// ==========================================

function actualizarDashboardUI() {
  const historial = db.getHistorial();
  const objetivos = db.getObjetivos();
  const perfil = db.getPerfil();
  const retos = db.getRetosCompletados();

  // Actualizar estadísticas rápidas
  document.getElementById("stats-total-entrenos").textContent = historial.length;
  document.getElementById("stats-total-objetivos").textContent = Object.keys(retos).length;
  document.getElementById("stats-current-weight").textContent = perfil.peso ? perfil.peso.toFixed(1) : "75.0";

  // Renderizar Lista de Objetivos Activos
  const listContainer = document.getElementById("dashboard-goals-list");
  listContainer.innerHTML = "";

  if (objetivos.length === 0) {
    listContainer.innerHTML = `
      <div class="card glass text-center">
        <p class="card-text"><i class="fa-solid fa-hourglass-empty"></i> No tienes metas activas aún. ¡Crea una haciendo clic arriba!</p>
      </div>`;
    return;
  }

  objetivos.forEach(goal => {
    const isCompleted = goal.completado;
    
    // Calcular porcentaje de progreso aproximado
    let pct = 0;
    if (goal.tipo === "peso") {
      const diffTotal = Math.abs(perfil.peso - goal.valor_objetivo);
      pct = diffTotal === 0 ? 100 : Math.max(5, Math.min(100, (1 - (diffTotal / perfil.peso)) * 100));
    } else {
      pct = isCompleted ? 100 : 35;
    }

    listContainer.innerHTML += `
      <div class="goal-card ${isCompleted ? 'completed' : ''}" id="goal-item-${goal.id}">
        <div class="goal-info">
          <div class="goal-title-wrapper">
            <div class="goal-checkbox ${isCompleted ? 'checked' : ''}" onclick="toggleMetaCompletada(${goal.id})"></div>
            <div>
              <span class="goal-val-title">${capitalizar(goal.tipo)} Meta: ${goal.valor_objetivo}</span>
              <div class="goal-deadline"><i class="fa-solid fa-calendar-days"></i> Límite: ${goal.fecha_fin}</div>
            </div>
          </div>
          <button class="goal-delete-btn" onclick="eliminarMeta(${goal.id})">
            <i class="fa-solid fa-trash"></i>
          </button>
        </div>
        <div class="goal-progress-bar">
          <div class="goal-progress-fill" style="width: ${pct}%"></div>
        </div>
      </div>
    `;
  });
}

function toggleMetaCompletada(id) {
  db.toggleObjetivoCompletado(id);
  actualizarDashboardUI();
}

function eliminarMeta(id) {
  if (confirm("¿Estás seguro de que deseas eliminar este objetivo?")) {
    db.eliminarObjetivo(id);
    actualizarDashboardUI();
  }
}

// ==========================================
// ENTRENO VIEW: GENERADOR PLAN ANUAL
// ==========================================

function generarPlanFuerzaAnual() {
  const exerciseName = document.getElementById("gen-exercise").value;
  const rmTeorico = parseFloat(document.getElementById("gen-rm").value);
  const days = parseInt(document.getElementById("gen-days").value);
  const months = parseInt(document.getElementById("gen-months").value);

  const baseEx = algo.DEFAULT_EXERCISES.find(e => e.name === exerciseName);
  if (!baseEx) return;

  const planData = algo.calcularProgreso(rmTeorico, baseEx.increment, days, months, baseEx.exerciseType);
  const estimacion = algo.estimarTiempoParaPeso(baseEx.weight, rmTeorico, baseEx.increment, days);

  document.getElementById("generator-results").classList.remove("hidden");

  const estimationCard = document.getElementById("estimation-card");
  if (estimacion.meses > 0 || estimacion.dias > 0) {
    estimationCard.innerHTML = `
      <h3 class="color-coral"><i class="fa-solid fa-hourglass-half"></i> Estimación de Tiempo</h3>
      <p class="card-text">Basado en tus incrementos de cargas progresivas de <strong>+${baseEx.increment} kg</strong>, alcanzarás tus ${rmTeorico} kg de 1RM en aproximadamente:</p>
      <div class="metric-value color-coral">${estimacion.meses} mes(es) y ${estimacion.dias} día(s)</div>
      <p class="card-text" style="font-size: 11px; margin-top: 4px;">Requiere aproximadamente ${estimacion.totalEntrenamientos} entrenamientos dedicados sin fallos.</p>
    `;
  } else {
    estimationCard.innerHTML = `
      <h3 class="color-purple"><i class="fa-solid fa-trophy"></i> ¡Meta Alcanzada!</h3>
      <p class="card-text">Tu RM actual es igual o superior al peso objetivo deseado. ¡Excelente fuerza!</p>
    `;
  }

  const grid = document.getElementById("plan-weeks-grid");
  grid.innerHTML = "";

  const planPorSemanas = {};
  planData.forEach(p => {
    const key = `Mes ${p.mes} - Semana ${p.semana}`;
    if (!planPorSemanas[key]) planPorSemanas[key] = [];
    planPorSemanas[key].push(p);
  });

  Object.keys(planPorSemanas).forEach(weekKey => {
    const daysList = planPorSemanas[weekKey];
    const weekNumber = parseInt(weekKey.split("Semana ")[1]);
    const esDescarga = weekNumber % 4 === 0;

    let weekHtml = `
      <div class="week-box ${esDescarga ? 'highlight-border' : ''}">
        <div class="week-title" style="${esDescarga ? 'color: var(--primary); border-color: rgba(255, 85, 0, 0.25);' : ''}">
          <i class="fa-solid ${esDescarga ? 'fa-battery-quarter' : 'fa-chart-line'}"></i> ${weekKey} ${esDescarga ? '(Semana de Descarga)' : ''}
        </div>
        <div class="days-list">
    `;

    daysList.forEach(d => {
      const isEntreno = d.tipo === "Entrenamiento";
      weekHtml += `
        <div class="day-row">
          <span class="day-name">Día ${d.dia}</span>
          <span class="day-weight-label ${isEntreno ? 'entreno' : 'descanso'}">
            ${isEntreno ? `${d.peso.toFixed(1)} kg` : 'Descanso'}
          </span>
        </div>
      `;
    });

    weekHtml += `
        </div>
      </div>
    `;
    grid.innerHTML += weekHtml;
  });

  document.getElementById("generator-results").scrollIntoView({ behavior: "smooth" });
}

// ==========================================
// ENTRENO VIEW: LOG DE SERIES RÁPIDAS
// ==========================================

function registrarSerieEntrenamiento() {
  const ejercicio = document.getElementById("log-exercise").value;
  const peso = parseFloat(document.getElementById("log-weight").value);
  const repeticiones = parseInt(document.getElementById("log-reps").value);
  const notas = document.getElementById("log-notes").value;

  if (!ejercicio || isNaN(peso) || isNaN(repeticiones)) {
    alert("Por favor, rellena los datos correctamente.");
    return;
  }

  db.addSeguimiento(ejercicio, peso, repeticiones, notas);
  document.getElementById("log-notes").value = "";
  
  const btn = document.querySelector("#logger-form button[type='submit']");
  const oldText = btn.innerHTML;
  btn.innerHTML = `<i class="fa-solid fa-circle-check"></i> ¡Guardado!`;
  btn.style.background = "var(--success)";
  btn.style.boxShadow = "0 0 16px rgba(0, 230, 118, 0.4)";
  
  setTimeout(() => {
    btn.innerHTML = oldText;
    btn.style.background = "";
    btn.style.boxShadow = "";
  }, 1500);

  actualizarLoggerRecientes();
}

function actualizarLoggerRecientes() {
  const historial = db.getHistorial();
  const list = document.getElementById("recent-logs-list");
  if (!list) return;

  list.innerHTML = "";

  const recientes = [...historial].reverse().slice(0, 4);

  if (recientes.length === 0) {
    list.innerHTML = `<p class="card-text text-center"><i class="fa-solid fa-info-circle"></i> No has registrado series hoy.</p>`;
    return;
  }

  recientes.forEach(item => {
    const RM = item.repeticiones === 0 ? item.peso : item.peso * (36 / (37 - item.repeticiones));
    
    list.innerHTML += `
      <div class="log-item-card">
        <div class="log-item-info">
          <h4>${item.ejercicio}</h4>
          <span>${formatearFechaHora(item.fecha)}</span>
        </div>
        <div class="log-item-stats">
          ${item.peso} kg ${item.repeticiones > 0 ? `x ${item.repeticiones} reps` : ""} 
          ${item.repeticiones > 0 ? `<span style="font-size:11px; font-weight:400; color:var(--text-secondary)">(1RM: ~${RM.toFixed(1)}k)</span>` : ""}
        </div>
      </div>
    `;
  });
}

function formatearFechaHora(isoString) {
  const d = new Date(isoString);
  return `${d.getDate()}/${d.getMonth()+1} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`;
}

// ==========================================
// RUNTINAS CLÁSICAS
// ==========================================

const RUTINAS_DATA = [
  {
    id: "arnold",
    nombre: "Rutina Arnold Schwarzenegger",
    descripcion: "La legendaria división de alta frecuencia y volumen creada por Arnold para hipertrofia máxima.",
    icono: "fa-solid fa-dumbbell",
    detalles: `
      <h4>Estructura de Frecuencia:</h4>
      <p>6 Días de entrenamiento a la semana. División: Antagonistas (Pecho/Espalda, Hombros/Brazos, Piernas).</p>
      <br>
      <h4>Días 1 y 4: Pecho y Espalda</h4>
      <ul>
        <li>Press de Banca Plano: 5 series x 8-12 reps</li>
        <li>Remo con Barra: 5 series x 8-12 reps</li>
        <li>Press Inclinado con Mancuernas: 4 series x 10 reps</li>
        <li>Dominadas: 4 series x al fallo</li>
        <li>Aperturas con Mancuernas: 4 series x 12 reps</li>
      </ul>
      <br>
      <h4>Días 2 y 5: Hombros y Brazos</h4>
      <ul>
        <li>Press Militar con Barra: 5 series x 8-10 reps</li>
        <li>Elevaciones Laterales: 4 series x 12-15 reps</li>
        <li>Curl de Bíceps con Barra Z: 4 series x 10-12 reps</li>
        <li>Press de Banca Agarre Cerrado: 4 series x 10-12 reps</li>
        <li>Curl Martillo: 3 series x 12 reps</li>
      </ul>
      <br>
      <h4>Días 3 y 6: Piernas y Core</h4>
      <ul>
        <li>Sentadillas: 5 series x 8-12 reps</li>
        <li>Peso Muerto Rumano: 4 series x 10 reps</li>
        <li>Prensa de Piernas: 4 series x 12 reps</li>
        <li>Curl de Isquiotibiales: 4 series x 15 reps</li>
        <li>Elevaciones de Gemelos: 5 series x 20 reps</li>
      </ul>
    `
  },
  {
    id: "weider",
    nombre: "Rutina Weider Principiantes",
    descripcion: "La división clásica por excelencia. Ideal para concentrar toda la fatiga en un solo grupo muscular.",
    icono: "fa-solid fa-cubes",
    detalles: `
      <h4>Estructura de Frecuencia:</h4>
      <p>5 Días de entrenamiento a la semana. Un grupo muscular principal por sesión.</p>
      <br>
      <h4>Lunes: Pecho</h4>
      <ul>
        <li>Press de Banca Plano: 4 series x 10 reps</li>
        <li>Press Inclinado con Mancuernas: 4 series x 12 reps</li>
        <li>Aperturas Inclinadas: 3 series x 15 reps</li>
        <li>Fondos en Paralelas: 3 series x al fallo</li>
      </ul>
      <br>
      <h4>Martes: Espalda</h4>
      <ul>
        <li>Remo con Barra: 4 series x 10 reps</li>
        <li>Jalón al Pecho: 4 series x 12 reps</li>
        <li>Remo con Mancuerna: 3 series x 10 reps</li>
        <li>Hiperextensiones: 3 series x 15 reps</li>
      </ul>
      <br>
      <h4>Miércoles: Hombros</h4>
      <ul>
        <li>Press Militar con Mancuernas: 4 series x 10 reps</li>
        <li>Elevaciones Laterales: 4 series x 15 reps</li>
        <li>Elevaciones Posteriores (Pájaros): 4 series x 15 reps</li>
        <li>Remo al Mentón: 3 series x 12 reps</li>
      </ul>
      <br>
      <h4>Jueves: Piernas</h4>
      <ul>
        <li>Sentadillas: 4 series x 10 reps</li>
        <li>Prensa de Piernas: 4 series x 12 reps</li>
        <li>Extensiones de Cuádriceps: 3 series x 15 reps</li>
        <li>Curl de Isquiotibiales: 3 series x 15 reps</li>
      </ul>
      <br>
      <h4>Viernes: Brazos (Bíceps/Tríceps)</h4>
      <ul>
        <li>Curl de Bíceps con Barra: 4 series x 12 reps</li>
        <li>Extensiones en Polea Alta: 4 series x 12 reps</li>
        <li>Curl Martillo: 3 series x 12 reps</li>
        <li>Press Francés: 3 series x 12 reps</li>
      </ul>
    `
  },
  {
    id: "fuerza",
    nombre: "Rutina de Fuerza 5x5",
    descripcion: "Enfoque absoluto en el desarrollo de la fuerza máxima en los tres levantamientos básicos.",
    icono: "fa-solid fa-weight-hanging",
    detalles: `
      <h4>Estructura de Frecuencia:</h4>
      <p>3 Días de entrenamiento a la semana (Lunes, Miércoles, Viernes). Alternancia A y B.</p>
      <br>
      <h4>Entrenamiento A:</h4>
      <ul>
        <li>Sentadillas Traseras: 5 series x 5 reps (Pesado)</li>
        <li>Press de Banca Plano: 5 series x 5 reps (Pesado)</li>
        <li>Remo Pendlay / Con Barra: 5 series x 5 reps</li>
        <li>Crunches Abdominales: 3 series x 15 reps</li>
      </ul>
      <br>
      <h4>Entrenamiento B:</h4>
      <ul>
        <li>Sentadillas Traseras: 5 series x 5 reps (Pesado)</li>
        <li>Press Militar con Barra: 5 series x 5 reps (Pesado)</li>
        <li>Peso Muerto Convencional: 1 serie x 5 reps (Muy Pesado)</li>
        <li>Planchas Abdominales: 3 series x 60 segundos</li>
      </ul>
      <br>
      <h4>Regla de Progresión:</h4>
      <p>Si completas las 5x5 reps de forma limpia, aumenta 2.5 kg en Sentadillas, Press de Banca y Press Militar en la siguiente sesión, y 5 kg en Peso Muerto.</p>
    `
  }
];

function cargarRutinasClasicas() {
  const container = document.getElementById("routines-list");
  if (!container) return;

  container.innerHTML = "";
  RUTINAS_DATA.forEach(r => {
    container.innerHTML += `
      <div class="routine-card" onclick="verDetalleRutina('${r.id}')">
        <div class="routine-icon-box">
          <i class="${r.icono}"></i>
        </div>
        <div class="routine-info">
          <h4 class="routine-name">${r.nombre}</h4>
          <span class="routine-desc">${r.descripcion}</span>
        </div>
        <button class="btn-icon"><i class="fa-solid fa-chevron-right"></i></button>
      </div>
    `;
  });
}

function verDetalleRutina(id) {
  const r = RUTINAS_DATA.find(x => x.id === id);
  if (!r) return;

  document.getElementById("routine-modal-title").textContent = r.nombre;
  document.getElementById("routine-modal-body").innerHTML = r.detalles;
  openModal("modal-routine-details");
}

// ==========================================
// CREADOR DE RUTINAS PERSONALIZADAS Y TRACKER (NUEVO)
// ==========================================

function showRoutineBuilder(show) {
  const builder = document.getElementById("custom-routine-builder");
  const mainView = document.getElementById("routine-main-view");
  const listHeader = mainView.querySelector(".section-header");
  const listGrid = document.getElementById("custom-routines-list");
  
  if (show) {
    builder.classList.remove("hidden");
    if (listHeader) listHeader.classList.add("hidden");
    if (listGrid) listGrid.classList.add("hidden");
    builderSelectedExercises = [];
    document.getElementById("builder-routine-name-input").value = "";
    actualizarSelectedExercisesBuilderList();
    filterBuilderExercises("todos");
  } else {
    builder.classList.add("hidden");
    if (listHeader) listHeader.classList.remove("hidden");
    if (listGrid) listGrid.classList.remove("hidden");
    poblarCustomRoutinesList();
  }
}

function filterBuilderExercises(type) {
  builderActiveFilter = type;
  
  // Cambiar chips activos
  document.querySelectorAll(".filter-chip").forEach(chip => {
    chip.classList.remove("active");
  });
  
  const activeChip = document.getElementById(`filter-${type}`);
  if (activeChip) activeChip.classList.add("active");

  poblarSearchableExercises();
}

function poblarSearchableExercises() {
  const container = document.getElementById("builder-searchable-exercises");
  if (!container) return;

  container.innerHTML = "";

  const filtered = algo.DEFAULT_EXERCISES.filter(ex => 
    builderActiveFilter === "todos" || ex.equipmentType === builderActiveFilter
  ).sort((a, b) => a.name.localeCompare(b.name));

  filtered.forEach(ex => {
    // Verificar si ya está añadido
    const yaAnadido = builderSelectedExercises.some(s => s.ejercicio === ex.name);
    
    container.innerHTML += `
      <div class="builder-ex-item">
        <div>
          <strong>${ex.name}</strong> 
          <span style="font-size:10px; color:var(--text-muted);">(${capitalizar(ex.targetMuscle)} - ${capitalizar(ex.equipmentType)})</span>
        </div>
        <button type="button" class="btn-secondary btn-small" ${yaAnadido ? 'disabled' : ''} onclick="addExerciseToBuilder('${ex.name}')">
          ${yaAnadido ? '<i class="fa-solid fa-check text-green"></i> Añadido' : '<i class="fa-solid fa-plus"></i> Añadir'}
        </button>
      </div>
    `;
  });
}

function addExerciseToBuilder(name) {
  const baseEx = algo.DEFAULT_EXERCISES.find(e => e.name === name);
  if (!baseEx) return;

  // Intentar leer el peso programado / actual de 1RM si existe en LocalStorage
  const pesosGuardados = db.getPesosEjercicios();
  let pesoPorDefecto = baseEx.weight;
  
  if (pesosGuardados[name]) {
    pesoPorDefecto = pesosGuardados[name].weight;
  }

  builderSelectedExercises.push({
    ejercicio: name,
    series: 3,
    repeticiones: 10,
    peso: pesoPorDefecto
  });

  poblarSearchableExercises();
  actualizarSelectedExercisesBuilderList();
}

function removeExerciseFromBuilder(name) {
  builderSelectedExercises = builderSelectedExercises.filter(e => e.ejercicio !== name);
  poblarSearchableExercises();
  actualizarSelectedExercisesBuilderList();
}

function actualizarSelectedExercisesBuilderList() {
  const container = document.getElementById("builder-selected-exercises-container");
  const emptyMsg = document.getElementById("builder-empty-msg");
  
  if (builderSelectedExercises.length === 0) {
    if (emptyMsg) emptyMsg.classList.remove("hidden");
    container.querySelectorAll(".selected-ex-card").forEach(c => c.remove());
    return;
  }

  if (emptyMsg) emptyMsg.classList.add("hidden");
  
  // Limpiar antiguos cards
  container.querySelectorAll(".selected-ex-card").forEach(c => c.remove());

  builderSelectedExercises.forEach((ex, index) => {
    const card = document.createElement("div");
    card.className = "selected-ex-card";
    card.innerHTML = `
      <div class="selected-ex-header">
        <span>${ex.ejercicio}</span>
        <button type="button" class="goal-delete-btn" onclick="removeExerciseFromBuilder('${ex.ejercicio}')">
          <i class="fa-solid fa-xmark"></i> Quitar
        </button>
      </div>
      <div class="selected-ex-inputs">
        <div class="form-group">
          <label>Series</label>
          <input type="number" value="${ex.series}" min="1" class="form-input" onchange="updateBuilderExData('${ex.ejercicio}', 'series', this.value)">
        </div>
        <div class="form-group">
          <label>Reps</label>
          <input type="number" value="${ex.repeticiones}" min="1" class="form-input" onchange="updateBuilderExData('${ex.ejercicio}', 'repeticiones', this.value)">
        </div>
        <div class="form-group">
          <label>Peso (kg)</label>
          <input type="number" value="${ex.peso}" min="0" step="0.5" class="form-input" onchange="updateBuilderExData('${ex.ejercicio}', 'peso', this.value)">
        </div>
      </div>
    `;
    container.appendChild(card);
  });
}

function updateBuilderExData(name, field, value) {
  const ex = builderSelectedExercises.find(e => e.ejercicio === name);
  if (ex) {
    if (field === "peso") {
      ex.peso = parseFloat(value);
    } else {
      ex[field] = parseInt(value);
    }
  }
}

function guardarRutinaCreada() {
  const nombre = document.getElementById("builder-routine-name-input").value;
  
  if (builderSelectedExercises.length === 0) {
    alert("Por favor, añade al menos un ejercicio a tu rutina.");
    return;
  }

  db.addRutinaPersonalizada(nombre, builderSelectedExercises);
  showRoutineBuilder(false);
  alert("Rutina creada y guardada con éxito.");
}

function poblarCustomRoutinesList() {
  const container = document.getElementById("custom-routines-list");
  if (!container) return;

  container.innerHTML = "";
  const rutinas = db.getRutinasPersonalizadas();

  if (rutinas.length === 0) {
    container.innerHTML = `
      <div class="card glass text-center">
        <p class="card-text"><i class="fa-solid fa-folder-open"></i> Aún no tienes rutinas personalizadas creadas. ¡Crea una pulsando el botón superior!</p>
      </div>`;
    return;
  }

  rutinas.forEach(r => {
    // Listar ejercicios
    const exString = r.ejercicios.map(e => `${e.ejercicio} (${e.series}x${e.repeticiones})`).join(", ");
    
    container.innerHTML += `
      <div class="routine-card" style="border-color: rgba(255, 85, 0, 0.15)">
        <div class="routine-icon-box" style="background: rgba(255, 85, 0, 0.08); color: var(--primary-light);">
          <i class="fa-solid fa-list-check"></i>
        </div>
        <div class="routine-info" onclick="startCustomRoutine(${r.id})">
          <h4 class="routine-name">${r.nombre}</h4>
          <span class="routine-desc" style="white-space: normal; overflow: visible; display:-webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;">${exString}</span>
        </div>
        <div style="display:flex; gap: 8px;">
          <button class="btn-primary btn-small" onclick="startCustomRoutine(${r.id})"><i class="fa-solid fa-play"></i> Iniciar</button>
          <button class="goal-delete-btn" onclick="eliminarRutinaUsuario(${r.id})"><i class="fa-solid fa-trash"></i></button>
        </div>
      </div>
    `;
  });
}

function eliminarRutinaUsuario(id) {
  if (confirm("¿Estás seguro de que deseas eliminar esta rutina?")) {
    db.eliminarRutinaPersonalizada(id);
    poblarCustomRoutinesList();
  }
}

// --- TRACKER DE RUNTINA EN VIVO TÁCTIL ---

function startCustomRoutine(id) {
  const rutinas = db.getRutinasPersonalizadas();
  const r = rutinas.find(x => x.id === id);
  if (!r) return;

  activeSessionRoutine = r;
  activeSessionLogs = {};

  // Inicializar series a completar en memoria
  r.ejercicios.forEach(ex => {
    activeSessionLogs[ex.ejercicio] = [];
    for (let i = 1; i <= ex.series; i++) {
      activeSessionLogs[ex.ejercicio].push({
        set: i,
        peso: ex.peso,
        reps: ex.repeticiones,
        completado: false
      });
    }
  });

  // Mostrar el tracker activo
  document.getElementById("routine-main-view").classList.add("hidden");
  document.getElementById("routine-active-tracker-view").classList.remove("hidden");
  
  document.getElementById("tracker-routine-name").innerHTML = `<i class="fa-solid fa-dumbbell"></i> ${r.nombre}`;
  
  // Renderizar la grilla de tachado
  poblarActiveTrackerUI();
}

function poblarActiveTrackerUI() {
  const container = document.getElementById("tracker-exercises-container");
  container.innerHTML = "";

  Object.keys(activeSessionLogs).forEach(exName => {
    const sets = activeSessionLogs[exName];
    
    let exCard = `
      <div class="tracker-exercise-card mt-20">
        <h4 class="tracker-ex-title">${exName}</h4>
        <div class="tracker-sets-list">
    `;

    sets.forEach((setObj, index) => {
      const idUnico = `chk-${exName.replace(/\s+/g, '-')}-${setObj.set}`;
      exCard += `
        <div class="tracker-set-row ${setObj.completado ? 'completed' : ''}" id="row-${idUnico}">
          <span>Set ${setObj.set}</span>
          <div class="form-group" style="margin:0;">
            <input type="number" value="${setObj.peso}" step="0.5" class="form-input btn-small" style="padding:4px 8px; width:70px;" onchange="updateActiveTrackerValue('${exName}', ${setObj.set}, 'peso', this.value)">
          </div>
          <div class="form-group" style="margin:0;">
            <input type="number" value="${setObj.reps}" class="form-input btn-small" style="padding:4px 8px; width:60px;" onchange="updateActiveTrackerValue('${exName}', ${setObj.set}, 'reps', this.value)">
          </div>
          <div class="goal-checkbox ${setObj.completado ? 'checked' : ''}" onclick="toggleActiveTrackerSet('${exName}', ${setObj.set}, '${idUnico}')"></div>
        </div>
      `;
    });

    exCard += `
        </div>
      </div>
    `;
    container.innerHTML += exCard;
  });
}

function updateActiveTrackerValue(exName, setNum, field, val) {
  const sets = activeSessionLogs[exName];
  const setObj = sets.find(s => s.set === setNum);
  if (setObj) {
    if (field === "peso") {
      setObj.peso = parseFloat(val);
    } else {
      setObj.reps = parseInt(val);
    }
  }
}

function toggleActiveTrackerSet(exName, setNum, idUnico) {
  const sets = activeSessionLogs[exName];
  const setObj = sets.find(s => s.set === setNum);
  if (setObj) {
    setObj.completado = !setObj.completado;
    
    // Reproducir un pitido rápido de éxito
    if (setObj.completado) {
      playBeepSound(800, 0.05);
    }

    poblarActiveTrackerUI();
  }
}

function cancelActiveWorkout() {
  if (confirm("¿Estás seguro de que deseas cancelar la sesión activa? Se perderán las series hechas.")) {
    document.getElementById("routine-main-view").classList.remove("hidden");
    document.getElementById("routine-active-tracker-view").classList.add("hidden");
    activeSessionRoutine = null;
    activeSessionLogs = {};
  }
}

function finishActiveWorkout() {
  let guardadosCount = 0;
  
  // Guardar todas las series completadas en la base de datos
  Object.keys(activeSessionLogs).forEach(exName => {
    const sets = activeSessionLogs[exName];
    sets.forEach(setObj => {
      if (setObj.completado) {
        db.addSeguimiento(exName, setObj.peso, setObj.reps, `Serie ${setObj.set} de la rutina: ${activeSessionRoutine.nombre}`);
        guardadosCount++;
      }
    });
  });

  if (guardadosCount === 0) {
    alert("No has completado ninguna serie de tu rutina activa.");
    return;
  }

  // Resetear
  document.getElementById("routine-main-view").classList.remove("hidden");
  document.getElementById("routine-active-tracker-view").classList.add("hidden");
  activeSessionRoutine = null;
  activeSessionLogs = {};

  alert(`¡Felicidades! Entrenamiento finalizado. Se han registrado ${guardadosCount} series en tu bitácora de progreso.`);
  actualizarDashboardUI();
}


// ==========================================
// RETOS VIEW LOGIC (CROSSFIT, RUNNING & COMBA)
// ==========================================

function actualizarRetosUI() {
  // 1. Cargar Retos de Running
  const runningContainer = document.getElementById("running-challenges-container");
  runningContainer.innerHTML = "";
  
  const retosDb = db.getRetosCompletados();

  algo.RUNNING_CHALLENGES.forEach(r => {
    const completado = retosDb[r.id];
    runningContainer.innerHTML += `
      <div class="challenge-card ${completado ? 'highlight-border' : ''}">
        ${completado ? `<i class="fa-solid fa-medal challenge-badge-medal"></i>` : ""}
        <div class="challenge-header">
          <h4 class="challenge-title">${r.name} (${r.distance}K)</h4>
        </div>
        <p class="challenge-desc">${r.desc}</p>
        <div class="challenge-footer">
          <span class="challenge-record">${completado ? `<i class="fa-solid fa-stopwatch"></i> Récord: ${completado.marca}` : "Pendiente"}</span>
          <button class="${completado ? 'btn-secondary btn-small' : 'btn-primary btn-small'}" onclick="abrirModalRegistrarReto('running', '${r.id}', '${r.name}')">
            ${completado ? 'Mejorar Marca' : 'Completar Reto'}
          </button>
        </div>
      </div>
    `;
  });

  // 2. Cargar Retos de Comba
  const combaContainer = document.getElementById("comba-challenges-container");
  combaContainer.innerHTML = "";

  algo.COMBA_CHALLENGES.forEach(c => {
    const completado = retosDb[c.id];
    combaContainer.innerHTML += `
      <div class="challenge-card ${completado ? 'highlight-border' : ''}">
        ${completado ? `<i class="fa-solid fa-medal challenge-badge-medal"></i>` : ""}
        <div class="challenge-header">
          <h4 class="challenge-title">${c.name}</h4>
        </div>
        <p class="challenge-desc">${c.desc}</p>
        <div class="challenge-footer">
          <span class="challenge-record">${completado ? `<i class="fa-solid fa-circle-check"></i> Marca: ${completado.marca}` : "Pendiente"}</span>
          <button class="${completado ? 'btn-secondary btn-small' : 'btn-primary btn-small'}" onclick="abrirModalRegistrarReto('comba', '${c.id}', '${c.name}')">
            ${completado ? 'Actualizar' : 'Marcar Completado'}
          </button>
        </div>
      </div>
    `;
  });

  // 3. Cargar CrossFit WODs
  const crossfitContainer = document.getElementById("crossfit-wods-container");
  crossfitContainer.innerHTML = "";

  algo.CROSSFIT_WODS.forEach(w => {
    const completado = retosDb[w.id];
    crossfitContainer.innerHTML += `
      <div class="wod-card ${completado ? 'highlight-border' : ''}">
        <div class="wod-card-header">
          <h4 class="wod-card-title">${w.name}</h4>
          <span class="wod-type-chip">${w.type}</span>
        </div>
        <div class="wod-description">
          ${w.desc}
        </div>
        <p class="challenge-desc" style="margin-bottom:0; font-style:italic;">Instrucciones: ${w.instructions}</p>
        <div class="challenge-footer" style="margin-top:10px;">
          <span class="challenge-record" style="color:var(--primary-light);">
            ${completado ? `<i class="fa-solid fa-trophy text-purple"></i> Marca Lograda: ${completado.marca}` : "Aún no realizado"}
          </span>
          <div style="display:flex; gap: 8px;">
            <button class="btn-secondary btn-small" onclick="abrirModalRegistrarReto('crossfit', '${w.id}', '${w.name}')">
              ${completado ? 'Actualizar Marca' : 'Registrar Marca'}
            </button>
          </div>
        </div>
      </div>
    `;
  });
}

function abrirModalRegistrarReto(type, id, name) {
  document.getElementById("challenge-modal-title").textContent = `Registrar ${name}`;
  document.getElementById("challenge-modal-type-input").value = type;
  document.getElementById("challenge-modal-id-input").value = id;
  
  const descBox = document.getElementById("challenge-modal-description-box");
  const inputScore = document.getElementById("challenge-log-score");
  
  document.getElementById("challenge-log-date").value = new Date().toISOString().split("T")[0];
  
  if (type === "running") {
    descBox.innerHTML = "<p class='card-text'><i class='fa-solid fa-running'></i> Registra el tiempo exacto que tardaste en completar la distancia (Ejemplo: <strong>23:45</strong> en formato mm:ss).</p>";
    inputScore.placeholder = "Minutos:Segundos (Ej: 24:15)";
  } else if (type === "comba") {
    descBox.innerHTML = "<p class='card-text'><i class='fa-solid fa-arrow-up-9-1'></i> Registra la marca acumulada, tiempo o indica 'Completado' en tu reto de comba.</p>";
    inputScore.placeholder = "Ej: 100 saltos o Completado";
  } else {
    // CrossFit WOD
    const WOD = algo.CROSSFIT_WODS.find(x => x.id === id);
    descBox.innerHTML = `<p class='card-text'><i class='fa-solid fa-fire'></i> Escribe la puntuación obtenida en el WOD ${name}. (Ej: <strong>14 rondas</strong> para Cindy, o <strong>22:15 minutos</strong> para Murph).</p>`;
    inputScore.placeholder = "Ej: 15 rondas o 24:12 mins";
  }

  inputScore.value = "";
  openModal("modal-log-challenge");
}

function guardarMarcaRetoLogueada() {
  const type = document.getElementById("challenge-modal-type-input").value;
  const id = document.getElementById("challenge-modal-id-input").value;
  const marca = document.getElementById("challenge-log-score").value;
  const fecha = document.getElementById("challenge-log-date").value;

  if (!marca) {
    alert("Por favor, introduce una marca.");
    return;
  }

  // Guardar en la base de datos
  db.completarReto(id, marca, fecha);
  closeModal("modal-log-challenge");
  actualizarRetosUI();
  
  // Pitido largo triunfal
  playBeepSound(900, 0.3);
  
  alert("¡Felicitaciones! Reto registrado de forma local.");
}

// ==========================================
// PROGRESO VIEW: GRÁFICOS (CHART.JS)
// ==========================================

function renderProgressCharts() {
  const progressSelect = document.getElementById("progress-exercise-select");
  if (!progressSelect) return;
  
  const exerciseName = progressSelect.value;
  const historial = db.getHistorial();
  
  const logsEjercicio = historial.filter(item => item.ejercicio === exerciseName)
                                 .sort((a, b) => new Date(a.fecha) - new Date(b.fecha));

  const labelsRm = [];
  const datosRm = [];
  const datosPesoLevantado = [];

  logsEjercicio.forEach(item => {
    const fecha = new Date(item.fecha).toLocaleDateString("es-ES", { day: 'numeric', month: 'short' });
    const RM = item.repeticiones === 0 ? item.peso : item.peso * (36 / (37 - item.repeticiones));
    labelsRm.push(fecha);
    datosRm.push(Math.round(RM * 10) / 10);
    datosPesoLevantado.push(item.peso);
  });

  const ctxRm = document.getElementById("rmProgressChart").getContext("2d");
  
  if (rmChartInstance) {
    rmChartInstance.destroy();
  }

  rmChartInstance = new Chart(ctxRm, {
    type: "line",
    data: {
      labels: labelsRm.length > 0 ? labelsRm : ["Sin datos"],
      datasets: [
        {
          label: "1RM Teórico Estimado (kg)",
          data: datosRm.length > 0 ? datosRm : [0],
          borderColor: "#FF5500",
          backgroundColor: "rgba(255, 85, 0, 0.1)",
          borderWidth: 3,
          tension: 0.3,
          fill: true,
          pointRadius: 4,
          pointBackgroundColor: "#FF5500"
        },
        {
          label: "Peso Efectivo Levantado (kg)",
          data: datosPesoLevantado.length > 0 ? datosPesoLevantado : [0],
          borderColor: "#00B0FF",
          borderWidth: 2,
          borderDash: [5, 5],
          tension: 0.1,
          fill: false,
          pointRadius: 2,
          pointBackgroundColor: "#00B0FF"
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: { color: "#FFF", font: { family: "Outfit" } }
        }
      },
      scales: {
        x: { grid: { color: "rgba(255,255,255,0.05)" }, ticks: { color: "rgba(255,255,255,0.6)" } },
        y: { grid: { color: "rgba(255,255,255,0.05)" }, ticks: { color: "rgba(255,255,255,0.6)" } }
      }
    }
  });

  // Peso Corporal
  const logsPeso = historial.filter(item => item.ejercicio === "peso_corporal" || item.tipo === "peso")
                            .sort((a, b) => new Date(a.fecha) - new Date(b.fecha));
  
  const labelsPeso = [];
  const datosPeso = [];

  if (logsPeso.length === 0) {
    const perfil = db.getPerfil();
    labelsPeso.push("Hoy");
    datosPeso.push(perfil.peso);
  } else {
    logsPeso.forEach(item => {
      const fecha = new Date(item.fecha).toLocaleDateString("es-ES", { day: 'numeric', month: 'short' });
      labelsPeso.push(fecha);
      datosPeso.push(item.valor || item.peso);
    });
  }

  const ctxWeight = document.getElementById("weightProgressChart").getContext("2d");
  
  if (weightChartInstance) {
    weightChartInstance.destroy();
  }

  weightChartInstance = new Chart(ctxWeight, {
    type: "line",
    data: {
      labels: labelsPeso,
      datasets: [
        {
          label: "Peso Corporal (kg)",
          data: datosPeso,
          borderColor: "#FF8500",
          backgroundColor: "rgba(255, 133, 0, 0.1)",
          borderWidth: 3,
          tension: 0.2,
          fill: true,
          pointRadius: 4,
          pointBackgroundColor: "#FF8500"
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false }
      },
      scales: {
        x: { grid: { color: "rgba(255,255,255,0.05)" }, ticks: { color: "rgba(255,255,255,0.6)" } },
        y: { grid: { color: "rgba(255,255,255,0.05)" }, ticks: { color: "rgba(255,255,255,0.6)" } }
      }
    }
  });
}

function actualizarTablaHistorial() {
  const historial = db.getHistorial();
  const body = document.getElementById("history-table-body");
  if (!body) return;

  body.innerHTML = "";

  if (historial.length === 0) {
    body.innerHTML = `<tr><td colspan="6" class="text-center">No hay entrenamientos registrados aún.</td></tr>`;
    return;
  }

  const ordenado = [...historial].reverse();

  ordenado.forEach(item => {
    const fecha = new Date(item.fecha).toLocaleDateString("es-ES", { day: '2-digit', month: '2-digit', year: '2-digit' });
    const RM = item.repeticiones === 0 ? item.peso : item.peso * (36 / (37 - item.repeticiones));

    body.innerHTML += `
      <tr>
        <td>${fecha}</td>
        <td><strong>${item.ejercicio}</strong></td>
        <td>${item.peso} kg</td>
        <td>${item.repeticiones > 0 ? item.repeticiones : "Calibración"}</td>
        <td class="color-purple">${RM.toFixed(1)} kg</td>
        <td class="text-center"><i class="fa-solid fa-trash-can" onclick="eliminarFilaHistorial(${item.id})"></i></td>
      </tr>
    `;
  });
}

function eliminarFilaHistorial(id) {
  if (confirm("¿Estás seguro de que deseas eliminar este registro?")) {
    db.eliminarSeguimiento(id);
    actualizarTablaHistorial();
    renderProgressCharts();
    actualizarDashboardUI();
  }
}

function clearAllHistorial() {
  if (confirm("¡ATENCIÓN! Se eliminará TODO tu historial de forma permanente.")) {
    localStorage.setItem("f365_historial", JSON.stringify([]));
    actualizarTablaHistorial();
    renderProgressCharts();
    actualizarDashboardUI();
  }
}

// ==========================================
// BIOMETRÍA & PERFIL FUSIONADOS EN AJUSTES
// ==========================================

function precargarDatosBiometricos() {
  const perfil = db.getPerfil();
  if (perfil.peso) document.getElementById("bio-weight").value = perfil.peso;
  if (perfil.altura) document.getElementById("bio-height").value = perfil.altura;
}

function ejecutarCalculosBiometricos() {
  const sexo = document.getElementById("bio-gender").value;
  const edad = parseInt(document.getElementById("bio-age").value);
  const altura = parseFloat(document.getElementById("bio-height").value);
  const peso = parseFloat(document.getElementById("bio-weight").value);
  const actividad = document.getElementById("bio-activity").value;

  if (isNaN(altura) || isNaN(peso) || isNaN(edad)) {
    alert("Por favor, introduce valores correctos.");
    return;
  }

  // 1. Calcular IMC
  const alturaM = altura / 100;
  const imc = peso / (alturaM * alturaM);
  
  let categoriaImc = "Normal";
  let badgeClass = "bg-gradient-purple";
  if (imc < 18.5) {
    categoriaImc = "Bajo peso";
    badgeClass = "btn-secondary";
  } else if (imc < 25) {
    categoriaImc = "Normal";
    badgeClass = "bg-gradient-purple";
  } else if (imc < 30) {
    categoriaImc = "Sobrepeso";
    badgeClass = "bg-gradient-coral";
  } else {
    categoriaImc = "Obesidad";
    badgeClass = "btn-danger";
  }

  // 2. Calcular Grasa Corporal (YMCA)
  let grasa = 0;
  if (sexo === "masculino") {
    grasa = (1.20 * imc) + (0.23 * edad) - 16.2;
  } else {
    grasa = (1.20 * imc) + (0.23 * edad) - 5.4;
  }
  grasa = Math.max(3, Math.min(60, grasa));

  // 3. Masa muscular
  const masaGrasa = peso * (grasa / 100);
  const masaMuscular = peso - masaGrasa;

  // 4. Calorías (Mifflin-St Jeor)
  let tmb = (10 * peso) + (6.25 * altura) - (5 * edad);
  if (sexo === "masculino") {
    tmb += 5;
  } else {
    tmb -= 161;
  }

  const factorActividad = {
    sedentario: 1.2,
    ligero: 1.375,
    moderado: 1.55,
    activo: 1.725,
    muy_activo: 1.9
  };

  const calorias = tmb * factorActividad[actividad];

  // Mostrar
  document.getElementById("biometric-results").classList.remove("hidden");
  
  document.getElementById("bio-result-imc").textContent = imc.toFixed(1);
  const badgeImc = document.getElementById("bio-badge-imc");
  badgeImc.textContent = categoriaImc;
  badgeImc.className = `metric-badge ${badgeClass}`;

  document.getElementById("bio-result-grasa").textContent = `${grasa.toFixed(1)}%`;
  document.getElementById("bio-result-musculo").textContent = `Masa Magra: ${masaMuscular.toFixed(1)} kg`;
  document.getElementById("bio-result-calorias").textContent = `${Math.round(calorias)} kcal`;

  // Renderizar Doughnut
  const ctxComp = document.getElementById("bodyCompositionChart").getContext("2d");
  
  if (bodyCompChartInstance) {
    bodyCompChartInstance.destroy();
  }

  bodyCompChartInstance = new Chart(ctxComp, {
    type: "doughnut",
    data: {
      labels: ["Masa Magra (kg)", "Grasa Corporal (kg)"],
      datasets: [{
        data: [Math.round(masaMuscular), Math.round(masaGrasa)],
        backgroundColor: ["#00E676", "#FF4D00"],
        borderColor: "rgba(6, 7, 10, 0.8)",
        borderWidth: 3
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "bottom",
          labels: { color: "#FFF", font: { family: "Outfit" } }
        }
      },
      cutout: "70%"
    }
  });

  // Guardar datos
  const perfil = db.getPerfil();
  perfil.peso = peso;
  perfil.altura = altura;
  db.savePerfil(perfil);

  db.addSeguimiento("peso_corporal", peso, 0, "Registro biométrico");
}

// ==========================================
// GALERÍA DE PROGRESO VISUAL
// ==========================================

let selectedPhotoFileBase64 = null;

function previewGalleryImage(event) {
  const file = event.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = (e) => {
    selectedPhotoFileBase64 = e.target.result;
    document.getElementById("preview-img").src = selectedPhotoFileBase64;
    document.getElementById("gallery-preview").classList.remove("hidden");
  };
  reader.readAsDataURL(file);
}

async function subirFotoProgreso() {
  const categoria = document.getElementById("gallery-category").value;
  const desc = document.getElementById("gallery-desc").value;

  if (!selectedPhotoFileBase64) {
    alert("Por favor, selecciona una foto primero.");
    return;
  }

  try {
    await db.guardarFoto(selectedPhotoFileBase64, desc, categoria);
    
    document.getElementById("gallery-file").value = "";
    document.getElementById("gallery-desc").value = "";
    document.getElementById("gallery-preview").classList.add("hidden");
    selectedPhotoFileBase64 = null;

    alert("Foto guardada con éxito en tu móvil.");
    actualizarGaleriaUI();
  } catch (e) {
    alert("Error: " + e);
  }
}

async function actualizarGaleriaUI() {
  const grid = document.getElementById("photos-grid");
  if (!grid) return;

  grid.innerHTML = "";
  
  try {
    const fotos = await db.obtenerFotos();

    if (fotos.length === 0) {
      grid.innerHTML = `<div class="card glass text-center" style="grid-column: span 3;"><p class="card-text"><i class="fa-solid fa-images"></i> No tienes fotos aún. ¡Sube tu primera foto!</p></div>`;
      return;
    }

    const comp1 = document.getElementById("compare-photo-1");
    const comp2 = document.getElementById("compare-photo-2");
    comp1.innerHTML = `<option value="">Elige foto inicial...</option>`;
    comp2.innerHTML = `<option value="">Elige foto reciente...</option>`;

    fotos.forEach(f => {
      const fechaStr = new Date(f.fecha).toLocaleDateString("es-ES", { day: '2-digit', month: '2-digit', year: 'numeric' });
      const label = `${fechaStr} - ${capitalizar(f.categoria)}`;
      
      comp1.innerHTML += `<option value="${f.id}">${label}</option>`;
      comp2.innerHTML += `<option value="${f.id}">${label}</option>`;

      grid.innerHTML += `
        <div class="photo-card" id="photo-item-${f.id}">
          <span class="photo-card-badge">${capitalizar(f.categoria)}</span>
          <img src="${f.imagen}" alt="Progreso">
          <button class="photo-delete-btn" onclick="eliminarFotoGaleria(${f.id})"><i class="fa-solid fa-xmark"></i></button>
          <div class="photo-card-body">
            <span class="photo-card-date">${fechaStr}</span>
            <p class="photo-card-desc">${f.descripcion || "Evolución"}</p>
          </div>
        </div>
      `;
    });
  } catch (e) {
    console.error(e);
  }
}

async function eliminarFotoGaleria(id) {
  if (confirm("¿Estás seguro de que deseas eliminar esta foto?")) {
    await db.eliminarFoto(id);
    actualizarGaleriaUI();
  }
}

function openPhotoComparison() {
  openModal("modal-photo-comparison");
}

async function updateComparisonPhotos() {
  const id1 = parseInt(document.getElementById("compare-photo-1").value);
  const id2 = parseInt(document.getElementById("compare-photo-2").value);

  const img1 = document.getElementById("compare-img-1");
  const img2 = document.getElementById("compare-img-2");
  const placeholder1 = document.getElementById("placeholder-1");
  const placeholder2 = document.getElementById("placeholder-2");

  try {
    const fotos = await db.obtenerFotos();
    
    const f1 = fotos.find(f => f.id === id1);
    if (f1) {
      img1.src = f1.imagen;
      img1.classList.remove("hidden");
      placeholder1.classList.add("hidden");
      document.getElementById("compare-label-1").textContent = `Antes: ${new Date(f1.fecha).toLocaleDateString()}`;
    } else {
      img1.classList.add("hidden");
      placeholder1.classList.remove("hidden");
      document.getElementById("compare-label-1").textContent = "Antes";
    }

    const f2 = fotos.find(f => f.id === id2);
    if (f2) {
      img2.src = f2.imagen;
      img2.classList.remove("hidden");
      placeholder2.classList.add("hidden");
      document.getElementById("compare-label-2").textContent = `Después: ${new Date(f2.fecha).toLocaleDateString()}`;
    } else {
      img2.classList.add("hidden");
      placeholder2.classList.remove("hidden");
      document.getElementById("compare-label-2").textContent = "Después";
    }
  } catch (e) {
    console.error(e);
  }
}

// ==========================================
// AJUSTES & PROFILE & MEDIDAS
// ==========================================

function actualizarAjustesUI() {
  const perfil = db.getPerfil();
  const config = db.getConfig();

  document.getElementById("prof-nombre").value = perfil.nombre;
  document.getElementById("prof-apellidos").value = perfil.apellidos || "";
  document.getElementById("prof-units").value = perfil.sistema_unidades;
  document.getElementById("prof-theme").value = config.tema;

  document.getElementById("meas-brazo").value = perfil.brazo || "";
  document.getElementById("meas-pierna").value = perfil.pierna || "";
  document.getElementById("meas-cintura").value = perfil.cintura || "";
  document.getElementById("meas-cadera").value = perfil.cadera || "";
}

function guardarPerfilGeneral() {
  const nombre = document.getElementById("prof-nombre").value;
  const apellidos = document.getElementById("prof-apellidos").value;
  const units = document.getElementById("prof-units").value;
  
  if (!nombre) {
    alert("Introduce tu nombre.");
    return;
  }

  const perfil = db.getPerfil();
  perfil.nombre = nombre;
  perfil.apellidos = apellidos;
  perfil.sistema_unidades = units;
  db.savePerfil(perfil);

  alert("Perfil actualizado correctamente.");
  actualizarInfoPerfilUI();
}

function guardarMedidasMusculares() {
  const brazo = parseFloat(document.getElementById("meas-brazo").value);
  const pierna = parseFloat(document.getElementById("meas-pierna").value);
  const cintura = parseFloat(document.getElementById("meas-cintura").value);
  const cadera = parseFloat(document.getElementById("meas-cadera").value);

  const perfil = db.getPerfil();
  if (!isNaN(brazo)) perfil.brazo = brazo;
  if (!isNaN(pierna)) perfil.pierna = pierna;
  if (!isNaN(cintura)) perfil.cintura = cintura;
  if (!isNaN(cadera)) perfil.cadera = cadera;
  
  db.savePerfil(perfil);
  alert("Contornos guardados con éxito.");
}

function changeTheme(themeValue) {
  const config = db.getConfig();
  config.tema = themeValue;
  db.saveConfig(config);
  document.body.className = `theme-${themeValue}`;
}

async function handleImportBackup(event) {
  const file = event.target.files[0];
  if (!file) return;

  if (confirm("¡ATENCIÓN! La importación de un backup reemplazará todos tus datos y fotos actuales.")) {
    try {
      await db.importarBackup(file);
      alert("¡Copia de seguridad restaurada correctamente!");
      window.location.reload();
    } catch (e) {
      alert("Error: " + e);
    }
  }
}

// ==========================================
// AUXILIARES DE MODALES
// ==========================================

function openModal(modalId) {
  document.getElementById(modalId).classList.add("active");
}

function closeModal(modalId) {
  document.getElementById(modalId).classList.remove("active");
}

function openRmCalculator() {
  openModal("modal-rm-calculator");
  
  const calcWeight = document.getElementById("calc-weight");
  const calcReps = document.getElementById("calc-reps");
  
  const recalcular = () => {
    const w = parseFloat(calcWeight.value);
    const r = parseInt(calcReps.value);
    if (!isNaN(w) && !isNaN(r)) {
      const rm = w * (36 / (37 - r));
      document.getElementById("rm-calc-result").textContent = `${rm.toFixed(1)} kg`;
    }
  };

  calcWeight.addEventListener("input", recalcular);
  calcReps.addEventListener("input", recalcular);
  recalcular();
}

function applyCalculatedRm() {
  const res = parseFloat(document.getElementById("rm-calc-result").textContent);
  document.getElementById("gen-rm").value = res.toFixed(1);
  closeModal("modal-rm-calculator");
}

function crearNuevoObjetivo() {
  const tipo = document.getElementById("goal-type").value;
  const val = parseFloat(document.getElementById("goal-val").value);
  const fin = document.getElementById("goal-date").value;

  if (isNaN(val) || !fin) {
    alert("Rellena todos los campos.");
    return;
  }

  db.addObjetivo(tipo, val, fin);
  closeModal("modal-nuevo-objetivo");
  actualizarDashboardUI();
}

// ==========================================
// SINTETIZADOR DE AUDIO WEB ( Pitidos Offline )
// ==========================================

const audioCtx = new (window.AudioContext || window.webkitAudioContext)();

function playBeepSound(frequency, duration) {
  try {
    if (audioCtx.state === 'suspended') {
      audioCtx.resume();
    }
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();

    osc.type = "sine";
    osc.frequency.setValueAtTime(frequency, audioCtx.currentTime);
    gain.gain.setValueAtTime(0.2, audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.00001, audioCtx.currentTime + duration);

    osc.connect(gain);
    gain.connect(audioCtx.destination);

    osc.start();
    osc.stop(audioCtx.currentTime + duration);
  } catch (e) {
    console.warn("Audio Context bloqueado", e);
  }
}

// ==========================================
// TEMPORIZADOR TABATA INDEPENDIENTE
// ==========================================

function openTimerTab() {
  openModal("modal-tabata");
  document.getElementById("tabata-setup").classList.remove("hidden");
  document.getElementById("tabata-active").classList.add("hidden");
}

function closeTabataTimer() {
  clearInterval(tabataInterval);
  tabataInterval = null;
  closeModal("modal-tabata");
}

function startTabataTimer() {
  tabataSettings = {
    work: parseInt(document.getElementById("tabata-work").value),
    rest: parseInt(document.getElementById("tabata-rest").value),
    rounds: parseInt(document.getElementById("tabata-rounds").value),
    prep: parseInt(document.getElementById("tabata-prep").value)
  };

  document.getElementById("tabata-setup").classList.add("hidden");
  document.getElementById("tabata-active").classList.remove("hidden");

  tabataRound = 1;
  tabataState = "prep";
  tabataTimeLeft = tabataSettings.prep;
  tabataIsPaused = false;
  
  ejecutarTabataTick();
  tabataInterval = setInterval(ejecutarTabataTick, 1000);
}

function toggleTabataPause() {
  tabataIsPaused = !tabataIsPaused;
  const btn = document.getElementById("tabata-pause-btn");
  if (tabataIsPaused) {
    btn.innerHTML = `<i class="fa-solid fa-play"></i> Reanudar`;
    btn.className = "btn-primary btn-small";
  } else {
    btn.innerHTML = `<i class="fa-solid fa-pause"></i> Pausar`;
    btn.className = "btn-secondary btn-small";
  }
}

function stopTabataTimer() {
  clearInterval(tabataInterval);
  tabataInterval = null;
  document.getElementById("tabata-setup").classList.remove("hidden");
  document.getElementById("tabata-active").classList.add("hidden");
}

function ejecutarTabataTick() {
  if (tabataIsPaused) return;

  const display = document.getElementById("tabata-countdown");
  const stateLabel = document.getElementById("tabata-current-state");
  const roundLabel = document.getElementById("tabata-current-round");

  display.textContent = tabataTimeLeft.toString().padStart(2, '0');
  roundLabel.textContent = `Ronda: ${tabataRound} / ${tabataSettings.rounds}`;

  if (tabataState === "prep") {
    stateLabel.textContent = "¡PREPÁRATE!";
    stateLabel.className = "tabata-status-label state-prep";
    display.style.color = "var(--warning)";
  } else if (tabataState === "work") {
    stateLabel.textContent = "¡TRABAJA!";
    stateLabel.className = "tabata-status-label state-work";
    display.style.color = "var(--success)";
  } else if (tabataState === "rest") {
    stateLabel.textContent = "DESCANSA";
    stateLabel.className = "tabata-status-label state-rest";
    display.style.color = "var(--secondary)";
  }

  if (tabataTimeLeft <= 3 && tabataTimeLeft > 0) {
    playBeepSound(600, 0.1);
  }

  if (tabataTimeLeft === 0) {
    playBeepSound(1000, 0.4);

    if (tabataState === "prep") {
      tabataState = "work";
      tabataTimeLeft = tabataSettings.work;
    } else if (tabataState === "work") {
      if (tabataRound < tabataSettings.rounds) {
        tabataState = "rest";
        tabataTimeLeft = tabataSettings.rest;
      } else {
        clearInterval(tabataInterval);
        tabataInterval = null;
        stateLabel.textContent = "¡TERMINADO!";
        display.textContent = "FIN";
        display.style.color = "var(--primary-light)";
        setTimeout(stopTabataTimer, 2000);
        return;
      }
    } else if (tabataState === "rest") {
      tabataRound++;
      tabataState = "work";
      tabataTimeLeft = tabataSettings.work;
    }
  } else {
    tabataTimeLeft--;
  }
}
