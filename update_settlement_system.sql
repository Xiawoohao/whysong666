-- 創建結算記錄表
CREATE TABLE IF NOT EXISTS settlements (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    settlement_type ENUM('restaurant', 'delivery') NOT NULL,
    recipient_id INT NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    settlement_date DATETIME NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id)
);

-- 添加結算狀態列到 orders 表
ALTER TABLE orders ADD COLUMN IF NOT EXISTS settlement_status ENUM('未結算', '已結算') DEFAULT '未結算';

-- 更新後端管理員的角色
UPDATE users SET role = 'backend' WHERE id = 4;

-- 如果用戶不存在，則插入
INSERT INTO users (email, password, name, role)
SELECT 'backend@example.com', 'backend123', '後端管理員', 'backend'
WHERE NOT EXISTS (
    SELECT 1 FROM users WHERE email = 'backend@example.com'
);

-- 更新所有已完成訂單的結算狀態
UPDATE orders SET settlement_status = '未結算' WHERE status = '已完成' AND settlement_status IS NULL;
