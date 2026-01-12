"""
Script para geração de massa de dados de teste para MySQL e PostgreSQL.

Gera dados realistas usando Faker e SQLAlchemy para testar o sistema de backup/restore.

Configuração:
- MySQL: 192.168.15.197:3306 (root/W123Mudar)
- PostgreSQL: 192.168.15.197:5432 (postgres/W123Mudar)
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path
import random

from sqlalchemy import (
    create_engine, Column, Integer, String, Text, Numeric, DateTime,
    Date, Enum, ForeignKey, Index, text
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.pool import NullPool
from faker import Faker

# Configurar Faker para português
fake = Faker('pt_BR')

# Configurações de conexão
MYSQL_HOST = '192.168.15.197'
MYSQL_PORT = 3306
MYSQL_USER = 'root'
MYSQL_PASSWORD = 'W123Mudar'

POSTGRESQL_HOST = '192.168.15.197'
POSTGRESQL_PORT = 5432
POSTGRESQL_USER = 'postgres'
POSTGRESQL_PASSWORD = 'W123Mudar'

# MySQL URLs
MYSQL_ADMIN_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/"
MYSQL_DB_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/test_ecommerce"

# PostgreSQL URLs
PG_ADMIN_URL = f"postgresql+psycopg://{POSTGRESQL_USER}:{POSTGRESQL_PASSWORD}@{POSTGRESQL_HOST}:{POSTGRESQL_PORT}/postgres"
PG_DB_URL = f"postgresql+psycopg://{POSTGRESQL_USER}:{POSTGRESQL_PASSWORD}@{POSTGRESQL_HOST}:{POSTGRESQL_PORT}/test_inventory"


def print_header(message):
    """Imprime cabeçalho formatado."""
    print("\n" + "=" * 80)
    print(f"  {message}")
    print("=" * 80)


def print_success(message):
    """Imprime mensagem de sucesso."""
    print(f"✅ {message}")


def print_info(message):
    """Imprime mensagem informativa."""
    print(f"📊 {message}")


# ============================================================================
# MySQL Models
# ============================================================================

MySQLBase = declarative_base()


class Customer(MySQLBase):
    __tablename__ = 'customers'
    
    customer_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    phone = Column(String(20))
    cpf = Column(String(14), unique=True)
    birth_date = Column(Date)
    created_at = Column(DateTime, default=datetime.now)
    
    orders = relationship("Order", back_populates="customer")
    
    __table_args__ = (
        Index('idx_email', 'email'),
        Index('idx_cpf', 'cpf'),
    )


class Product(MySQLBase):
    __tablename__ = 'products'
    
    product_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(100))
    price = Column(Numeric(10, 2), nullable=False)
    stock_quantity = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    
    order_items = relationship("OrderItem", back_populates="product")
    
    __table_args__ = (
        Index('idx_category', 'category'),
    )


class Order(MySQLBase):
    __tablename__ = 'orders'
    
    order_id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey('customers.customer_id'), nullable=False)
    order_date = Column(DateTime, default=datetime.now)
    total_amount = Column(Numeric(10, 2), nullable=False)
    status = Column(
        Enum('pending', 'processing', 'shipped', 'delivered', 'cancelled', name='order_status'),
        default='pending'
    )
    
    customer = relationship("Customer", back_populates="orders")
    order_items = relationship("OrderItem", back_populates="order")
    
    __table_args__ = (
        Index('idx_customer', 'customer_id'),
        Index('idx_status', 'status'),
        Index('idx_date', 'order_date'),
    )


class OrderItem(MySQLBase):
    __tablename__ = 'order_items'
    
    item_id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey('orders.order_id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.product_id'), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    
    order = relationship("Order", back_populates="order_items")
    product = relationship("Product", back_populates="order_items")
    
    __table_args__ = (
        Index('idx_order', 'order_id'),
    )


# ============================================================================
# PostgreSQL Models
# ============================================================================

PostgreSQLBase = declarative_base()


class Supplier(PostgreSQLBase):
    __tablename__ = 'suppliers'
    
    supplier_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    phone = Column(String(20))
    cnpj = Column(String(18), unique=True)
    address = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    
    inventory_items = relationship("InventoryItem", back_populates="supplier")


class Category(PostgreSQLBase):
    __tablename__ = 'categories'
    
    category_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    
    inventory_items = relationship("InventoryItem", back_populates="category")


class InventoryItem(PostgreSQLBase):
    __tablename__ = 'inventory_items'
    
    item_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    category_id = Column(Integer, ForeignKey('categories.category_id'))
    supplier_id = Column(Integer, ForeignKey('suppliers.supplier_id'))
    quantity = Column(Integer, default=0)
    unit_price = Column(Numeric(10, 2), nullable=False)
    location = Column(String(100))
    last_updated = Column(DateTime, default=datetime.now)
    
    category = relationship("Category", back_populates="inventory_items")
    supplier = relationship("Supplier", back_populates="inventory_items")
    stock_movements = relationship("StockMovement", back_populates="item")
    
    __table_args__ = (
        Index('idx_items_category', 'category_id'),
        Index('idx_items_supplier', 'supplier_id'),
    )


class StockMovement(PostgreSQLBase):
    __tablename__ = 'stock_movements'
    
    movement_id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(Integer, ForeignKey('inventory_items.item_id'))
    movement_type = Column(String(20), nullable=False)  # IN, OUT, ADJUSTMENT
    quantity = Column(Integer, nullable=False)
    reference_number = Column(String(50))
    movement_date = Column(DateTime, default=datetime.now)
    notes = Column(Text)
    
    item = relationship("InventoryItem", back_populates="stock_movements")
    
    __table_args__ = (
        Index('idx_movements_item', 'item_id'),
        Index('idx_movements_date', 'movement_date'),
    )


# ============================================================================
# MySQL Setup and Data Generation
# ============================================================================

def setup_mysql_database():
    """Cria database e tabelas MySQL."""
    print_header("MYSQL - Setup Database")
    
    # Conectar como admin para criar database
    engine = create_engine(MYSQL_ADMIN_URL, poolclass=NullPool, echo=False)
    
    with engine.connect() as conn:
        # Dropar e criar database
        conn.execute(text("DROP DATABASE IF EXISTS test_ecommerce"))
        conn.execute(text("CREATE DATABASE test_ecommerce CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
        conn.commit()
    
    engine.dispose()
    print_success("Database 'test_ecommerce' criado")
    
    # Conectar ao database e criar tabelas
    engine = create_engine(MYSQL_DB_URL, poolclass=NullPool, echo=False)
    MySQLBase.metadata.create_all(engine)
    engine.dispose()
    
    print_success("Tabelas criadas: customers, products, orders, order_items")
    
    return True


def generate_mysql_data():
    """Gera massa de dados MySQL."""
    print_header("MYSQL - Gerando Massa de Dados")
    
    engine = create_engine(MYSQL_DB_URL, poolclass=NullPool, echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Gerar clientes
        print_info("Gerando 1.000 clientes...")
        customers = []
        for i in range(1000):
            customer = Customer(
                name=fake.name(),
                email=fake.unique.email(),
                phone=fake.phone_number(),
                cpf=fake.unique.cpf(),
                birth_date=fake.date_of_birth(minimum_age=18, maximum_age=80)
            )
            customers.append(customer)
            
            if (i + 1) % 200 == 0:
                session.bulk_save_objects(customers)
                session.commit()
                customers = []
        
        if customers:
            session.bulk_save_objects(customers)
            session.commit()
        
        print_success("1.000 clientes inseridos")
        
        # Gerar produtos
        print_info("Gerando 500 produtos...")
        categories = ['Eletrônicos', 'Roupas', 'Livros', 'Alimentos', 'Móveis', 'Esportes', 'Beleza', 'Brinquedos']
        products = []
        for i in range(500):
            product = Product(
                name=fake.catch_phrase(),
                description=fake.text(max_nb_chars=200),
                category=random.choice(categories),
                price=round(random.uniform(10.0, 5000.0), 2),
                stock_quantity=random.randint(0, 1000)
            )
            products.append(product)
            
            if (i + 1) % 100 == 0:
                session.bulk_save_objects(products)
                session.commit()
                products = []
        
        if products:
            session.bulk_save_objects(products)
            session.commit()
        
        print_success("500 produtos inseridos")
        
        # Gerar pedidos
        print_info("Gerando 2.000 pedidos...")
        statuses = ['pending', 'processing', 'shipped', 'delivered', 'cancelled']
        orders = []
        for i in range(2000):
            order = Order(
                customer_id=random.randint(1, 1000),
                order_date=fake.date_time_between(start_date='-1y', end_date='now'),
                total_amount=round(random.uniform(50.0, 5000.0), 2),
                status=random.choice(statuses)
            )
            orders.append(order)
            
            if (i + 1) % 400 == 0:
                session.bulk_save_objects(orders)
                session.commit()
                orders = []
        
        if orders:
            session.bulk_save_objects(orders)
            session.commit()
        
        print_success("2.000 pedidos inseridos")
        
        # Gerar itens dos pedidos
        print_info("Gerando itens dos pedidos...")
        order_items = []
        for order_id in range(1, 2001):
            num_items = random.randint(3, 5)
            for _ in range(num_items):
                item = OrderItem(
                    order_id=order_id,
                    product_id=random.randint(1, 500),
                    quantity=random.randint(1, 10),
                    unit_price=round(random.uniform(10.0, 1000.0), 2)
                )
                order_items.append(item)
                
                if len(order_items) >= 1000:
                    session.bulk_save_objects(order_items)
                    session.commit()
                    order_items = []
        
        if order_items:
            session.bulk_save_objects(order_items)
            session.commit()
        
        total_items = session.query(OrderItem).count()
        print_success(f"{total_items} itens de pedidos inseridos")
        
        session.commit()
        print_success("Massa de dados MySQL gerada com sucesso!")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Erro ao gerar dados MySQL: {e}")
        raise
    finally:
        session.close()
        engine.dispose()


def create_mysql_users():
    """Cria usuários MySQL para teste."""
    print_header("MYSQL - Criando Usuários de Teste")
    
    engine = create_engine(MYSQL_ADMIN_URL, poolclass=NullPool, echo=False)
    
    users_config = [
        ("app_user", "App123!", "%", "SELECT, INSERT, UPDATE, DELETE ON test_ecommerce.*"),
        ("readonly_user", "Read123!", "localhost", "SELECT ON test_ecommerce.*"),
        ("backup_user", "Backup123!", "%", "SELECT, SHOW VIEW, LOCK TABLES, RELOAD ON *.*"),
        ("analytics_user", "Analytics123!", "%", "SELECT ON test_ecommerce.*"),
    ]
    
    with engine.connect() as conn:
        for username, password, host, privileges in users_config:
            # Dropar usuário se existir
            conn.execute(text(f"DROP USER IF EXISTS '{username}'@'{host}'"))
            
            # Criar usuário
            conn.execute(text(f"CREATE USER '{username}'@'{host}' IDENTIFIED BY '{password}'"))
            
            # Conceder privilégios
            conn.execute(text(f"GRANT {privileges} TO '{username}'@'{host}'"))
            
            print_success(f"{username}@{host} criado")
        
        conn.execute(text("FLUSH PRIVILEGES"))
        conn.commit()
    
    engine.dispose()
    print_success("Usuários MySQL criados com sucesso!")


# ============================================================================
# PostgreSQL Setup and Data Generation
# ============================================================================

def setup_postgresql_database():
    """Cria database e tabelas PostgreSQL."""
    print_header("POSTGRESQL - Setup Database")
    
    # Conectar como admin para criar database
    engine = create_engine(PG_ADMIN_URL, isolation_level="AUTOCOMMIT", poolclass=NullPool, echo=False)
    
    with engine.connect() as conn:
        # Dropar e criar database
        conn.execute(text("DROP DATABASE IF EXISTS test_inventory"))
        conn.execute(text("CREATE DATABASE test_inventory"))
    
    engine.dispose()
    print_success("Database 'test_inventory' criado")
    
    # Conectar ao database e criar tabelas
    engine = create_engine(PG_DB_URL, poolclass=NullPool, echo=False)
    PostgreSQLBase.metadata.create_all(engine)
    engine.dispose()
    
    print_success("Tabelas criadas: suppliers, categories, inventory_items, stock_movements")
    
    return True


def generate_postgresql_data():
    """Gera massa de dados PostgreSQL."""
    print_header("POSTGRESQL - Gerando Massa de Dados")
    
    engine = create_engine(PG_DB_URL, poolclass=NullPool, echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Gerar fornecedores
        print_info("Gerando 200 fornecedores...")
        suppliers = []
        for i in range(200):
            supplier = Supplier(
                name=fake.company(),
                email=fake.unique.company_email(),
                phone=fake.phone_number(),
                cnpj=fake.unique.cnpj(),
                address=fake.address()
            )
            suppliers.append(supplier)
        
        session.bulk_save_objects(suppliers)
        session.commit()
        print_success("200 fornecedores inseridos")
        
        # Gerar categorias
        print_info("Gerando 50 categorias...")
        categories_list = [
            'Eletrônicos', 'Informática', 'Móveis', 'Papelaria', 'Limpeza',
            'Ferramentas', 'Elétrica', 'Hidráulica', 'Construção', 'Automotivo',
            'Esportivo', 'Vestuário', 'Alimentação', 'Bebidas', 'Higiene',
            'Cosméticos', 'Farmácia', 'Livros', 'Brinquedos', 'Pet Shop',
            'Jardinagem', 'Decoração', 'Cama/Mesa/Banho', 'Utilidades', 'Embalagens',
            'Segurança', 'Telecomunicações', 'Audio/Video', 'Fotografia', 'Games',
            'Musical', 'Arte', 'Artesanato', 'Camping', 'Pesca',
            'Ciclismo', 'Academia', 'Natação', 'Futebol', 'Tênis',
            'Eletrodomésticos', 'Linha Branca', 'Climatização', 'Iluminação', 'Refrigeração',
            'Eletroportáteis', 'Informação', 'Escritório', 'Escolar', 'Industrial'
        ]
        
        categories = []
        for cat_name in categories_list:
            category = Category(
                name=cat_name,
                description=f"Categoria de {cat_name}"
            )
            categories.append(category)
        
        session.bulk_save_objects(categories)
        session.commit()
        print_success("50 categorias inseridas")
        
        # Gerar itens de inventário
        print_info("Gerando 1.500 itens de inventário...")
        locations = ['A1', 'A2', 'A3', 'B1', 'B2', 'B3', 'C1', 'C2', 'C3', 'D1', 'D2', 'D3']
        items = []
        for i in range(1500):
            item = InventoryItem(
                name=fake.catch_phrase(),
                description=fake.text(max_nb_chars=150),
                category_id=random.randint(1, 50),
                supplier_id=random.randint(1, 200),
                quantity=random.randint(0, 500),
                unit_price=round(random.uniform(5.0, 2000.0), 2),
                location=random.choice(locations)
            )
            items.append(item)
            
            if (i + 1) % 300 == 0:
                session.bulk_save_objects(items)
                session.commit()
                items = []
        
        if items:
            session.bulk_save_objects(items)
            session.commit()
        
        print_success("1.500 itens inseridos")
        
        # Gerar movimentações
        print_info("Gerando 5.000 movimentações de estoque...")
        movement_types = ['IN', 'OUT', 'ADJUSTMENT']
        movements = []
        for i in range(5000):
            movement = StockMovement(
                item_id=random.randint(1, 1500),
                movement_type=random.choice(movement_types),
                quantity=random.randint(1, 100),
                reference_number=f"REF-{random.randint(10000, 99999)}",
                movement_date=fake.date_time_between(start_date='-6m', end_date='now'),
                notes=fake.text(max_nb_chars=100) if random.random() > 0.7 else None
            )
            movements.append(movement)
            
            if (i + 1) % 1000 == 0:
                session.bulk_save_objects(movements)
                session.commit()
                movements = []
        
        if movements:
            session.bulk_save_objects(movements)
            session.commit()
        
        print_success("5.000 movimentações inseridas")
        
        session.commit()
        print_success("Massa de dados PostgreSQL gerada com sucesso!")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Erro ao gerar dados PostgreSQL: {e}")
        raise
    finally:
        session.close()
        engine.dispose()


def create_postgresql_roles():
    """Cria roles PostgreSQL para teste."""
    print_header("POSTGRESQL - Criando Roles de Teste")
    
    # Conectar ao postgres database para criar roles
    engine = create_engine(PG_ADMIN_URL, isolation_level="AUTOCOMMIT", poolclass=NullPool, echo=False)
    
    roles_config = [
        ("app_role", "App123Pg!", True, "Aplicação principal"),
        ("readonly_role", "Read123Pg!", True, "Leitura apenas"),
        ("backup_role", "Backup123Pg!", True, "Backup do banco"),
        ("analytics_role", "Analytics123Pg!", True, "Análise de dados"),
        ("admin_group", None, False, "Grupo de administradores"),
    ]
    
    with engine.connect() as conn:
        for rolename, password, can_login, description in roles_config:
            # Dropar role se existir
            conn.execute(text(f"DROP ROLE IF EXISTS {rolename}"))
            
            # Criar role
            if can_login and password:
                conn.execute(text(f"CREATE ROLE {rolename} WITH LOGIN PASSWORD '{password}'"))
            else:
                conn.execute(text(f"CREATE ROLE {rolename}"))
            
            # Adicionar comentário
            conn.execute(text(f"COMMENT ON ROLE {rolename} IS '{description}'"))
            
            login_status = "LOGIN" if can_login else "NOLOGIN"
            print_success(f"{rolename} ({login_status}) criado")
    
    engine.dispose()
    
    # Conectar ao test_inventory para conceder permissões
    engine = create_engine(PG_DB_URL, isolation_level="AUTOCOMMIT", poolclass=NullPool, echo=False)
    
    with engine.connect() as conn:
        # App role - CRUD completo
        conn.execute(text("GRANT CONNECT ON DATABASE test_inventory TO app_role"))
        conn.execute(text("GRANT USAGE ON SCHEMA public TO app_role"))
        conn.execute(text("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_role"))
        conn.execute(text("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_role"))
        
        # Readonly role - apenas leitura
        conn.execute(text("GRANT CONNECT ON DATABASE test_inventory TO readonly_role"))
        conn.execute(text("GRANT USAGE ON SCHEMA public TO readonly_role"))
        conn.execute(text("GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_role"))
        
        # Backup role - leitura completa
        conn.execute(text("GRANT CONNECT ON DATABASE test_inventory TO backup_role"))
        conn.execute(text("GRANT USAGE ON SCHEMA public TO backup_role"))
        conn.execute(text("GRANT SELECT ON ALL TABLES IN SCHEMA public TO backup_role"))
        
        # Analytics role - leitura completa
        conn.execute(text("GRANT CONNECT ON DATABASE test_inventory TO analytics_role"))
        conn.execute(text("GRANT USAGE ON SCHEMA public TO analytics_role"))
        conn.execute(text("GRANT SELECT ON ALL TABLES IN SCHEMA public TO analytics_role"))
    
    engine.dispose()
    print_success("Roles PostgreSQL criadas e permissões concedidas!")


# ============================================================================
# Verificação e Resumo
# ============================================================================

def verify_data():
    """Verifica os dados gerados."""
    print_header("VERIFICAÇÃO DE DADOS")
    
    # Verificar MySQL
    print("\n🐬 MYSQL (test_ecommerce):")
    engine = create_engine(MYSQL_DB_URL, poolclass=NullPool, echo=False)
    with engine.connect() as conn:
        tables = ['customers', 'products', 'orders', 'order_items']
        for table in tables:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.scalar()
            print(f"   • {table}: {count:,} registros")
        
        # Verificar usuários
        result = conn.execute(text("""
            SELECT User, Host FROM mysql.user 
            WHERE User NOT IN ('root', 'mysql.sys', 'mysql.session', 'mysql.infoschema')
            ORDER BY User
        """))
        users = result.fetchall()
        print(f"\n   Usuários criados: {len(users)}")
        for user, host in users:
            print(f"   • {user}@{host}")
    
    engine.dispose()
    
    # Verificar PostgreSQL
    print("\n🐘 POSTGRESQL (test_inventory):")
    engine = create_engine(PG_DB_URL, poolclass=NullPool, echo=False)
    with engine.connect() as conn:
        tables = ['suppliers', 'categories', 'inventory_items', 'stock_movements']
        for table in tables:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.scalar()
            print(f"   • {table}: {count:,} registros")
        
        # Verificar roles
        result = conn.execute(text("""
            SELECT rolname, rolcanlogin FROM pg_roles 
            WHERE rolname NOT LIKE 'pg_%' AND rolname != 'postgres'
            ORDER BY rolname
        """))
        roles = result.fetchall()
        print(f"\n   Roles criadas: {len(roles)}")
        for rolename, can_login in roles:
            login_status = "LOGIN" if can_login else "NOLOGIN"
            print(f"   • {rolename} ({login_status})")
    
    engine.dispose()


def print_summary():
    """Imprime resumo final."""
    print_header("🎉 AMBIENTE DE TESTE CONFIGURADO COM SUCESSO!")
    
    summary = f"""
