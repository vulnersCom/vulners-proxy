from fastapi import APIRouter


class Router(APIRouter):
    settings: NotImplemented
    cache: NotImplemented
    session: NotImplemented
    logger: NotImplemented
