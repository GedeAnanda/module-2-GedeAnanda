from app.extensions import db
from app.models import Order, Product


def _create_order(client, headers, product_id, quantity=1):
    return client.post('/orders', headers=headers, json={
        "items": [{"product_id": product_id, "quantity": quantity}]
    })


def _register_other_user(client):
    client.post('/auth/register', json={
        "username": "other",
        "email": "other@test.com",
        "password": "password123"
    })
    login = client.post('/auth/login', json={
        "email": "other@test.com",
        "password": "password123"
    })
    return {"Authorization": f"Bearer {login.get_json()['data']['access_token']}"}


def test_create_order(client, customer_headers, sample_product):
    response = _create_order(client, customer_headers, sample_product.id, 2)
    assert response.status_code == 201

    data = response.get_json()['data']
    assert data['status'] == 'pending'
    assert data['total_amount'] == 2000.0
    assert len(data['items']) == 1
    assert data['items'][0]['quantity'] == 2
    assert data['items'][0]['subtotal'] == 2000.0


def test_create_order_includes_product_details(client, customer_headers, sample_product):
    response = _create_order(client, customer_headers, sample_product.id)

    item = response.get_json()['data']['items'][0]
    assert item['product']['name'] == 'Laptop'


def test_create_order_reduces_stock(client, customer_headers, sample_product):
    _create_order(client, customer_headers, sample_product.id, 3)

    response = client.get(f'/products/{sample_product.id}')
    assert response.get_json()['data']['stock'] == 7


def test_create_order_records_price_at_time_of_purchase(
    client, admin_headers, customer_headers, sample_product
):
    order = _create_order(client, customer_headers, sample_product.id, 1)
    order_id = order.get_json()['data']['id']

    client.put(f'/products/{sample_product.id}', headers=admin_headers, json={"price": 5000})

    response = client.get(f'/orders/{order_id}', headers=customer_headers)
    item = response.get_json()['data']['items'][0]

    assert item['price'] == 1000.0


def test_create_order_merges_duplicate_products(client, customer_headers, sample_product):
    response = client.post('/orders', headers=customer_headers, json={
        "items": [
            {"product_id": sample_product.id, "quantity": 2},
            {"product_id": sample_product.id, "quantity": 3}
        ]
    })
    assert response.status_code == 201

    data = response.get_json()['data']
    assert len(data['items']) == 1
    assert data['items'][0]['quantity'] == 5
    assert data['total_amount'] == 5000.0


def test_create_order_with_multiple_products(client, customer_headers, sample_category, sample_product):
    second = Product(category_id=sample_category.id, name='Mouse', price=50, stock=20)
    db.session.add(second)
    db.session.commit()

    response = client.post('/orders', headers=customer_headers, json={
        "items": [
            {"product_id": sample_product.id, "quantity": 1},
            {"product_id": second.id, "quantity": 2}
        ]
    })
    assert response.status_code == 201

    data = response.get_json()['data']
    assert len(data['items']) == 2
    assert data['total_amount'] == 1100.0


def test_create_order_insufficient_stock(client, customer_headers, sample_product):
    response = _create_order(client, customer_headers, sample_product.id, 999)
    assert response.status_code == 409
    assert 'error' in response.get_json()


def test_create_order_does_not_change_stock_when_rejected(client, customer_headers, sample_product):
    _create_order(client, customer_headers, sample_product.id, 999)

    response = client.get(f'/products/{sample_product.id}')
    assert response.get_json()['data']['stock'] == 10


def test_create_order_inactive_product(client, customer_headers, sample_category):
    inactive = Product(
        category_id=sample_category.id, name='Discontinued',
        price=100, stock=5, is_active=False
    )
    db.session.add(inactive)
    db.session.commit()

    response = _create_order(client, customer_headers, inactive.id)
    assert response.status_code == 409


def test_create_order_unknown_product(client, customer_headers):
    response = _create_order(client, customer_headers, 9999)
    assert response.status_code == 404


def test_create_order_empty_items(client, customer_headers):
    response = client.post('/orders', headers=customer_headers, json={"items": []})
    assert response.status_code == 400


def test_create_order_items_not_a_list(client, customer_headers):
    response = client.post('/orders', headers=customer_headers, json={"items": "not a list"})
    assert response.status_code == 400


def test_create_order_zero_quantity(client, customer_headers, sample_product):
    response = _create_order(client, customer_headers, sample_product.id, 0)
    assert response.status_code == 400


def test_create_order_negative_quantity(client, customer_headers, sample_product):
    response = _create_order(client, customer_headers, sample_product.id, -1)
    assert response.status_code == 400


def test_create_order_requires_auth(client, sample_product):
    response = client.post('/orders', json={
        "items": [{"product_id": sample_product.id, "quantity": 1}]
    })
    assert response.status_code == 401


