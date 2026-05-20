import sqlite3

import pytest

import app as app_module


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "database.db"

    connection = sqlite3.connect(str(db_path))
    cursor = connection.cursor()
    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        status TEXT NOT NULL,
        progress INTEGER DEFAULT 0,
        thumbnail TEXT,
        description TEXT,
        user_id INTEGER,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    """)
    connection.commit()
    connection.close()

    monkeypatch.chdir(tmp_path)
    app_module.app.config["TESTING"] = True

    with app_module.app.test_client() as client:
        yield client
