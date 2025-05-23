from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
from functools import wraps
from datetime import datetime
import logging

# 配置日誌
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # 用於 session 和 flash 訊息

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',  # 請替換為你的 MySQL 密碼
    'database': 'delivery_platform',
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci',
    'use_unicode': True
}

# Database connection
def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        logger.error(f"Database connection error: {err}")
        return None

# 登入檢查裝飾器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            logger.info("User not logged in, redirecting to login page")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# 角色檢查裝飾器
def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            logger.info(f"Checking role. Session: {session}")
            if 'role' not in session:
                logger.warning("User role not found in session")
                flash('您沒有權限訪問此頁面')
                return redirect(url_for('login'))
            
            user_role = session.get('role', '')
            logger.info(f"User role: {user_role}, Allowed roles: {allowed_roles}")
            
            if not user_role:
                logger.warning("User role is empty")
                flash('用戶角色未設置')
                return redirect(url_for('login'))
            
            if user_role not in allowed_roles:
                logger.warning(f"User role {user_role} not in allowed roles {allowed_roles}")
                flash('您沒有權限訪問此頁面')
                return redirect(url_for('login'))
            
            logger.info(f"Role check passed. User role: {user_role}")
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # 根據角色重定向到相應的頁面
    role = session.get('role')
    if not role:
        return redirect(url_for('login'))
        
    if role == 'restaurant_owner':
        return redirect(url_for('restaurant_menu_list'))
    elif role == 'delivery_person':
        return redirect(url_for('delivery_order_list'))
    elif role == 'customer':
        return redirect(url_for('customer_restaurant_list'))
    elif role == 'admin':
        return redirect(url_for('admin_settlement_list'))
    elif role == 'backend':
        return redirect(url_for('backend_settlement_list'))
    
    # 如果角色不匹配任何已知角色，清除會話並重定向到登入頁面
    session.clear()
    flash('無效的用戶角色')
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            email = request.form.get('email')
            password = request.form.get('password')
            
            logger.info(f"Login attempt for email: {email}")
            
            if not email or not password:
                logger.warning("Missing email or password")
                flash('請輸入電子郵件和密碼')
                return render_template('login.html')
            
            conn = get_db_connection()
            if conn is None:
                logger.error("Database connection failed")
                flash('資料庫連接錯誤')
                return render_template('login.html')
            
            try:
                cursor = conn.cursor(dictionary=True)
                # 先檢查用戶是否存在
                cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
                user = cursor.fetchone()
                if not user:
                    logger.warning(f"User not found for email: {email}")
                    flash('電子郵件或密碼錯誤')
                    return render_template('login.html')
                
                logger.info(f"Found user: {user}")
                
                # 檢查密碼
                cursor.execute('SELECT * FROM users WHERE email = %s AND password = %s', (email, password))
                user = cursor.fetchone()
                
                if user:
                    if not user.get('role'):
                        logger.warning(f"User has no role: {user}")
                        # 嘗試更新用戶角色
                        try:
                            update_cursor = conn.cursor()
                            update_cursor.execute('UPDATE users SET role = %s WHERE id = %s', ('backend', user['id']))
                            conn.commit()
                            update_cursor.close()
                            logger.info(f"Updated user role to backend for user ID: {user['id']}")
                            user['role'] = 'backend'
                        except Exception as e:
                            logger.error(f"Failed to update user role: {e}")
                            flash('用戶角色更新失敗')
                            return render_template('login.html')
                    
                    logger.info(f"User authenticated successfully: {user}")
                    session.clear()
                    session['user_id'] = user['id']
                    session['role'] = user['role']
                    session['name'] = user['name']
                    logger.info(f"Session after login: {session}")
                    
                    # 根據角色重定向到相應的頁面
                    if user['role'] == 'restaurant_owner':
                        logger.info("Redirecting to restaurant_menu_list")
                        return redirect(url_for('restaurant_menu_list'))
                    elif user['role'] == 'delivery_person':
                        logger.info("Redirecting to delivery_order_list")
                        return redirect(url_for('delivery_order_list'))
                    elif user['role'] == 'customer':
                        logger.info("Redirecting to customer_restaurant_list")
                        return redirect(url_for('customer_restaurant_list'))
                    elif user['role'] == 'admin':
                        logger.info("Redirecting to admin_settlement_list")
                        return redirect(url_for('admin_settlement_list'))
                    elif user['role'] == 'backend':
                        logger.info("Redirecting to backend_settlement_list")
                        return redirect(url_for('backend_settlement_list'))
                    
                    logger.warning(f"Unknown role: {user['role']}")
                    flash('無效的用戶角色')
                    return render_template('login.html')
                else:
                    logger.warning(f"Invalid password for email: {email}")
                    flash('電子郵件或密碼錯誤')
            except mysql.connector.Error as err:
                logger.error(f"Database error during login: {err}")
                flash('登入時發生錯誤')
            finally:
                cursor.close()
                conn.close()
        except Exception as e:
            logger.error(f"Unexpected error during login: {e}")
            flash('登入時發生錯誤')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# 餐廳商家功能
