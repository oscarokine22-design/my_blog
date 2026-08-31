import os
import sqlite3

from datetime import datetime

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash
)

from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from werkzeug.utils import secure_filename

from config import Config

from models import (
    db,
    User,
    Post,
    PostImage,
    Like,
    Comment,
    Follow,
    Notification
)


app = Flask(__name__)

app.config.from_object(Config)


# =========================
# UPLOADS
# =========================

UPLOAD_FOLDER = os.path.join(
    app.root_path,
    "static",
    "uploads"
)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True
)


ALLOWED_IMAGE_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "gif",
    "webp"
}


ALLOWED_VIDEO_EXTENSIONS = {
    "mp4",
    "webm",
    "ogg",
    "mov"
}


# =========================
# DATABASE
# =========================

db.init_app(app)


# =========================
# LOGIN
# =========================

login_manager = LoginManager()

login_manager.init_app(app)

login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):

    return db.session.get(
        User,
        int(user_id)
    )


# =========================
# HELPERS
# =========================

def allowed_image(filename):

    return (
        "." in filename
        and filename.rsplit(
            ".",
            1
        )[1].lower()
        in ALLOWED_IMAGE_EXTENSIONS
    )


def allowed_video(filename):

    return (
        "." in filename
        and filename.rsplit(
            ".",
            1
        )[1].lower()
        in ALLOWED_VIDEO_EXTENSIONS
    )


def create_notification(
    user_id,
    message,
    post_id=None,
    notification_type=None
):

    notification = Notification(
        user_id=user_id,
        message=message,
        post_id=post_id,
        notification_type=notification_type,
        is_read=False
    )

    db.session.add(notification)


def admin_required():

    if not current_user.is_authenticated:

        return False

    return bool(
        getattr(
            current_user,
            "is_admin",
            False
        )
    )


# =========================
# GLOBAL DATA
# =========================

@app.context_processor
def inject_notifications():

    unread_notifications = 0

    if current_user.is_authenticated:

        unread_notifications = Notification.query.filter_by(
            user_id=current_user.id,
            is_read=False
        ).count()

    return {
        "unread_notifications":
            unread_notifications
    }


# =========================
# HOME
# =========================

@app.route("/")
def home():

    page = request.args.get(
        "page",
        1,
        type=int
    )

    if page < 1:
        page = 1

    posts = Post.query.filter_by(
        is_hidden=False
    ).order_by(
        Post.id.desc()
    ).paginate(
        page=page,
        per_page=5,
        error_out=False
    )

    return render_template(
        "index.html",
        posts=posts
    )


# =========================
# REGISTER
# =========================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if current_user.is_authenticated:

        return redirect(
            url_for("home")
        )

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        if not username or not password:

            flash(
                "Please fill in all fields.",
                "error"
            )

            return redirect(
                url_for("register")
            )

        existing_user = User.query.filter_by(
            username=username
        ).first()

        if existing_user:

            flash(
                "Username already exists.",
                "error"
            )

            return redirect(
                url_for("register")
            )

        new_user = User(
            username=username,
            password=generate_password_hash(
                password
            ),
            bio="No bio yet",
            profile_image="default.jpg",
            is_admin=False
        )

        db.session.add(new_user)

        db.session.commit()

        flash(
            "Account created successfully.",
            "success"
        )

        return redirect(
            url_for("login")
        )

    return render_template(
        "register.html"
    )


# =========================
# LOGIN
# =========================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if current_user.is_authenticated:

        return redirect(
            url_for("home")
        )

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        user = User.query.filter_by(
            username=username
        ).first()

        if user and check_password_hash(
            user.password,
            password
        ):

            login_user(user)

            flash(
                "Welcome back!",
                "success"
            )

            return redirect(
                url_for("home")
            )

        flash(
            "Invalid username or password.",
            "error"
        )

    return render_template(
        "login.html"
    )


# =========================
# LOGOUT
# =========================

@app.route("/logout")
@login_required
def logout():

    logout_user()

    return redirect(
        url_for("home")
    )


