from flask import Flask, render_template, request, redirect, session
import sqlite3
import re
import requests

app = Flask(__name__)

app.secret_key = 'readstack_secret'

# =========================
# LOGIN
# =========================
@app.route('/', methods=['GET', 'POST'])
def login():

    error = None

    if request.method == 'POST':

        email = request.form['email']
        password = request.form['password']

        connection = sqlite3.connect('database.db')
        cursor = connection.cursor()

        cursor.execute("""
            SELECT * FROM users
            WHERE email = ? AND password = ?
        """, (email, password))

        user = cursor.fetchone()

        connection.close()

        if user:

            session['user'] = user[1]

            return redirect('/dashboard')

        else:
            error = 'Email ou senha inválidos'

    return render_template('login.html', error=error)

# =========================
# CADASTRO
# =========================
@app.route('/register', methods=['GET', 'POST'])
def register():

    error = None

    if request.method == 'POST':

        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        # =========================
        # VALIDAR EMAIL
        # =========================
        email_pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'

        if not re.match(email_pattern, email):

            error = 'Digite um email válido'

            return render_template('register.html', error=error)

        connection = sqlite3.connect('database.db')
        cursor = connection.cursor()

        # =========================
        # VERIFICAR EMAIL EXISTENTE
        # =========================
        cursor.execute("""
            SELECT * FROM users
            WHERE email = ?
        """, (email,))

        existing_user = cursor.fetchone()

        if existing_user:

            connection.close()

            error = 'Este email já está cadastrado'

            return render_template('register.html', error=error)

        # =========================
        # INSERIR USUÁRIO
        # =========================
        cursor.execute("""
            INSERT INTO users (username, email, password)
            VALUES (?, ?, ?)
        """, (username, email, password))

        connection.commit()
        connection.close()

        return redirect('/')

    return render_template('register.html', error=error)

# =========================
# DASHBOARD
# =========================
@app.route('/dashboard')
def dashboard():

    if 'user' not in session:
        return redirect('/')

    connection = sqlite3.connect('database.db')
    cursor = connection.cursor()

    # =========================
    # PEGAR USUÁRIO
    # =========================
    cursor.execute("""
        SELECT * FROM users
        WHERE username = ?
    """, (session['user'],))

    user = cursor.fetchone()

    user_id = user[0]

    # =========================
    # PESQUISA
    # =========================
    search = request.args.get('search', '')

    query = f"%{search}%"

    # =========================
    # QUERO LER
    # =========================
    cursor.execute("""
        SELECT * FROM books
        WHERE status = 'Quero Ler'
        AND user_id = ?
        AND (
            title LIKE ?
            OR author LIKE ?
        )
    """, (user_id, query, query))

    want_to_read = cursor.fetchall()

    # =========================
    # LENDO
    # =========================
    cursor.execute("""
        SELECT * FROM books
        WHERE status = 'Lendo'
        AND user_id = ?
        AND (
            title LIKE ?
            OR author LIKE ?
        )
    """, (user_id, query, query))

    reading = cursor.fetchall()

    # =========================
    # LIDO
    # =========================
    cursor.execute("""
        SELECT * FROM books
        WHERE status = 'Lido'
        AND user_id = ?
        AND (
            title LIKE ?
            OR author LIKE ?
        )
    """, (user_id, query, query))

    finished = cursor.fetchall()

    connection.close()

    return render_template(
        'dashboard.html',
        want_to_read=want_to_read,
        reading=reading,
        finished=finished,
        search=search
    )

# =========================
# ADICIONAR LIVRO
# =========================
@app.route('/add_book', methods=['GET', 'POST'])
def add_book():

    if 'user' not in session:
        return redirect('/')

    connection = sqlite3.connect('database.db')
    cursor = connection.cursor()

    cursor.execute("""
        SELECT * FROM users
        WHERE username = ?
    """, (session['user'],))

    user = cursor.fetchone()

    user_id = user[0]

    if request.method == 'POST':

        title = request.form['title']
        status = request.form['status']

        # =========================
        # GOOGLE BOOKS API
        # =========================
        url = f"https://www.googleapis.com/books/v1/volumes?q={title}"

        response = requests.get(url)

        data = response.json()

        author = "Autor desconhecido"
        thumbnail = ""
        description = "Sem descrição"

        if 'items' in data:

            book_info = data['items'][0]['volumeInfo']

            if 'authors' in book_info:
                author = book_info['authors'][0]

            if 'imageLinks' in book_info:
                thumbnail = book_info['imageLinks'].get('thumbnail', '')

            if 'description' in book_info:
                description = book_info['description']

        # =========================
        # INSERIR LIVRO
        # =========================
        cursor.execute("""
            INSERT INTO books (
                title,
                author,
                status,
                thumbnail,
                description,
                user_id
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            title,
            author,
            status,
            thumbnail,
            description,
            user_id
        ))

        connection.commit()
        connection.close()

        return redirect('/dashboard')

    return render_template('add_book.html')

# =========================
# MOVER LIVRO
# =========================
@app.route('/move_book/<int:book_id>/<status>')
def move_book(book_id, status):

    if 'user' not in session:
        return redirect('/')

    connection = sqlite3.connect('database.db')
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE books
        SET status = ?
        WHERE id = ?
    """, (status, book_id))

    connection.commit()
    connection.close()

    return redirect('/dashboard')
# =========================
# EXCLUIR LIVRO
# =========================
@app.route('/delete_book/<int:book_id>')
def delete_book(book_id):

    if 'user' not in session:
        return redirect('/')

    connection = sqlite3.connect('database.db')
    cursor = connection.cursor()

    cursor.execute("""
        DELETE FROM books
        WHERE id = ?
    """, (book_id,))

    connection.commit()
    connection.close()

    return redirect('/dashboard')

# =========================
# LOGOUT
# =========================
@app.route('/logout')
def logout():

    session.clear()

    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)