@app.route('/restaurant/menu', methods=['GET'])
@login_required
@role_required(['restaurant_owner'])
def restaurant_menu_list():
    conn = get_db_connection()
    if conn is None:
        logger.error("Database connection failed")
        flash('資料庫連接錯誤')
        return redirect(url_for('index'))
    
    cursor = conn.cursor(dictionary=True)
    
    # 獲取餐廳信息
    cursor.execute('SELECT * FROM restaurants WHERE owner_id = %s', (session['user_id'],))
    restaurant = cursor.fetchone()
    
    if not restaurant:
        logger.warning("Restaurant not found")
        flash('請先建立餐廳資料')
        return redirect(url_for('index'))
    
    # 獲取菜單
    cursor.execute('SELECT * FROM foods WHERE restaurant_id = %s', (restaurant['id'],))
    menu_items = cursor.fetchall()
    
    conn.close()
    return render_template('restaurant/menu.html', menu_items=menu_items, restaurant=restaurant)

@app.route('/restaurant/menu/add', methods=['GET', 'POST'])
@login_required
@role_required(['restaurant_owner'])
def add_menu_item():
    if request.method == 'POST':
        name = request.form.get('name')
        price = float(request.form.get('price'))
        description = request.form.get('description')
        
        if not name or price <= 0:
            logger.warning("Invalid menu item data")
            flash('請填寫完整的商品資訊')
            return redirect(url_for('add_menu_item'))
        
        conn = get_db_connection()
        if conn is None:
            logger.error("Database connection failed")
            flash('資料庫連接錯誤')
            return redirect(url_for('index'))
        
        cursor = conn.cursor(dictionary=True)
        
        # 獲取餐廳ID
        cursor.execute('SELECT id FROM restaurants WHERE owner_id = %s', (session['user_id'],))
        restaurant = cursor.fetchone()
        
        if not restaurant:
            logger.warning("Restaurant not found")
            flash('請先建立餐廳資料')
            return redirect(url_for('index'))
        
        # 新增菜單項目
        cursor.execute('''
            INSERT INTO foods (restaurant_id, name, price, description)
            VALUES (%s, %s, %s, %s)
        ''', (restaurant['id'], name, price, description))
        
        conn.commit()
        conn.close()
        
        logger.info("Menu item added successfully")
        flash('商品已新增')
        return redirect(url_for('restaurant_menu_list'))
    
    return render_template('restaurant/add_menu_item.html')

@app.route('/restaurant/menu/edit/<int:food_id>', methods=['GET', 'POST'])
@login_required
@role_required(['restaurant_owner'])
def edit_menu_item(food_id):
    conn = get_db_connection()
    if conn is None:
        logger.error("Database connection failed")
        flash('資料庫連接錯誤')
        return redirect(url_for('index'))
    
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        name = request.form.get('name')
        price = float(request.form.get('price'))
        description = request.form.get('description')
        
        if not name or price <= 0:
            logger.warning("Invalid menu item data")
            flash('請填寫完整的商品資訊')
            return redirect(url_for('edit_menu_item', food_id=food_id))
        
        # 確保只能編輯自己餐廳的菜單
        cursor.execute('''
            UPDATE foods f
            JOIN restaurants r ON f.restaurant_id = r.id
            SET f.name = %s, f.price = %s, f.description = %s
            WHERE f.id = %s AND r.owner_id = %s
        ''', (name, price, description, food_id, session['user_id']))
        
        conn.commit()
        logger.info("Menu item updated successfully")
        flash('商品已更新')
        return redirect(url_for('restaurant_menu_list'))
    
    # 獲取菜單項目
    cursor.execute('''
        SELECT f.*
        FROM foods f
        JOIN restaurants r ON f.restaurant_id = r.id
        WHERE f.id = %s AND r.owner_id = %s
    ''', (food_id, session['user_id']))
    food = cursor.fetchone()
    
    conn.close()
    
    if not food:
        logger.warning("Menu item not found")
        flash('找不到該商品')
        return redirect(url_for('restaurant_menu_list'))
    
    return render_template('restaurant/edit_menu_item.html', food=food)

