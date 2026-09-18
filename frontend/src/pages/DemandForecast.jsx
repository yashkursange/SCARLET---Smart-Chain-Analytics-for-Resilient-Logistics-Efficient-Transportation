import React, { useState } from 'react';
import axios from 'axios';
import DemandChart from '../components/DemandChart';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:4000';

const ERROR_MESSAGES = {
  product_not_found: 'No product was found with that ID.',
  market_not_found: 'No market was found with that ID.',
  product_not_mapped: 'This product has not been linked to the demand model yet (an admin needs to set its ml_item_id/ml_dept_id/ml_cat_id mapping).',
  market_not_mapped: 'This market has not been linked to the demand model yet (an admin needs to set its ml_store_id/ml_state_id mapping).',
  insufficient_history: 'Not enough historical demand is recorded for this product/market yet — at least 28 days of daily history are required.',
  model_not_loaded: 'The demand model is not currently loaded on the ML service.',
  no_inventory_record: 'No inventory record exists for this product at this market\u2019s node, so inventory cannot be projected.',
  invalid_request: 'Please provide a valid product ID, market ID and horizon.',
};

const RISK_STYLES = {
  OK:       'bg-emerald-900/40 border-emerald-500 text-emerald-200',
  LOW:      'bg-amber-900/40 border-amber-500 text-amber-200',
  CRITICAL: 'bg-orange-900/40 border-orange-500 text-orange-200',
  STOCKOUT: 'bg-red-900/50 border-red-500 text-red-200',
};

