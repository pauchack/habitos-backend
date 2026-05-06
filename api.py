from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pymysql
import os

app = FastAPI()

def get_db():
    return pymysql.connect(
        host=os.environ.get("MYSQLHOST", "localhost"),
        port=int(os.environ.get("MYSQLPORT", 3306)),
        user=os.environ.get("MYSQLUSER", "root"),
        password=os.environ.get("MYSQLPASSWORD", ""),
        database=os.environ.get("MYSQLDATABASE", "railway"),
        cursorclass=pymysql.cursors.DictCursor
    )

class HabitoCreate(BaseModel):
    nombre: str
    categoria: str
    importante: bool
    hora: str

class HabitoCompletar(BaseModel):
    completado: bool

class UsuarioCreate(BaseModel):
    username: str
    email: str
    telefono: str
    password: str

class UsuarioLogin(BaseModel):
    username: str
    password: str

# === HABITOS ===

@app.get("/habitos/{user_id}")
def get_habitos(user_id: int):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "SELECT id, nombre, categoria, importante, DATE_FORMAT(hora, '%%H:%%i') as hora, completado FROM habitos WHERE id_usuario=%s",
        (user_id,)
    )
    habitos = cursor.fetchall()
    for h in habitos:
        h["importante"] = bool(h["importante"])
        h["completado"] = bool(h["completado"])
    db.close()
    return habitos

@app.post("/habitos/{user_id}")
def create_habito(user_id: int, habito: HabitoCreate):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO habitos (id_usuario, nombre, categoria, importante, hora) VALUES (%s, %s, %s, %s, %s)",
        (user_id, habito.nombre, habito.categoria, habito.importante, habito.hora)
    )
    db.commit()
    new_id = cursor.lastrowid
    db.close()
    return {"id": new_id, "nombre": habito.nombre, "categoria": habito.categoria, "importante": habito.importante, "hora": habito.hora, "completado": False}

@app.put("/habitos/{habito_id}")
def update_habito(habito_id: int, habito: HabitoCreate):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "UPDATE habitos SET nombre=%s, categoria=%s, importante=%s, hora=%s WHERE id=%s",
        (habito.nombre, habito.categoria, habito.importante, habito.hora, habito_id)
    )
    db.commit()
    if cursor.rowcount == 0:
        db.close()
        raise HTTPException(status_code=404, detail="Hábito no encontrado")
    db.close()
    return {"id": habito_id, "nombre": habito.nombre, "categoria": habito.categoria, "importante": habito.importante, "hora": habito.hora}

@app.patch("/habitos/{habito_id}/completar")
def completar_habito(habito_id: int, data: HabitoCompletar):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "UPDATE habitos SET completado=%s WHERE id=%s",
        (data.completado, habito_id)
    )
    db.commit()
    if cursor.rowcount == 0:
        db.close()
        raise HTTPException(status_code=404, detail="Hábito no encontrado")
    db.close()
    return {"id": habito_id, "completado": data.completado}

class UsuarioUpdate(BaseModel):
    username: str
    email: str
    telefono: str

@app.put("/usuarios/{user_id}")
def update_usuario(user_id: int, usuario: UsuarioUpdate):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id FROM usuarios WHERE username=%s AND id!=%s", (usuario.username, user_id))
    if cursor.fetchone():
        db.close()
        raise HTTPException(status_code=400, detail="El usuario ya existe")
    cursor.execute("SELECT id FROM usuarios WHERE email=%s AND id!=%s", (usuario.email, user_id))
    if cursor.fetchone():
        db.close()
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    cursor.execute(
        "UPDATE usuarios SET username=%s, email=%s, telefono=%s WHERE id=%s",
        (usuario.username, usuario.email, usuario.telefono, user_id)
    )
    db.commit()
    db.close()
    return {"id": user_id, "username": usuario.username, "email": usuario.email, "telefono": usuario.telefono}


@app.delete("/habitos/{habito_id}")
def delete_habito(habito_id: int):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM habitos WHERE id=%s", (habito_id,))
    db.commit()
    if cursor.rowcount == 0:
        db.close()
        raise HTTPException(status_code=404, detail="Hábito no encontrado")
    db.close()
    return {"message": "Hábito eliminado"}


# === HISTORIAL ===

class HistorialCreate(BaseModel):
    tipo: str
    nombre_habito: str
    categoria: str
    importante: bool
    hora: str

@app.post("/historial/{user_id}")
def add_historial(user_id: int, entrada: HistorialCreate):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO historial (id_usuario, tipo, nombre_habito, categoria, importante, hora) VALUES (%s, %s, %s, %s, %s, %s)",
        (user_id, entrada.tipo, entrada.nombre_habito, entrada.categoria, entrada.importante, entrada.hora)
    )
    db.commit()
    db.close()
    return {"message": "Entrada añadida al historial"}

@app.get("/historial/{user_id}")
def get_historial(user_id: int):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "SELECT id, tipo, nombre_habito, categoria, importante, hora, DATE_FORMAT(fecha, '%%d/%%m/%%Y %%H:%%i') as fecha FROM historial WHERE id_usuario=%s ORDER BY fecha DESC",
        (user_id,)
    )
    historial = cursor.fetchall()
    for h in historial:
        h["importante"] = bool(h["importante"])
    db.close()
    return historial

# === USUARIOS ===

@app.get("/usuarios")
def get_usuarios():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id, username, email, telefono FROM usuarios")
    usuarios = cursor.fetchall()
    db.close()
    return usuarios

@app.post("/register")
def register(usuario: UsuarioCreate):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id FROM usuarios WHERE username=%s", (usuario.username,))
    if cursor.fetchone():
        db.close()
        raise HTTPException(status_code=400, detail="El usuario ya existe")
    cursor.execute("SELECT id FROM usuarios WHERE email=%s", (usuario.email,))
    if cursor.fetchone():
        db.close()
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    cursor.execute(
        "INSERT INTO usuarios (username, email, telefono, password) VALUES (%s, %s, %s, %s)",
        (usuario.username, usuario.email, usuario.telefono, usuario.password)
    )
    db.commit()
    new_id = cursor.lastrowid
    db.close()
    return {"id": new_id, "username": usuario.username, "email": usuario.email, "telefono": usuario.telefono}

@app.post("/login")
def login(usuario: UsuarioLogin):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "SELECT id, username, email, telefono FROM usuarios WHERE username=%s AND password=%s",
        (usuario.username, usuario.password)
    )
    user = cursor.fetchone()
    db.close()
    if not user:
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
    return user

@app.delete("/usuarios/{user_id}")
def delete_usuario(user_id: int):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM historial WHERE id_usuario=%s", (user_id,))
    cursor.execute("DELETE FROM habitos WHERE id_usuario=%s", (user_id,))
    cursor.execute("DELETE FROM usuarios WHERE id=%s", (user_id,))
    db.commit()
    if cursor.rowcount == 0:
        db.close()
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    db.close()
    return {"message": "Usuario eliminado"}
