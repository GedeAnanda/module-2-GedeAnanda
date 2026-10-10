from app.extensions import db

class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
    updated_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now(), onupdate=db.func.now())
    
    products = db.relationship('Product', backref='category', lazy=True)
    
    def to_dict(self) : 
        return{
            "id" : self.id,
            "name": self.name,
            "description" : self.description, 
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    
class Product(db.Model):
    __tablename__ = 'products'
    __table_args__=(
        db.CheckConstraint('price >=0', name='products_price_check'),
        db.CheckConstraint('stock >=0', name='products_stock_check')
    )
    
    id = db.Column(db.Integer, primary_key=True)
    category_id=db.Column(
        db.Integer, 
        db.ForeignKey('categories.id', ondelete='RESTRICT', onupdate='CASCADE')
    )
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Numeric(12, 2), nullable=False)
    stock = db.Column(db.Integer, nullable=False, server_default=db.text('0'))
    description = db.Column(db.Text)
    image_url = db.Column(db.String(500))
    is_active = db.Column(db.Boolean, server_default=db.text('true'))
    created_at = db.Column(
        db.DateTime(timezone=True), 
        server_default=db.func.now()
    )

    updated_at = db.Column(
        db.DateTime(timezone=True), 
        server_default=db.func.now(), 
        onupdate=db.func.now()
    )

    def to_dict(self):
        return {
            "id": self.id,
            "category_id": self.category_id,
            "name": self.name,
            "price": float(self.price),
            "stock": self.stock,
            "description": self.description,
            "image_url": self.image_url,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }