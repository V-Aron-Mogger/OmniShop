import os
import sqlite3
from flask import Flask, render_template, request, jsonify
import random
import datetime

app = Flask(__name__)
DB_NAME = 'omnidrop.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Products table
    c.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        cost_price REAL NOT NULL,
        retail_price REAL NOT NULL,
        image_url TEXT,
        category TEXT,
        source TEXT, -- 'AliExpress' or 'Temu'
        supplier_item_id TEXT,
        rating REAL,
        sales_count INTEGER
    )''')

    # Orders table
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_ref TEXT UNIQUE,
        customer_name TEXT,
        customer_email TEXT,
        shipping_address TEXT,
        total_amount REAL,
        wallet_profit REAL,
        status TEXT, -- 'Pending', 'Processing with Supplier', 'Shipped', 'Delivered'
        supplier_order_id TEXT,
        created_at TEXT
    )''')

    # Order items table
    c.execute('''CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_ref TEXT,
        product_id INTEGER,
        title TEXT,
        quantity INTEGER,
        price REAL,
        cost_price REAL
    )''')

    # Wallet / Earnings table
    c.execute('''CREATE TABLE IF NOT EXISTS wallet_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        description TEXT,
        amount REAL,
        type TEXT, -- 'CREDIT' or 'DEBIT'
        created_at TEXT
    )''')

    # Seed initial products if empty
    c.execute('SELECT COUNT(*) FROM products')
    if c.fetchone()[0] == 0:
        sample_products = [
            ("Wireless Ergonomic Vertical Mouse", "High precision 2.4G wireless vertical mouse for wrist health and gaming.", 8.50, 8.93, "https://images.unsplash.com/photo-1615663245857-ac93bb7c39e7?w=500&auto=format&fit=crop&q=60", "Electronics", "AliExpress", "AE-98231", 4.8, 1420),
            ("Mini Portable Thermal Photo Printer", "Bluetooth wireless pocket printer for notes, labels, and photos without ink.", 14.20, 14.91, "https://images.unsplash.com/photo-1612815154858-60aa4c59eaa6?w=500&auto=format&fit=crop&q=60", "Gadgets", "Temu", "TM-44120", 4.7, 3150),
            ("Smart LED Ambient Sunset Lamp", "16-color projection sunset lamp with remote control for bedroom aesthetics.", 6.80, 7.14, "https://images.unsplash.com/photo-1513506003901-1e6a229e2d15?w=500&auto=format&fit=crop&q=60", "Home & Living", "AliExpress", "AE-55210", 4.9, 5890),
            ("Ultrasonic Facial Skin Scrubber", "Deep cleansing spatula for blackhead removal and facial lifting.", 11.00, 11.55, "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=500&auto=format&fit=crop&q=60", "Beauty", "Temu", "TM-88231", 4.6, 920),
            ("MagSafe Magnetic Power Bank 10000mAh", "Fast wireless portable charger battery pack compatible with iPhone and Android.", 18.50, 19.43, "https://images.unsplash.com/photo-1609592424158-4796790a382d?w=500&auto=format&fit=crop&q=60", "Electronics", "AliExpress", "AE-11029", 4.8, 2300),
            ("Stainless Steel Insulated Tumbler 40oz", "Leak-proof travel mug with handle and straw for cold and hot beverages.", 9.30, 9.77, "https://images.unsplash.com/photo-1514228742587-6b1558fcca3d?w=500&auto=format&fit=crop&q=60", "Home & Living", "Temu", "TM-33291", 4.9, 4100),
            ("Mini Drone 4K Dual Camera Obstacle Avoidance", "Foldable RC quadcopter professional aerial photography toy drone.", 28.00, 29.40, "https://images.unsplash.com/photo-1527977966376-1c8408f9f108?w=500&auto=format&fit=crop&q=60", "Toys & Hobbies", "AliExpress", "AE-77420", 4.5, 840),
            ("Posture Corrector Adjustable Back Brace", "Comfortable clavicle support spine brace for back and neck pain relief.", 4.50, 4.73, "https://images.unsplash.com/photo-1584017911766-d451b3d0e843?w=500&auto=format&fit=crop&q=60", "Health", "Temu", "TM-11923", 4.7, 1890)
        ]
        c.executemany('''INSERT INTO products (title, description, cost_price, retail_price, image_url, category, source, supplier_item_id, rating, sales_count)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', sample_products)

        # Initial wallet deposit
        c.execute('''INSERT INTO wallet_transactions (description, amount, type, created_at)
                     VALUES (?, ?, ?, ?)''', ('Initial Welcome Bonus', 25.00, 'CREDIT', datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    conn.commit()
    conn.close()

init_db()

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    db = get_db()
    products = db.execute('SELECT * FROM products ORDER BY id DESC').fetchall()

    # Calculate wallet balance
    txs = db.execute('SELECT SUM(CASE WHEN type = "CREDIT" THEN amount ELSE -amount END) as balance FROM wallet_transactions').fetchone()
    wallet_balance = txs['balance'] if txs['balance'] else 0.00

    orders = db.execute('SELECT * FROM orders ORDER BY id DESC LIMIT 10').fetchall()
    db.close()
    return render_template('index.html', products=products, wallet_balance=wallet_balance, orders=orders)

@app.route('/api/products')
def api_products():
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    db = get_db()
    query = 'SELECT * FROM products WHERE 1=1'
    params = []
    if search:
        query += ' AND (title LIKE ? OR description LIKE ? OR category LIKE ?)'
        params.extend([f'%{search}%', f'%{search}%', f'%{search}%'])
    if category and category != 'All':
        query += ' AND category = ?'
        params.append(category)

    products = db.execute(query, params).fetchall()
    db.close()
    return jsonify([dict(p) for p in products])

@app.route('/api/search-external', methods=['POST'])
def search_external():
    """Simulates searching AliExpress or Temu for ANY product the shopper wants, importing it instantly with 5% markup."""
    data = request.json
    keyword = data.get('keyword', '').strip()
    if not keyword:
        return jsonify({'success': False, 'error': 'Keyword is required'})

    source = random.choice(['AliExpress', 'Temu'])
    cost = round(random.uniform(3.00, 45.00), 2)
    retail = round(cost * 1.05, 2) # 5% markup as requested

    images = [
        "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=500&auto=format&fit=crop&q=60",
        "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=500&auto=format&fit=crop&q=60",
        "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=500&auto=format&fit=crop&q=60",
        "https://images.unsplash.com/photo-1526170375885-4d8ecf77b99f?w=500&auto=format&fit=crop&q=60",
        "https://images.unsplash.com/photo-1583394838336-acd977736f90?w=500&auto=format&fit=crop&q=60",
        "https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?w=500&auto=format&fit=crop&q=60"
    ]
    img = random.choice(images)

    title = f"{keyword.title()} - Global Sourced Edition"
    description = f"Direct global fulfillment. High quality {keyword}, factory tested with express international dispatch."
    category = random.choice(['Electronics', 'Gadgets', 'Home & Living', 'Fashion', 'Beauty', 'Toys & Hobbies'])
    supplier_item_id = f"{'AE' if source == 'AliExpress' else 'TM'}-{random.randint(10000, 99999)}"
    rating = round(random.uniform(4.5, 5.0), 1)
    sales_count = random.randint(50, 1200)

    db = get_db()
    cursor = db.cursor()
    cursor.execute('''INSERT INTO products (title, description, cost_price, retail_price, image_url, category, source, supplier_item_id, rating, sales_count)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                   (title, description, cost, retail, img, category, source, supplier_item_id, rating, sales_count))
    db.commit()
    new_id = cursor.lastrowid

    new_product = db.execute('SELECT * FROM products WHERE id = ?', (new_id,)).fetchone()
    db.close()

    return jsonify({
        'success': True,
        'message': f'Successfully added "{title}" to store catalog with 5.0% profit markup.',
        'product': dict(new_product)
    })

