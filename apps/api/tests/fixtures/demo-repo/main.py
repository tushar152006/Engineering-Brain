def authenticate_user(token: str) -> bool:
    return token == "dev-token"


def index_repository(path: str) -> str:
    return path
