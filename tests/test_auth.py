def test_register_success(client):
    response = client.post('/auth/register', json={
        "username": "nanda",
        "email": "nanda@test.com",
        "password": "password123"
    })
    assert response.status_code == 201

    data = response.get_json()['data']
    assert data['user']['email'] == 'nanda@test.com'
    assert data['user']['role'] == 'customer'
    assert 'access_token' not in data
    assert 'refresh_token' not in data


def test_register_does_not_expose_password(client):
    response = client.post('/auth/register', json={
        "username": "nanda",
        "email": "nanda@test.com",
        "password": "password123"
    })
    user = response.get_json()['data']['user']
    assert 'password' not in user
    assert 'password_hash' not in user


def test_register_normalizes_email(client):
    client.post('/auth/register', json={
        "username": "nanda",
        "email": "Nanda@Test.COM",
        "password": "password123"
    })

    response = client.post('/auth/login', json={
        "email": "nanda@test.com",
        "password": "password123"
    })
    assert response.status_code == 200


def test_register_duplicate_email(client):
    payload = {
        "username": "nanda",
        "email": "nanda@test.com",
        "password": "password123"
    }
    client.post('/auth/register', json=payload)

    response = client.post('/auth/register', json=payload)
    assert response.status_code == 409
    assert 'error' in response.get_json()


def test_register_short_password(client):
    response = client.post('/auth/register', json={
        "username": "nanda",
        "email": "nanda@test.com",
        "password": "short"
    })
    assert response.status_code == 400


def test_register_missing_fields(client):
    response = client.post('/auth/register', json={"email": "nanda@test.com"})
    assert response.status_code == 400


def test_register_blank_username(client):
    response = client.post('/auth/register', json={
        "username": "   ",
        "email": "nanda@test.com",
        "password": "password123"
    })
    assert response.status_code == 400


def test_register_empty_body(client):
    response = client.post('/auth/register', json={})
    assert response.status_code == 400


def test_login_success(client, customer_headers):
    response = client.post('/auth/login', json={
        "email": "customer@test.com",
        "password": "password123"
    })
    assert response.status_code == 200
    assert 'access_token' in response.get_json()['data']


def test_login_wrong_password(client, customer_headers):
    response = client.post('/auth/login', json={
        "email": "customer@test.com",
        "password": "wrongpassword"
    })
    assert response.status_code == 401


def test_login_unknown_email(client):
    response = client.post('/auth/login', json={
        "email": "ghost@test.com",
        "password": "password123"
    })
    assert response.status_code == 401


def test_login_missing_fields(client):
    response = client.post('/auth/login', json={"email": "nanda@test.com"})
    assert response.status_code == 400


def test_me_returns_current_user(client, customer_headers):
    response = client.get('/auth/me', headers=customer_headers)
    assert response.status_code == 200
    assert response.get_json()['data']['email'] == 'customer@test.com'


def test_me_requires_token(client):
    response = client.get('/auth/me')
    assert response.status_code == 401


def test_me_rejects_invalid_token(client):
    response = client.get('/auth/me', headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 422


def test_refresh_returns_new_access_token(client):
    client.post('/auth/register', json={
        "username": "nanda",
        "email": "nanda@test.com",
        "password": "password123"
    })
    login = client.post('/auth/login', json={
        "email": "nanda@test.com",
        "password": "password123"
    })
    refresh_token = login.get_json()['data']['refresh_token']

    response = client.post('/auth/refresh', headers={
        "Authorization": f"Bearer {refresh_token}"
    })
    assert response.status_code == 200
    assert 'access_token' in response.get_json()['data']


def test_refresh_rejects_access_token(client, customer_headers):
    response = client.post('/auth/refresh', headers=customer_headers)
    assert response.status_code == 422


def test_logout_revokes_token(client, customer_headers):
    logout = client.post('/auth/logout', headers=customer_headers)
    assert logout.status_code == 200

    response = client.get('/auth/me', headers=customer_headers)
    assert response.status_code == 401


def test_logout_requires_token(client):
    response = client.post('/auth/logout')
    assert response.status_code == 401