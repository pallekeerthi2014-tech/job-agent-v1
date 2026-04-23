def test_candidate_crud_flow(client) -> None:
    create_response = client.post(
        "/api/v1/candidates",
        json={
            "name": "Priya Claims Analyst",
            "assigned_employee": None,
            "work_authorization": "US Citizen",
            "years_experience": 6,
            "salary_min": 115000,
            "salary_unit": "year",
            "active": True,
        },
    )
    assert create_response.status_code == 201
    created = create_response.json()
    candidate_id = created["id"]

    list_response = client.get("/api/v1/candidates", params={"candidate_id": candidate_id})
    assert list_response.status_code == 200
    assert list_response.json()["meta"]["total"] == 1
    assert list_response.json()["items"][0]["name"] == "Priya Claims Analyst"

    get_response = client.get(f"/api/v1/candidates/{candidate_id}")
    assert get_response.status_code == 200
    assert get_response.json()["work_authorization"] == "US Citizen"

    update_response = client.put(
        f"/api/v1/candidates/{candidate_id}",
        json={
            "name": "Priya Senior Claims Analyst",
            "years_experience": 7,
            "active": False,
        },
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["name"] == "Priya Senior Claims Analyst"
    assert updated["years_experience"] == 7
    assert updated["active"] is False

    delete_response = client.delete(f"/api/v1/candidates/{candidate_id}")
    assert delete_response.status_code == 204

    missing_response = client.get(f"/api/v1/candidates/{candidate_id}")
    assert missing_response.status_code == 404
