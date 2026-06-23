// algorithm.js - Algoritmo de Fuerza, WODs de CrossFit y Retos Aeróbicos de Fuerza365

class Exercise {
  constructor(name, weight, increment, maxReps = 12, exerciseType = "compound", targetMuscle = null, equipmentType = "libre", failureType = "controlled") {
    this.name = name;
    this.weight = weight; // Peso inicial de referencia
    this.increment = increment;
    this.maxReps = maxReps;
    this.exerciseType = exerciseType;   // compound, isolation, bodyweight
    this.targetMuscle = targetMuscle;   // piernas, pecho, espalda, hombros, biceps, triceps, abdominales, core
    this.equipmentType = equipmentType; // libre, maquina, corporal (FILTRO NUEVO SOLICITADO)
    this.failureType = failureType;     // controlled, failure, technical_failure
    
    this.oneRm = this.calculateOneRm();
    this.intensity = this.getInitialIntensity();
    this.volume = this.getInitialVolume();
    this.reps = this.getInitialReps();
    this.restDays = this.getRestDays();
    this.warmupSets = this.getWarmupSets();
    this.restBetweenSets = this.getRestBetweenSets();
  }

  // Calcular 1RM (Fórmula de Epley)
  calculateOneRm() {
    if (this.exerciseType === "bodyweight" || this.equipmentType === "corporal") {
      return this.weight;
    }
    return this.weight * (36 / (37 - this.maxReps));
  }

  // Series de calentamiento
  getWarmupSets() {
    const oneRm = this.oneRm;
    if (this.exerciseType === "compound") {
      return [
        { weight: Math.round((oneRm * 0.4) * 2) / 2, reps: 12 },
        { weight: Math.round((oneRm * 0.5) * 2) / 2, reps: 8 },
        { weight: Math.round((oneRm * 0.6) * 2) / 2, reps: 5 }
      ];
    } else {
      return [
        { weight: Math.round((oneRm * 0.5) * 2) / 2, reps: 12 },
        { weight: Math.round((oneRm * 0.6) * 2) / 2, reps: 8 }
      ];
    }
  }

  // Descanso sugerido
  getRestBetweenSets() {
    if (this.exerciseType === "compound") return 180;
    if (this.exerciseType === "isolation") return 90;
    return 60; // Corporal
  }

  getInitialIntensity() {
    if (this.equipmentType === "corporal") return 1.0;
    if (this.exerciseType === "compound") return 0.6;
    return 0.7;
  }

  getInitialVolume() {
    if (this.equipmentType === "corporal") return 4;
    if (this.exerciseType === "compound") return 3;
    return 4;
  }

  getInitialReps() {
    if (this.equipmentType === "corporal") return 15;
    if (this.exerciseType === "compound") return 8;
    return 12;
  }

  getRestDays() {
    return this.exerciseType === "compound" ? 2 : 1;
  }

  adjustIntensity(weekNumber) {
    let currentIntensity = this.intensity;
    if (this.equipmentType === "corporal") {
      if (weekNumber % 4 === 0) return currentIntensity * 0.8;
      if (weekNumber % 4 === 3) return Math.min(currentIntensity * 1.2, 1.2);
    } else {
      if (weekNumber % 4 === 0) return currentIntensity * 0.8;
      if (weekNumber % 4 === 3) return Math.min(currentIntensity * 1.1, 0.9);
    }
    return currentIntensity;
  }

  calculateWorkingWeight(weekNumber) {
    const adjustedIntensity = this.adjustIntensity(weekNumber);
    if (this.equipmentType === "corporal") {
      return this.weight * adjustedIntensity;
    }
    return this.oneRm * adjustedIntensity;
  }