@app.route('/restaurant/menu/delete/<int:food_id>', methods=['POST'])
@login_required
@role_required(['restaurant_owner'])
def delete_menu_item(food_id):
    conn = get_db_connection()
    if conn is None:
        logger.error("Database connection failed")
        flash('資料庫連接錯誤')
        return redirect(url_for('index'))
    
    cursor = conn.cursor()
    
    # 檢查是否有相關訂單
    cursor.execute('''
        SELECT COUNT(*) as count
        FROM order_items oi
        WHERE oi.food_id = %s
    ''', (food_id,))
    result = cursor.fetchone()
    
    if result[0] > 0:
        flash('此商品已有訂單記錄，無法刪除')
        conn.close()
        return redirect(url_for('restaurant_menu_list'))
    
    # 確保只能刪除自己餐廳的菜單
    cursor.execute('''
        DELETE f FROM foods f
        JOIN restaurants r ON f.restaurant_id = r.id
        WHERE f.id = %s AND r.owner_id = %s
    ''', (food_id, session['user_id']))
    
    conn.commit()
    conn.close()
    
    logger.info("Menu item deleted successfully")
    flash('商品已刪除')
    return redirect(url_for('restaurant_menu_list'))

@app.route('/restaurant/orders')
@login_required
@role_required(['restaurant_owner'])
def restaurant_order_list():
    conn = get_db_connection()
    if conn is None:
        logger.error("Database connection failed")
        flash('資料庫連接錯誤')
        return redirect(url_for('index'))
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT o.*, u.name as customer_name
        FROM orders o
        JOIN users u ON o.user_id = u.id
        JOIN restaurants r ON o.restaurant_id = r.id
        WHERE r.owner_id = %s
        ORDER BY o.created_at DESC
    ''', (session['user_id'],))
    orders = cursor.fetchall()
    conn.close()
    
    return render_template('restaurant/orders.html', orders=orders)

@app.route('/restaurant/confirm_order/<int:order_id>')
@login_required
@role_required(['restaurant_owner'])
def confirm_order(order_id):
    conn = get_db_connection()
    if conn is None:
        logger.error("Database connection failed")
        flash('資料庫連接錯誤')
        return redirect(url_for('index'))
    
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE orders 
        SET status = '待接單'
        WHERE id = %s AND status = '待確認' AND restaurant_id = (
            SELECT id FROM restaurants WHERE owner_id = %s
        )
    ''', (order_id, session['user_id']))
    
    conn.commit()
    conn.close()
    
    logger.info("Order confirmed successfully")
    flash('訂單已確認')
    return redirect(url_for('restaurant_order_list'))

@app.route('/restaurant/reject_order/<int:order_id>', methods=['POST'])
@login_required
@role_required(['restaurant_owner'])
def reject_order(order_id):
    conn = get_db_connection()
    if conn is None:
        logger.error("Database connection failed")
        flash('資料庫連接錯誤')
        return redirect(url_for('index'))
    
    cursor = conn.cursor()
    try:
        # 檢查訂單是否屬於該餐廳且狀態為待確認
        cursor.execute('''
            SELECT o.* FROM orders o
            JOIN restaurants r ON o.restaurant_id = r.id
            WHERE o.id = %s AND r.owner_id = %s AND o.status = '待確認'
        ''', (order_id, session['user_id']))
        
        if cursor.fetchone() is None:
            flash('無法拒絕此訂單')
            return redirect(url_for('restaurant_order_list'))
        
        # 更新訂單狀態為已拒絕
        cursor.execute('''
            UPDATE orders 
            SET status = '已拒絕'
            WHERE id = %s
        ''', (order_id,))
        
        conn.commit()
        flash('訂單已拒絕')
        logger.info(f"Order {order_id} rejected by restaurant")
    except mysql.connector.Error as err:
        logger.error(f"Database error while rejecting order: {err}")
        flash('拒絕訂單時發生錯誤')
        conn.rollback()
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('restaurant_order_list'))

@app.route('/restaurant/notify_pickup/<int:order_id>')
@login_required
@role_required(['restaurant_owner'])
def notify_pickup(order_id):
    # 這裡可以加入通知系統的邏輯
    logger.info("Pickup notification sent")
    flash('已通知顧客取餐')
    return redirect(url_for('restaurant_order_list'))