# =========================
# SEARCH
# =========================

@app.route("/search")
def search():

    query = request.args.get(
        "q",
        ""
    ).strip()

    if query:

        search_term = f"%{query}%"

        posts = Post.query.filter(
            Post.is_hidden == False,
            db.or_(
                Post.title.ilike(
                    search_term
                ),
                Post.content.ilike(
                    search_term
                ),
                Post.category.ilike(
                    search_term
                )
            )
        ).order_by(
            Post.id.desc()
        ).all()

    else:

        posts = []

    return render_template(
        "search.html",
        posts=posts,
        query=query
    )


# =========================
# CATEGORY
# =========================

@app.route(
    "/category/<category>"
)
def category(category):

    posts = Post.query.filter_by(
        category=category,
        is_hidden=False
    ).order_by(
        Post.id.desc()
    ).all()

    return render_template(
        "category.html",
        posts=posts,
        category=category
    )


# =========================
# PROFILE
# =========================

@app.route(
    "/profile/<username>"
)
def profile(username):

    user = User.query.filter_by(
        username=username
    ).first_or_404()

    posts = Post.query.filter_by(
        author_id=user.id,
        is_hidden=False
    ).order_by(
        Post.id.desc()
    ).all()

    is_following = False

    if current_user.is_authenticated:

        if current_user.id != user.id:

            is_following = Follow.query.filter_by(
                follower_id=current_user.id,
                followed_id=user.id
            ).first() is not None

    follower_count = Follow.query.filter_by(
        followed_id=user.id
    ).count()

    following_count = Follow.query.filter_by(
        follower_id=user.id
    ).count()

    return render_template(
        "profile.html",
        user=user,
        posts=posts,
        is_following=is_following,
        follower_count=follower_count,
        following_count=following_count
    )


# =========================
# FOLLOW
# =========================

@app.route(
    "/follow/<int:user_id>"
)
@login_required
def follow(user_id):

    user = db.session.get(
        User,
        user_id
    )

    if not user:

        return redirect(
            url_for("home")
        )

    if user.id == current_user.id:

        return redirect(
            url_for(
                "profile",
                username=user.username
            )
        )

    existing_follow = Follow.query.filter_by(
        follower_id=current_user.id,
        followed_id=user.id
    ).first()

    if existing_follow:

        db.session.delete(
            existing_follow
        )

    else:

        new_follow = Follow(
            follower_id=current_user.id,
            followed_id=user.id
        )

        db.session.add(
            new_follow
        )

        create_notification(
            user.id,
            f"{current_user.username} started following you.",
            notification_type="follow"
        )

    db.session.commit()

    return redirect(
        url_for(
            "profile",
            username=user.username
        )
    )


# =========================
# DASHBOARD
# =========================

@app.route("/dashboard")
@login_required
def dashboard():

    posts = Post.query.filter_by(
        author_id=current_user.id
    ).order_by(
        Post.id.desc()
    ).all()

    follower_count = Follow.query.filter_by(
        followed_id=current_user.id
    ).count()

    following_count = Follow.query.filter_by(
        follower_id=current_user.id
    ).count()

    total_likes = 0
    total_comments = 0

    for post in posts:

        total_likes += len(
            post.likes
        )

        total_comments += len(
            post.comments
        )

    return render_template(
        "dashboard.html",
        posts=posts,
        follower_count=follower_count,
        following_count=following_count,
        total_likes=total_likes,
        total_comments=total_comments
    )


# =========================
# EDIT PROFILE
# =========================

