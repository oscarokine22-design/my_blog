import os


class Config:

    BASE_DIR = os.path.abspath(
        os.path.dirname(__file__)
    )

    SECRET_KEY = os.environ.get("SECRET_KEY")

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///"
        + os.path.join(BASE_DIR, "blog.db")
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False