# 外送員功能
@app.route('/delivery/orders')
@login_required
@role_required(['delivery_person'])
def delivery_order_list():
    conn = get_db_connection()
    if conn is None:
        logger.error("Database connection failed")
        flash('資料庫連接錯誤')
        return redirect(url_for('index'))
    
    cursor = conn.cursor(dictionary=True)
    
    # 獲取待接單的訂單和自己正在配送的訂單
    query = '''
        SELECT o.*, 
               r.name as restaurant_name,
               r.address as restaurant_address,
               u.name as customer_name
        FROM orders o
        JOIN restaurants r ON o.restaurant_id = r.id
        JOIN users u ON o.user_id = u.id
        WHERE (o.status = '待接單') OR 
              (o.status = '配送中' AND o.delivery_person_id = %s)
        ORDER BY o.created_at DESC
    '''
    logger.debug(f"Executing query: {query}")
    cursor.execute(query, (session['user_id'],))
    orders = cursor.fetchall()
    
    # 記錄找到的訂單數量
    logger.info(f"Found {len(orders)} orders for delivery person {session['user_id']}")
    for order in orders:
        logger.debug(f"Order {order['id']}: status={order['status']}")
    
    # 確保 created_at 是 datetime 對象
    for order in orders:
        if isinstance(order['created_at'], str):
            order['created_at'] = datetime.strptime(order['created_at'], '%Y-%m-%d %H:%M:%S')
    
    conn.close()
    return render_template('delivery/orders.html', orders=orders)

@app.route('/delivery/orders/<int:order_id>/accept', methods=['POST'])
@login_required
@role_required(['delivery_person'])
def accept_order(order_id):
    conn = get_db_connection()
    if conn is None:
        logger.error("Database connection failed")
        flash('資料庫連接錯誤')
        return redirect(url_for('index'))
    
    cursor = conn.cursor()
    
    # 確保訂單狀態是待接單
    cursor.execute('''
        UPDATE orders 
        SET status = '配送中', 
            delivery_person_id = %s
        WHERE id = %s AND status = '待接單'
    ''', (session['user_id'], order_id))
    
    if cursor.rowcount == 0:
        logger.warning("Order already accepted by another delivery person")
        flash('訂單已被其他外送員接走了')
    else:
        logger.info("Order accepted successfully")
        flash('已接單')
        conn.commit()
    
    conn.close()
    return redirect(url_for('delivery_order_list'))

@app.route('/delivery/orders/<int:order_id>/complete', methods=['POST'])
@login_required
@role_required(['delivery_person'])
def complete_delivery(order_id):
    conn = get_db_connection()
    if conn is None:
        logger.error("Database connection failed")
        flash('資料庫連接錯誤')
        return redirect(url_for('index'))
    
    cursor = conn.cursor()
    
    # 確保是自己接的單
    cursor.execute('''
        UPDATE orders 
        SET status = '已送達' 
        WHERE id = %s AND status = '配送中' AND delivery_person_id = %s
    ''', (order_id, session['user_id']))
    
    if cursor.rowcount == 0:
        logger.warning("Order not found or not delivered by this delivery person")
        flash('無法完成配送')
    else:
        logger.info("Delivery completed successfully")
        flash('配送已完成')
        conn.commit()
    
    conn.close()
    return redirect(url_for('delivery_order_list'))

# 客戶功能
@app.route('/restaurants')
@login_required
@role_required(['customer'])
def customer_restaurant_list():
    conn = get_db_connection()
    if conn is None:
        logger.error("Database connection failed")
        flash('資料庫連接錯誤')
        return redirect(url_for('index'))
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM restaurants')
    restaurants = cursor.fetchall()
    conn.close()
    
    return render_template('customer/restaurants.html', restaurants=restaurants)

@app.route('/restaurants/<int:restaurant_id>/menu')
@login_required
@role_required(['customer'])
def customer_menu(restaurant_id):
    conn = get_db_connection()
    if conn is None:
        logger.error("Database connection failed")
        flash('資料庫連接錯誤')
        return redirect(url_for('index'))
    
    cursor = conn.cursor(dictionary=True)
    
    # 獲取餐廳資訊
    cursor.execute('SELECT * FROM restaurants WHERE id = %s', (restaurant_id,))
    restaurant = cursor.fetchone()
    
    if not restaurant:
        logger.warning("Restaurant not found")
        flash('餐廳不存在')
        return redirect(url_for('customer_restaurant_list'))
    
    # 獲取餐廳的菜單
    cursor.execute('SELECT * FROM foods WHERE restaurant_id = %s', (restaurant_id,))
    menu_items = cursor.fetchall()
    conn.close()
    
    return render_template('customer/menu.html', 
                         restaurant=restaurant,
                         menu_items=menu_items)

