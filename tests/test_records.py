def test_analyst_create_list_record(client, analyst_headers, analyst_user, engine):
    r = client.post(
        "/records",
        headers=analyst_headers,
        json={
            "amount": 100.5,
            "type": "income",
            "category": "salary",
            "date": "2024-01-15",
            "notes": "monthly",
        },
    )
    assert r.status_code == 201, r.text
    rid = r.json()["id"]

    r = client.get("/records", headers=analyst_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 1
    assert any(x["id"] == rid for x in data["items"])

    r = client.get(f"/records/{rid}", headers=analyst_headers)
    assert r.status_code == 200


def test_viewer_cannot_create_record(client, viewer_headers):
    r = client.post(
        "/records",
        headers=viewer_headers,
        json={
            "amount": 10,
            "type": "expense",
            "category": "coffee",
            "date": "2024-02-01",
        },
    )
    assert r.status_code == 403


def test_search_q_parameter(client, analyst_headers, engine, analyst_user):
    client.post(
        "/records",
        headers=analyst_headers,
        json={
            "amount": 20,
            "type": "expense",
            "category": "groceries",
            "date": "2024-03-01",
            "notes": "weekly shop",
        },
    )
    r = client.get("/records?q=grocer", headers=analyst_headers)
    assert r.status_code == 200
    assert r.json()["total"] >= 1


def test_soft_delete(client, analyst_headers, analyst_user):
    r = client.post(
        "/records",
        headers=analyst_headers,
        json={
            "amount": 5,
            "type": "expense",
            "category": "x",
            "date": "2024-04-01",
        },
    )
    rid = r.json()["id"]
    r = client.delete(f"/records/{rid}", headers=analyst_headers)
    assert r.status_code == 204
    r = client.get(f"/records/{rid}", headers=analyst_headers)
    assert r.status_code == 404
