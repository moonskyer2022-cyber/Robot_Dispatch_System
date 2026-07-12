import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import backend.auth as auth_module
import backend.main as main_module
from backend.database import Base, get_db


class ApiFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(cls.engine)
        cls.session_factory = sessionmaker(bind=cls.engine, autoflush=False)
        cls.original_session_local = main_module.SessionLocal
        cls.original_username = auth_module.ADMIN_USERNAME
        cls.original_password = auth_module.ADMIN_PASSWORD
        cls.original_app_env = auth_module.APP_ENV

        auth_module.ADMIN_USERNAME = "admin"
        auth_module.ADMIN_PASSWORD = "test-password"
        auth_module.APP_ENV = "test"
        main_module.SessionLocal = cls.session_factory

        def override_get_db():
            db = cls.session_factory()
            try:
                yield db
            finally:
                db.close()

        main_module.app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(main_module.app)
        cls.client.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)
        main_module.app.dependency_overrides.clear()
        main_module.SessionLocal = cls.original_session_local
        auth_module.ADMIN_USERNAME = cls.original_username
        auth_module.ADMIN_PASSWORD = cls.original_password
        auth_module.APP_ENV = cls.original_app_env
        cls.engine.dispose()

    def setUp(self):
        self.client.cookies.clear()

    def test_protected_route_requires_login(self):
        response = self.client.get("/api/robots")

        self.assertEqual(401, response.status_code)

    def test_database_failure_has_actionable_startup_error(self):
        with patch.object(
            main_module,
            "SessionLocal",
            side_effect=SQLAlchemyError("db down"),
        ):
            with self.assertRaises(RuntimeError) as raised:
                main_module.initialize_application()

        self.assertIn("Database initialization failed", str(raised.exception))

    def test_login_create_and_dispatch_flow(self):
        login = self.client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "test-password"},
        )
        self.assertEqual(200, login.status_code)
        self.assertTrue(login.json()["authenticated"])

        robots = self.client.get("/api/robots")
        self.assertEqual(200, robots.status_code)
        self.assertGreaterEqual(len(robots.json()), 1)

        task = self.client.post(
            "/api/tasks",
            json={
                "type": "delivery",
                "priority": 8,
                "start_node": "A01",
                "end_node": "D01",
            },
        )
        self.assertEqual(200, task.status_code)

        dispatch = self.client.post("/api/dispatch/run")
        self.assertEqual(200, dispatch.status_code)
        self.assertTrue(dispatch.json()["assigned"])


if __name__ == "__main__":
    unittest.main()