def test_get_orders_only_returns_own(client, customer_headers, sample_product):
    _create_order(client, customer_headers, sample_product.id)

    other_headers = _register_other_user(client)

    response = client.get('/orders', headers=other_headers)
    assert response.status_code == 200
    assert response.get_json()['data'] == []


def test_get_orders_admin_sees_all(client, admin_headers, customer_headers, sample_product):
    _create_order(client, customer_headers, sample_product.id)

    response = client.get('/orders', headers=admin_headers)
    assert response.status_code == 200
    assert len(response.get_json()['data']) == 1


def test_get_orders_filter_by_status(client, customer_headers, sample_product):
    _create_order(client, customer_headers, sample_product.id)

    response = client.get('/orders?status=pending', headers=customer_headers)
    assert len(response.get_json()['data']) == 1

    response = client.get('/orders?status=shipped', headers=customer_headers)
    assert response.get_json()['data'] == []


def test_get_orders_invalid_status(client, customer_headers):
    response = client.get('/orders?status=nonsense', headers=customer_headers)
    assert response.status_code == 400


def test_get_order_by_id(client, customer_headers, sample_product):
    order = _create_order(client, customer_headers, sample_product.id)
    order_id = order.get_json()['data']['id']

    response = client.get(f'/orders/{order_id}', headers=customer_headers)
    assert response.status_code == 200
    assert response.get_json()['data']['id'] == order_id


def test_get_order_not_found(client, customer_headers):
    response = client.get('/orders/9999', headers=customer_headers)
    assert response.status_code == 404


def test_get_order_of_another_user_returns_404(client, customer_headers, sample_product):
    order = _create_order(client, customer_headers, sample_product.id)
    order_id = order.get_json()['data']['id']

    other_headers = _register_other_user(client)

    response = client.get(f'/orders/{order_id}', headers=other_headers)
    assert response.status_code == 404


def test_update_order_status_as_admin(client, admin_headers, customer_headers, sample_product):
    order = _create_order(client, customer_headers, sample_product.id)
    order_id = order.get_json()['data']['id']

    response = client.put(f'/orders/{order_id}/status', headers=admin_headers, json={
        "status": "shipped"
    })
    assert response.status_code == 200
    assert response.get_json()['data']['status'] == 'shipped'


def test_update_order_status_forbidden_for_customer(client, customer_headers, sample_product):
    order = _create_order(client, customer_headers, sample_product.id)
    order_id = order.get_json()['data']['id']

    response = client.put(f'/orders/{order_id}/status', headers=customer_headers, json={
        "status": "shipped"
    })
    assert response.status_code == 403


def test_update_order_status_invalid_value(client, admin_headers, customer_headers, sample_product):
    order = _create_order(client, customer_headers, sample_product.id)
    order_id = order.get_json()['data']['id']

    response = client.put(f'/orders/{order_id}/status', headers=admin_headers, json={
        "status": "teleported"
    })
    assert response.status_code == 400


def test_update_order_status_missing_value(client, admin_headers, customer_headers, sample_product):
    order = _create_order(client, customer_headers, sample_product.id)
    order_id = order.get_json()['data']['id']

    response = client.put(f'/orders/{order_id}/status', headers=admin_headers, json={})
    assert response.status_code == 400


def test_cancel_order_restores_stock(client, customer_headers, sample_product):
    order = _create_order(client, customer_headers, sample_product.id, 4)
    order_id = order.get_json()['data']['id']

    response = client.post(f'/orders/{order_id}/cancel', headers=customer_headers)
    assert response.status_code == 200
    assert response.get_json()['data']['status'] == 'cancelled'

    product = client.get(f'/products/{sample_product.id}')
    assert product.get_json()['data']['stock'] == 10


def test_cancel_order_twice_is_rejected(client, customer_headers, sample_product):
    order = _create_order(client, customer_headers, sample_product.id, 2)
    order_id = order.get_json()['data']['id']

    client.post(f'/orders/{order_id}/cancel', headers=customer_headers)
    response = client.post(f'/orders/{order_id}/cancel', headers=customer_headers)

    assert response.status_code == 409

    product = client.get(f'/products/{sample_product.id}')
    assert product.get_json()['data']['stock'] == 10


def test_cancel_shipped_order_is_rejected(client, admin_headers, customer_headers, sample_product):
    order = _create_order(client, customer_headers, sample_product.id)
    order_id = order.get_json()['data']['id']

    client.put(f'/orders/{order_id}/status', headers=admin_headers, json={"status": "shipped"})

    response = client.post(f'/orders/{order_id}/cancel', headers=customer_headers)
    assert response.status_code == 409


def test_cancel_order_of_another_user_returns_404(client, customer_headers, sample_product):
    order = _create_order(client, customer_headers, sample_product.id)
    order_id = order.get_json()['data']['id']

    other_headers = _register_other_user(client)

    response = client.post(f'/orders/{order_id}/cancel', headers=other_headers)
    assert response.status_code == 404