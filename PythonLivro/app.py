import os
from functools import wraps

import requests
from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from database import get_db_connection, init_db

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "chave-secreta-troque-em-producao")
app.config["DEBUG"] = False

STATUS_VALIDOS = ["Pendente", "Em andamento", "Concluída"]
API_FRASE_MOTIVACIONAL = "https://api.adviceslip.com/advice"




def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if "usuario_id" not in session:
            flash("Faça login para continuar.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapper


@app.route("/")
def index():
    if "usuario_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")

        if not nome or not email or not senha:
            flash("Preencha todos os campos.", "danger")
            return redirect(url_for("registro"))

        if len(senha) < 6:
            flash("A senha deve ter pelo menos 6 caracteres.", "danger")
            return redirect(url_for("registro"))

        conn = get_db_connection()
        usuario_existente = conn.execute(
            "SELECT id FROM usuarios WHERE email = ?", (email,)
        ).fetchone()

        if usuario_existente:
            conn.close()
            flash("Este e-mail já está cadastrado.", "danger")
            return redirect(url_for("registro"))

        senha_hash = generate_password_hash(senha)
        conn.execute(
            "INSERT INTO usuarios (nome, email, senha) VALUES (?, ?, ?)",
            (nome, email, senha_hash),
        )
        conn.commit()
        conn.close()

        flash("Cadastro realizado com sucesso! Faça login.", "success")
        return redirect(url_for("login"))

    return render_template("registro.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")

        conn = get_db_connection()
        usuario = conn.execute(
            "SELECT * FROM usuarios WHERE email = ?", (email,)
        ).fetchone()
        conn.close()

        if usuario and check_password_hash(usuario["senha"], senha):
            session.clear()
            session["usuario_id"] = usuario["id"]
            session["usuario_nome"] = usuario["nome"]
            flash(f"Bem-vindo(a), {usuario['nome']}!", "success")
            return redirect(url_for("dashboard"))

        flash("E-mail ou senha inválidos.", "danger")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Você saiu da sua conta.", "info")
    return redirect(url_for("login"))




def buscar_frase_motivacional():
    try:
        resposta = requests.get(API_FRASE_MOTIVACIONAL, timeout=3)
        resposta.raise_for_status()
        dados = resposta.json()
        return dados["slip"]["advice"]
    except Exception:
        return "Continue firme, cada tarefa concluída é um passo adiante!"




@app.route("/dashboard")
@login_required
def dashboard():
    conn = get_db_connection()
    tarefas = conn.execute(
        "SELECT * FROM tarefas WHERE usuario_id = ? ORDER BY id DESC",
        (session["usuario_id"],),
    ).fetchall()
    conn.close()

    frase = buscar_frase_motivacional()

    return render_template(
        "dashboard.html",
        tarefas=tarefas,
        frase=frase,
        status_validos=STATUS_VALIDOS,
    )




@app.route("/nova_tarefa", methods=["GET", "POST"])
@login_required
def nova_tarefa():
    if request.method == "POST":
        titulo = request.form.get("titulo", "").strip()
        descricao = request.form.get("descricao", "").strip()
        status = request.form.get("status", "Pendente")

        if not titulo:
            flash("O título da tarefa é obrigatório.", "danger")
            return redirect(url_for("nova_tarefa"))

        if status not in STATUS_VALIDOS:
            status = "Pendente"

        conn = get_db_connection()
        conn.execute(
            "INSERT INTO tarefas (titulo, descricao, status, usuario_id) VALUES (?, ?, ?, ?)",
            (titulo, descricao, status, session["usuario_id"]),
        )
        conn.commit()
        conn.close()

        flash("Tarefa criada com sucesso!", "success")
        return redirect(url_for("dashboard"))

    return render_template("nova_tarefa.html", status_validos=STATUS_VALIDOS)


@app.route("/editar/<int:tarefa_id>", methods=["GET", "POST"])
@login_required
def editar(tarefa_id):
    conn = get_db_connection()
    tarefa = conn.execute(
        "SELECT * FROM tarefas WHERE id = ? AND usuario_id = ?",
        (tarefa_id, session["usuario_id"]),
    ).fetchone()

    if tarefa is None:
        conn.close()
        flash("Tarefa não encontrada.", "danger")
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        titulo = request.form.get("titulo", "").strip()
        descricao = request.form.get("descricao", "").strip()
        status = request.form.get("status", "Pendente")

        if not titulo:
            flash("O título da tarefa é obrigatório.", "danger")
            conn.close()
            return redirect(url_for("editar", tarefa_id=tarefa_id))

        if status not in STATUS_VALIDOS:
            status = "Pendente"

        conn.execute(
            "UPDATE tarefas SET titulo = ?, descricao = ?, status = ? WHERE id = ? AND usuario_id = ?",
            (titulo, descricao, status, tarefa_id, session["usuario_id"]),
        )
        conn.commit()
        conn.close()

        flash("Tarefa atualizada com sucesso!", "success")
        return redirect(url_for("dashboard"))

    conn.close()
    return render_template("editar_tarefa.html", tarefa=tarefa, status_validos=STATUS_VALIDOS)


@app.route("/excluir/<int:tarefa_id>", methods=["POST"])
@login_required
def excluir(tarefa_id):
    conn = get_db_connection()
    conn.execute(
        "DELETE FROM tarefas WHERE id = ? AND usuario_id = ?",
        (tarefa_id, session["usuario_id"]),
    )
    conn.commit()
    conn.close()

    flash("Tarefa excluída.", "info")
    return redirect(url_for("dashboard"))


@app.route("/concluir/<int:tarefa_id>", methods=["POST"])
@login_required
def concluir(tarefa_id):
    conn = get_db_connection()
    conn.execute(
        "UPDATE tarefas SET status = ? WHERE id = ? AND usuario_id = ?",
        ("Concluída", tarefa_id, session["usuario_id"]),
    )
    conn.commit()
    conn.close()

    flash("Tarefa marcada como concluída!", "success")
    return redirect(url_for("dashboard"))



@app.route("/api/tarefas")
@login_required
def api_tarefas():
    status = request.args.get("status", "todas")

    conn = get_db_connection()
    if status == "todas":
        tarefas = conn.execute(
            "SELECT * FROM tarefas WHERE usuario_id = ? ORDER BY id DESC",
            (session["usuario_id"],),
        ).fetchall()
    else:
        tarefas = conn.execute(
            "SELECT * FROM tarefas WHERE usuario_id = ? AND status = ? ORDER BY id DESC",
            (session["usuario_id"], status),
        ).fetchall()
    conn.close()

    return jsonify([dict(tarefa) for tarefa in tarefas])


@app.route("/api/progresso")
@login_required
def api_progresso():
    conn = get_db_connection()
    linhas = conn.execute(
        "SELECT status, COUNT(*) as total FROM tarefas WHERE usuario_id = ? GROUP BY status",
        (session["usuario_id"],),
    ).fetchall()
    conn.close()

    contagem = {status: 0 for status in STATUS_VALIDOS}
    for linha in linhas:
        contagem[linha["status"]] = linha["total"]

    return jsonify(contagem)


if __name__ == "__main__":
    init_db()
    app.run(debug=False)
