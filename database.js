const estudiantesDB = [];
const codigosUnicos = new Set();

function insertarRegistroSQL(registroCrudo) {
    if (codigosUnicos.has(registroCrudo.codigo)) {
        console.warn(`Alerta SQL: Registro duplicado bloqueado para el código ${registroCrudo.codigo}`);
        return false; 
    }

    const nombreEstandar = registroCrudo.nombre.trim().toUpperCase();
    const carreraEstandar = registroCrudo.carrera.trim().toUpperCase();

    let riesgo_calculado = "ESTABLE";
    let problema_calculado = "NINGUNO";

    if (registroCrudo.estres > 85 || registroCrudo.lms > 12 || registroCrudo.sentimiento < -0.7) {
        riesgo_calculado = "Crítico";
        problema_calculado = ['Ansiedad', 'Estrés'][Math.floor(Math.random() * 2)];
    } else if (registroCrudo.estres > 60 || registroCrudo.lms > 5) {
        riesgo_calculado = "Observación";
        problema_calculado = ['Ansiedad', 'Estrés', 'Otros'][Math.floor(Math.random() * 3)];
    } else {
        problema_calculado = "Otros";
    }

    estudiantesDB.push({
        id: registroCrudo.id,
        codigo: registroCrudo.codigo,
        nombre: nombreEstandar,
        carrera: carreraEstandar,
        ciclo: registroCrudo.ciclo,
        estres: registroCrudo.estres,
        lms: registroCrudo.lms,
        nota: registroCrudo.nota,
        sentimiento: registroCrudo.sentimiento,
        riesgo: riesgo_calculado,
        problema: problema_calculado
    });

    codigosUnicos.add(registroCrudo.codigo);
    return true;
}

const nombres = ["Álvaro", "Sofía", "Ricardo", "Ana", "Luis", "María", "Jorge", "Lucía", "Carlos", "Elena", "Diego", "Valeria", "Mateo", "Camila", "Sebastián"];
const apellidos = ["Mendoza", "Valdivia", "Palma", "Torres", "Castro", "Rojas", "Gómez", "Silva", "Flores", "Pérez", "Quispe", "Mamani", "García", "Rodríguez", "López"];
const carreras = ['Ing. de Sistemas', 'Administración', 'Derecho', 'Psicología', 'Medicina'];
const ciclos = ['I', 'III', 'IV', 'VI', 'VIII', 'IX', 'X'];

let registrosInsertados = 0;
let iterador = 1;

while (registrosInsertados < 500) {
    let notaGenerada = parseFloat((Math.random() * (18 - 8) + 8).toFixed(1));
    let sentimientoGenerado = parseFloat((Math.random() * 2 - 1).toFixed(2));
    
    let payload = {
        id: iterador,
        codigo: `2026-${iterador.toString().padStart(4, '0')}`,
        nombre: `  ${nombres[Math.floor(Math.random() * nombres.length)]} ${apellidos[Math.floor(Math.random() * apellidos.length)]}  `,
        carrera: carreras[Math.floor(Math.random() * carreras.length)],
        ciclo: ciclos[Math.floor(Math.random() * ciclos.length)],
        estres: Math.floor(Math.random() * 100),
        lms: Math.floor(Math.random() * 20),
        nota: notaGenerada,
        sentimiento: sentimientoGenerado
    };

    let exito = insertarRegistroSQL(payload);
    
    if (exito) {
        registrosInsertados++;
    }
    iterador++;
}

console.log("✔ Base de datos cargada: 500 registros listos.");

function descargarBaseDatos() {
    let csvContent = "data:text/csv;charset=utf-8,";
    csvContent += "ID_Estudiante,Codigo_Uni,Nombre_Completo,Carrera,Ciclo,Puntaje_Estres,Faltas_LMS,Nota_Promedio,Sentimiento_IA,Nivel_Riesgo,Problema_Detectado\n";
    
    estudiantesDB.forEach(function(rowArray) {
        let row = `${rowArray.id},${rowArray.codigo},${rowArray.nombre},${rowArray.carrera},${rowArray.ciclo},${rowArray.estres},${rowArray.lms},${rowArray.nota},${rowArray.sentimiento},${rowArray.riesgo},${rowArray.problema}`;
        csvContent += row + "\n";
    });

    var encodedUri = encodeURI(csvContent);
    var link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "BD_Salud_Mental_500_Alumnos_Standard.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}