@app.route('/cart')
@login_required
@role_required(['customer'])
def customer_cart_list():
    conn = get_db_connection()
    if conn is None:
        logger.error("Database connection failed")
        flash('資料庫連接錯誤')
        return redirect(url_for('index'))
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT c.*, f.name, f.price, (f.price * c.quantity) as total
        FROM cart c
        JOIN foods f ON c.food_id = f.id
        WHERE c.user_id = %s
    ''', (session['user_id'],))
    cart_items = cursor.fetchall()
    
    total_amount = sum(item['total'] for item in cart_items)
    conn.close()
    
    return render_template('customer/cart.html', cart_items=cart_items, total_amount=total_amount)

@app.route('/orders')
@login_required
@role_required(['customer'])
def customer_order_list():
    conn = get_db_connection()
    if conn is None:
        logger.error("Database connection failed")
        flash('資料庫連接錯誤')
        return redirect(url_for('index'))
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT o.*, r.name as restaurant_name,
               CASE WHEN rv.id IS NOT NULL THEN 1 ELSE 0 END as has_review
        FROM orders o
        JOIN restaurants r ON o.restaurant_id = r.id
        LEFT JOIN reviews rv ON o.id = rv.order_id
        WHERE o.user_id = %s
        ORDER BY o.created_at DESC
    ''', (session['user_id'],))
    orders = cursor.fetchall()
    
    # 確保 created_at 是 datetime 對象
    for order in orders:
        if isinstance(order['created_at'], str):
            order['created_at'] = datetime.strptime(order['created_at'], '%Y-%m-%d %H:%M:%S')
    
    conn.close()
    return render_template('customer/orders.html', orders=orders)

@app.route('/orders/<int:order_id>/confirm', methods=['POST'])
@login_required
@role_required(['customer'])
def customer_confirm_order(order_id):
    conn = get_db_connection()
    if conn is None:
        logger.error("Database connection failed")
        flash('資料庫連接錯誤')
        return redirect(url_for('index'))
    
    cursor = conn.cursor()
    
    # 確保是自己的訂單且狀態是已送達
    cursor.execute('''
        UPDATE orders 
        SET status = '已完成' 
        WHERE id = %s AND user_id = %s AND status = '已送達'
    ''', (order_id, session['user_id']))
    
    if cursor.rowcount == 0:
        logger.warning("Order not found or not delivered")
        flash('無法確認訂單')
    else:
        logger.info("Order confirmed successfully")
        flash('訂單已完成')
        conn.commit()
    
    conn.close()
    return redirect(url_for('customer_order_list'))

@app.route('/orders/<int:order_id>/review', methods=['GET', 'POST'])
@login_required
@role_required(['customer'])
def review_order(order_id):
    if request.method == 'POST':
        rating = int(request.form.get('rating'))
        review_text = request.form.get('review_text')
        
        if not rating or rating < 1 or rating > 5:
            logger.warning("Invalid rating")
            flash('請給出1-5星的評價')
            return redirect(url_for('review_order', order_id=order_id))
        
        conn = get_db_connection()
        if conn is None:
            logger.error("Database connection failed")
            flash('資料庫連接錯誤')
            return redirect(url_for('index'))
        
        cursor = conn.cursor()
        
        # 確保是自己的已完成訂單且還未評價
        cursor.execute('''
            INSERT INTO reviews (order_id, user_id, restaurant_id, rating, review_text)
            SELECT %s, %s, restaurant_id, %s, %s
            FROM orders
            WHERE id = %s AND user_id = %s AND status = '已完成'
            AND NOT EXISTS (SELECT 1 FROM reviews WHERE order_id = %s)
        ''', (order_id, session['user_id'], rating, review_text, 
              order_id, session['user_id'], order_id))
        
        if cursor.rowcount == 0:
            logger.warning("Order not found or already reviewed")
            flash('無法評價此訂單')
        else:
            logger.info("Review submitted successfully")
            flash('評價已提交')
            conn.commit()
        
        conn.close()
        return redirect(url_for('customer_order_list'))
    
    return render_template('customer/review.html', order_id=order_id)

