import json


def _register_and_login(client):
    """Helper: register a test user and log in, return access token and response (with cookies)."""
    client.post('/api/users', json={
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'TestPass123'
    })
    response = client.post('/api/token', json={
        'username': 'testuser',
        'password': 'TestPass123'
    })
    return response


def test_login_returns_access_token_and_sets_refresh_cookie(client):
    """POST /api/token should return access_token in body and set refresh cookie."""
    response = _register_and_login(client)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'access_token' in data
    # Check that a Set-Cookie header was set for the refresh token
    cookies = response.headers.getlist('Set-Cookie')
    refresh_cookie_set = any('refresh_token' in c for c in cookies)
    assert refresh_cookie_set


def test_refresh_returns_new_access_token(client):
    """POST /api/token/refresh with valid refresh cookie returns new access token."""
    _register_and_login(client)
    # The test client automatically stores cookies
    refresh_response = client.post('/api/token/refresh')
    assert refresh_response.status_code == 200
    data = json.loads(refresh_response.data)
    assert 'access_token' in data


def test_refresh_blocklists_old_token(client, db):
    """After refresh, the old refresh token's jti should be in the blocklist."""
    from models import TokenBlocklist
    _register_and_login(client)
    # First refresh
    client.post('/api/token/refresh')
    # The blocklist should now have at least one entry
    assert db.session.query(TokenBlocklist).count() >= 1


def test_revoke_blocklists_and_clears_cookie(client, db):
    """POST /api/token/revoke should blocklist the token and clear the cookie."""
    from models import TokenBlocklist
    _register_and_login(client)
    initial_count = db.session.query(TokenBlocklist).count()
    revoke_response = client.post('/api/token/revoke')
    assert revoke_response.status_code == 200
    data = json.loads(revoke_response.data)
    assert data['message'] == 'Token revoked'
    assert db.session.query(TokenBlocklist).count() > initial_count


def test_refresh_with_revoked_token_fails(client):
    """After revoking, refresh should fail with 401."""
    _register_and_login(client)
    client.post('/api/token/revoke')
    refresh_response = client.post('/api/token/refresh')
    assert refresh_response.status_code == 401


def test_protected_endpoint_with_expired_or_missing_token(client):
    """GET /api/me without a valid access token should return 401."""
    response = client.get('/api/me')
    assert response.status_code == 401


def test_registration_rejects_weak_password(client):
    """POST /api/users should reject passwords that don't meet requirements."""
    # Test password too short
    response = client.post('/api/users', json={
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'short'
    })
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'at least 8 characters' in data['error'].lower()

    # Test password without uppercase
    response = client.post('/api/users', json={
        'username': 'testuser2',
        'email': 'test2@example.com',
        'password': 'password123'
    })
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'uppercase' in data['error'].lower()

    # Test password without lowercase
    response = client.post('/api/users', json={
        'username': 'testuser3',
        'email': 'test3@example.com',
        'password': 'PASSWORD123'
    })
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'lowercase' in data['error'].lower()

    # Test password without number
    response = client.post('/api/users', json={
        'username': 'testuser4',
        'email': 'test4@example.com',
        'password': 'PasswordOnly'
    })
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'number' in data['error'].lower()

    # Test password with special characters
    response = client.post('/api/users', json={
        'username': 'testuser5',
        'email': 'test5@example.com',
        'password': 'Password123!'
    })
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'only letters and numbers' in data['error'].lower()


def test_registration_accepts_valid_password(client):
    """POST /api/users should accept passwords that meet all requirements."""
    response = client.post('/api/users', json={
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'ValidPass123'
    })
    assert response.status_code == 201
