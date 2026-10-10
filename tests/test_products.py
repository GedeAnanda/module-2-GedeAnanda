from app.extensions import db
from app.models import Category, Product


def test_get_products_empty(client):
    response = client.get('/products')
    assert response.status_code == 200
    assert response.get_json()['data'] == []


def test_get_products_with_data(client, sample_product):
    response = client.get('/products')
    assert response.status_code == 200

    data = response.get_json()['data']
    assert len(data) == 1
    assert data[0]['name'] == 'Laptop'


def test_get_products_includes_pagination(client, sample_product):
    response = client.get('/products')
    pagination = response.get_json()['pagination']

    assert pagination['page'] == 1
    assert pagination['total_items'] == 1
    assert pagination['total_pages'] == 1


def test_get_products_pagination_splits_pages(client, sample_category):
    for i in range(5):
        db.session.add(Product(
            category_id=sample_category.id,
            name=f'Product {i}',
            price=100,
            stock=5
        ))
    db.session.commit()

    response = client.get('/products?page=1&per_page=2')
    body = response.get_json()

    assert len(body['data']) == 2
    assert body['pagination']['total_items'] == 5
    assert body['pagination']['total_pages'] == 3


def test_get_products_filter_by_category(client, sample_product):
    other = Category(name='Books')
    db.session.add(other)
    db.session.commit()

    db.session.add(Product(category_id=other.id, name='Novel', price=50, stock=3))
    db.session.commit()

    response = client.get(f'/products?category_id={other.id}')
    data = response.get_json()['data']

    assert len(data) == 1
    assert data[0]['name'] == 'Novel'


def test_get_products_filter_by_is_active(client, sample_category):
    db.session.add(Product(
        category_id=sample_category.id, name='Active', price=10, stock=1, is_active=True
    ))
    db.session.add(Product(
        category_id=sample_category.id, name='Inactive', price=10, stock=1, is_active=False
    ))
    db.session.commit()

    response = client.get('/products?is_active=false')
    data = response.get_json()['data']

    assert len(data) == 1
    assert data[0]['name'] == 'Inactive'


def test_get_products_search_is_case_insensitive(client, sample_product):
    response = client.get('/products?search=lap')
    assert len(response.get_json()['data']) == 1

    response = client.get('/products?search=LAPTOP')
    assert len(response.get_json()['data']) == 1

    response = client.get('/products?search=zzz')
    assert response.get_json()['data'] == []


def test_get_product_by_id(client, sample_product):
    response = client.get(f'/products/{sample_product.id}')
    assert response.status_code == 200

    data = response.get_json()['data']
    assert data['name'] == 'Laptop'
    assert data['price'] == 1000.0
    assert data['stock'] == 10


def test_get_product_not_found(client):
    response = client.get('/products/9999')
    assert response.status_code == 404


def test_create_product(client, admin_headers, sample_category):
    response = client.post('/products', headers=admin_headers, json={
        "category_id": sample_category.id,
        "name": "Mouse",
        "price": 25.50,
        "stock": 100,
        "description": "Wireless mouse"
    })
    assert response.status_code == 201

    data = response.get_json()['data']
    assert data['name'] == 'Mouse'
    assert data['price'] == 25.50
    assert data['stock'] == 100
    assert data['is_active'] is True


def test_create_product_defaults_stock_to_zero(client, admin_headers, sample_category):
    response = client.post('/products', headers=admin_headers, json={
        "category_id": sample_category.id,
        "name": "Mouse",
        "price": 25
    })
    assert response.status_code == 201
    assert response.get_json()['data']['stock'] == 0


def test_create_product_with_image_url(client, admin_headers, sample_category):
    response = client.post('/products', headers=admin_headers, json={
        "category_id": sample_category.id,
        "name": "Mouse",
        "price": 25,
        "image_url": "https://cdn.example.com/mouse.png"
    })
    assert response.status_code == 201
    assert response.get_json()['data']['image_url'] == 'https://cdn.example.com/mouse.png'


def test_create_product_image_url_defaults_to_null(client, admin_headers, sample_category):
    response = client.post('/products', headers=admin_headers, json={
        "category_id": sample_category.id,
        "name": "Mouse",
        "price": 25
    })
    assert response.status_code == 201
    assert response.get_json()['data']['image_url'] is None


def test_create_product_invalid_image_url(client, admin_headers, sample_category):
    for bad in ("not-a-url", "ftp://example.com/a.png", 123, "https://" + "a" * 500):
        response = client.post('/products', headers=admin_headers, json={
            "category_id": sample_category.id,
            "name": "Mouse",
            "price": 25,
            "image_url": bad
        })
        assert response.status_code == 400, bad


def test_create_product_missing_fields(client, admin_headers):
    response = client.post('/products', headers=admin_headers, json={"name": "Mouse"})
    assert response.status_code == 400
    assert 'error' in response.get_json()


def test_create_product_blank_name(client, admin_headers, sample_category):
    response = client.post('/products', headers=admin_headers, json={
        "category_id": sample_category.id,
        "name": "   ",
        "price": 25
    })
    assert response.status_code == 400


