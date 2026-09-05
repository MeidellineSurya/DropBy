import pg from "pg";

const { Pool } = pg;

export function createPool(connectionString: string): pg.Pool {
  return new Pool({
    connectionString,
    max: 15,
    idleTimeoutMillis: 30_000,
    connectionTimeoutMillis: 5_000,
  });
}

export type Database = pg.Pool;
