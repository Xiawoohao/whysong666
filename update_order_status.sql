-- 更新訂單表的狀態字段
ALTER TABLE orders MODIFY COLUMN status ENUM(
    '待確認',   -- 客戶剛下單
    '待接單',   -- 餐廳已確認，等待外送員接單
    '配送中',   -- 外送員已接單，正在配送
    '已送達',   -- 外送員已送達
    '已完成'    -- 顧客已確認收貨
) NOT NULL DEFAULT '待確認';

-- 更新現有訂單的狀態
UPDATE orders SET status = '待確認' WHERE status NOT IN ('待確認', '待接單', '配送中', '已送達', '已完成');