@app.route('/cart/add/<int:food_id>', methods=['POST'])
@login_required
@role_required(['customer'])
def add_to_cart(food_id):
    quantity = int(request.form.get('quantity', 1))
    if quantity < 1 or quantity > 10:
        logger.warning("Invalid quantity")
        flash('數量必須在1到10之間')
        return redirect(request.referrer)
    
    conn = get_db_connection()
    if conn is None:
        logger.error("Database connection failed")
        flash('資料庫連接錯誤')
        return redirect(url_for('index'))
    
    cursor = conn.cursor(dictionary=True)
    
    # 檢查食品是否存在
    cursor.execute('SELECT * FROM foods WHERE id = %s', (food_id,))
    food = cursor.fetchone()
    
    if not food:
        logger.warning("Food not found")
        flash('商品不存在')
        return redirect(url_for('customer_restaurant_list'))
    
    # 檢查購物車中是否已有此商品
    cursor.execute('''
        SELECT * FROM cart 
        WHERE user_id = %s AND food_id = %s
    ''', (session['user_id'], food_id))
    cart_item = cursor.fetchone()
    
    if cart_item:
        # 更新數量
        new_quantity = min(cart_item['quantity'] + quantity, 10)
        cursor.execute('''
            UPDATE cart 
            SET quantity = %s 
            WHERE user_id = %s AND food_id = %s
        ''', (new_quantity, session['user_id'], food_id))
    else:
        # 新增到購物車
        cursor.execute('''
            INSERT INTO cart (user_id, food_id, quantity)
            VALUES (%s, %s, %s)
        ''', (session['user_id'], food_id, quantity))
    
    conn.commit()
    conn.close()
    
    logger.info("Item added to cart successfully")
    flash('已加入購物車')
    return redirect(request.referrer)

@app.route('/cart/delete/<int:cart_item_id>', methods=['POST'])
@login_required
@role_required(['customer'])
def delete_from_cart(cart_item_id):
    conn = get_db_connection()
    if conn is None:
        logger.error("Database connection failed")
        flash('資料庫連接錯誤')
        return redirect(url_for('index'))
    
    cursor = conn.cursor()
    
    # 確保只能刪除自己的購物車項目
    cursor.execute('''
        DELETE FROM cart 
        WHERE id = %s AND user_id = %s
    ''', (cart_item_id, session['user_id']))
    
    conn.commit()
    conn.close()
    
    logger.info("Item deleted from cart successfully")
    flash('已從購物車移除')
    return redirect(url_for('customer_cart_list'))

@app.route('/order/create', methods=['POST'])
@login_required
@role_required(['customer'])
def create_order():
    conn = get_db_connection()
    if conn is None:
        logger.error("Database connection failed")
        flash('資料庫連接錯誤')
        return redirect(url_for('index'))
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 檢查用戶是否有設置送餐地址
        cursor.execute('SELECT delivery_address FROM users WHERE id = %s', (session['user_id'],))
        user = cursor.fetchone()
        if not user or not user['delivery_address']:
            flash('請先設置送餐地址')
            return redirect(url_for('update_delivery_address'))
        
        # 獲取購物車內容
        cursor.execute('''
            SELECT c.*, f.name, f.price, f.restaurant_id,
                   (f.price * c.quantity) as total
            FROM cart c
            JOIN foods f ON c.food_id = f.id
            WHERE c.user_id = %s
        ''', (session['user_id'],))
        cart_items = cursor.fetchall()
        
        if not cart_items:
            logger.warning("Cart is empty")
            flash('購物車是空的')
            return redirect(url_for('customer_cart_list'))
        
        # 確保所有商品都來自同一家餐廳
        restaurant_id = cart_items[0]['restaurant_id']
        if any(item['restaurant_id'] != restaurant_id for item in cart_items):
            logger.warning("Cart items from different restaurants")
            flash('購物車中的商品必須來自同一家餐廳')
            return redirect(url_for('customer_cart_list'))
        
        # 計算總金額
        total_amount = sum(item['total'] for item in cart_items)
        
        # 創建訂單
        cursor.execute('''
            INSERT INTO orders 
            (user_id, restaurant_id, total_amount, status, created_at)
            VALUES (%s, %s, %s, '待確認', NOW())
        ''', (session['user_id'], restaurant_id, total_amount))
        order_id = cursor.lastrowid
        
        # 創建訂單詳情
        for item in cart_items:
            cursor.execute('''
                INSERT INTO order_items 
                (order_id, food_id, quantity, price)
                VALUES (%s, %s, %s, %s)
            ''', (order_id, item['food_id'], item['quantity'], item['price']))
        
        # 清空購物車
        cursor.execute('DELETE FROM cart WHERE user_id = %s', (session['user_id'],))
        
        conn.commit()
        logger.info("Order created successfully")
        flash('訂單已成功建立')
        return redirect(url_for('customer_order_list'))
        
    except Exception as e:
        conn.rollback()
        logger.error("Error creating order")
        flash('建立訂單時發生錯誤')
        return redirect(url_for('customer_cart_list'))
    finally:
        conn.close()