@app.route(
    "/edit_profile",
    methods=["GET", "POST"]
)
@login_required
def edit_profile():

    if request.method == "POST":

        bio = request.form.get(
            "bio",
            ""
        ).strip()

        current_user.bio = bio

        image = request.files.get(
            "profile_image"
        )

        if image and image.filename:

            if allowed_image(
                image.filename
            ):

                filename = secure_filename(
                    image.filename
                )

                image.save(
                    os.path.join(
                        app.config["UPLOAD_FOLDER"],
                        filename
                    )
                )

                current_user.profile_image = filename

            else:

                flash(
                    "Invalid image format.",
                    "error"
                )

                return redirect(
                    url_for("edit_profile")
                )

        db.session.commit()

        flash(
            "Profile updated successfully.",
            "success"
        )

        return redirect(
            url_for(
                "profile",
                username=current_user.username
            )
        )

    return render_template(
        "edit_profile.html"
    )


# =========================
# CREATE POST
# =========================

@app.route(
    "/create",
    methods=["GET", "POST"]
)
@login_required
def create():

    if request.method == "POST":

        title = request.form.get(
            "title",
            ""
        ).strip()

        content = request.form.get(
            "content",
            ""
        ).strip()

        category = request.form.get(
            "category",
            ""
        ).strip()

        if not title or not content:

            flash(
                "Title and content are required.",
                "error"
            )

            return redirect(
                url_for("create")
            )

        post = Post(
            title=title,
            content=content,
            category=category,
            author_id=current_user.id,
            is_hidden=False
        )

        db.session.add(post)

        db.session.flush()

        images = request.files.getlist(
            "images"
        )

        for image in images:

            if image and image.filename:

                if allowed_image(
                    image.filename
                ):

                    filename = secure_filename(
                        image.filename
                    )

                    image.save(
                        os.path.join(
                            app.config["UPLOAD_FOLDER"],
                            filename
                        )
                    )

                    post_image = PostImage(
                        filename=filename,
                        post_id=post.id
                    )

                    db.session.add(
                        post_image
                    )

        image = request.files.get(
            "image"
        )

        if image and image.filename:

            if allowed_image(
                image.filename
            ):

                filename = secure_filename(
                    image.filename
                )

                image.save(
                    os.path.join(
                        app.config["UPLOAD_FOLDER"],
                        filename
                    )
                )

                post.image = filename

        video = request.files.get(
            "video"
        )

        if video and video.filename:

            if allowed_video(
                video.filename
            ):

                filename = secure_filename(
                    video.filename
                )

                video.save(
                    os.path.join(
                        app.config["UPLOAD_FOLDER"],
                        filename
                    )
                )

                post.video = filename

            else:

                flash(
                    "Invalid video format.",
                    "error"
                )

                return redirect(
                    url_for("create")
                )

        db.session.commit()

        flash(
            "Post published successfully.",
            "success"
        )

        return redirect(
            url_for(
                "post",
                id=post.id
            )
        )

    return render_template(
        "create.html"
    )


# =========================
# VIEW POST
# =========================

@app.route(
    "/post/<int:id>"
)
def post(id):

    post = Post.query.get_or_404(id)

    if post.is_hidden:

        if not current_user.is_authenticated:

            flash(
                "This post is unavailable.",
                "error"
            )

            return redirect(
                url_for("home")
            )

        if (
            post.author_id
            != current_user.id
            and not admin_required()
        ):

            flash(
                "This post is unavailable.",
                "error"
            )

            return redirect(
                url_for("home")
            )

    return render_template(
        "post.html",
        post=post
    )


# =========================
# LIKE
# =========================

@app.route(
    "/like/<int:id>"
)
@login_required
def like(id):

    post = Post.query.get_or_404(id)

    existing_like = Like.query.filter_by(
        user_id=current_user.id,
        post_id=post.id
    ).first()

    if existing_like:

        db.session.delete(
            existing_like
        )

    else:

        new_like = Like(
            user_id=current_user.id,
            post_id=post.id
        )

        db.session.add(
            new_like
        )

        if post.author_id != current_user.id:

            create_notification(
                post.author_id,
                f"{current_user.username} liked your post '{post.title}'.",
                post_id=post.id,
                notification_type="like"
            )

    db.session.commit()

    return redirect(
        url_for(
            "post",
            id=id
        )
    )


# =========================
# COMMENT
# =========================

