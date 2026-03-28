from fastapi.testclient import TestClient

from factory_analytics.main import app


client = TestClient(app)


def test_groups_page_renders_full_group_management():
    response = client.get("/groups")
    assert response.status_code == 200
    html = response.text
    assert "Groups" in html
    assert "Create Group" in html
    assert "Group Management" in html
