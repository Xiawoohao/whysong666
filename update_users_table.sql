-- 添加送餐地址欄位
ALTER TABLE users ADD COLUMN delivery_address VARCHAR(255) DEFAULT NULL;

-- 更新現有用戶的送餐地址（如果需要）
UPDATE users SET delivery_address = '請更新您的送餐地址' WHERE role = 'customer' AND delivery_address IS NULL;
