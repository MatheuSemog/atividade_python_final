import os
import sqlite3
from functools import wraps
from pathlib import Path

import requests
from flask import Flask, flash, g, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "instance" / "tarefas.db"

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-change-this-secret-key")
app.config["DATABASE"] = DB_PATH


def get_db():
    if "db" not in g:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            senha TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS tarefas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            descricao TEXT,
            status TEXT NOT NULL DEFAULT 'Pendente'
                CHECK (status IN ('Pendente', 'Em andamento', 'Concluída')),
            usuario_id INTEGER NOT NULL,
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE
        );
        """
    )
    db.commit()


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if "usuario_id" not in session:
            flash("Faça login para acessar esta página.", "warning")
            return redirect(url_for("login"))
        return view(**kwargs)

    return wrapped_view


def task_to_dict(row):
    return {
        "id": row["id"],
        "titulo": row["titulo"],
        "descricao": row["descricao"] or "",
        "status": row["status"],
        "usuario_id": row["usuario_id"],
    }


def get_user_task(task_id):
    task = get_db().execute(
        "SELECT * FROM tarefas WHERE id = ? AND usuario_id = ?",
        (task_id, session["usuario_id"]),
    ).fetchone()
    return task


def get_daily_advice():
    try:
        response = requests.get("https://api.adviceslip.com/advice", timeout=3)
        response.raise_for_status()
        data = response.json()
        return data.get("slip", {}).get("advice", "Continue avançando, uma tarefa de cada vez.")
    except (requests.RequestException, ValueError):
        return "Continue avançando, uma tarefa de cada vez."


@app.route("/")
def index():
    if "usuario_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html")


@app.route("/registro", methods=("GET", "POST"))
def registro():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")

        erro = None
        if not nome:
            erro = "Informe seu nome."
        elif not email or "@" not in email:
            erro = "Informe um e-mail válido."
        elif len(senha) < 6:
            erro = "A senha deve ter pelo menos 6 caracteres."

        if erro is None:
            try:
                db = get_db()
                db.execute(
                    "INSERT INTO usuarios (nome, email, senha) VALUES (?, ?, ?)",
                    (nome, email, generate_password_hash(senha)),
                )
                db.commit()
                flash("Cadastro realizado. Agora faça login.", "success")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                erro = "Este e-mail já está cadastrado."

        flash(erro, "danger")

    return render_template("registro.html")


@app.route("/login", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")
        usuario = get_db().execute(
            "SELECT * FROM usuarios WHERE email = ?", (email,)
        ).fetchone()

        if usuario is None or not check_password_hash(usuario["senha"], senha):
            flash("E-mail ou senha inválidos.", "danger")
        else:
            session.clear()
            session["usuario_id"] = usuario["id"]
            session["usuario_nome"] = usuario["nome"]
            return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Sessão encerrada.", "info")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    tarefas = get_db().execute(
        "SELECT * FROM tarefas WHERE usuario_id = ? ORDER BY id DESC",
        (session["usuario_id"],),
    ).fetchall()
    conselho = get_daily_advice()
    return render_template("dashboard.html", tarefas=tarefas, conselho=conselho)


@app.route("/nova", methods=("GET", "POST"))
@login_required
def nova_tarefa():
    if request.method == "POST":
        titulo = request.form.get("titulo", "").strip()
        descricao = request.form.get("descricao", "").strip()
        status = request.form.get("status", "Pendente")

        if not titulo:
            flash("O título é obrigatório.", "danger")
        elif status not in {"Pendente", "Em andamento", "Concluída"}:
            flash("Status inválido.", "danger")
        else:
            db = get_db()
            db.execute(
                "INSERT INTO tarefas (titulo, descricao, status, usuario_id) VALUES (?, ?, ?, ?)",
                (titulo, descricao, status, session["usuario_id"]),
            )
            db.commit()
            flash("Tarefa criada com sucesso.", "success")
            return redirect(url_for("dashboard"))

    return render_template("form_tarefa.html", tarefa=None)


@app.route("/editar/<int:task_id>", methods=("GET", "POST"))
@login_required
def editar_tarefa(task_id):
    tarefa = get_user_task(task_id)
    if tarefa is None:
        flash("Tarefa não encontrada.", "danger")
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        titulo = request.form.get("titulo", "").strip()
        descricao = request.form.get("descricao", "").strip()
        status = request.form.get("status", "Pendente")

        if not titulo:
            flash("O título é obrigatório.", "danger")
        elif status not in {"Pendente", "Em andamento", "Concluída"}:
            flash("Status inválido.", "danger")
        else:
            db = get_db()
            db.execute(
                "UPDATE tarefas SET titulo = ?, descricao = ?, status = ? WHERE id = ? AND usuario_id = ?",
                (titulo, descricao, status, task_id, session["usuario_id"]),
            )
            db.commit()
            flash("Tarefa atualizada.", "success")
            return redirect(url_for("dashboard"))

    return render_template("form_tarefa.html", tarefa=tarefa)


@app.post("/excluir/<int:task_id>")
@login_required
def excluir_tarefa(task_id):
    if get_user_task(task_id) is None:
        return jsonify({"erro": "Tarefa não encontrada"}), 404
    db = get_db()
    db.execute(
        "DELETE FROM tarefas WHERE id = ? AND usuario_id = ?",
        (task_id, session["usuario_id"]),
    )
    db.commit()
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"ok": True})
    flash("Tarefa excluída.", "success")
    return redirect(url_for("dashboard"))


@app.post("/concluir/<int:task_id>")
@login_required
def concluir_tarefa(task_id):
    if get_user_task(task_id) is None:
        return jsonify({"erro": "Tarefa não encontrada"}), 404
    db = get_db()
    db.execute(
        "UPDATE tarefas SET status = 'Concluída' WHERE id = ? AND usuario_id = ?",
        (task_id, session["usuario_id"]),
    )
    db.commit()
    return jsonify({"ok": True, "status": "Concluída"})


@app.get("/tarefas/filtro")
@login_required
def filtro_tarefas():
    status = request.args.get("status", "Todas")
    params = [session["usuario_id"]]
    sql = "SELECT * FROM tarefas WHERE usuario_id = ?"
    if status in {"Pendente", "Em andamento", "Concluída"}:
        sql += " AND status = ?"
        params.append(status)
    sql += " ORDER BY id DESC"
    rows = get_db().execute(sql, params).fetchall()
    return jsonify([task_to_dict(row) for row in rows])


@app.get("/api/progresso")
@login_required
def api_progresso():
    rows = get_db().execute(
        """
        SELECT status, COUNT(*) AS total
        FROM tarefas
        WHERE usuario_id = ?
        GROUP BY status
        """,
        (session["usuario_id"],),
    ).fetchall()
    contagem = {"Pendente": 0, "Em andamento": 0, "Concluída": 0}
    for row in rows:
        contagem[row["status"]] = row["total"]
    return jsonify(contagem)


@app.get("/progresso")
@login_required
def progresso():
    return render_template("progresso.html")


# REST API - versão JSON da aplicação
@app.get("/api/tarefas")
@login_required
def api_listar_tarefas():
    rows = get_db().execute(
        "SELECT * FROM tarefas WHERE usuario_id = ? ORDER BY id DESC",
        (session["usuario_id"],),
    ).fetchall()
    return jsonify([task_to_dict(row) for row in rows])


@app.post("/api/tarefas")
@login_required
def api_criar_tarefa():
    data = request.get_json(silent=True) or {}
    titulo = str(data.get("titulo", "")).strip()
    descricao = str(data.get("descricao", "")).strip()
    status = data.get("status", "Pendente")
    if not titulo:
        return jsonify({"erro": "O título é obrigatório"}), 400
    if status not in {"Pendente", "Em andamento", "Concluída"}:
        return jsonify({"erro": "Status inválido"}), 400

    db = get_db()
    cursor = db.execute(
        "INSERT INTO tarefas (titulo, descricao, status, usuario_id) VALUES (?, ?, ?, ?)",
        (titulo, descricao, status, session["usuario_id"]),
    )
    db.commit()
    row = get_user_task(cursor.lastrowid)
    return jsonify(task_to_dict(row)), 201


@app.route("/api/tarefas/<int:task_id>", methods=("GET", "PUT", "PATCH", "DELETE"))
@login_required
def api_tarefa(task_id):
    tarefa = get_user_task(task_id)
    if tarefa is None:
        return jsonify({"erro": "Tarefa não encontrada"}), 404

    if request.method == "GET":
        return jsonify(task_to_dict(tarefa))

    if request.method == "DELETE":
        db = get_db()
        db.execute(
            "DELETE FROM tarefas WHERE id = ? AND usuario_id = ?",
            (task_id, session["usuario_id"]),
        )
        db.commit()
        return "", 204

    data = request.get_json(silent=True) or {}
    titulo = str(data.get("titulo", tarefa["titulo"])).strip()
    descricao = str(data.get("descricao", tarefa["descricao"] or "")).strip()
    status = data.get("status", tarefa["status"])
    if not titulo:
        return jsonify({"erro": "O título é obrigatório"}), 400
    if status not in {"Pendente", "Em andamento", "Concluída"}:
        return jsonify({"erro": "Status inválido"}), 400

    db = get_db()
    db.execute(
        "UPDATE tarefas SET titulo = ?, descricao = ?, status = ? WHERE id = ? AND usuario_id = ?",
        (titulo, descricao, status, task_id, session["usuario_id"]),
    )
    db.commit()
    return jsonify(task_to_dict(get_user_task(task_id)))


with app.app_context():
    init_db()


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1")
