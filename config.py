import os


class Config:

    SECRET_KEY = os.environ.get(
        "SECRET_KEY",
        "myblog-development-secret-key-change-this-later"
    )

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///blog.db"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False