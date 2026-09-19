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
    PostBlock,
    Like,
    Comment,
    Follow,
    Notification
)


# ============================================================
# APP CONFIGURATION
# ============================================================

app = Flask(__name__)
app.config.from_object(Config)

app.config["UPLOAD_FOLDER"] = os.path.join(
    app.root_path,
    "static",
    "uploads"
)

os.makedirs(
    app.config["UPLOAD_FOLDER"],
    exist_ok=True
)


# ============================================================
# DATABASE
# ============================================================

db.init_app(app)


# ============================================================
# LOGIN MANAGER
# ============================================================

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):

    return User.query.get(int(user_id))


# ============================================================
# GLOBAL TEMPLATE VARIABLES
# ============================================================

@app.context_processor
def inject_unread_notifications():

    unread_notifications = 0

    if current_user.is_authenticated:

        unread_notifications = Notification.query.filter_by(
            user_id=current_user.id,
            is_read=False
        ).count()

    return {
        "unread_notifications": unread_notifications
    }


# ============================================================
# ALLOWED FILE TYPES
# ============================================================

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

ALLOWED_DOCUMENT_EXTENSIONS = {
    "pdf"
}


def allowed_image(filename):

    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_IMAGE_EXTENSIONS
    )


def allowed_video(filename):

    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_VIDEO_EXTENSIONS
    )


def allowed_document(filename):

    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_DOCUMENT_EXTENSIONS
    )


# ============================================================
# DATABASE UPDATE
# ============================================================

