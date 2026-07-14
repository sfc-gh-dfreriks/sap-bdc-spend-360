import path from "node:path";
import dotenv from "dotenv";

dotenv.config({ path: path.resolve(import.meta.dirname, "../../.env") });

import express from "express";
import cors from "cors";
import apiRouter from "./routes/api.js";

const app = express();
const PORT = parseInt(process.env.PORT ?? "3007", 10);

app.use(cors());
app.use(express.json());

app.get("/healthcheck", (_req, res) => res.status(200).send("ok"));

app.use(apiRouter);

const clientDist = process.env.CLIENT_DIST;
if (clientDist) {
  app.use(express.static(clientDist));
  app.get("*", (req, res, next) => {
    if (req.path.startsWith("/api/")) return next();
    res.sendFile(path.join(clientDist, "index.html"));
  });
}

app.listen(PORT, () => {
  console.log(`Server listening on http://localhost:${PORT} (spcs=${!!process.env.SNOWFLAKE_HOST})`);
  if (process.env.SNOWFLAKE_HOST) {
    import("./services/snowflake.js")
      .then(async ({ runQuery }) => {
        const cnt = await runQuery("SELECT COUNT(*) AS n FROM APP_DATA.DT_SPEND_360");
        console.log(`SELFCHECK ok: DT_SPEND_360 rows=${cnt[0]?.n}`);
      })
      .catch((e) => console.error("SELFCHECK failed:", String(e)));
  }
});