  getSeriesStructure(weekNumber) {
    const workingWeight = Math.round(this.calculateWorkingWeight(weekNumber) * 2) / 2;
    const series = [];

    // Series de calentamiento
    if (this.equipmentType !== "corporal") {
      const warmups = this.getWarmupSets();
      warmups.forEach(w => {
        series.push({
          weight: Math.round(w.weight * 2) / 2,
          reps: w.reps,
          type: "warmup",
          rest: 60
        });
      });
    }

    // Series efectivas
    for (let i = 0; i < this.volume; i++) {
      series.push({
        weight: workingWeight,
        reps: this.reps,
        type: "working",
        rest: this.restBetweenSets,
        failure: this.failureType
      });
    }

    return series;
  }
}

// ==========================================
// LISTADO DE EJERCICIOS CON ATRIBUTO DE EQUIPAMIENTO EXPLICITO
// ==========================================
const DEFAULT_EXERCISES = [
  // PIERNAS
  new Exercise("Sentadillas", 50, 2.5, 12, "compound", "piernas", "libre", "controlled"),
  new Exercise("Peso Muerto Rumano", 40, 2.0, 12, "compound", "piernas", "libre", "controlled"),
  new Exercise("Zancadas con Mancuernas", 30, 1.0, 12, "compound", "piernas", "libre", "controlled"),
  new Exercise("Sentadilla Búlgara", 20, 1.0, 12, "compound", "piernas", "libre", "controlled"),
  new Exercise("Hip Thrust", 60, 2.5, 12, "compound", "piernas", "libre", "controlled"),
  new Exercise("Peso Muerto Sumo", 50, 2.5, 10, "compound", "piernas", "libre", "controlled"),
  
  new Exercise("Prensa de Piernas", 80, 2.5, 12, "compound", "piernas", "maquina", "controlled"),
  new Exercise("Extensiones de Cuádriceps", 30, 1.0, 15, "isolation", "piernas", "maquina", "technical_failure"),
  new Exercise("Curl de Isquiotibiales", 25, 1.0, 15, "isolation", "piernas", "maquina", "technical_failure"),
  new Exercise("Elevaciones de Gemelos en Prensa", 40, 1.0, 20, "isolation", "piernas", "maquina", "technical_failure"),
  
  new Exercise("Sentadillas al Aire (Sin peso)", 0, 1.0, 25, "compound", "piernas", "corporal", "controlled"),
  new Exercise("Zancadas Alternas", 0, 1.0, 20, "compound", "piernas", "corporal", "controlled"),

  // ESPALDA
  new Exercise("Peso Muerto Convencional", 60, 2.5, 8, "compound", "espalda", "libre", "controlled"),
  new Exercise("Remo con Barra", 30, 2.5, 10, "compound", "espalda", "libre", "controlled"),
  new Exercise("Remo con Mancuerna", 20, 1.0, 12, "compound", "espalda", "libre", "controlled"),
  
  new Exercise("Jalón al Pecho", 40, 1.5, 12, "compound", "espalda", "maquina", "controlled"),
  new Exercise("Remo en Máquina (Gironda)", 35, 1.5, 12, "compound", "espalda", "maquina", "controlled"),
  new Exercise("Hiperextensiones Lumbares", 10, 1.0, 15, "isolation", "espalda", "maquina", "technical_failure"),
  
  new Exercise("Dominadas Estrictas", 0, 1.0, 8, "bodyweight", "espalda", "corporal", "controlled"),
  new Exercise("Dominadas Agarre Neutro", 0, 1.0, 8, "bodyweight", "espalda", "corporal", "controlled"),
  new Exercise("Remo Invertido en Barra", 0, 1.0, 12, "bodyweight", "espalda", "corporal", "controlled"),

  // PECHO
  new Exercise("Press de Banca con Barra", 40, 2.5, 8, "compound", "pecho", "libre", "controlled"),
  new Exercise("Press Inclinado con Mancuernas", 14, 1.0, 12, "compound", "pecho", "libre", "controlled"),
  new Exercise("Aperturas con Mancuernas", 12, 1.0, 15, "isolation", "pecho", "libre", "technical_failure"),
  
  new Exercise("Crossover en Poleas (Pecho)", 15, 1.0, 15, "isolation", "pecho", "maquina", "technical_failure"),
  new Exercise("Press de Pecho en Máquina", 35, 2.0, 12, "compound", "pecho", "maquina", "controlled"),
  
  new Exercise("Flexiones de Pecho (Pushups)", 0, 1.0, 15, "bodyweight", "pecho", "corporal", "technical_failure"),
  new Exercise("Fondos en Paralelas", 0, 1.0, 12, "bodyweight", "pecho", "corporal", "controlled"),
  new Exercise("Flexiones Declinadas", 0, 1.0, 12, "bodyweight", "pecho", "corporal", "technical_failure"),

  // HOMBROS
  new Exercise("Press Militar con Barra", 20, 2.5, 8, "compound", "hombros", "libre", "controlled"),
  new Exercise("Elevaciones Laterales con Mancuerna", 8, 1.0, 15, "isolation", "hombros", "libre", "technical_failure"),
  new Exercise("Press Arnold con Mancuerna", 14, 1.0, 12, "compound", "hombros", "libre", "controlled"),
  
  new Exercise("Elevaciones Laterales en Polea", 10, 0.5, 15, "isolation", "hombros", "maquina", "technical_failure"),
  new Exercise("Face Pull en Polea", 15, 1.0, 15, "isolation", "hombros", "maquina", "technical_failure"),
  
  new Exercise("Flexiones de Hombro (Pike Pushups)", 0, 1.0, 10, "bodyweight", "hombros", "corporal", "technical_failure"),

  // BÍCEPS
  new Exercise("Curl de Bíceps con Barra", 15, 1.0, 12, "isolation", "biceps", "libre", "technical_failure"),
  new Exercise("Curl Martillo con Mancuernas", 14, 1.0, 12, "isolation", "biceps", "libre", "technical_failure"),
  new Exercise("Curl de Predicador con Mancuerna", 12, 1.0, 12, "isolation", "biceps", "libre", "technical_failure"),
  new Exercise("Curl Alternado con Mancuernas", 12, 1.0, 12, "isolation", "biceps", "libre", "technical_failure"),
  
  new Exercise("Curl de Bíceps en Polea Baja", 15, 1.0, 15, "isolation", "biceps", "maquina", "technical_failure"),

  // TRÍCEPS
  new Exercise("Press Francés con Barra", 18, 1.0, 12, "isolation", "triceps", "libre", "technical_failure"),
  new Exercise("Press de Banca Agarre Cerrado", 30, 2.0, 12, "compound", "triceps", "libre", "controlled"),
  
  new Exercise("Extensiones en Polea Alta con Barra", 25, 1.0, 15, "isolation", "triceps", "maquina", "technical_failure"),
  new Exercise("Extensiones en Polea con Cuerda", 20, 1.0, 15, "isolation", "triceps", "maquina", "technical_failure"),
  
  new Exercise("Fondos en Banco para Tríceps", 0, 1.0, 15, "bodyweight", "triceps", "corporal", "controlled"),

  // ABDOMINALES/CORE
  new Exercise("Crunches Abdominales", 0, 1.0, 20, "isolation", "abdominales", "corporal", "failure"),
  new Exercise("Elevaciones de Pierna en Suelo", 0, 1.0, 15, "bodyweight", "abdominales", "corporal", "technical_failure"),
  new Exercise("Russian Twist con Peso", 10, 1.0, 20, "isolation", "abdominales", "libre", "technical_failure"),
  new Exercise("Plancha Abdominal Estática", 0, 5.0, 60, "bodyweight", "core", "corporal", "controlled"),
  new Exercise("Plancha Lateral Izq/Der", 0, 5.0, 30, "bodyweight", "core", "corporal", "controlled")
];