def test_create_product_negative_price(client, admin_headers, sample_category):
    response = client.post('/products', headers=admin_headers, json={
        "category_id": sample_category.id,
        "name": "Mouse",
        "price": -10
    })
    assert response.status_code == 400


def test_create_product_non_numeric_price(client, admin_headers, sample_category):
    response = client.post('/products', headers=admin_headers, json={
        "category_id": sample_category.id,
        "name": "Mouse",
        "price": "abc"
    })
    assert response.status_code == 400


def test_create_product_negative_stock(client, admin_headers, sample_category):
    response = client.post('/products', headers=admin_headers, json={
        "category_id": sample_category.id,
        "name": "Mouse",
        "price": 25,
        "stock": -5
    })
    assert response.status_code == 400


def test_create_product_rejects_boolean_stock(client, admin_headers, sample_category):
    response = client.post('/products', headers=admin_headers, json={
        "category_id": sample_category.id,
        "name": "Mouse",
        "price": 25,
        "stock": True
    })
    assert response.status_code == 400


def test_create_product_unknown_category(client, admin_headers):
    response = client.post('/products', headers=admin_headers, json={
        "category_id": 9999,
        "name": "Mouse",
        "price": 25
    })
    assert response.status_code == 400


def test_create_product_requires_auth(client, sample_category):
    response = client.post('/products', json={
        "category_id": sample_category.id,
        "name": "Mouse",
        "price": 25
    })
    assert response.status_code == 401


def test_create_product_forbidden_for_customer(client, customer_headers, sample_category):
    response = client.post('/products', headers=customer_headers, json={
        "category_id": sample_category.id,
        "name": "Mouse",
        "price": 25
    })
    assert response.status_code == 403


def test_update_product(client, admin_headers, sample_product):
    response = client.put(f'/products/{sample_product.id}', headers=admin_headers, json={
        "name": "Gaming Laptop",
        "price": 1500
    })
    assert response.status_code == 200

    data = response.get_json()['data']
    assert data['name'] == 'Gaming Laptop'
    assert data['price'] == 1500.0
    assert data['stock'] == 10


def test_update_product_partial(client, admin_headers, sample_product):
    response = client.put(f'/products/{sample_product.id}', headers=admin_headers, json={
        "stock": 50
    })
    assert response.status_code == 200

    data = response.get_json()['data']
    assert data['stock'] == 50
    assert data['name'] == 'Laptop'


def test_update_product_image_url(client, admin_headers, sample_product):
    response = client.put(f'/products/{sample_product.id}', headers=admin_headers, json={
        "image_url": "https://cdn.example.com/laptop.jpg"
    })
    assert response.status_code == 200
    assert response.get_json()['data']['image_url'] == 'https://cdn.example.com/laptop.jpg'

    response = client.put(f'/products/{sample_product.id}', headers=admin_headers, json={
        "image_url": None
    })
    assert response.status_code == 200
    assert response.get_json()['data']['image_url'] is None


def test_update_product_invalid_image_url(client, admin_headers, sample_product):
    response = client.put(f'/products/{sample_product.id}', headers=admin_headers, json={
        "image_url": "javascript:alert(1)"
    })
    assert response.status_code == 400


def test_update_product_not_found(client, admin_headers):
    response = client.put('/products/9999', headers=admin_headers, json={"name": "Ghost"})
    assert response.status_code == 404


def test_update_product_negative_price(client, admin_headers, sample_product):
    response = client.put(f'/products/{sample_product.id}', headers=admin_headers, json={
        "price": -1
    })
    assert response.status_code == 400


def test_update_product_unknown_category(client, admin_headers, sample_product):
    response = client.put(f'/products/{sample_product.id}', headers=admin_headers, json={
        "category_id": 9999
    })
    assert response.status_code == 400


def test_update_product_forbidden_for_customer(client, customer_headers, sample_product):
    response = client.put(f'/products/{sample_product.id}', headers=customer_headers, json={
        "name": "Hacked"
    })
    assert response.status_code == 403


def test_delete_product(client, admin_headers, sample_product):
    response = client.delete(f'/products/{sample_product.id}', headers=admin_headers)
    assert response.status_code == 200

    follow_up = client.get(f'/products/{sample_product.id}')
    assert follow_up.status_code == 404


def test_delete_product_not_found(client, admin_headers):
    response = client.delete('/products/9999', headers=admin_headers)
    assert response.status_code == 404


def test_delete_product_with_orders_blocked(client, admin_headers, customer_headers, sample_product):
    order = client.post('/orders', headers=customer_headers, json={
        "items": [{"product_id": sample_product.id, "quantity": 1}]
    })
    assert order.status_code == 201

    response = client.delete(f'/products/{sample_product.id}', headers=admin_headers)
    assert response.status_code == 409
    assert 'error' in response.get_json()


def test_delete_product_forbidden_for_customer(client, customer_headers, sample_product):
    response = client.delete(f'/products/{sample_product.id}', headers=customer_headers)
    assert response.status_code == 403