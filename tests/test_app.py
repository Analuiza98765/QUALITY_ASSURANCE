import sqlite3

import pytest

import app as app_module


class DummyResponse:
    def __init__(self, json_data):
        self._json_data = json_data

    def json(self):
        return self._json_data


def register_user(client, username="tester", email="tester@example.com", password="secret"):
    return client.post(
        "/register",
        data={"username": username, "email": email, "password": password},
        follow_redirects=False,
    )


def login_user(client, email="tester@example.com", password="secret"):
    return client.post(
        "/",
        data={"email": email, "password": password},
        follow_redirects=False,
    )


def test_login_page_returns_200(client):
    response = client.get("/")
    text = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "E-mail" in text
    assert "Senha" in text


def test_register_page_returns_200(client):
    response = client.get("/register")
    text = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Usuário" in text
    assert "E-mail" in text
    assert "Senha" in text


def test_register_invalid_email_shows_error(client):
    response = client.post(
        "/register",
        data={"username": "tester", "email": "bad-email", "password": "secret"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Digite um email v\xc3\xa1lido" in response.data


def test_register_duplicate_email_shows_error(client):
    register_user(client)
    second = register_user(client)

    assert second.status_code == 200
    assert b"Este email j\xc3\xa1 est\xc3\xa1 cadastrado" in second.data


def test_register_success_redirects_to_login(client):
    response = register_user(client)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")


def test_login_invalid_credentials_shows_error(client):
    response = login_user(client, email="missing@example.com", password="wrong")

    assert response.status_code == 200
    assert b"Email ou senha inv\xc3\xa1lidos" in response.data


def test_dashboard_requires_login(client):
    response = client.get("/dashboard")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")


def test_dashboard_after_login_shows_books(client):
    register_user(client)
    login_response = login_user(client)
    assert login_response.status_code == 302

    dashboard = client.get("/dashboard")

    assert dashboard.status_code == 200
    assert b"Quero Ler" in dashboard.data
    assert b"Lendo" in dashboard.data
    assert b"Lido" in dashboard.data


def test_add_book_get_requires_login(client):
    response = client.get("/add_book")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")


def test_add_book_get_page_after_login(client):
    register_user(client)
    login_user(client)

    response = client.get("/add_book")
    text = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Adicionar Livro" in text
    assert "Salvar Livro" in text


def test_add_book_post_creates_book(client, monkeypatch):
    monkeypatch.setattr(
        app_module.requests,
        "get",
        lambda url: DummyResponse(
            {
                "items": [
                    {
                        "volumeInfo": {
                            "authors": ["Author QA"],
                            "imageLinks": {"thumbnail": "http://example.com/thumb.jpg"},
                            "description": "Description QA",
                        }
                    }
                ]
            }
        ),
    )

    register_user(client)
    login_user(client)

    add_response = client.post(
        "/add_book",
        data={"title": "Test Book", "status": "Quero Ler"},
        follow_redirects=False,
    )

    assert add_response.status_code == 302
    assert add_response.headers["Location"].endswith("/dashboard")

    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()
    cursor.execute("SELECT title, author, status FROM books")
    book = cursor.fetchone()
    connection.close()

    assert book == ("Test Book", "Author QA", "Quero Ler")


def test_move_book_redirects_when_not_logged_in(client):
    response = client.get("/move_book/1/Lido")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")


def test_move_book_updates_status(client):
    register_user(client)
    login_user(client)

    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO books (title, author, status, thumbnail, description, user_id) VALUES (?, ?, ?, ?, ?, ?)",
        ("Book Move", "Author Move", "Quero Ler", "", "", 1),
    )
    connection.commit()
    connection.close()

    response = client.get("/move_book/1/Lido", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard")

    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()
    cursor.execute("SELECT status FROM books WHERE id = 1")
    status = cursor.fetchone()[0]
    connection.close()

    assert status == "Lido"


def test_delete_book_redirects_when_not_logged_in(client):
    response = client.get("/delete_book/1")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")


def test_delete_book_removes_book(client):
    register_user(client)
    login_user(client)

    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO books (title, author, status, thumbnail, description, user_id) VALUES (?, ?, ?, ?, ?, ?)",
        ("Book Delete", "Author Delete", "Quero Ler", "", "", 1),
    )
    connection.commit()
    connection.close()

    response = client.get("/delete_book/1", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard")

    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM books")
    count = cursor.fetchone()[0]
    connection.close()

    assert count == 0


def test_logout_clears_session(client):
    register_user(client)
    login_user(client)

    logout_response = client.get("/logout", follow_redirects=False)

    assert logout_response.status_code == 302
    assert logout_response.headers["Location"].endswith("/")

    dashboard = client.get("/dashboard")
    assert dashboard.status_code == 302
    assert dashboard.headers["Location"].endswith("/")