def update_database():

    """
    Adds newer columns/tables to older databases
    without deleting existing data.
    """

    database_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")

    if database_uri.startswith("sqlite:///"):

        database_path = database_uri.replace(
            "sqlite:///",
            "",
            1
        )

        if not os.path.isabs(database_path):

            database_path = os.path.join(
                app.root_path,
                database_path
            )

        if os.path.exists(database_path):

            connection = sqlite3.connect(
                database_path
            )

            cursor = connection.cursor()


            # ------------------------------------------------
            # EXISTING RESEARCH COLUMNS
            # ------------------------------------------------

            cursor.execute(
                "PRAGMA table_info(post)"
            )

            existing_columns = {
                row[1]
                for row in cursor.fetchall()
            }


            columns_to_add = {

                "post_type":
                    "TEXT",

                "abstract":
                    "TEXT",

                "research_authors":
                    "TEXT",

                "journal":
                    "TEXT",

                "publication_year":
                    "TEXT",

                "doi":
                    "TEXT",

                "external_link":
                    "TEXT",

                "research_file":
                    "TEXT"
            }


            for column, column_type in (
                columns_to_add.items()
            ):

                if column not in existing_columns:

                    cursor.execute(
                        f"""
                        ALTER TABLE post
                        ADD COLUMN {column}
                        {column_type}
                        """
                    )


            # ------------------------------------------------
            # NEW POST BLOCK TABLE
            # ------------------------------------------------

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS post_block (

                    id INTEGER PRIMARY KEY,

                    post_id INTEGER NOT NULL,

                    block_type VARCHAR(20) NOT NULL,

                    content TEXT,

                    position INTEGER NOT NULL DEFAULT 0,

                    created_at DATETIME,

                    FOREIGN KEY(post_id)
                    REFERENCES post(id)
                    ON DELETE CASCADE

                )
                """
            )


            connection.commit()
            connection.close()


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    page = request.args.get(
        "page",
        1,
        type=int
    )

    posts = (
        Post.query
        .filter_by(is_hidden=False)
        .order_by(Post.created_at.desc())
        .paginate(
            page=page,
            per_page=10,
            error_out=False
        )
    )

    return render_template(
        "index.html",
        posts=posts
    )


# ============================================================
# REGISTER
# ============================================================

@app.route("/register", methods=["GET", "POST"])
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
                "Username and password are required.",
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


        hashed_password = (
            generate_password_hash(password)
        )


        user = User(
            username=username,
            password=hashed_password
        )


        db.session.add(user)
        db.session.commit()


        flash(
            "Registration successful. Please log in.",
            "success"
        )


        return redirect(
            url_for("login")
        )


    return render_template(
        "register.html"
    )


# ============================================================
# LOGIN
# ============================================================

@app.route("/login", methods=["GET", "POST"])
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


        if (
            user
            and check_password_hash(
                user.password,
                password
            )
        ):

            login_user(user)

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


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
@login_required
def logout():

    logout_user()

    return redirect(
        url_for("home")
    )


# ============================================================
# SEARCH
# ============================================================

@app.route("/search")
def search():

    query = request.args.get(
        "q",
        ""
    ).strip()


    posts = []


    if query:

        search_pattern = f"%{query}%"


        posts = (
            Post.query
            .filter(
                Post.is_hidden == False,
                (
                    Post.title.ilike(search_pattern)
                    |
                    Post.content.ilike(search_pattern)
                    |
                    Post.category.ilike(search_pattern)
                )
            )
            .order_by(
                Post.created_at.desc()
            )
            .all()
        )


    return render_template(
        "search.html",
        posts=posts,
        query=query
    )


# ============================================================
# CATEGORY
# ============================================================

@app.route("/category/<category>")
def category(category):

    posts = (
        Post.query
        .filter_by(
            category=category,
            is_hidden=False
        )
        .order_by(
            Post.created_at.desc()
        )
        .all()
    )


    return render_template(
        "category.html",
        posts=posts,
        category=category
    )


# ============================================================
# PROFILE
# ============================================================

@app.route("/profile/<username>")
def profile(username):

    user = User.query.filter_by(
        username=username
    ).first_or_404()


    posts = (
        Post.query
        .filter_by(
            author_id=user.id,
            is_hidden=False
        )
        .order_by(
            Post.created_at.desc()
        )
        .all()
    )


    followers_count = Follow.query.filter_by(
        followed_id=user.id
    ).count()


    following_count = Follow.query.filter_by(
        follower_id=user.id
    ).count()


    is_following = False


    if current_user.is_authenticated:

        is_following = (
            Follow.query.filter_by(
                follower_id=current_user.id,
                followed_id=user.id
            ).first()
            is not None
        )


    return render_template(
        "profile.html",
        user=user,
        posts=posts,
        followers_count=followers_count,
        following_count=following_count,
        is_following=is_following
    )


# ============================================================
# FOLLOW / UNFOLLOW
# ============================================================

@app.route(
    "/follow/<int:user_id>",
    methods=["POST"]
)
@login_required
def follow(user_id):

    user = User.query.get_or_404(
        user_id
    )


    if user.id == current_user.id:

        flash(
            "You cannot follow yourself.",
            "error"
        )

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


        notification = Notification(
            user_id=user.id,
            message=(
                f"{current_user.username} "
                f"started following you."
            )
        )

        db.session.add(
            notification
        )


    db.session.commit()


    return redirect(
        url_for(
            "profile",
            username=user.username
        )
    )


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/dashboard")
@login_required
def dashboard():

    posts = (
        Post.query
        .filter_by(
            author_id=current_user.id
        )
        .order_by(
            Post.created_at.desc()
        )
        .all()
    )


    return render_template(
        "dashboard.html",
        posts=posts
    )


# ============================================================
# EDIT PROFILE
# ============================================================

@app.route(
    "/edit-profile",
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


        profile_image = request.files.get(
            "profile_image"
        )


        if (
            profile_image
            and profile_image.filename
        ):

            if allowed_image(
                profile_image.filename
            ):

                filename = secure_filename(
                    profile_image.filename
                )


                base, extension = (
                    os.path.splitext(
                        filename
                    )
                )


                filename = (
                    f"user_{current_user.id}_"
                    f"{int(datetime.utcnow().timestamp())}_"
                    f"{base}{extension}"
                )


                profile_image.save(
                    os.path.join(
                        app.config[
                            "UPLOAD_FOLDER"
                        ],
                        filename
                    )
                )


                current_user.profile_image = (
                    filename
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


# ============================================================
# CREATE POST
# ============================================================

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

        category = request.form.get(
            "category",
            ""
        ).strip()

        post_type = request.form.get(
            "post_type",
            "regular"
        ).strip().lower()


        abstract = request.form.get(
            "abstract",
            ""
        ).strip()

        research_authors = request.form.get(
            "research_authors",
            ""
        ).strip()

        journal = request.form.get(
            "journal",
            ""
        ).strip()

        publication_year = request.form.get(
            "publication_year",
            ""
        ).strip()

        doi = request.form.get(
            "doi",
            ""
        ).strip()

        external_link = request.form.get(
            "external_link",
            ""
        ).strip()


        if post_type not in [
            "regular",
            "research"
        ]:

            post_type = "regular"


        # ----------------------------------------------------
        # CONTENT BLOCKS
        # ----------------------------------------------------

        block_types = request.form.getlist(
            "block_type"
        )

        block_contents = request.form.getlist(
            "block_content"
        )


        if not title:

            flash(
                "Title is required.",
                "error"
            )

            return redirect(
                url_for("create")
            )


        if not block_types:

            flash(
                "Please add at least one content block.",
                "error"
            )

            return redirect(
                url_for("create")
            )


        # ----------------------------------------------------
        # CREATE POST
        # ----------------------------------------------------

        post = Post(

            title=title,

            content="",

            category=category,

            post_type=post_type,

            abstract=(
                abstract
                if post_type == "research"
                else None
            ),

            research_authors=(
                research_authors
                if post_type == "research"
                else None
            ),

            journal=(
                journal
                if post_type == "research"
                else None
            ),

            publication_year=(
                publication_year
                if post_type == "research"
                else None
            ),

            doi=(
                doi
                if post_type == "research"
                else None
            ),

            external_link=(
                external_link
                if post_type == "research"
                else None
            ),

            author_id=current_user.id,

            is_hidden=False

        )


        db.session.add(post)

        db.session.flush()


        # ----------------------------------------------------
        # CREATE BLOCKS
        # ----------------------------------------------------

        text_for_search = []

        position = 0


        for index, block_type in enumerate(
            block_types
        ):

            block_type = (
                block_type
                .strip()
                .lower()
            )


            if block_type not in [
                "text",
                "image",
                "video"
            ]:

                continue


            # =================================================
            # TEXT BLOCK
            # =================================================

            if block_type == "text":

                content = ""


                if index < len(
                    block_contents
                ):

                    content = (
                        block_contents[index]
                        .strip()
                    )


                if not content:

                    continue


                block = PostBlock(

                    post_id=post.id,

                    block_type="text",

                    content=content,

                    position=position

                )


                db.session.add(block)


                text_for_search.append(
                    content
                )


                position += 1


            # =================================================
            # IMAGE BLOCK
            # =================================================

            elif block_type == "image":

                image = None

                # Find the file belonging to this block.
                # The frontend names media files using block
                # positions, but we also check the uploaded
                # file list directly for reliability.

                file_key = f"block_file_{index}"

                image = request.files.get(file_key)

                if (
                    not image
                    or not image.filename
                ):

                    continue


                filename_original = image.filename.strip()


                if not allowed_image(
                    filename_original
                ):

                    flash(
                        f"Invalid image format: {filename_original}",
                        "error"
                    )

                    db.session.rollback()

                    return redirect(
                        url_for("create")
                    )


                filename = secure_filename(
                    filename_original
                )


                base, extension = (
                    os.path.splitext(
                        filename
                    )
                )


                filename = (
                    f"{current_user.id}_"
                    f"{int(datetime.utcnow().timestamp())}_"
                    f"{index}_"
                    f"{base}{extension}"
                )


                image.save(
                    os.path.join(
                        app.config[
                            "UPLOAD_FOLDER"
                        ],
                        filename
                    )
                )


                block = PostBlock(

                    post_id=post.id,

                    block_type="image",

                    content=filename,

                    position=position

                )


                db.session.add(block)

                position += 1


            # =================================================
            # VIDEO BLOCK
            # =================================================

            elif block_type == "video":

                video = None

                file_key = f"block_file_{index}"

                video = request.files.get(
                    file_key
                )


                if (
                    not video
                    or not video.filename
                ):

                    continue


                filename_original = video.filename.strip()


                if not allowed_video(
                    filename_original
                ):

                    flash(
                        f"Invalid video format: {filename_original}",
                        "error"
                    )

                    db.session.rollback()

                    return redirect(
                        url_for("create")
                    )


                filename = secure_filename(
                    filename_original
                )


                base, extension = (
                    os.path.splitext(
                        filename
                    )
                )


                filename = (
                    f"{current_user.id}_"
                    f"{int(datetime.utcnow().timestamp())}_"
                    f"{index}_"
                    f"{base}{extension}"
                )


                video.save(
                    os.path.join(
                        app.config[
                            "UPLOAD_FOLDER"
                        ],
                        filename
                    )
                )


                block = PostBlock(

                    post_id=post.id,

                    block_type="video",

                    content=filename,

                    position=position

                )


                db.session.add(block)

                position += 1

        # ----------------------------------------------------
        # CHECK CONTENT
        # ----------------------------------------------------

        if position == 0:

            db.session.rollback()

            flash(
                "Please add valid content to your post.",
                "error"
            )

            return redirect(
                url_for("create")
            )


        # ----------------------------------------------------
        # OLD CONTENT FIELD
        #
        # Keep text here for search/compatibility.
        # ----------------------------------------------------

        post.content = "\n\n".join(
            text_for_search
        )


        # ----------------------------------------------------
        # OLD FEATURED IMAGE
        # ----------------------------------------------------

        featured_image = request.files.get(
            "image"
        )


        if (
            featured_image
            and featured_image.filename
        ):

            if not allowed_image(
                featured_image.filename
            ):

                flash(
                    "Invalid featured image format.",
                    "error"
                )

                db.session.rollback()

                return redirect(
                    url_for("create")
                )


            filename = secure_filename(
                featured_image.filename
            )


            base, extension = (
                os.path.splitext(
                    filename
                )
            )


            filename = (
                f"{current_user.id}_"
                f"{int(datetime.utcnow().timestamp())}_"
                f"featured_"
                f"{base}{extension}"
            )


            featured_image.save(
                os.path.join(
                    app.config[
                        "UPLOAD_FOLDER"
                    ],
                    filename
                )
            )


            post.image = filename


        # ----------------------------------------------------
        # OLD FEATURED VIDEO
        # ----------------------------------------------------

        featured_video = request.files.get(
            "video"
        )


        if (
            featured_video
            and featured_video.filename
        ):

            if not allowed_video(
                featured_video.filename
            ):

                flash(
                    "Invalid featured video format.",
                    "error"
                )

                db.session.rollback()

                return redirect(
                    url_for("create")
                )


            filename = secure_filename(
                featured_video.filename
            )


            base, extension = (
                os.path.splitext(
                    filename
                )
            )


            filename = (
                f"{current_user.id}_"
                f"{int(datetime.utcnow().timestamp())}_"
                f"featured_"
                f"{base}{extension}"
            )


            featured_video.save(
                os.path.join(
                    app.config[
                        "UPLOAD_FOLDER"
                    ],
                    filename
                )
            )


            post.video = filename


        # ----------------------------------------------------
        # RESEARCH PDF
        # ----------------------------------------------------

        if post_type == "research":

            research_file = request.files.get(
                "research_file"
            )


            if (
                research_file
                and research_file.filename
            ):

                if not allowed_document(
                    research_file.filename
                ):

                    flash(
                        "Only PDF research files are allowed.",
                        "error"
                    )

                    db.session.rollback()

                    return redirect(
                        url_for("create")
                    )


                filename = secure_filename(
                    research_file.filename
                )


                base, extension = (
                    os.path.splitext(
                        filename
                    )
                )


                filename = (
                    f"{current_user.id}_"
                    f"{int(datetime.utcnow().timestamp())}_"
                    f"research_"
                    f"{base}{extension}"
                )


                research_file.save(
                    os.path.join(
                        app.config[
                            "UPLOAD_FOLDER"
                        ],
                        filename
                    )
                )


                post.research_file = filename


        # ----------------------------------------------------
        # SAVE
        # ----------------------------------------------------

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


# ============================================================
# VIEW POST
# ============================================================

@app.route("/post/<int:id>")
def post(id):

    post = Post.query.get_or_404(
        id
    )


    if post.is_hidden:

        if (
            not current_user.is_authenticated
            or (
                current_user.id
                != post.author_id
                and not current_user.is_admin
            )
        ):

            flash(
                "This post is currently hidden.",
                "error"
            )

            return redirect(
                url_for("home")
            )


    return render_template(
        "post.html",
        post=post
    )


# ============================================================
# LIKE
# ============================================================

@app.route(
    "/like/<int:post_id>",
    methods=["POST"]
)
@login_required
def like(post_id):

    post = Post.query.get_or_404(
        post_id
    )


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

            notification = Notification(
                user_id=post.author_id,
                message=(
                    f"{current_user.username} "
                    f"liked your post."
                ),
                post_id=post.id
            )

            db.session.add(
                notification
            )


    db.session.commit()


    return redirect(
        request.referrer
        or url_for(
            "post",
            id=post.id
        )
    )


# ============================================================
# COMMENT
# ============================================================

@app.route(
    "/comment/<int:post_id>",
    methods=["POST"]
)
@login_required
def comment(post_id):

    post = Post.query.get_or_404(
        post_id
    )


    content = request.form.get(
        "content",
        ""
    ).strip()


    if not content:

        flash(
            "Comment cannot be empty.",
            "error"
        )

        return redirect(
            url_for(
                "post",
                id=post.id
            )
        )


    new_comment = Comment(

        content=content,

        user_id=current_user.id,

        post_id=post.id

    )


    db.session.add(
        new_comment
    )


    if post.author_id != current_user.id:

        notification = Notification(

            user_id=post.author_id,

            message=(
                f"{current_user.username} "
                f"commented on your post."
            ),

            post_id=post.id

        )

        db.session.add(
            notification
        )


    db.session.commit()


    return redirect(
        url_for(
            "post",
            id=post.id
        )
    )


# ============================================================
# REPLY
# ============================================================

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

        flash(
            "Reply cannot be empty.",
            "error"
        )

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

        parent_id=parent_comment.id

    )


    db.session.add(
        new_reply
    )


    if (
        parent_comment.user_id
        != current_user.id
    ):

        notification = Notification(

            user_id=parent_comment.user_id,

            message=(
                f"{current_user.username} "
                f"replied to your comment."
            ),

            post_id=parent_comment.post_id

        )

        db.session.add(
            notification
        )


    db.session.commit()


    return redirect(
        url_for(
            "post",
            id=parent_comment.post_id
        )
    )


# ============================================================
# NOTIFICATIONS
# ============================================================

@app.route("/notifications")
@login_required
def notifications():

    notifications_list = (
        Notification.query
        .filter_by(
            user_id=current_user.id
        )
        .order_by(
            Notification.created_at.desc()
        )
        .all()
    )


    return render_template(
        "notifications.html",
        notifications=notifications_list
    )


# ============================================================
# MARK NOTIFICATION AS READ
# ============================================================

@app.route(
    "/notification/<int:id>/read"
)
@login_required
def notification_read(id):

    notification = (
        Notification.query
        .filter_by(
            id=id,
            user_id=current_user.id
        )
        .first_or_404()
    )


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
        url_for(
            "notifications"
        )
    )


# ============================================================
# EDIT POST
# ============================================================

@app.route(
    "/edit/<int:id>",
    methods=["GET", "POST"]
)
@login_required
def edit(id):

    post = Post.query.get_or_404(
        id
    )


    # --------------------------------------------------------
    # AUTHOR CHECK
    # --------------------------------------------------------

    if post.author_id != current_user.id:

        flash(
            "You are not allowed to edit this post.",
            "error"
        )

        return redirect(
            url_for(
                "post",
                id=post.id
            )
        )


    if request.method == "POST":

        title = request.form.get(
            "title",
            ""
        ).strip()

        category = request.form.get(
            "category",
            ""
        ).strip()


        if not title:

            flash(
                "Title is required.",
                "error"
            )

            return redirect(
                url_for(
                    "edit",
                    id=post.id
                )
            )


        # ----------------------------------------------------
        # BASIC POST INFORMATION
        # ----------------------------------------------------

        post.title = title

        post.category = category


        # ----------------------------------------------------
        # GET BLOCK DATA
        # ----------------------------------------------------

        block_types = request.form.getlist(
            "block_type"
        )

        block_contents = request.form.getlist(
            "block_content"
        )


        if not block_types:

            flash(
                "Please add at least one content block.",
                "error"
            )

            return redirect(
                url_for(
                    "edit",
                    id=post.id
                )
            )


        # ----------------------------------------------------
        # SAVE OLD BLOCK FILE NAMES
        #
        # This allows us to remove files later if necessary.
        # ----------------------------------------------------

        old_block_files = []

        for old_block in post.blocks:

            if old_block.block_type in [
                "image",
                "video"
            ]:

                if old_block.content:

                    old_block_files.append(
                        old_block.content
                    )


        # ----------------------------------------------------
        # DELETE OLD BLOCK RECORDS
        # ----------------------------------------------------

        for old_block in list(
            post.blocks
        ):

            db.session.delete(
                old_block
            )


        db.session.flush()


        # ----------------------------------------------------
        # CREATE NEW BLOCKS
        # ----------------------------------------------------

        text_for_search = []

        position = 0

        kept_files = []


        for index, block_type in enumerate(
            block_types
        ):

            block_type = (
                block_type
                .strip()
                .lower()
            )


            if block_type not in [
                "text",
                "image",
                "video"
            ]:

                continue


            # =================================================
            # TEXT
            # =================================================

            if block_type == "text":

                content = ""


                if index < len(
                    block_contents
                ):

                    content = (
                        block_contents[index]
                        .strip()
                    )


                if not content:

                    continue


                block = PostBlock(

                    post_id=post.id,

                    block_type="text",

                    content=content,

                    position=position

                )


                db.session.add(
                    block
                )


                text_for_search.append(
                    content
                )


                position += 1


            # =================================================
            # IMAGE
            # =================================================

            elif block_type == "image":

                old_filename = ""


                if index < len(
                    block_contents
                ):

                    old_filename = (
                        block_contents[index]
                        .strip()
                    )


                file_key = (
                    f"block_file_{index}"
                )


                image = request.files.get(
                    file_key
                )


                filename = old_filename


                # --------------------------------------------
                # NEW IMAGE
                # --------------------------------------------

                if (
                    image
                    and image.filename
                ):

                    if not allowed_image(
                        image.filename
                    ):

                        flash(
                            "Invalid image format.",
                            "error"
                        )

                        db.session.rollback()

                        return redirect(
                            url_for(
                                "edit",
                                id=post.id
                            )
                        )


                    filename = secure_filename(
                        image.filename
                    )


                    base, extension = (
                        os.path.splitext(
                            filename
                        )
                    )


                    filename = (
                        f"{current_user.id}_"
                        f"{int(datetime.utcnow().timestamp())}_"
                        f"edit_{index}_"
                        f"{base}{extension}"
                    )


                    image.save(
                        os.path.join(
                            app.config[
                                "UPLOAD_FOLDER"
                            ],
                            filename
                        )
                    )


                # --------------------------------------------
                # NO IMAGE
                # --------------------------------------------

                if not filename:

                    continue


                block = PostBlock(

                    post_id=post.id,

                    block_type="image",

                    content=filename,

                    position=position

                )


                db.session.add(
                    block
                )


                kept_files.append(
                    filename
                )


                position += 1


            # =================================================
            # VIDEO
            # =================================================

            elif block_type == "video":

                old_filename = ""


                if index < len(
                    block_contents
                ):

                    old_filename = (
                        block_contents[index]
                        .strip()
                    )


                file_key = (
                    f"block_file_{index}"
                )


                video = request.files.get(
                    file_key
                )


                filename = old_filename


                # --------------------------------------------
                # NEW VIDEO
                # --------------------------------------------

                if (
                    video
                    and video.filename
                ):

                    if not allowed_video(
                        video.filename
                    ):

                        flash(
                            "Invalid video format.",
                            "error"
                        )

                        db.session.rollback()

                        return redirect(
                            url_for(
                                "edit",
                                id=post.id
                            )
                        )


                    filename = secure_filename(
                        video.filename
                    )


                    base, extension = (
                        os.path.splitext(
                            filename
                        )
                    )


                    filename = (
                        f"{current_user.id}_"
                        f"{int(datetime.utcnow().timestamp())}_"
                        f"edit_{index}_"
                        f"{base}{extension}"
                    )


                    video.save(
                        os.path.join(
                            app.config[
                                "UPLOAD_FOLDER"
                            ],
                            filename
                        )
                    )


                # --------------------------------------------
                # NO VIDEO
                # --------------------------------------------

                if not filename:

                    continue


                block = PostBlock(

                    post_id=post.id,

                    block_type="video",

                    content=filename,

                    position=position

                )


                db.session.add(
                    block
                )


                kept_files.append(
                    filename
                )


                position += 1


        # ----------------------------------------------------
        # MAKE SURE CONTENT EXISTS
        # ----------------------------------------------------

        if position == 0:

            db.session.rollback()

            flash(
                "Please add at least one valid content block.",
                "error"
            )

            return redirect(
                url_for(
                    "edit",
                    id=post.id
                )
            )


        # ----------------------------------------------------
        # UPDATE LEGACY CONTENT FIELD
        # ----------------------------------------------------

        post.content = "\n\n".join(
            text_for_search
        )


        # ----------------------------------------------------
        # DELETE UNUSED OLD BLOCK FILES
        # ----------------------------------------------------

        for filename in old_block_files:

            if filename not in kept_files:

                file_path = os.path.join(
                    app.config[
                        "UPLOAD_FOLDER"
                    ],
                    filename
                )


                if os.path.exists(
                    file_path
                ):

                    try:

                        os.remove(
                            file_path
                        )

                    except OSError:

                        pass


        # ----------------------------------------------------
        # SAVE
        # ----------------------------------------------------

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


# ============================================================
# DELETE POST
# ============================================================

@app.route(
    "/delete/<int:id>",
    methods=["POST"]
)
@login_required
def delete(id):

    post = Post.query.get_or_404(
        id
    )


    if (
        post.author_id != current_user.id
        and not current_user.is_admin
    ):

        flash(
            "You are not allowed to delete this post.",
            "error"
        )

        return redirect(
            url_for(
                "post",
                id=post.id
            )
        )


    # --------------------------------------------------------
    # DELETE BLOCK FILES
    # --------------------------------------------------------

    for block in post.blocks:

        if block.content:

            if block.block_type in [
                "image",
                "video"
            ]:

                file_path = os.path.join(
                    app.config[
                        "UPLOAD_FOLDER"
                    ],
                    block.content
                )


                if os.path.exists(
                    file_path
                ):

                    try:

                        os.remove(
                            file_path
                        )

                    except OSError:

                        pass


    # --------------------------------------------------------
    # DELETE LEGACY MEDIA
    # --------------------------------------------------------

    legacy_files = []


    if post.image:

        legacy_files.append(
            post.image
        )


    if post.video:

        legacy_files.append(
            post.video
        )


    if post.research_file:

        legacy_files.append(
            post.research_file
        )


    for image in post.images:

        if image.filename:

            legacy_files.append(
                image.filename
            )


    for filename in legacy_files:

        file_path = os.path.join(
            app.config[
                "UPLOAD_FOLDER"
            ],
            filename
        )


        if os.path.exists(
            file_path
        ):

            try:

                os.remove(
                    file_path
                )

            except OSError:

                pass


    db.session.delete(
        post
    )

    db.session.commit()


    flash(
        "Post deleted successfully.",
        "success"
    )


    return redirect(
        url_for("home")
    )


# ============================================================
# ADMIN
# ============================================================

@app.route("/admin")
@login_required
def admin():

    if not current_user.is_admin:

        flash(
            "Admin access required.",
            "error"
        )

        return redirect(
            url_for("home")
        )


    users = (
        User.query
        .order_by(
            User.created_at.desc()
        )
        .all()
    )


    posts = (
        Post.query
        .order_by(
            Post.created_at.desc()
        )
        .all()
    )


    comments = (
        Comment.query
        .order_by(
            Comment.created_at.desc()
        )
        .all()
    )


    return render_template(
        "admin.html",
        users=users,
        posts=posts,
        comments=comments
    )


# ============================================================
# ADMIN TOGGLE USER
# ============================================================

@app.route(
    "/admin/user/<int:user_id>/toggle",
    methods=["POST"]
)
@login_required
def admin_toggle_user(user_id):

    if not current_user.is_admin:

        flash(
            "Admin access required.",
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
            "You cannot change your own admin status.",
            "error"
        )

        return redirect(
            url_for("admin")
        )


    user.is_admin = not user.is_admin

    db.session.commit()


    return redirect(
        url_for("admin")
    )


# ============================================================
# ADMIN DELETE USER
# ============================================================

@app.route(
    "/admin/user/<int:user_id>/delete",
    methods=["POST"]
)
@login_required
def admin_delete_user(user_id):

    if not current_user.is_admin:

        flash(
            "Admin access required.",
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
            "You cannot delete your own account.",
            "error"
        )

        return redirect(
            url_for("admin")
        )


    # Delete files belonging to user's posts
    for post in user.posts:

        for block in post.blocks:

            if (
                block.content
                and block.block_type in [
                    "image",
                    "video"
                ]
            ):

                file_path = os.path.join(
                    app.config[
                        "UPLOAD_FOLDER"
                    ],
                    block.content
                )


                if os.path.exists(
                    file_path
                ):

                    try:

                        os.remove(
                            file_path
                        )

                    except OSError:

                        pass


        files_to_delete = []


        if post.image:

            files_to_delete.append(
                post.image
            )


        if post.video:

            files_to_delete.append(
                post.video
            )


        if post.research_file:

            files_to_delete.append(
                post.research_file
            )


        for image in post.images:

            if image.filename:

                files_to_delete.append(
                    image.filename
                )


        for filename in files_to_delete:

            file_path = os.path.join(
                app.config[
                    "UPLOAD_FOLDER"
                ],
                filename
            )


            if os.path.exists(
                file_path
            ):

                try:

                    os.remove(
                        file_path
                    )

                except OSError:

                    pass


    db.session.delete(
        user
    )

    db.session.commit()


    flash(
        "User deleted successfully.",
        "success"
    )


    return redirect(
        url_for("admin")
    )


# ============================================================
# ADMIN HIDE POST
# ============================================================

@app.route(
    "/admin/post/<int:post_id>/hide",
    methods=["POST"]
)
@login_required
def admin_hide_post(post_id):

    if not current_user.is_admin:

        flash(
            "Admin access required.",
            "error"
        )

        return redirect(
            url_for("home")
        )


    post = Post.query.get_or_404(
        post_id
    )


    post.is_hidden = not post.is_hidden

    db.session.commit()


    return redirect(
        url_for("admin")
    )


# ============================================================
# ADMIN DELETE POST
# ============================================================

@app.route(
    "/admin/post/<int:post_id>/delete",
    methods=["POST"]
)
@login_required
def admin_delete_post(post_id):

    if not current_user.is_admin:

        flash(
            "Admin access required.",
            "error"
        )

        return redirect(
            url_for("home")
        )


    post = Post.query.get_or_404(
        post_id
    )


    # Delete block files
    for block in post.blocks:

        if (
            block.content
            and block.block_type in [
                "image",
                "video"
            ]
        ):

            file_path = os.path.join(
                app.config[
                    "UPLOAD_FOLDER"
                ],
                block.content
            )


            if os.path.exists(
                file_path
            ):

                try:

                    os.remove(
                        file_path
                    )

                except OSError:

                    pass


    # Delete legacy files
    files_to_delete = []


    if post.image:

        files_to_delete.append(
            post.image
        )


    if post.video:

        files_to_delete.append(
            post.video
        )


    if post.research_file:

        files_to_delete.append(
            post.research_file
        )


    for image in post.images:

        if image.filename:

            files_to_delete.append(
                image.filename
            )


    for filename in files_to_delete:

        file_path = os.path.join(
            app.config[
                "UPLOAD_FOLDER"
            ],
            filename
        )


        if os.path.exists(
            file_path
        ):

            try:

                os.remove(
                    file_path
                )

            except OSError:

                pass


    db.session.delete(
        post
    )

    db.session.commit()


    flash(
        "Post deleted successfully.",
        "success"
    )


    return redirect(
        url_for("admin")
    )


# ============================================================
# ADMIN HIDE COMMENT
# ============================================================

@app.route(
    "/admin/comment/<int:comment_id>/hide",
    methods=["POST"]
)
@login_required
def admin_hide_comment(comment_id):

    if not current_user.is_admin:

        flash(
            "Admin access required.",
            "error"
        )

        return redirect(
            url_for("home")
        )


    comment = Comment.query.get_or_404(
        comment_id
    )


    if hasattr(comment, "is_hidden"):

        comment.is_hidden = not comment.is_hidden

        db.session.commit()


    return redirect(
        url_for("admin")
    )


# ============================================================
# ADMIN DELETE COMMENT
# ============================================================

@app.route(
    "/admin/comment/<int:comment_id>/delete",
    methods=["POST"]
)
@login_required
def admin_delete_comment(comment_id):

    if not current_user.is_admin:

        flash(
            "Admin access required.",
            "error"
        )

        return redirect(
            url_for("home")
        )


    comment = Comment.query.get_or_404(
        comment_id
    )


    db.session.delete(
        comment
    )

    db.session.commit()


    flash(
        "Comment deleted successfully.",
        "success"
    )


    return redirect(
        url_for("admin")
    )


# ============================================================
# ROUTES
# ============================================================

@app.route("/routes")
def routes():

    route_list = []


    for rule in app.url_map.iter_rules():

        route_list.append(
            {
                "endpoint": rule.endpoint,
                "methods": sorted(
                    rule.methods
                ),
                "path": str(rule)
            }
        )


    return render_template(
        "routes.html",
        routes=route_list
    )


# ============================================================
# START APPLICATION
# ============================================================

with app.app_context():

    db.create_all()

    update_database()


if __name__ == "__main__":

    print(
        "MY UPDATED APP IS RUNNING."
    )

    app.run(
        debug=True
    )