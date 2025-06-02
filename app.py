from flask import Flask, jsonify, request
import json
import os
from datetime import datetime

app = Flask(__name__)

# Funciones para leer y guardar archivos JSON
def cargar_datos(nombre_archivo):
    if not os.path.exists(nombre_archivo):
        return []
    with open(nombre_archivo, 'r') as f:
        return json.load(f)

def guardar_datos(nombre_archivo, datos):
    with open(nombre_archivo, 'w') as f:
        json.dump(datos, f, indent=2)

# Archivos de datos
ARCHIVO_ASIENTOS = 'asientos.json'
ARCHIVO_USUARIOS = 'usuarios.json'
ARCHIVO_VENTAS = 'ventas.json'

# Precios por zona
precios = {
    "VIP": 200,
    "Preferencial": 150,
    "General": 100
}

# Días del evento
funciones = {
    1: {"dia": "Día 1", "descuento": 0},
    2: {"dia": "Día 2", "descuento": 0.2}
}

# Simulación de validación contra sistema central
def validar_con_sistema_central(asiento_id):
    asientos = cargar_datos(ARCHIVO_ASIENTOS)
    asiento = next((a for a in asientos if a["id"] == asiento_id), None)
    return asiento and not asiento["vendido"]

@app.route('/')
def home():
    return "Sistema de Boletas - Proyecto Estadio"

@app.route('/asientos', methods=['GET'])
def obtener_asientos():
    return jsonify(cargar_datos(ARCHIVO_ASIENTOS))

@app.route('/asientos/disponibles', methods=['GET'])
def asientos_disponibles():
    asientos = cargar_datos(ARCHIVO_ASIENTOS)
    disponibles = [a for a in asientos if not a["vendido"]]
    return jsonify(disponibles)

@app.route('/asientos/vendidos', methods=['GET'])
def asientos_vendidos():
    asientos = cargar_datos(ARCHIVO_ASIENTOS)
    vendidos = [a for a in asientos if a["vendido"]]
    return jsonify(vendidos)

@app.route('/usuarios', methods=['POST'])
def crear_usuario():
    data = request.get_json()
    cedula = data.get("cedula")
    nombre = data.get("nombre")
    apellido = data.get("apellido")

    if not cedula or not nombre or not apellido:
        return jsonify({"error": "Faltan datos obligatorios"}), 400

    usuarios = cargar_datos(ARCHIVO_USUARIOS)
    if any(u["cedula"] == cedula for u in usuarios):
        return jsonify({"error": "Usuario ya existe"}), 400

    usuarios.append({"cedula": cedula, "nombre": nombre, "apellido": apellido})
    guardar_datos(ARCHIVO_USUARIOS, usuarios)

    return jsonify({"mensaje": "Usuario registrado con éxito"}), 201

@app.route('/usuarios/<cedula>', methods=['GET'])
def obtener_usuario(cedula):
    usuarios = cargar_datos(ARCHIVO_USUARIOS)
    usuario = next((u for u in usuarios if u["cedula"] == cedula), None)
    if not usuario:
        return jsonify({"error": "Usuario no encontrado"}), 404
    return jsonify(usuario)

@app.route('/vender', methods=['POST'])
def vender_asiento():
    data = request.get_json()

    asiento_id = data.get("asiento_id")
    dia_funcion = data.get("funcion_id")
    cedula = data.get("cedula", None)

    asientos = cargar_datos(ARCHIVO_ASIENTOS)
    asiento = next((a for a in asientos if a["id"] == asiento_id), None)
    if not asiento:
        return jsonify({"error": "Asiento no encontrado"}), 404

    if not validar_con_sistema_central(asiento_id):
        return jsonify({"error": "Asiento no disponible según sistema central"}), 409

    funcion = funciones.get(dia_funcion)
    if not funcion:
        return jsonify({"error": "Función inválida"}), 400

    precio_base = precios[asiento["ubicacion"]]
    descuento = funcion["descuento"] if asiento["ubicacion"] != "VIP" else 0
    total = precio_base * (1 - descuento)

    asiento["vendido"] = True
    for i, a in enumerate(asientos):
        if a["id"] == asiento_id:
            asientos[i] = asiento
            break
    guardar_datos(ARCHIVO_ASIENTOS, asientos)

    # Registrar usuario si viene
    if cedula:
        usuarios = cargar_datos(ARCHIVO_USUARIOS)
        if not any(u["cedula"] == cedula for u in usuarios):
            usuarios.append({"cedula": cedula})
            guardar_datos(ARCHIVO_USUARIOS, usuarios)

    # Guardar en ventas.json
    ventas = cargar_datos(ARCHIVO_VENTAS)
    venta = {
        "asiento_id": asiento_id,
        "ubicacion": asiento["ubicacion"],
        "funcion_id": dia_funcion,
        "cedula": cedula if cedula else None,
        "total_pagado": total,
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    ventas.append(venta)
    guardar_datos(ARCHIVO_VENTAS, ventas)

    print("🔄 Enviando al sistema central: asiento", asiento_id, "vendido.")

    return jsonify({
        "mensaje": "Venta realizada",
        "asiento_id": asiento_id,
        "ubicacion": asiento["ubicacion"],
        "precio_base": precio_base,
        "descuento_aplicado": descuento,
        "total_pagado": total
    })

@app.route('/ventas', methods=['GET'])
def listar_ventas():
    ventas = cargar_datos(ARCHIVO_VENTAS)
    return jsonify(ventas)

if __name__ == '__main__':
    app.run(debug=True)
