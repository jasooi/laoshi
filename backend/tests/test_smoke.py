def test_health_check(client):
    """GET /api/ should return 200 with the health check message."""
    response = client.get('/api/')
    assert response.status_code == 200


def test_words_requires_auth(client):
    """GET /api/words without a JWT should return 401."""
    response = client.get('/api/words')
    assert response.status_code == 401