// ==========================================
// RETOS AERÓBICOS: RUNNING Y COMBA (NUEVOS MÓDULOS)
// ==========================================

const RUNNING_CHALLENGES = [
  { id: "run-2k", distance: 2.0, name: "Reto Resistencia 2K", desc: "Completa 2 kilómetros corriendo sin detenerte. Excelente reto para activar tu sistema cardiovascular y ganar base aeróbica." },
  { id: "run-5k", distance: 5.0, name: "Reto Resistencia 5K", desc: "El gran hito de los 5 kilómetros. Corre a ritmo constante y registra tu tiempo de fondo inicial." },
  { id: "run-7k", distance: 7.0, name: "Reto Resistencia 7K", desc: "Sube de nivel. 7 kilómetros continuos. Controla tu respiración y ritmo de carrera." },
  { id: "run-10k", distance: 10.0, name: "Reto Resistencia 10K", desc: "El desafío rey de la resistencia general. 10 kilómetros. Requiere consistencia física y mental." },
  { id: "run-12k", distance: 12.0, name: "Reto Resistencia 12K", desc: "Fondo extremo. 12 kilómetros corriendo. Demuestra tu increíble capacidad de resistencia pulmonar." }
];

const COMBA_CHALLENGES = [
  { id: "comba-100", target: 100, name: "100 Saltos Seguidos", desc: "Realiza 100 saltos seguidos a la comba a pies juntos sin tropezar. Trabaja tu coordinación y pantorrillas." },
  { id: "comba-500", target: 500, name: "500 Saltos Totales", desc: "Completa 500 saltos totales en el menor tiempo posible. Se permite tropezar y continuar acumulando." },
  { id: "comba-hiit", target: 10, name: "HIIT Comba 10 Rondas", desc: "10 Rondas de 30 segundos de saltos a máxima velocidad y 30 segundos de descanso absoluto. ¡Quema calórica brutal!" }
];