@app.route('/customer/update_address', methods=['GET', 'POST'])
@login_required
@role_required(['customer'])
def update_delivery_address():
    if request.method == 'POST':
        delivery_address = request.form.get('delivery_address')
        if not delivery_address:
            flash('請輸入送餐地址')
            return redirect(url_for('update_delivery_address'))
        
        conn = get_db_connection()
        if conn is None:
            logger.error("Database connection failed")
            flash('資料庫連接錯誤')
            return redirect(url_for('index'))
        
        try:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users 
                SET delivery_address = %s 
                WHERE id = %s
            ''', (delivery_address, session['user_id']))
            conn.commit()
            flash('送餐地址已更新')
            return redirect(url_for('customer_restaurant_list'))
        except mysql.connector.Error as err:
            logger.error(f"Database error during address update: {err}")
            flash('更新地址時發生錯誤')
        finally:
            cursor.close()
            conn.close()
    
    return render_template('customer/update_address.html')

# 平台管理功能
@app.route('/admin/settlements')
@login_required
@role_required(['admin'])
def admin_settlement_list():
    conn = get_db_connection()
    if conn is None:
        logger.error("Database connection failed")
        flash('資料庫連接錯誤')
        return redirect(url_for('index'))
    
    cursor = conn.cursor(dictionary=True)
    
    # 獲取餐廳結算資料
    cursor.execute('''
        SELECT r.name as restaurant_name,
               COUNT(o.id) as order_count,
               SUM(o.total_amount) as total_amount,
               SUM(o.total_amount * 0.1) as platform_fee,
               SUM(o.total_amount * 0.9) as payable_amount,
               r.id as restaurant_id
        FROM restaurants r
        LEFT JOIN orders o ON r.id = o.restaurant_id
        WHERE o.status = '已完成'
        GROUP BY r.id
    ''')
    restaurant_settlements = cursor.fetchall()
    
    # 獲取外送員結算資料
    cursor.execute('''
        SELECT u.name as delivery_person_name,
               COUNT(o.id) as delivery_count,
               SUM(30) as delivery_fee_total,
               u.id as delivery_person_id
        FROM users u
        LEFT JOIN orders o ON u.id = o.delivery_person_id
        WHERE u.role = 'delivery_person' AND o.status = '已完成'
        GROUP BY u.id
    ''')
    delivery_settlements = cursor.fetchall()
    
    conn.close()
    
    return render_template('admin/settlements.html',
                         restaurant_settlements=restaurant_settlements,
                         delivery_settlements=delivery_settlements)

# 後端人員功能
@app.route('/backend/settlements')
@login_required
@role_required(['backend', 'admin'])  # 允許 backend 和 admin 角色訪問
def backend_settlement_list():
    conn = get_db_connection()
    if conn is None:
        logger.error("Database connection failed")
        flash('資料庫連接錯誤')
        return redirect(url_for('index'))
    
    cursor = conn.cursor(dictionary=True)
    
    # 獲取所有未結算的訂單
    cursor.execute('''
        SELECT 
            o.id as order_id,
            o.created_at,
            o.total_amount,
            r.name as restaurant_name,
            r.id as restaurant_id,
            u.name as delivery_person_name,
            u.id as delivery_person_id,
            o.settlement_status
        FROM orders o
        JOIN restaurants r ON o.restaurant_id = r.id
        LEFT JOIN users u ON o.delivery_person_id = u.id
        WHERE o.status = '已完成' AND o.settlement_status = '未結算'
        ORDER BY o.created_at DESC
    ''')
    pending_settlements = cursor.fetchall()
    
    # 獲取已結算的歷史記錄
    cursor.execute('''
        SELECT 
            s.id as settlement_id,
            s.order_id,
            s.settlement_type,
            s.amount,
            s.settlement_date,
            CASE 
                WHEN s.settlement_type = 'restaurant' THEN r.name
                WHEN s.settlement_type = 'delivery' THEN u.name
            END as recipient_name
        FROM settlements s
        LEFT JOIN orders o ON s.order_id = o.id
        LEFT JOIN restaurants r ON s.recipient_id = r.id AND s.settlement_type = 'restaurant'
        LEFT JOIN users u ON s.recipient_id = u.id AND s.settlement_type = 'delivery'
        ORDER BY s.settlement_date DESC
        LIMIT 100
    ''')
    settlement_history = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('backend/settlements.html',
                         pending_settlements=pending_settlements,
                         settlement_history=settlement_history)

@app.route('/backend/process_settlement', methods=['POST'])
@login_required
@role_required(['backend'])
def process_settlement():
    order_id = request.form.get('order_id')
    settlement_type = request.form.get('settlement_type')
    
    if not order_id or not settlement_type:
        flash('缺少必要參數')
        return redirect(url_for('backend_settlement_list'))
    
    logger.info(f"Processing settlement for order {order_id}, type: {settlement_type}")
    
    conn = get_db_connection()
    if conn is None:
        logger.error("Database connection failed")
        flash('資料庫連接錯誤')
        return redirect(url_for('backend_settlement_list'))
    
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        
        # 檢查訂單是否存在且未結算
        cursor.execute('''
            SELECT 
                o.id, 
                o.total_amount,
                o.status,
                o.settlement_status,
                r.id as restaurant_id,
                u.id as delivery_person_id
            FROM orders o
            LEFT JOIN restaurants r ON o.restaurant_id = r.id
            LEFT JOIN users u ON o.delivery_person_id = u.id
            WHERE o.id = %s
        ''', (order_id,))
        
        order = cursor.fetchone()
        logger.info(f"Order data: {order}")  # 添加調試信息
        
        if not order:
            logger.error(f"Order not found: {order_id}")
            flash('訂單不存在')
            return redirect(url_for('backend_settlement_list'))
        
        if order.get('status') != '已完成':
            logger.warning(f"Order not completed: {order_id}")
            flash('只能結算已完成的訂單')
            return redirect(url_for('backend_settlement_list'))
        
        if order.get('settlement_status') == '已結算':
            logger.warning(f"Order already settled: {order_id}")
            flash('此訂單已結算')
            return redirect(url_for('backend_settlement_list'))
        
        # 開始交易
        conn.start_transaction()
        
        # 根據結算類型處理
        try:
            if settlement_type == 'restaurant':
                if not order['restaurant_id']:
                    raise Exception('找不到餐廳信息')
                amount = float(order['total_amount']) * 0.9  # 餐廳獲得90%
                recipient_id = order['restaurant_id']
            elif settlement_type == 'delivery':
                if not order['delivery_person_id']:
                    raise Exception('找不到外送員信息')
                amount = 30  # 固定配送費
                recipient_id = order['delivery_person_id']
            else:
                raise Exception('無效的結算類型')
            
            logger.info(f"Settlement details - Order: {order_id}, Type: {settlement_type}, Amount: {amount}, Recipient: {recipient_id}")
            
            # 檢查是否已有相同類型的結算記錄
            cursor.execute('''
                SELECT COUNT(*) as count
                FROM settlements
                WHERE order_id = %s AND settlement_type = %s
            ''', (order_id, settlement_type))
            
            existing_settlement = cursor.fetchone()
            if existing_settlement and existing_settlement['count'] > 0:
                raise Exception('此訂單的此類型結算已存在')
            
            # 插入結算記錄
            cursor.execute('''
                INSERT INTO settlements 
                (order_id, settlement_type, recipient_id, amount, settlement_date)
                VALUES (%s, %s, %s, %s, NOW())
            ''', (order_id, settlement_type, recipient_id, amount))
            
            # 如果兩種類型都已結算，則更新訂單狀態
            cursor.execute('''
                SELECT COUNT(*) as count
                FROM settlements
                WHERE order_id = %s
            ''', (order_id,))
            
            settlement_count = cursor.fetchone()['count']
            if settlement_count >= 2:  # 如果已經有兩種結算
                cursor.execute('''
                    UPDATE orders 
                    SET settlement_status = '已結算'
                    WHERE id = %s
                ''', (order_id,))
            
            conn.commit()
            logger.info(f"Settlement processed successfully for order {order_id}")
            flash('結算處理成功')
            
        except Exception as e:
            logger.error(f"Error during settlement processing: {str(e)}")
            raise e  # 重新拋出異常以觸發外層的錯誤處理
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Settlement processing error: {str(e)}")
        flash(f'結算處理失敗: {str(e)}')
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return redirect(url_for('backend_settlement_list'))

@app.route('/check_user/<email>')
def check_user(email):
    if not app.debug:
        return "This endpoint is only available in debug mode"
    
    conn = get_db_connection()
    if conn is None:
        return "Database connection failed"
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT id, email, role, name FROM users WHERE email = %s', (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user:
            return str(user)
        return "User not found"
    except Exception as e:
        return str(e)

if __name__ == '__main__':
    app.debug = True  # 啟用調試模式
    app.run(host='0.0.0.0', port=5000)
