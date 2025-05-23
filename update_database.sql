-- 更新訂單表，確保有正確的狀態字段
ALTER TABLE orders MODIFY COLUMN status ENUM('待接單', '配送中', '已送達', '已完成') NOT NULL DEFAULT '待接單';

-- 創建評價表（如果不存在）
CREATE TABLE IF NOT EXISTS reviews (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    user_id INT NOT NULL,
    restaurant_id INT NOT NULL,
    rating INT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    review_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (restaurant_id) REFERENCES restaurants(id),
    UNIQUE KEY unique_order_review (order_id)
);
