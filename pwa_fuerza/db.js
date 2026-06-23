// db.js - Gestor de Base de Datos Local Híbrido Expandido (Fuerza365)

const DB_NAME = "Fuerza365_Photos_DB";
const STORE_NAME = "evolution_photos";

class LocalDB {
  constructor() {
    this.initLocalStorage();
    this.initIndexedDB();
  }

  // ==========================================
  // LOCALSTORAGE: Para datos estructurados ligeros
  // ==========================================
  
  initLocalStorage() {
    // 1. Perfil del Usuario
    if (!localStorage.getItem("f365_perfil")) {
      const defaultPerfil = {
        nombre: "Campeón",
        apellidos: "",
        peso: 75.0,
        altura: 175.0,
        cintura: null,
        cadera: null,
        brazo: null,
        pierna: null,
        sistema_unidades: "metrico", // metrico o imperial
        idioma: "es"
      };
      localStorage.setItem("f365_perfil", JSON.stringify(defaultPerfil));
    }

    // 2. Configuración general
    if (!localStorage.getItem("f365_config")) {
      const defaultConfig = {
        tema: "oscuro",
        dias_entrenamiento: ["lunes", "miercoles", "viernes"],
        hora_entrenamiento: "09:00",
        duracion_entrenamiento: 60,
        nivel_entrenamiento: "intermedio"
      };
      localStorage.setItem("f365_config", JSON.stringify(defaultConfig));
    }

    // 3. Historial de Entrenamientos
    if (!localStorage.getItem("f365_historial")) {
      localStorage.setItem("f365_historial", JSON.stringify([]));
    }

    // 4. Objetivos del Dashboard
    if (!localStorage.getItem("f365_objetivos")) {
      const defaultObjetivos = [
        {
          id: 1,
          tipo: "peso",
          valor_objetivo: 70.0,
          fecha_inicio: new Date().toISOString().split("T")[0],
          fecha_fin: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split("T")[0],
          completado: false
        }
      ];
      localStorage.setItem("f365_objetivos", JSON.stringify(defaultObjetivos));
    }

    // 5. Ejercicios modificados / Pesos actuales de 1RM
    if (!localStorage.getItem("f365_ejercicios")) {
      localStorage.setItem("f365_ejercicios", JSON.stringify({}));
    }

    // 6. Rutinas personalizadas creadas por el usuario (NUEVO REQUERIMIENTO)
    if (!localStorage.getItem("f365_rutinas")) {
      localStorage.setItem("f365_rutinas", JSON.stringify([]));
    }

    // 7. Registro de retos de Running, Comba y CrossFit completados (NUEVO REQUERIMIENTO)
    if (!localStorage.getItem("f365_retos")) {
      localStorage.setItem("f365_retos", JSON.stringify({}));
    }
  }

  // --- MÉTODOS DE PERFIL ---
  getPerfil() {
    return JSON.parse(localStorage.getItem("f365_perfil"));
  }

  savePerfil(perfil) {
    localStorage.setItem("f365_perfil", JSON.stringify(perfil));
    return true;
  }

  // --- MÉTODOS DE CONFIGURACIÓN ---
  getConfig() {
    return JSON.parse(localStorage.getItem("f365_config"));
  }

  saveConfig(config) {
    localStorage.setItem("f365_config", JSON.stringify(config));
    return true;
  }

  // --- MÉTODOS DE HISTORIAL ---
  getHistorial() {
    return JSON.parse(localStorage.getItem("f365_historial"));
  }

  addSeguimiento(ejercicio, peso, repeticiones, notas = "") {
    const historial = this.getHistorial();
    const nuevoLog = {
      id: Date.now(),
      fecha: new Date().toISOString(),
      ejercicio: ejercicio,
      peso: parseFloat(peso),
      repeticiones: parseInt(repeticiones),
      notas: notas
    };
    historial.push(nuevoLog);
    localStorage.setItem("f365_historial", JSON.stringify(historial));
    
    this.actualizarPesoEjercicio(ejercicio, peso);
    return nuevoLog;
  }

  actualizarPesoEjercicio(nombreEjercicio, peso) {
    const ejercs = JSON.parse(localStorage.getItem("f365_ejercicios")) || {};
    ejercs[nombreEjercicio] = {
      weight: parseFloat(peso),
      lastUpdated: new Date().toISOString()
    };
    localStorage.setItem("f365_ejercicios", JSON.stringify(ejercs));
  }

