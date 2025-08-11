import os
import psycopg2
from psycopg2.extras import RealDictCursor

DDL = """
CREATE TABLE IF NOT EXISTS circulars (
  id SERIAL PRIMARY KEY,
  source_id INTEGER NOT NULL,
  title TEXT,
  valid_from DATE,
  valid_to DATE,
  retrieved_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pages (
  id SERIAL PRIMARY KEY,
  circular_id INTEGER REFERENCES circulars(id) ON DELETE CASCADE,
  page_no INTEGER NOT NULL,
  image_url TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS items (
  id SERIAL PRIMARY KEY,
  circular_id INTEGER REFERENCES circulars(id) ON DELETE CASCADE,
  page_id INTEGER REFERENCES pages(id) ON DELETE CASCADE,
  page INTEGER,
  product_text TEXT,
  price_raw TEXT,
  price_amount NUMERIC,
  currency TEXT,
  offer_type TEXT,         -- unit | multi | percent | unknown
  multi_qty INTEGER,
  multi_price NUMERIC,
  unit TEXT,
  extracted_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_items_circ_page ON items(circular_id, page);
"""

class DB:
    def __init__(self, dsn: str):
        self.dsn = dsn

    @classmethod
    def from_env(cls):
        host = os.getenv("DB_HOST", "db")
        port = int(os.getenv("DB_PORT", "5432"))
        name = os.getenv("DB_NAME", "kundeaviser")
        user = os.getenv("DB_USER", "postgres")
        pw   = os.getenv("DB_PASS", "coop")
        dsn = f"host={host} port={port} dbname={name} user={user} password={pw}"
        return cls(dsn)

    def connect(self):
        return psycopg2.connect(self.dsn, cursor_factory=RealDictCursor)

    def migrate(self):
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(DDL)
            conn.commit()

    def ensure_circular(self, source_id: int, title=None, valid_from=None, valid_to=None) -> int:
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute("""
                INSERT INTO circulars (source_id, title, valid_from, valid_to)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (source_id, title, valid_from, valid_to))
            cid = cur.fetchone()["id"]
            conn.commit()
            return cid

    def ensure_page(self, circular_id: int, page_no: int, image_url: str) -> int:
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute("""
                INSERT INTO pages (circular_id, page_no, image_url)
                VALUES (%s, %s, %s)
                RETURNING id
            """, (circular_id, page_no, image_url))
            pid = cur.fetchone()["id"]
            conn.commit()
            return pid

    def insert_item(self, **kw):
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute("""
                INSERT INTO items
                (circular_id, page_id, page, product_text, price_raw, price_amount, currency,
                 offer_type, multi_qty, multi_price, unit)
                VALUES
                (%(circular_id)s, %(page_id)s, %(page)s, %(product_text)s, %(price_raw)s,
                 %(price_amount)s, %(currency)s, %(offer_type)s, %(multi_qty)s, %(multi_price)s,
                 %(unit)s)
            """, kw)
            conn.commit()