@app.route(
    "/comment/<int:id>",
    methods=["POST"]
)
@login_required
def comment(id):

    post = Post.query.get_or_404(id)

    content = request.form.get(
        "content",
        ""
    ).strip()

    if content:

        new_comment = Comment(
            content=content,
            user_id=current_user.id,
            post_id=post.id,
            parent_id=None,
            is_hidden=False
        )

        db.session.add(
            new_comment
        )

        if post.author_id != current_user.id:

            create_notification(
                post.author_id,
                f"{current_user.username} commented on your post '{post.title}'.",
                post_id=post.id,
                notification_type="comment"
            )

        db.session.commit()

    return redirect(
        url_for(
            "post",
            id=id
        )
    )


# =========================
# REPLY TO COMMENT
# =========================

@app.route(
    "/reply/<int:comment_id>",
    methods=["POST"]
)
@login_required
def reply(comment_id):

    parent_comment = Comment.query.get_or_404(
        comment_id
    )

    content = request.form.get(
        "content",
        ""
    ).strip()

    if not content:

        return redirect(
            url_for(
                "post",
                id=parent_comment.post_id
            )
        )

    new_reply = Comment(
        content=content,
        user_id=current_user.id,
        post_id=parent_comment.post_id,
        parent_id=parent_comment.id,
        is_hidden=False
    )

    db.session.add(
        new_reply
    )

    if parent_comment.user_id != current_user.id:

        create_notification(
            parent_comment.user_id,
            f"{current_user.username} replied to your comment.",
            post_id=parent_comment.post_id,
            notification_type="reply"
        )

    db.session.commit()

    return redirect(
        url_for(
            "post",
            id=parent_comment.post_id
        )
    )


# =========================
# NOTIFICATIONS
# =========================

@app.route("/notifications")
@login_required
def notifications():

    notifications_list = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Notification.id.desc()
    ).all()

    return render_template(
        "notifications.html",
        notifications=notifications_list
    )


@app.route(
    "/notification/read/<int:id>"
)
@login_required
def notification_read(id):

    notification = Notification.query.filter_by(
        id=id,
        user_id=current_user.id
    ).first_or_404()

    notification.is_read = True

    db.session.commit()

    if notification.post_id:

        return redirect(
            url_for(
                "post",
                id=notification.post_id
            )
        )

    return redirect(
        url_for("notifications")
    )


# =========================
# EDIT POST
# =========================

@app.route(
    "/edit/<int:id>",
    methods=["GET", "POST"]
)
@login_required
def edit(id):

    post = Post.query.get_or_404(id)

    if post.author_id != current_user.id:

        flash(
            "You cannot edit this post.",
            "error"
        )

        return redirect(
            url_for("home")
        )

    if request.method == "POST":

        post.title = request.form.get(
            "title",
            ""
        ).strip()

        post.content = request.form.get(
            "content",
            ""
        ).strip()

        post.category = request.form.get(
            "category",
            ""
        ).strip()

        db.session.commit()

        flash(
            "Post updated successfully.",
            "success"
        )

        return redirect(
            url_for(
                "post",
                id=post.id
            )
        )

    return render_template(
        "edit.html",
        post=post
    )


# =========================
# DELETE POST
# =========================

@app.route(
    "/delete/<int:id>"
)
@login_required
def delete(id):

    post = Post.query.get_or_404(id)

    if (
        post.author_id != current_user.id
        and not admin_required()
    ):

        flash(
            "You cannot delete this post.",
            "error"
        )

        return redirect(
            url_for("home")
        )

    db.session.delete(post)

    db.session.commit()

    flash(
        "Post deleted successfully.",
        "success"
    )

    return redirect(
        url_for("home")
    )


# =========================
# ADMIN PANEL
# =========================

@app.route("/admin")
@login_required
def admin():

    if not admin_required():

        flash(
            "Administrator access required.",
            "error"
        )

        return redirect(
            url_for("home")
        )

    users = User.query.order_by(
        User.id.desc()
    ).all()

    posts = Post.query.order_by(
        Post.id.desc()
    ).all()

    comments = Comment.query.order_by(
        Comment.id.desc()
    ).all()

    return render_template(
        "admin.html",
        users=users,
        posts=posts,
        comments=comments
    )


