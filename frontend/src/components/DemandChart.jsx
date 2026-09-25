/**
 * DemandChart.jsx — minimal inline SVG bar chart for historical + forecast
 * demand, styled to match the existing dark dashboard theme. No charting
 * library dependency is added (frontend/package.json only lists axios,
 * react, react-dom) — this keeps the integration change minimal.
 */
export default function DemandChart({ history, forecast }) {
  const historyBars = history.map(h => ({ date: h.date, value: h.actual_demand, kind: 'history' }));
  const forecastBars = forecast.map(f => ({ date: f.date, value: f.predicted_demand, kind: 'forecast' }));
  const bars = [...historyBars, ...forecastBars];

  if (bars.length === 0) return null;

  const max = Math.max(1, ...bars.map(b => b.value));
  const width = Math.max(bars.length * 14, 300);
  const height = 140;
  const barWidth = 8;

  return (
    <div className="overflow-x-auto">
      <svg width={width} height={height + 24} className="block">
        {bars.map((b, i) => {
          const barHeight = (b.value / max) * height;
          const x = i * 14;
          const y = height - barHeight;
          const color = b.kind === 'history' ? '#64748b' /* slate-500 */ : '#f43f5e' /* rose-500 */;
          return (
            <g key={`${b.kind}-${b.date}`}>
              <rect x={x} y={y} width={barWidth} height={barHeight} fill={color} rx={1.5} />
            </g>
          );
        })}
        {/* divider between history and forecast */}
        {historyBars.length > 0 && forecastBars.length > 0 && (
          <line
            x1={historyBars.length * 14 - 3}
            y1={0}
            x2={historyBars.length * 14 - 3}
            y2={height}
            stroke="#334155"
            strokeDasharray="3,3"
          />
        )}
      </svg>
      <div className="flex items-center gap-4 mt-2 text-xs text-slate-500">
        <span className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-slate-500 inline-block" /> Historical demand
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-rose-500 inline-block" /> Predicted demand
        </span>
      </div>
    </div>
  );
}