  getPesosEjercicios() {
    return JSON.parse(localStorage.getItem("f365_ejercicios")) || {};
  }

  eliminarSeguimiento(id) {
    let historial = this.getHistorial();
    historial = historial.filter(item => item.id !== id);
    localStorage.setItem("f365_historial", JSON.stringify(historial));
    return true;
  }

  // --- MÉTODOS DE OBJETIVOS ---
  getObjetivos() {
    return JSON.parse(localStorage.getItem("f365_objetivos"));
  }

  addObjetivo(tipo, valor_objetivo, fecha_fin) {
    const objetivos = this.getObjetivos();
    const nuevoObj = {
      id: Date.now(),
      tipo: tipo,
      valor_objetivo: parseFloat(valor_objetivo),
      fecha_inicio: new Date().toISOString().split("T")[0],
      fecha_fin: fecha_fin,
      completado: false
    };
    objetivos.push(nuevoObj);
    localStorage.setItem("f365_objetivos", JSON.stringify(objetivos));
    return nuevoObj;
  }

  toggleObjetivoCompletado(id) {
    const objetivos = this.getObjetivos();
    const obj = objetivos.find(o => o.id === id);
    if (obj) {
      obj.completado = !obj.completado;
      localStorage.setItem("f365_objetivos", JSON.stringify(objetivos));
      return obj;
    }
    return null;
  }

  eliminarObjetivo(id) {
    let objetivos = this.getObjetivos();
    objetivos = objetivos.filter(o => o.id !== id);
    localStorage.setItem("f365_objetivos", JSON.stringify(objetivos));
    return true;
  }

  // --- MÉTODOS DE RUTINAS PERSONALIZADAS (NUEVO) ---
  getRutinasPersonalizadas() {
    return JSON.parse(localStorage.getItem("f365_rutinas")) || [];
  }

  addRutinaPersonalizada(nombre, ejercicios) {
    const rutinas = this.getRutinasPersonalizadas();
    const nuevaRutina = {
      id: Date.now(),
      nombre: nombre,
      ejercicios: ejercicios // Array de { ejercicio: String, series: Number, repeticiones: Number }
    };
    rutinas.push(nuevaRutina);
    localStorage.setItem("f365_rutinas", JSON.stringify(rutinas));
    return nuevaRutina;
  }

  eliminarRutinaPersonalizada(id) {
    let rutinas = this.getRutinasPersonalizadas();
    rutinas = rutinas.filter(r => r.id !== id);
    localStorage.setItem("f365_rutinas", JSON.stringify(rutinas));
    return true;
  }

  // --- MÉTODOS DE RETOS AERÓBICOS / CROSSFIT (NUEVO) ---
  getRetosCompletados() {
    return JSON.parse(localStorage.getItem("f365_retos")) || {};
  }

  completarReto(retoId, marca, fecha = null) {
    const retos = this.getRetosCompletados();
    retos[retoId] = {
      completado: true,
      marca: marca, // Ej: "24:35" o "15 rondas"
      fecha: fecha || new Date().toISOString().split("T")[0]
    };
    localStorage.setItem("f365_retos", JSON.stringify(retos));
    return retos[retoId];
  }

  eliminarReto(retoId) {
    const retos = this.getRetosCompletados();
    if (retos[retoId]) {
      delete retos[retoId];
      localStorage.setItem("f365_retos", JSON.stringify(retos));
    }
    return true;
  }


  // ==========================================
  // INDEXEDDB: Para almacenamiento de fotos
  // ==========================================

