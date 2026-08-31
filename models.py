from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime


db = SQLAlchemy()


# =========================
# USER
# =========================

class User(UserMixin, db.Model):

    __tablename__ = "user"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    username = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(255),
        nullable=False
    )

    bio = db.Column(
        db.Text,
        default="No bio yet"
    )

    profile_image = db.Column(
        db.String(255),
        default="default.jpg"
    )

    is_admin = db.Column(
        db.Boolean,
        default=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    posts = db.relationship(
        "Post",
        backref="author",
        lazy=True,
        cascade="all, delete-orphan"
    )

    comments = db.relationship(
        "Comment",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan"
    )

    likes = db.relationship(
        "Like",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan"
    )

    notifications = db.relationship(
        "Notification",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan"
    )


# =========================
# POST
# =========================

class Post(db.Model):

    __tablename__ = "post"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    title = db.Column(
        db.String(200),
        nullable=False
    )

    content = db.Column(
        db.Text,
        nullable=False
    )

    image = db.Column(
        db.String(255)
    )

    video = db.Column(
        db.String(255)
    )

    author_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    category = db.Column(
        db.String(100)
    )

    is_hidden = db.Column(
        db.Boolean,
        default=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    images = db.relationship(
        "PostImage",
        backref="post",
        lazy=True,
        cascade="all, delete-orphan"
    )

    likes = db.relationship(
        "Like",
        backref="post",
        lazy=True,
        cascade="all, delete-orphan"
    )

    comments = db.relationship(
        "Comment",
        backref="post",
        lazy=True,
        cascade="all, delete-orphan"
    )

    notifications = db.relationship(
        "Notification",
        backref="post",
        lazy=True
    )


# =========================
# MULTIPLE POST IMAGES
# =========================

class PostImage(db.Model):

    __tablename__ = "post_image"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    filename = db.Column(
        db.String(255),
        nullable=False
    )

    post_id = db.Column(
        db.Integer,
        db.ForeignKey("post.id"),
        nullable=False
    )


# =========================
# LIKE
# =========================

class Like(db.Model):

    __tablename__ = "like"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    post_id = db.Column(
        db.Integer,
        db.ForeignKey("post.id"),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


# =========================
# COMMENT
# =========================

class Comment(db.Model):

    __tablename__ = "comment"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    content = db.Column(
        db.Text,
        nullable=False
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    post_id = db.Column(
        db.Integer,
        db.ForeignKey("post.id"),
        nullable=False
    )

    parent_id = db.Column(
        db.Integer,
        db.ForeignKey("comment.id"),
        nullable=True
    )

    is_hidden = db.Column(
        db.Boolean,
        default=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    replies = db.relationship(
        "Comment",
        backref=db.backref(
            "parent",
            remote_side=[id]
        ),
        lazy=True,
        cascade="all, delete-orphan"
    )


# =========================
# FOLLOW
# =========================

class Follow(db.Model):

    __tablename__ = "follow"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    follower_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    followed_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


# =========================
# NOTIFICATION
# =========================

class Notification(db.Model):

    __tablename__ = "notification"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    message = db.Column(
        db.String(500),
        nullable=False
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    is_read = db.Column(
        db.Boolean,
        default=False
    )

    post_id = db.Column(
        db.Integer,
        db.ForeignKey("post.id"),
        nullable=True
    )

    notification_type = db.Column(
        db.String(50),
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )