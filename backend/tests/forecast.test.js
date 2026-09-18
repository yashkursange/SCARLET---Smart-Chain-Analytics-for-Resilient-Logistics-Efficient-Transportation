/**
 * tests/forecast.test.js — Express forecast/inventory proxy route tests
 *
 * Mocks axios (the ML service call) so these tests run without a live
 * Python ML service, following the same mocking approach as health.test.js.
 */
process.env.DB_HOST     = 'localhost';
process.env.DB_PORT     = '5432';
process.env.DB_NAME     = 'scarlet_test';
process.env.DB_USER     = 'scarlet_user';
process.env.DB_PASSWORD = 'test_password';
process.env.ML_SERVICE_URL = 'http://localhost:8000';

const request = require('supertest');

jest.mock('../src/config/db', () => ({ query: jest.fn(), on: jest.fn() }));
jest.mock('axios');
const axios = require('axios');
const app = require('../src/app');

const VALID = { product_id: 'p1', market_id: 'm1', horizon: 7 };

describe('POST /api/forecast/demand', () => {
  afterEach(() => jest.clearAllMocks());

  it('proxies a successful forecast from the ML service', async () => {
    const mlResponse = {
      success: true,
      product_id: 'p1',
      market_id: 'm1',
      model_version: 'scarlet-demand-v1.0',
      forecast: [{ date: '2026-01-01', predicted_demand: 1.23 }],
    };
    axios.post.mockResolvedValueOnce({ data: mlResponse });

    const res = await request(app).post('/api/forecast/demand').send(VALID);

    expect(res.status).toBe(200);
    expect(res.body).toEqual(mlResponse);
    expect(axios.post).toHaveBeenCalledWith(
      'http://localhost:8000/api/ml/demand/forecast',
      expect.objectContaining({ product_id: 'p1', market_id: 'm1', horizon: 7 })
    );
  });

  it('rejects a request missing product_id without calling the ML service', async () => {
    const res = await request(app).post('/api/forecast/demand').send({ market_id: 'm1' });
    expect(res.status).toBe(400);
    expect(res.body.error_code).toBe('invalid_request');
    expect(axios.post).not.toHaveBeenCalled();
  });

  it('rejects an out-of-range horizon', async () => {
    const res = await request(app)
      .post('/api/forecast/demand')
      .send({ ...VALID, horizon: 99 });
    expect(res.status).toBe(400);
    expect(axios.post).not.toHaveBeenCalled();
  });

  it('preserves the ML service 404 for an unknown product', async () => {
    axios.post.mockRejectedValueOnce({
      response: { status: 404, data: { success: false, error_code: 'product_not_found', error: 'No product' } },
    });

    const res = await request(app).post('/api/forecast/demand').send(VALID);
    expect(res.status).toBe(404);
    expect(res.body.error_code).toBe('product_not_found');
  });

  it('preserves the ML service 422 for an unmapped product', async () => {
    axios.post.mockRejectedValueOnce({
      response: { status: 422, data: { success: false, error_code: 'product_not_mapped', error: 'Not mapped' } },
    });

    const res = await request(app).post('/api/forecast/demand').send(VALID);
    expect(res.status).toBe(422);
    expect(res.body.error_code).toBe('product_not_mapped');
  });

  it('returns 503 when the ML service reports the model is not loaded', async () => {
    axios.post.mockRejectedValueOnce({
      response: { status: 503, data: { success: false, error_code: 'model_not_loaded', error: 'not loaded' } },
    });

    const res = await request(app).post('/api/forecast/demand').send(VALID);
    expect(res.status).toBe(503);
    expect(res.body.error_code).toBe('model_not_loaded');
  });

  it('returns 503 when the ML service is unreachable', async () => {
    const err = new Error('connect ECONNREFUSED');
    err.code = 'ECONNREFUSED';
    axios.post.mockRejectedValueOnce(err);

    const res = await request(app).post('/api/forecast/demand').send(VALID);
    expect(res.status).toBe(503);
    expect(res.body.error).toMatch(/unavailable/i);
  });
});

describe('POST /api/forecast/inventory-projection', () => {
  afterEach(() => jest.clearAllMocks());

  it('proxies a successful inventory projection', async () => {
    const mlResponse = {
      success: true,
      risk_level: 'LOW',
      projected_stockout_date: null,
      projection: [{ date: '2026-01-01', projected_on_hand: 12.5 }],
    };
    axios.post.mockResolvedValueOnce({ data: mlResponse });

    const res = await request(app).post('/api/forecast/inventory-projection').send(VALID);

    expect(res.status).toBe(200);
    expect(res.body.risk_level).toBe('LOW');
    expect(axios.post).toHaveBeenCalledWith(
      'http://localhost:8000/api/ml/inventory/projection',
      expect.objectContaining({ product_id: 'p1', market_id: 'm1' })
    );
  });

  it('preserves a 422 when no inventory record exists', async () => {
    axios.post.mockRejectedValueOnce({
      response: { status: 422, data: { success: false, error_code: 'no_inventory_record', error: 'none' } },
    });

    const res = await request(app).post('/api/forecast/inventory-projection').send(VALID);
    expect(res.status).toBe(422);
    expect(res.body.error_code).toBe('no_inventory_record');
  });
});

describe('GET /api/health/ml', () => {
  afterEach(() => jest.clearAllMocks());

  it('proxies ML service health', async () => {
    axios.get.mockResolvedValueOnce({
      data: { status: 'ok', service: 'ml-service', demand_model: { status: 'loaded' } },
    });

    const res = await request(app).get('/api/health/ml');
    expect(res.status).toBe(200);
    expect(res.body.demand_model.status).toBe('loaded');
  });

  it('returns 503 when the ML service is unreachable', async () => {
    axios.get.mockRejectedValueOnce(new Error('ECONNREFUSED'));

    const res = await request(app).get('/api/health/ml');
    expect(res.status).toBe(503);
    expect(res.body.demand_model.status).toBe('not_loaded');
  });
});