  initIndexedDB() {
    const request = indexedDB.open(DB_NAME, 1);

    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: "id", autoIncrement: true });
      }
    };

    request.onerror = (event) => {
      console.error("[IndexedDB] Error:", event.target.error);
    };

    request.onsuccess = (event) => {
      this.db = event.target.result;
    };
  }

  guardarFoto(imageDataUrl, descripcion = "", categoria = "general") {
    return new Promise((resolve, reject) => {
      if (!this.db) {
        reject("IndexedDB no abierta aún");
        return;
      }

      const transaction = this.db.transaction([STORE_NAME], "readwrite");
      const store = transaction.objectStore(STORE_NAME);

      const nuevaFoto = {
        fecha: new Date().toISOString(),
        imagen: imageDataUrl,
        descripcion: descripcion,
        categoria: categoria
      };

      const request = store.add(nuevaFoto);
      request.onsuccess = (event) => resolve({ id: event.target.result, ...nuevaFoto });
      request.onerror = (event) => reject(event.target.error);
    });
  }

  obtenerFotos() {
    return new Promise((resolve, reject) => {
      if (!this.db) {
        const request = indexedDB.open(DB_NAME, 1);
        request.onsuccess = (event) => {
          this.db = event.target.result;
          this.obtenerFotos().then(resolve).catch(reject);
        };
        request.onerror = () => reject("Error al abrir IndexedDB");
        return;
      }

      const transaction = this.db.transaction([STORE_NAME], "readonly");
      const store = transaction.objectStore(STORE_NAME);
      const request = store.getAll();

      request.onsuccess = (event) => {
        const fotos = event.target.result.sort((a, b) => new Date(b.fecha) - new Date(a.fecha));
        resolve(fotos);
      };
      request.onerror = (event) => reject(event.target.error);
    });
  }

  eliminarFoto(id) {
    return new Promise((resolve, reject) => {
      if (!this.db) {
        reject("IndexedDB no abierta");
        return;
      }

      const transaction = this.db.transaction([STORE_NAME], "readwrite");
      const store = transaction.objectStore(STORE_NAME);
      const request = store.delete(id);

      request.onsuccess = () => resolve(true);
      request.onerror = (event) => reject(event.target.error);
    });
  }


  // ==========================================
  // SISTEMA DE BACKUPS EXPANDIDO
  // ==========================================

  async exportarBackup() {
    try {
      const perfil = this.getPerfil();
      const config = this.getConfig();
      const historial = this.getHistorial();
      const objetivos = this.getObjetivos();
      const ejercicios = this.getPesosEjercicios();
      const rutinas = this.getRutinasPersonalizadas();
      const retos = this.getRetosCompletados();
      const fotos = await this.obtenerFotos();

      const backupData = {
        version: "2.0",
        fecha: new Date().toISOString(),
        perfil,
        config,
        historial,
        objetivos,
        ejercicios,
        rutinas, // Respaldar rutinas propias
        retos,   // Respaldar retos
        fotos
      };

      const jsonStr = JSON.stringify(backupData);
      const blob = new Blob([jsonStr], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      
      const link = document.createElement("a");
      link.href = url;
      link.download = `fuerza365_backup_v2_${new Date().toISOString().split("T")[0]}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      
      return true;
    } catch (e) {
      console.error("Error al exportar backup:", e);
      return false;
    }
  }

  importarBackup(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      
      reader.onload = async (event) => {
        try {
          const backup = JSON.parse(event.target.result);
          
          if (!backup.perfil || !backup.config || !backup.historial) {
            reject("El archivo de copia de seguridad no es válido.");
            return;
          }

          // Importar LocalStorage
          localStorage.setItem("f365_perfil", JSON.stringify(backup.perfil));
          localStorage.setItem("f365_config", JSON.stringify(backup.config));
          localStorage.setItem("f365_historial", JSON.stringify(backup.historial));
          if (backup.objetivos) localStorage.setItem("f365_objetivos", JSON.stringify(backup.objetivos));
          if (backup.ejercicios) localStorage.setItem("f365_ejercicios", JSON.stringify(backup.ejercicios));
          if (backup.rutinas) localStorage.setItem("f365_rutinas", JSON.stringify(backup.rutinas));
          if (backup.retos) localStorage.setItem("f365_retos", JSON.stringify(backup.retos));

          // Importar IndexedDB Fotos
          if (backup.fotos && this.db) {
            const transaction = this.db.transaction([STORE_NAME], "readwrite");
            const store = transaction.objectStore(STORE_NAME);
            store.clear();
            
            for (const foto of backup.fotos) {
              const fotoSinId = { ...foto };
              delete fotoSinId.id;
              store.add(fotoSinId);
            }
          }

          resolve(true);
        } catch (e) {
          reject("Error al analizar el backup: " + e.message);
        }
      };

      reader.onerror = () => reject("Error de lectura");
      reader.readAsText(file);
    });
  }
}

// Globalizar dbManager
window.dbManager = new LocalDB();
console.log("[db.js] Gestor dbManager expandido para la versión 2.0");
