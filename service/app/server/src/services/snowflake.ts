import snowflake from "snowflake-sdk";
import fs from "node:fs";
import path from "node:path";

let connection: snowflake.Connection | null = null;
let connectPromise: Promise<snowflake.Connection> | null = null;

/** SPCS injects an OAuth session token at this path when running inside a service. */
const SPCS_TOKEN_PATH = "/snowflake/session/token";

export function isSpcs(): boolean {
  return fs.existsSync(SPCS_TOKEN_PATH);
}

function resolveHome(filePath: string): string {
  if (filePath.startsWith("~/")) {
    return path.join(process.env.HOME ?? "", filePath.slice(2));
  }
  return filePath;
}

function buildConnectionOptions(): snowflake.ConnectionOptions {
  if (isSpcs()) {
    // Running inside Snowpark Container Services (Native App).
    // Authenticate with the injected OAuth session token — the connection
    // runs in the application's context, so reference('...') resolves the
    // consumer-bound objects. A warehouse is required for queries.
    const token = fs.readFileSync(SPCS_TOKEN_PATH, "ascii");
    return {
      account: process.env.SNOWFLAKE_ACCOUNT!,
      host: process.env.SNOWFLAKE_HOST!,
      authenticator: "OAUTH",
      token,
      warehouse: process.env.SNOWFLAKE_WAREHOUSE,
    } as snowflake.ConnectionOptions;
  }

  // Local development: external key-pair (JWT) auth.
  const keyPath = resolveHome(process.env.SNOWFLAKE_PRIVATE_KEY_PATH ?? "");
  const privateKey = fs.readFileSync(keyPath, "utf-8");
  return {
    account: process.env.SNOWFLAKE_ACCOUNT!,
    username: process.env.SNOWFLAKE_USER!,
    privateKey,
    authenticator: "SNOWFLAKE_JWT",
    warehouse: process.env.SNOWFLAKE_WAREHOUSE,
    database: process.env.SNOWFLAKE_DATABASE,
    schema: process.env.SNOWFLAKE_SCHEMA,
    role: process.env.SNOWFLAKE_ROLE,
  };
}

/** Execute a statement and return rows (used during connection warm-up). */
function execRows(conn: snowflake.Connection, sqlText: string): Promise<Record<string, unknown>[]> {
  return new Promise((resolve, reject) => {
    conn.execute({
      sqlText,
      complete(err, _stmt, rows) {
        if (err) reject(err);
        else resolve((rows ?? []) as Record<string, unknown>[]);
      },
    });
  });
}

/**
 * In SPCS the app owns a warehouse (named <app_db>_WH) and its data views live
 * in <app_db>.APP_DATA. Neither name is known at spec-build time, so discover
 * the warehouse (SHOW WAREHOUSES needs none) and the app database
 * (CURRENT_DATABASE), then USE them so view queries resolve.
 */
async function ensureSession(conn: snowflake.Connection): Promise<void> {
  if (!isSpcs()) return;
  const tryExec = async (sql: string): Promise<Record<string, unknown>[]> => {
    try {
      return await execRows(conn, sql);
    } catch (e) {
      console.error(`ensureSession step failed [${sql}]:`, String(e));
      return [];
    }
  };

  if (!process.env.SNOWFLAKE_WAREHOUSE) {
    const whRows = await tryExec("SHOW WAREHOUSES");
    const names = whRows.map((r) => String(r["name"] ?? r["NAME"] ?? ""));
    const wh = names.find((n) => n.toUpperCase().endsWith("_WH")) ?? names[0];
    if (wh) await tryExec(`USE WAREHOUSE IDENTIFIER('${wh}')`);
  }

  const dbRows = await tryExec("SELECT CURRENT_DATABASE() AS DB, CURRENT_ROLE() AS ROLE");
  console.log("ensureSession context: " + JSON.stringify(dbRows[0] ?? {}));
  // In a Native App the application's database name equals the app (role) name.
  // The container session has a null CURRENT_DATABASE, so fall back to the role.
  let db = String(dbRows[0]?.["DB"] ?? dbRows[0]?.["db"] ?? "");
  if (!db) db = String(dbRows[0]?.["ROLE"] ?? dbRows[0]?.["role"] ?? "");
  if (db) {
    await tryExec(`USE DATABASE IDENTIFIER('${db}')`);
    await tryExec("USE SCHEMA APP_DATA");
  }
}

function getConnection(): Promise<snowflake.Connection> {
  if (connectPromise) return connectPromise;

  connectPromise = new Promise((resolve, reject) => {
    const conn = snowflake.createConnection(buildConnectionOptions());
    conn.connect((err) => {
      if (err) {
        connectPromise = null;
        reject(err);
        return;
      }
      ensureSession(conn)
        .then(() => {
          connection = conn;
          resolve(conn);
        })
        .catch((sErr) => {
          connectPromise = null;
          reject(sErr);
        });
    });
  });

  return connectPromise;
}

/** Lowercase all column keys in a row object. */
function lowercaseKeys(row: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const key of Object.keys(row)) {
    out[key.toLowerCase()] = row[key];
  }
  return out;
}

export async function runQuery(
  sql: string,
  binds?: snowflake.Binds
): Promise<Record<string, unknown>[]> {
  const conn = await getConnection();
  return new Promise((resolve, reject) => {
    conn.execute({
      sqlText: sql,
      binds,
      complete(err, _stmt, rows) {
        if (err) {
          if (String(err).includes("terminated")) {
            connection = null;
            connectPromise = null;
            getConnection()
              .then((newConn) => {
                newConn.execute({
                  sqlText: sql,
                  binds,
                  complete(retryErr, _s, retryRows) {
                    if (retryErr) return reject(retryErr);
                    resolve((retryRows ?? []).map(lowercaseKeys));
                  },
                });
              })
              .catch(reject);
          } else {
            reject(err);
          }
        } else {
          resolve((rows ?? []).map(lowercaseKeys));
        }
      },
    });
  });
}

export async function destroy(): Promise<void> {
  if (!connection) return;
  return new Promise((resolve) => {
    connection!.destroy(() => {
      connection = null;
      connectPromise = null;
      resolve();
    });
  });
}
