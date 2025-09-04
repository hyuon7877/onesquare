-- 데이터베이스 문자셋 확인 및 설정
ALTER DATABASE onesquare CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 사용자 권한 재설정
GRANT ALL PRIVILEGES ON onesquare.* TO 'onesquare_admin'@'%' WITH GRANT OPTION;
FLUSH PRIVILEGES;

-- 타임존 설정 확인
SELECT @@global.time_zone, @@session.time_zone;

-- 성능 관련 변수 확인
SHOW VARIABLES LIKE 'innodb_buffer_pool_size';
SHOW VARIABLES LIKE 'max_connections';