@app.route('/api/checkout', methods=['POST'])
def checkout():
    data = request.json
    cart = data.get('cart', [])
    customer = data.get('customer', {})

    if not cart:
        return jsonify({'success': False, 'error': 'Cart is empty'})

    db = get_db()
    cursor = db.cursor()

    order_ref = f"ORD-{random.randint(100000, 999999)}"
    total_amount = 0
    total_profit = 0

    for item in cart:
        prod_id = item.get('id')
        qty = item.get('quantity', 1)
        prod = cursor.execute('SELECT * FROM products WHERE id = ?', (prod_id,)).fetchone()
        if prod:
            retail = prod['retail_price'] * qty
            cost = prod['cost_price'] * qty
            profit = retail - cost # 5% markup goes to wallet!
            total_amount += retail
            total_profit += profit

            cursor.execute('INSERT INTO order_items (order_ref, product_id, title, quantity, price, cost_price) VALUES (?, ?, ?, ?, ?, ?)',
                           (order_ref, prod_id, prod['title'], qty, prod['retail_price'], prod['cost_price']))

            cursor.execute('UPDATE products SET sales_count = sales_count + ? WHERE id = ?', (qty, prod_id))

    now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    cursor.execute('''INSERT INTO orders (order_ref, customer_name, customer_email, shipping_address, total_amount, wallet_profit, status, supplier_order_id, created_at)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                   (order_ref, customer.get('name', 'Valued Customer'), customer.get('email', 'customer@example.com'),
                    customer.get('address', '123 Main St'), round(total_amount, 2), round(total_profit, 2),
                    'Processing with Fulfillment Partner', f"SUP-{random.randint(10000000, 99990000)}", now_str))

    if total_profit > 0:
        cursor.execute('''INSERT INTO wallet_transactions (description, amount, type, created_at)
                          VALUES (?, ?, ?, ?)''',
                       (f'5% Markup Profit from Order {order_ref}', round(total_profit, 2), 'CREDIT', now_str))

    db.commit()
    db.close()

    return jsonify({
        'success': True,
        'order_ref': order_ref,
        'profit_earned': round(total_profit, 2),
        'total': round(total_amount, 2),
        'message': f'Order {order_ref} placed successfully! ${round(total_profit, 2)} credited to your owner wallet.'
    })

@app.route('/api/wallet')
def api_wallet():
    db = get_db()
    txs = db.execute('SELECT * FROM wallet_transactions ORDER BY id DESC').fetchall()
    bal_row = db.execute('SELECT SUM(CASE WHEN type = "CREDIT" THEN amount ELSE -amount END) as balance FROM wallet_transactions').fetchone()
    balance = bal_row['balance'] if bal_row['balance'] else 0.00
    db.close()
    return jsonify({
        'balance': round(balance, 2),
        'transactions': [dict(t) for t in txs]
    })

@app.route('/api/orders')
def api_orders():
    db = get_db()
    orders = db.execute('SELECT * FROM orders ORDER BY id DESC').fetchall()
    db.close()
    return jsonify([dict(o) for o in orders])

if __name__ == '__main__':
    print("Starting OmniStore Website...")
    print("Open your web browser at: http://localhost:5000")
    app.run(debug=True, port=5000)
