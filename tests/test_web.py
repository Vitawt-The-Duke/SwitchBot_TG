import unittest
from unittest.mock import patch, AsyncMock
from starlette.testclient import TestClient
from app.web import app


class TestWeb(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_check(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    @patch("app.web.bot_client.press", new_callable=AsyncMock)
    def test_api_press(self, mock_press):
        mock_press.return_value = {"success": True, "message": "Action press executed successfully!"}
        response = self.client.post("/api/press")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        mock_press.assert_awaited_once()

    @patch("app.web.bot_client.turn_on", new_callable=AsyncMock)
    def test_api_on(self, mock_on):
        mock_on.return_value = {"success": True, "message": "Action on executed successfully!"}
        response = self.client.post("/api/on")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        mock_on.assert_awaited_once()

    @patch("app.web.bot_client.turn_off", new_callable=AsyncMock)
    def test_api_off(self, mock_off):
        mock_off.return_value = {"success": True, "message": "Action off executed successfully!"}
        response = self.client.post("/api/off")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        mock_off.assert_awaited_once()

    @patch("app.web.bot_client.get_info", new_callable=AsyncMock)
    def test_api_info(self, mock_info):
        mock_info.return_value = {
            "success": True,
            "message": "Device info retrieved successfully",
            "data": {"battery": 95, "firmware": 4.9, "switchMode": False}
        }
        response = self.client.get("/api/info")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["battery"], 95)
        mock_info.assert_awaited_once()

    def test_index_page(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("SwitchBot S1", response.text)


if __name__ == "__main__":
    unittest.main()
