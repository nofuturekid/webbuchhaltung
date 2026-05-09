async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_unknown_route_returns_404(client):
    response = await client.get("/nonexistent")
    assert response.status_code == 404