📍 SERVIDOR: {MYSQL_HOST}

🐬 MYSQL (porta {MYSQL_PORT})
   Database: test_ecommerce
   Usuário Admin: {MYSQL_USER} / {MYSQL_PASSWORD}
   
   Tabelas com dados:
   • customers: 1.000 registros
   • products: 500 registros
   • orders: 2.000 registros
   • order_items: ~8.000 registros
   
   Usuários de teste:
   • app_user@% - CRUD completo
   • readonly_user@localhost - Somente leitura
   • backup_user@% - Backup permissions
   • analytics_user@% - Analytics

🐘 POSTGRESQL (porta {POSTGRESQL_PORT})
   Database: test_inventory
   Usuário Admin: {POSTGRESQL_USER} / {POSTGRESQL_PASSWORD}
   
   Tabelas com dados:
   • suppliers: 200 registros
   • categories: 50 registros
   • inventory_items: 1.500 registros
   • stock_movements: 5.000 registros
   
   Roles de teste:
   • app_role (LOGIN) - CRUD completo
   • readonly_role (LOGIN) - Somente leitura
   • backup_role (LOGIN) - Backup permissions
   • analytics_role (LOGIN) - Analytics
   • admin_group (NOLOGIN) - Grupo admin

📋 PRÓXIMOS PASSOS:
   1. Testar backup de databases usando VYA BackupDB
   2. Testar backup de usuários/roles
   3. Testar restore em ambiente limpo
   4. Validar integridade dos dados

✅ Ambiente pronto para testes de backup/restore!
"""
    print(summary)


# ============================================================================
# Main
# ============================================================================

def main():
    """Função principal."""
    try:
        print_header("GERADOR DE MASSA DE DADOS - VYA BACKUPDB")
        print(f"Iniciando em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # MySQL
        setup_mysql_database()
        generate_mysql_data()
        create_mysql_users()
        
        # PostgreSQL
        setup_postgresql_database()
        generate_postgresql_data()
        create_postgresql_roles()
        
        # Verificação
        verify_data()
        
        # Resumo
        print_summary()
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Erro durante execução: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
