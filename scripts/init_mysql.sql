-- Create core tables (UTC timestamps)
SET time_zone = '+00:00';

CREATE TABLE IF NOT EXISTS documents (
  id CHAR(36) PRIMARY KEY,
  title VARCHAR(255),
  source_uri VARCHAR(512),
  mime_type VARCHAR(100),
  checksum CHAR(64),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uniq_checksum (checksum)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS chunks (
  id CHAR(36) PRIMARY KEY,
  doc_id CHAR(36) NOT NULL,
  chunk_index INT NOT NULL,
  page_start INT NULL,
  page_end INT NULL,
  heading VARCHAR(255) NULL,
  token_count INT NULL,
  vector_id VARCHAR(128) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_doc_chunk (doc_id, chunk_index),
  CONSTRAINT fk_chunks_doc FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS conversations (
  id CHAR(36) PRIMARY KEY,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS messages (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  conversation_id CHAR(36) NOT NULL,
  role ENUM('system','user','assistant','tool') NOT NULL,
  content MEDIUMTEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_conv (conversation_id),
  CONSTRAINT fk_messages_conv FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS bookings (
  id CHAR(36) PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  email VARCHAR(255) NOT NULL,
  start_time_utc DATETIME NOT NULL,
  end_time_utc DATETIME NOT NULL,
  source_conversation_id CHAR(36) NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_time (start_time_utc, end_time_utc),
  INDEX idx_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;