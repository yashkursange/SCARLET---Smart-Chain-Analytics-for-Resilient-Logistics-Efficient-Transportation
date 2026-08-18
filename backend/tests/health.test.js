/**
 * tests/health.test.js — Express health endpoint tests
 *
 * Uses supertest to make real HTTP requests against the app without
 * binding to a port.  The DB pool is mocked so tests run without a
 * live PostgreSQL instance.
 */

// Load env variables before importing app (dotenv not called in app.js itself).
process.env.DB_HOST     = 'localhost';
process.env.DB_PORT     = '5432';
process.env.DB_NAME     = 'scarlet_test';
process.env.DB_USER     = 'scarlet_user';
process.env.DB_PASSWORD = 'test_password';

const request = require('supertest');
const app     = require('../src/app');

// Mock the pg pool so tests never need a real database.
jest.mock('../src/config/db', () => ({
  query: jest.fn(),
  on:    jest.fn(),
}));

const pool = require('../src/config/db');

// ── Test suite ────────────────────────────────────────────────────────────────

describe('GET /api/health', () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  it('returns 200 with status ok when database is reachable', async () => {
    pool.query.mockResolvedValueOnce({ rows: [{ '?column?': 1 }] });

    const res = await request(app).get('/api/health');

    expect(res.status).toBe(200);
    expect(res.body.status).toBe('ok');
    expect(res.body.service).toBe('scarlet-backend');
    expect(res.body.database).toBe('connected');
    expect(res.body.timestamp).toBeDefined();
  });

  it('returns 503 with status degraded when database is unreachable', async () => {
    pool.query.mockRejectedValueOnce(new Error('Connection refused'));

    const res = await request(app).get('/api/health');

    expect(res.status).toBe(503);
    expect(res.body.status).toBe('degraded');
    expect(res.body.database).toBe('error');
  });

  it('returns 404 for unknown routes', async () => {
    const res = await request(app).get('/api/unknown');
    expect(res.status).toBe(404);
  });
});
