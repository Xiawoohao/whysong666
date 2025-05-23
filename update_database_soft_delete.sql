-- 為 foods 表添加 is_deleted 欄位
ALTER TABLE foods ADD COLUMN is_deleted TINYINT(1) NOT NULL DEFAULT 0;

-- 更新現有記錄
UPDATE foods SET is_deleted = 0;
