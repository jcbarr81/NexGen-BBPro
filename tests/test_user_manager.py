import bcrypt
import pytest
from utils.user_manager import load_users, add_user, update_user


def test_add_user(tmp_path):
    users_file = tmp_path / "users.txt"
    admin_hash = bcrypt.hashpw(b"pass", bcrypt.gensalt()).decode()
    users_file.write_text(f"admin,{admin_hash},admin,\n")

    add_user("newuser", "pw", "owner", "LAX", file_path=str(users_file))

    users = load_users(str(users_file))
    new_user = next(u for u in users if u["username"] == "newuser")
    assert new_user["team_id"] == "LAX"
    assert bcrypt.checkpw(b"pw", new_user["password"].encode())


def test_duplicate_username(tmp_path):
    users_file = tmp_path / "users.txt"
    admin_hash = bcrypt.hashpw(b"pass", bcrypt.gensalt()).decode()
    user_hash = bcrypt.hashpw(b"pw", bcrypt.gensalt()).decode()
    users_file.write_text(f"admin,{admin_hash},admin,\nuser1,{user_hash},owner,LAX\n")

    with pytest.raises(ValueError):
        add_user("user1", "pw", "owner", "ARG", file_path=str(users_file))


def test_duplicate_team(tmp_path):
    users_file = tmp_path / "users.txt"
    admin_hash = bcrypt.hashpw(b"pass", bcrypt.gensalt()).decode()
    user_hash = bcrypt.hashpw(b"pw", bcrypt.gensalt()).decode()
    users_file.write_text(f"admin,{admin_hash},admin,\nuser1,{user_hash},owner,LAX\n")

    with pytest.raises(ValueError):
        add_user("user2", "pw", "owner", "LAX", file_path=str(users_file))


def test_update_password(tmp_path):
    users_file = tmp_path / "users.txt"
    old_hash = bcrypt.hashpw(b"old", bcrypt.gensalt()).decode()
    users_file.write_text(f"user1,{old_hash},owner,LAX\n")

    update_user("user1", new_password="new", file_path=str(users_file))

    users = load_users(str(users_file))
    updated = next(u for u in users if u["username"] == "user1")
    assert bcrypt.checkpw(b"new", updated["password"].encode())


def test_update_team(tmp_path):
    users_file = tmp_path / "users.txt"
    pw_hash = bcrypt.hashpw(b"pw", bcrypt.gensalt()).decode()
    users_file.write_text(f"user1,{pw_hash},owner,LAX\n")

    update_user("user1", new_team_id="ARG", file_path=str(users_file))

    users = load_users(str(users_file))
    assert any(u["username"] == "user1" and u["team_id"] == "ARG" for u in users)


def test_update_team_conflict(tmp_path):
    users_file = tmp_path / "users.txt"
    pw1_hash = bcrypt.hashpw(b"pw", bcrypt.gensalt()).decode()
    pw2_hash = bcrypt.hashpw(b"pw", bcrypt.gensalt()).decode()
    users_file.write_text(
        f"user1,{pw1_hash},owner,LAX\nuser2,{pw2_hash},owner,ARG\n"
    )

    with pytest.raises(ValueError):
        update_user("user1", new_team_id="ARG", file_path=str(users_file))
