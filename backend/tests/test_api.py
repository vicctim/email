import time

from fastapi.testclient import TestClient


def test_admin_crud_sites_accounts_rules(client: TestClient, auth_headers: dict[str, str]) -> None:
    suffix = int(time.time() * 1000)

    site_response = client.post(
        "/api/sites",
        json={
            "name": f"Smoke WP {suffix}",
            "base_url": f"https://wp-smoke-{suffix}.test",
            "username": "admin",
            "app_password": "secret",
            "default_status": "draft",
        },
        headers=auth_headers,
    )
    assert site_response.status_code == 201, site_response.text
    site_id = site_response.json()["id"]

    account_response = client.post(
        "/api/accounts",
        json={
            "name": f"Smoke Gmail {suffix}",
            "username": f"smoke-{suffix}@gmail.com",
            "password": "secret",
        },
        headers=auth_headers,
    )
    assert account_response.status_code == 201, account_response.text
    account_id = account_response.json()["id"]

    rule_response = client.post(
        "/api/rules",
        json={
            "name": f"Smoke Rule {suffix}",
            "email_account_id": account_id,
            "wordpress_site_id": site_id,
            "sender_contains": "example.com",
            "subject_regex": "Release",
        },
        headers=auth_headers,
    )
    assert rule_response.status_code == 201, rule_response.text
    rule_id = rule_response.json()["id"]

    assert client.get("/api/sites", headers=auth_headers).status_code == 200
    assert client.get("/api/accounts", headers=auth_headers).status_code == 200
    assert client.get("/api/rules", headers=auth_headers).status_code == 200

    toggle_response = client.patch(f"/api/rules/{rule_id}/toggle", headers=auth_headers)
    assert toggle_response.status_code == 200
    assert toggle_response.json()["active"] is False

    stats_response = client.get("/api/dashboard/stats", headers=auth_headers)
    assert stats_response.status_code == 200
    assert {"published_today", "pending", "processing", "errors"} <= set(stats_response.json())

    logs_response = client.get("/api/logs", headers=auth_headers)
    assert logs_response.status_code == 200
    events = {item["event"] for item in logs_response.json()}
    assert {"admin_login", "site_created", "account_created", "rule_created"} <= events

    assert client.delete(f"/api/rules/{rule_id}", headers=auth_headers).status_code == 204
    assert client.delete(f"/api/accounts/{account_id}", headers=auth_headers).status_code == 204
    assert client.delete(f"/api/sites/{site_id}", headers=auth_headers).status_code == 204