// ==========================================
// RUNTINAS PREDEFINIDAS DE CROSSFIT (WODs CORPORALES)
// ==========================================

const CROSSFIT_WODS = [
  {
    id: "wod-cindy",
    name: "WOD Cindy (AMRAP)",
    type: "AMRAP 20 Minutos",
    desc: "Completa tantas rondas como sea posible en 20 minutos de:<br>• 5 Dominadas<br>• 10 Flexiones<br>• 15 Sentadillas",
    instructions: "Pon el temporizador en 20 minutos. Ve a ritmo constante sin llegar al fallo total al principio. ¡Registra tus rondas completadas!"
  },
  {
    id: "wod-chelsea",
    name: "WOD Chelsea (EMOM)",
    type: "EMOM 30 Minutos",
    desc: "Cada minuto al empezar el minuto, realiza:<br>• 5 Dominadas<br>• 10 Flexiones<br>• 15 Sentadillas",
    instructions: "Si terminas antes de acabar el minuto, descansas el tiempo restante. Si en algún momento no puedes completar las repeticiones dentro del minuto, el WOD pasa a ser un AMRAP por el tiempo restante. ¡El objetivo es aguantar los 30 minutos enteros!"
  },
  {
    id: "wod-angie",
    name: "WOD Angie (For Time)",
    type: "Por Tiempo",
    desc: "Completa por tiempo en el menor tiempo posible:<br>• 100 Dominadas<br>• 100 Flexiones<br>• 100 Abdominales Sit-ups<br>• 100 Sentadillas",
    instructions: "Debes terminar las 100 repeticiones completas de un ejercicio antes de poder pasar al siguiente. Divide las series de forma inteligente (ej: 10 series de 10) para evitar fatiga prematura."
  },
  {
    id: "wod-barbara",
    name: "WOD Barbara (Rondas)",
    type: "5 Rondas por Tiempo",
    desc: "Completa 5 rondas enteras en el menor tiempo posible de:<br>• 20 Dominadas<br>• 30 Flexiones<br>• 40 Abdominales Sit-ups<br>• 50 Sentadillas<br><strong>(Descansa 3 minutos exactos entre rondas)</strong>",
    instructions: "Tu tiempo de puntuación final es el tiempo total sin contar los intervalos de descanso. ¡Apunta tu marca total!"
  },
  {
    id: "wod-murph",
    name: "WOD Murph (Corporal)",
    type: "Por Tiempo",
    desc: "Completa en el menor tiempo posible:<br>• 1.6 km Correr<br>• 100 Dominadas<br>• 200 Flexiones<br>• 300 Sentadillas<br>• 1.6 km Correr",
    instructions: "Puedes particionar las dominadas, flexiones y sentadillas como desees (ej: 20 rondas de 5 dominadas, 10 flexiones, 15 sentadillas) para mantener el ritmo alto. ¡Comienzas y terminas corriendo!"
  }
];

