/**
 * server.js — Entry point
 *
 * Loads environment variables, then starts the Express HTTP server.
 * All application logic lives in src/app.js.
 */

require('dotenv').config();

const app  = require('./src/app');
const port = parseInt(process.env.BACKEND_PORT, 10) || 4000;

app.listen(port, () => {
  console.log(`[scarlet-backend] Running on http://localhost:${port}`);
  console.log(`[scarlet-backend] Health endpoint → http://localhost:${port}/api/health`);
});