# =========================
# ADMIN MAKE / REMOVE ADMIN
# =========================

@app.route(
    "/admin/user/<int:user_id>/toggle"
)
@login_required
def admin_toggle_user(user_id):

    if not admin_required():

        flash(
            "Administrator access required.",
            "error"
        )

        return redirect(
            url_for("home")
        )

    user = User.query.get_or_404(
        user_id
    )

    if user.id == current_user.id:

        flash(
            "You cannot remove your own administrator access.",
            "error"
        )

        return redirect(
            url_for("admin")
        )

    user.is_admin = not user.is_admin

    db.session.commit()

    flash(
        "User administrator status updated.",
        "success"
    )

    return redirect(
        url_for("admin")
    )


# =========================
# ADMIN DELETE USER
# =========================

@app.route(
    "/admin/user/<int:user_id>/delete"
)
@login_required
def admin_delete_user(user_id):

    if not admin_required():

        return redirect(
            url_for("home")
        )

    user = User.query.get_or_404(
        user_id
    )

    if user.id == current_user.id:

        flash(
            "You cannot delete your own account.",
            "error"
        )

        return redirect(
            url_for("admin")
        )

    db.session.delete(user)

    db.session.commit()

    flash(
        "User deleted.",
        "success"
    )

    return redirect(
        url_for("admin")
    )


# =========================
# ADMIN HIDE / SHOW POST
# =========================

@app.route(
    "/admin/post/<int:post_id>/hide"
)
@login_required
def admin_hide_post(post_id):

    if not admin_required():

        return redirect(
            url_for("home")
        )

    post = Post.query.get_or_404(
        post_id
    )

    post.is_hidden = not post.is_hidden

    db.session.commit()

    flash(
        "Post visibility updated.",
        "success"
    )

    return redirect(
        url_for("admin")
    )


# =========================
# ADMIN DELETE POST
# =========================

@app.route(
    "/admin/post/<int:post_id>/delete"
)
@login_required
def admin_delete_post(post_id):

    if not admin_required():

        return redirect(
            url_for("home")
        )

    post = Post.query.get_or_404(
        post_id
    )

    db.session.delete(post)

    db.session.commit()

    flash(
        "Post deleted.",
        "success"
    )

    return redirect(
        url_for("admin")
    )


# =========================
# ADMIN HIDE / SHOW COMMENT
# =========================

@app.route(
    "/admin/comment/<int:comment_id>/hide"
)
@login_required
def admin_hide_comment(comment_id):

    if not admin_required():

        return redirect(
            url_for("home")
        )

    comment = Comment.query.get_or_404(
        comment_id
    )

    comment.is_hidden = not comment.is_hidden

    db.session.commit()

    flash(
        "Comment visibility updated.",
        "success"
    )

    return redirect(
        url_for("admin")
    )


# =========================
# ADMIN DELETE COMMENT
# =========================

@app.route(
    "/admin/comment/<int:comment_id>/delete"
)
@login_required
def admin_delete_comment(comment_id):

    if not admin_required():

        return redirect(
            url_for("home")
        )

    comment = Comment.query.get_or_404(
        comment_id
    )

    db.session.delete(comment)

    db.session.commit()

    flash(
        "Comment deleted.",
        "success"
    )

    return redirect(
        url_for("admin")
    )


# =========================
# ROUTES
# =========================

@app.route("/routes")
def routes():

    return "<br>".join(
        str(rule)
        for rule in app.url_map.iter_rules()
    )


# =========================
# START
# =========================

if __name__ == "__main__":

    with app.app_context():

        db.create_all()

    print("===================================")
    print("MYBLOG IS RUNNING")
    print("===================================")
    print("http://127.0.0.1:5000")

    app.run(
        debug=True
    )