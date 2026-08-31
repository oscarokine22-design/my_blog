import os
import sqlite3


print("===================================")
print("DATABASE UPDATE SCRIPT STARTED")
print("===================================")


BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

DB_PATH = os.path.join(
    BASE_DIR,
    "blog.db"
)


print("Project folder:")
print(BASE_DIR)

print()

print("Database location:")
print(DB_PATH)

print()


if not os.path.exists(DB_PATH):

    print("ERROR: blog.db was not found.")

    input("Press Enter to close...")

    raise SystemExit


print("blog.db found successfully.")
print()


connection = sqlite3.connect(DB_PATH)

cursor = connection.cursor()


def get_columns(table_name):

    cursor.execute(
        f'PRAGMA table_info("{table_name}")'
    )

    return [
        row[1]
        for row in cursor.fetchall()
    ]


def add_column_if_missing(
    table_name,
    column_name,
    column_definition
):

    columns = get_columns(
        table_name
    )

    if column_name in columns:

        print(
            f"{table_name}.{column_name} already exists."
        )

    else:

        print(
            f"Adding {table_name}.{column_name}..."
        )

        cursor.execute(
            f'ALTER TABLE "{table_name}" '
            f'ADD COLUMN "{column_name}" '
            f'{column_definition}'
        )

        print(
            f"SUCCESS: {table_name}.{column_name} added."
        )


# ===================================
# POST TABLE
# ===================================

print("Checking Post table...")

post_columns = get_columns(
    "post"
)

print("Current Post columns:")

for column in post_columns:

    print(" -", column)

print()


add_column_if_missing(
    "post",
    "category",
    "VARCHAR(100)"
)

print()


# ===================================
# LIKE TABLE
# ===================================

print("Checking Like table...")

like_columns = get_columns(
    "like"
)

print("Current Like columns:")

for column in like_columns:

    print(" -", column)

print()


add_column_if_missing(
    "like",
    "created_at",
    "DATETIME"
)

print()


# ===================================
# COMMENT TABLE
# ===================================

print("Checking Comment table...")

comment_columns = get_columns(
    "comment"
)

print("Current Comment columns:")

for column in comment_columns:

    print(" -", column)

print()


add_column_if_missing(
    "comment",
    "created_at",
    "DATETIME"
)

print()


# ===================================
# FOLLOW TABLE
# ===================================

print("Checking Follow table...")

follow_columns = get_columns(
    "follow"
)

print("Current Follow columns:")

for column in follow_columns:

    print(" -", column)

print()


add_column_if_missing(
    "follow",
    "created_at",
    "DATETIME"
)

print()


# ===================================
# NOTIFICATION TABLE
# ===================================

print("Checking Notification table...")

notification_columns = get_columns(
    "notification"
)

print("Current Notification columns:")

for column in notification_columns:

    print(" -", column)

print()


add_column_if_missing(
    "notification",
    "post_id",
    "INTEGER"
)

add_column_if_missing(
    "notification",
    "notification_type",
    "VARCHAR(50)"
)

print()


# ===================================
# COMMIT
# ===================================

connection.commit()


# ===================================
# FINAL DATABASE CHECK
# ===================================

print("===================================")
print("FINAL DATABASE CHECK")
print("===================================")

tables = [
    "user",
    "post",
    "post_image",
    "like",
    "comment",
    "follow",
    "notification"
]


for table in tables:

    try:

        columns = get_columns(table)

        print()
        print(
            f"{table.upper()} TABLE:"
        )

        for column in columns:

            print(
                " -",
                column
            )

    except Exception as error:

        print(
            f"Could not check {table}: {error}"
        )


connection.close()


print()
print("===================================")
print("DATABASE UPDATE COMPLETE")
print("===================================")

print()
print("You can now run:")
print("python app.py")

print()

input("Press Enter to close...")