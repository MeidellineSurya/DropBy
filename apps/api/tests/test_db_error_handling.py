import asyncio

from sqlalchemy.exc import IntegrityError

from app.main import db_constraint_error_handler


def test_db_constraint_errors_surface_as_422_not_500() -> None:
    exc = IntegrityError("INSERT ...", {}, Exception("constraint violated"))

    response = asyncio.run(db_constraint_error_handler(request=None, exc=exc))

    assert response.status_code == 422
    assert b"could not be saved" in response.body
