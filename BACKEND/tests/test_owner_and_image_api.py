\
"""Integration smoke tests for ARIA ORIGINAL account and image-edit API."""
import os
import tempfile
import unittest
from unittest.mock import patch

os.environ["ARIA_DB_PATH"] = tempfile.mktemp(suffix=".sqlite3")
os.environ["ARIA_OWNER_BOOTSTRAP_TOKEN"] = "test-bootstrap-token-" + ("x" * 24)
os.environ["OPENAI_API_KEY"] = "test-provider-key"
os.environ["ARIA_MAX_IMAGE_BYTES"] = "1048576"

from fastapi.testclient import TestClient
import app.main as api


class FakeResponse:
    status_code = 200
    def json(self):
        return {"data": [{"b64_json": "ZmFrZQ=="}]}


class FakeAsyncClient:
    last = None
    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs
        FakeAsyncClient.last = self
    async def __aenter__(self):
        return self
    async def __aexit__(self, *args):
        return False
    async def post(self, url, **kwargs):
        self.url = url
        self.post_kwargs = kwargs
        return FakeResponse()


class OwnerAndImageApiTests(unittest.TestCase):
    def test_owner_lockdown_entitlements_and_image_edit_upload(self):
        client = TestClient(api.app)
        self.assertEqual(client.get("/health").status_code, 200)

        user = client.post("/auth/register", json={
            "email": "ordinary@example.com", "password": "StrongPassword123!"
        })
        self.assertEqual(user.status_code, 200, user.text)
        user_headers = {"Authorization": "Bearer " + user.json()["token"]}

        self.assertEqual(client.get("/admin/overview", headers=user_headers).status_code, 403)

        owner = client.post("/owner/bootstrap", json={
            "email": "owner@example.com",
            "password": "OwnerStrongPassword123!",
            "bootstrap_token": os.environ["ARIA_OWNER_BOOTSTRAP_TOKEN"]
        })
        self.assertEqual(owner.status_code, 200, owner.text)
        owner_headers = {"Authorization": "Bearer " + owner.json()["token"]}

        second_owner = client.post("/owner/bootstrap", json={
            "email": "second@example.com",
            "password": "AnotherStrongPassword123!",
            "bootstrap_token": os.environ["ARIA_OWNER_BOOTSTRAP_TOKEN"]
        })
        self.assertEqual(second_owner.status_code, 409)

        grant = client.patch("/admin/users/1/plan", headers=owner_headers,
                             json={"plan": "PREMIUM", "source": "owner_grant"})
        self.assertEqual(grant.status_code, 200, grant.text)
        counts = client.get("/admin/overview", headers=owner_headers).json()
        self.assertEqual(counts["premium_free_granted"], 1)
        self.assertEqual(counts["premium_paid"], 0)
        self.assertEqual(counts["free_users"], 0)

        paid_without_billing = client.patch(
            "/admin/users/1/plan", headers=owner_headers,
            json={"plan": "PREMIUM", "source": "paid"}
        )
        self.assertEqual(paid_without_billing.status_code, 409)

        with patch.object(api.httpx, "AsyncClient", FakeAsyncClient):
            edit = client.post(
                "/v1/images/edits", headers=user_headers,
                files={"image": ("portrait.png", b"fake-image-bytes", "image/png")},
                data={"prompt": "Αφαίρεσε το φόντο", "quality": "medium", "output_format": "png"}
            )
        self.assertEqual(edit.status_code, 200, edit.text)
        sent_file = FakeAsyncClient.last.post_kwargs["files"]["image"]
        self.assertEqual(sent_file[0], "portrait.png")
        self.assertEqual(sent_file[1], b"fake-image-bytes")
        self.assertEqual(sent_file[2], "image/png")
        self.assertEqual(FakeAsyncClient.last.url, "https://api.openai.com/v1/images/edits")
        self.assertEqual(FakeAsyncClient.last.post_kwargs["data"]["quality"], "medium")
        self.assertEqual(FakeAsyncClient.last.post_kwargs["data"]["output_format"], "png")


if __name__ == "__main__":
    unittest.main()