export default function DemandForecast() {
  const [productId, setProductId] = useState('');
  const [marketId, setMarketId] = useState('');
  const [horizon, setHorizon] = useState(7);
  const [forecastDate, setForecastDate] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [projection, setProjection] = useState(null);

  const generateForecast = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.post(`${API_URL}/api/forecast/demand`, {
        product_id: productId,
        market_id: marketId,
        forecast_date: forecastDate || undefined,
        horizon,
      });
      setResult(response.data);
      setLastUpdated(new Date());

      // Inventory projection is a secondary, best-effort call: a product with
      // no inventory record still has a perfectly valid demand forecast, so a
      // failure here must not discard the forecast above.
      try {
        const projResponse = await axios.post(`${API_URL}/api/forecast/inventory-projection`, {
          product_id: productId,
          market_id: marketId,
          forecast_date: forecastDate || undefined,
          horizon,
        });
        setProjection(projResponse.data);
      } catch {
        setProjection(null);
      }
    } catch (err) {
      const body = err.response?.data;
      const friendly = body?.error_code ? ERROR_MESSAGES[body.error_code] : null;
      setError(friendly || body?.error || 'An error occurred while generating the forecast.');
      setResult(null);
      setProjection(null);
    } finally {
      setLoading(false);
    }
  };

  const changeLabel = (pct) => {
    if (pct === null || pct === undefined) return null;
    const up = pct >= 0;
    return (
      <span className={up ? 'text-emerald-400' : 'text-red-400'}>
        {up ? '▲' : '▼'} {Math.abs(pct)}% vs. recent history
      </span>
    );
  };

  return (
    <div className="max-w-4xl mx-auto text-white">
      <h1 className="text-3xl font-bold mb-6">Demand Forecast</h1>

      {/* ── Input form ── */}
      <div className="bg-slate-900 p-6 rounded-lg mb-8 shadow-lg">
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <label className="block text-sm text-slate-400 mb-1">Product ID (UUID)</label>
            <input type="text" value={productId} onChange={e => setProductId(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded p-2 text-white"
              placeholder="e.g. 123e4567-e89b-12d3-a456-426614174000" />
          </div>
          <div>
            <label className="block text-sm text-slate-400 mb-1">Market ID (UUID)</label>
            <input type="text" value={marketId} onChange={e => setMarketId(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded p-2 text-white"
              placeholder="e.g. 123e4567-e89b-12d3-a456-426614174000" />
          </div>
          <div>
            <label className="block text-sm text-slate-400 mb-1">Forecast Start Date (optional)</label>
            <input type="date" value={forecastDate} onChange={e => setForecastDate(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded p-2 text-white" />
          </div>
          <div>
            <label className="block text-sm text-slate-400 mb-1">Horizon (Days)</label>
            <select value={horizon} onChange={e => setHorizon(Number(e.target.value))}
              className="w-full bg-slate-800 border border-slate-700 rounded p-2 text-white">
              <option value={7}>7 Days</option>
              <option value={14}>14 Days</option>
              <option value={28}>28 Days</option>
            </select>
          </div>
        </div>
        <button onClick={generateForecast} disabled={loading || !productId || !marketId}
          className="bg-red-600 hover:bg-red-700 text-white font-bold py-2 px-4 rounded transition disabled:opacity-50">
          {loading ? 'Generating…' : 'Generate Forecast'}
        </button>
      </div>

      {/* ── Loading state ── */}
      {loading && (
        <div id="forecast-loading" className="flex items-center gap-2 text-slate-400 mb-6">
          <span className="relative flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-400" />
          </span>
          Generating forecast…
        </div>
      )}

      {/* ── Error state ── */}
      {error && !loading && (
        <div id="forecast-error" className="bg-red-900/50 border border-red-500 text-red-200 p-4 rounded mb-6">
          {error}
        </div>
      )}

      {/* ── Results ── */}
      {result && result.success && !loading && (
        <div className="bg-slate-900 p-6 rounded-lg shadow-lg space-y-6">

          {/* Model info + metrics */}
          <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-800 pb-4">
            <div>
              <h2 className="text-xl font-bold">{result.product_name || 'Forecast'}</h2>
              <p className="text-sm text-slate-400 mt-1">
                Model: <span className="text-slate-200 font-mono">{result.model?.name}</span>
                {' '}· Version: <span className="text-slate-200 font-mono">{result.model?.version}</span>
              </p>
              {lastUpdated && (
                <p className="text-xs text-slate-500 mt-1">Last updated: {lastUpdated.toLocaleTimeString()}</p>
              )}
            </div>
            {result.model?.metrics && (
              <div className="grid grid-cols-4 gap-3 text-center">
                {['MAE', 'RMSE', 'sMAPE', 'WAPE'].map(k => (
                  result.model.metrics[k] !== undefined && (
                    <div key={k} className="bg-slate-800/60 rounded-lg px-3 py-2">
                      <p className="text-[10px] uppercase tracking-widest text-slate-500">{k}</p>
                      <p className="text-sm font-mono text-slate-200">
                        {k === 'sMAPE' || k === 'WAPE'
                          ? `${result.model.metrics[k].toFixed(1)}%`
                          : result.model.metrics[k].toFixed(2)}
                      </p>
                    </div>
                  )
                ))}
              </div>
            )}
          </div>

          {/* Demand change summary */}
          {result.demand_change_pct !== null && result.demand_change_pct !== undefined && (
            <p className="text-sm">
              Forecast average demand is {changeLabel(result.demand_change_pct)}
            </p>
          )}

          {/* Chart: historical + predicted demand */}
          {result.history && result.forecast && (
            <DemandChart history={result.history} forecast={result.forecast} />
          )}

          {/* Inventory projection / stockout risk — driven by this same forecast */}
          {projection && projection.success && (
            <div className="border-t border-slate-800 pt-4">
              <h3 className="text-sm font-semibold uppercase tracking-widest text-slate-500 mb-3">
                Inventory Projection &amp; Stockout Risk
              </h3>

              <div className={`border rounded-lg p-4 mb-4 ${RISK_STYLES[projection.risk_level] || RISK_STYLES.OK}`}>
                <p className="font-bold">Risk level: {projection.risk_level}</p>
                {projection.projected_stockout_date ? (
                  <p className="text-sm mt-1">
                    Projected to run out on <span className="font-mono">{projection.projected_stockout_date}</span>.
                  </p>
                ) : (
                  <p className="text-sm mt-1">No stockout projected within this horizon.</p>
                )}
                <p className="text-xs mt-2 opacity-80">
                  On hand now: {projection.current_inventory?.available_quantity}
                  {' '}· Lowest projected: {projection.minimum_projected_on_hand}
                  {projection.days_of_cover_at_minimum !== null && projection.days_of_cover_at_minimum !== undefined && (
                    <> · Days of cover at minimum: {projection.days_of_cover_at_minimum}</>
                  )}
                </p>
              </div>

              <table className="w-full text-left border-collapse text-sm">
                <thead>
                  <tr className="border-b border-slate-700">
                    <th className="py-2 text-slate-300">Date</th>
                    <th className="py-2 text-slate-300 text-right">Inbound</th>
                    <th className="py-2 text-slate-300 text-right">Forecast Demand</th>
                    <th className="py-2 text-slate-300 text-right">Projected On Hand</th>
                  </tr>
                </thead>
                <tbody>
                  {projection.projection.map((p, idx) => (
                    <tr key={idx} className="border-b border-slate-800">
                      <td className="py-2 text-slate-400">{p.date}</td>
                      <td className="py-2 text-slate-400 font-mono text-right">{p.expected_inbound.toFixed(2)}</td>
                      <td className="py-2 text-slate-400 font-mono text-right">{p.forecast_demand.toFixed(2)}</td>
                      <td className={`py-2 font-mono text-right ${p.projected_on_hand <= 0 ? 'text-red-400 font-bold' : 'text-slate-200'}`}>
                        {p.projected_on_hand.toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Forecast table */}
          <div>
            <h3 className="text-sm font-semibold uppercase tracking-widest text-slate-500 mb-2">
              Forecast — next {result.forecast_horizon} day(s)
            </h3>
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-700">
                  <th className="py-2 text-slate-300">Date</th>
                  <th className="py-2 text-slate-300 text-right">Predicted Demand</th>
                </tr>
              </thead>
              <tbody>
                {result.forecast.map((f, idx) => (
                  <tr key={idx} className="border-b border-slate-800">
                    <td className="py-2 text-slate-400">{f.date}</td>
                    <td className="py-2 text-slate-200 font-mono text-right">{f.predicted_demand.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