// ==========================================
// FUNCIONES DEL ALGORITMO
// ==========================================

function calcularProgreso(pesoInicial, incremento, diasPorSemana, meses, exerciseType = "compound") {
  const progreso = [];
  let pesoActual = pesoInicial * 0.6;
  const totalDias = meses * 28;
  let diaContador = 1;
  let semanaActual = 1;
  let fatigaAcumulada = 0;

  for (let i = 0; i < totalDias; i++) {
    const mes = Math.floor(i / 28) + 1;
    const semana = Math.floor(i / 7) + 1;
    const diaSemana = (i % 7) + 1;
    
    const esDiaDescanso = diaSemana > diasPorSemana;
    let pesoTrabajo = pesoActual;
    
    if (!esDiaDescanso) {
      if (exerciseType === "bodyweight") {
        if (semana % 4 === 0) {
          pesoTrabajo *= 0.8;
          fatigaAcumulada = 0;
        } else if (semana % 4 === 3) {
          pesoTrabajo *= 1.2;
        }
      } else {
        if (semana % 4 === 0) {
          pesoTrabajo *= 0.8;
          fatigaAcumulada = 0;
        } else if (semana % 4 === 3) {
          pesoTrabajo *= 1.1;
        }
        
        if (fatigaAcumulada > 0.8) {
          pesoTrabajo *= 0.9;
          fatigaAcumulada = 0;
        }
      }
      
      if (semanaActual % 4 === 0 && (i % 7 === 0)) {
        if (exerciseType === "compound") {
          pesoActual += incremento;
        } else if (exerciseType === "isolation") {
          pesoActual += incremento * 0.8;
        }
      }
      
      fatigaAcumulada += 0.2;
      
      progreso.push({
        mes: mes,
        semana: semana,
        dia: diaSemana,
        tipo: "Entrenamiento",
        peso: Math.round(pesoTrabajo * 2) / 2,
        label: `Entreno: ${Math.round(pesoTrabajo * 2) / 2} kg`
      });
    } else {
      fatigaAcumulada = Math.max(0, fatigaAcumulada - 0.3);
      progreso.push({
        mes: mes,
        semana: semana,
        dia: diaSemana,
        tipo: "Descanso",
        peso: Math.round(pesoActual * 2) / 2,
        label: "Descanso"
      });
    }

    diaContador++;
    if (diaContador > diasPorSemana) {
      diaContador = 1;
      semanaActual++;
    }
  }

  return progreso;
}

function estimarTiempoParaPeso(pesoActual, pesoDeseado, incremento, diasPorSemana) {
  let pesoEstimado = pesoActual;
  let entrenamientos = 0;
  
  if (pesoDeseado <= pesoActual) return { meses: 0, dias: 0, totalEntrenamientos: 0 };

  while (pesoEstimado < pesoDeseado) {
    pesoEstimado += incremento;
    entrenamientos += 4;
  }

  const entrenosAlMes = diasPorSemana * 4;
  const mesesEstimados = Math.floor(entrenamientos / entrenosAlMes);
  const entrenosRestantes = entrenamientos % entrenosAlMes;
  const diasRestantes = Math.round(entrenosRestantes * (30 / entrenosAlMes));

  return {
    meses: mesesEstimados,
    dias: diasRestantes,
    totalEntrenamientos: entrenamientos
  };
}

// Exportar funciones globales
window.ExerciseManager = {
  Exercise,
  DEFAULT_EXERCISES,
  RUNNING_CHALLENGES,
  COMBA_CHALLENGES,
  CROSSFIT_WODS,
  calcularProgreso,
  estimarTiempoParaPeso
};

console.log("[algorithm.js] Registrado ExerciseManager expandido para CrossFit y Retos.");
