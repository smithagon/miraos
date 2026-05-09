import { useMemo } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

const PALETTE = ['#c9a84c', '#6366f1', '#34d399', '#f472b6', '#38bdf8', '#fb923c', '#a78bfa'];

export type ChartSpecType = 'line' | 'bar' | 'pie';

export interface ChartSeries {
  name: string;
  data: number[];
  color?: string;
}

export interface ChartSegment {
  name: string;
  value: number;
  color?: string;
}

export interface ChartSpec {
  type: ChartSpecType;
  title?: string;
  labels?: string[];
  series?: ChartSeries[];
  segments?: ChartSegment[];
  data?: number[];
  colors?: string[];
}

function stripFence(raw: string): string {
  let t = raw.trim();
  const fence = /^```(?:chart)?\s*\n?([\s\S]*?)\n?```$/m.exec(t);
  if (fence) t = fence[1].trim();
  return t;
}

function parseSpec(text: string): { ok: true; spec: ChartSpec } | { ok: false; error: string } {
  try {
    const json = stripFence(text);
    const spec = JSON.parse(json) as ChartSpec;
    if (!spec || typeof spec !== 'object') return { ok: false, error: 'Chart spec must be a JSON object.' };
    if (!['line', 'bar', 'pie'].includes(spec.type)) {
      return { ok: false, error: '`type` must be "line", "bar", or "pie".' };
    }
    if (spec.type === 'pie') {
      if (Array.isArray(spec.segments) && spec.segments.length > 0) {
        for (const s of spec.segments) {
          if (typeof s?.name !== 'string' || typeof s?.value !== 'number' || Number.isNaN(s.value)) {
            return { ok: false, error: 'Each pie `segments` item needs string `name` and numeric `value`.' };
          }
        }
        return { ok: true, spec };
      }
      const labels = spec.labels;
      const data = spec.data;
      if (!Array.isArray(labels) || !Array.isArray(data) || labels.length !== data.length || labels.length === 0) {
        return {
          ok: false,
          error: 'Pie charts need `segments: [{ name, value }, ...]` or matching `labels` and `data` arrays.',
        };
      }
      return { ok: true, spec };
    }
    const labels = spec.labels;
    if (!Array.isArray(labels) || labels.length === 0) {
      return { ok: false, error: 'Line and bar charts require a non-empty `labels` array.' };
    }
    // Graceful fallback: if model emits `data` without `series`, convert it to a single series.
    if ((!Array.isArray(spec.series) || spec.series.length === 0) && Array.isArray(spec.data) && spec.data.length === labels.length) {
      spec.series = [{ name: 'Value', data: spec.data }];
    }
    const series = spec.series;
    if (!Array.isArray(series) || series.length === 0) {
      return { ok: false, error: 'Line and bar charts require a non-empty `series` array.' };
    }

    // Graceful fallback for common malformed payload:
    // labels = ["A","B","C"], series = [{name:"x",data:[1]}, {name:"x",data:[2]}, {name:"x",data:[3]}]
    // Convert to one series: {name:"x", data:[1,2,3]}.
    const looksLikeExplodedSingleMetric =
      series.length === labels.length &&
      series.every((s) => Array.isArray(s?.data) && s.data.length === 1);
    if (looksLikeExplodedSingleMetric) {
      const points = series.map((s) => Number(s.data[0]));
      if (points.some((n) => Number.isNaN(n))) {
        return { ok: false, error: 'Line/bar series values must be numeric.' };
      }
      const uniqueNames = Array.from(new Set(series.map((s) => s.name).filter(Boolean)));
      spec.series = [
        {
          name: uniqueNames.length === 1 ? uniqueNames[0] : 'Value',
          data: points,
          color: series[0]?.color,
        },
      ];
    }

    const normalizedSeries = spec.series!;
    for (const s of normalizedSeries) {
      if (typeof s?.name !== 'string' || !Array.isArray(s.data)) {
        return { ok: false, error: 'Each `series` item needs `name` and `data` (number array).' };
      }
      if (s.data.length !== labels.length) {
        return { ok: false, error: `Series "${s.name}" length must match labels (${labels.length}).` };
      }
      if (s.data.some((v) => typeof v !== 'number' || Number.isNaN(v))) {
        return { ok: false, error: `Series "${s.name}" must contain numeric values only.` };
      }
    }
    return { ok: true, spec };
  } catch (e) {
    const msg = e instanceof Error ? e.message : 'Invalid JSON.';
    return { ok: false, error: msg };
  }
}

type Props = {
  source: string;
};

export default function ChatChartWidget({ source }: Props) {
  const parsed = useMemo(() => parseSpec(source), [source]);

  if (!parsed.ok) {
    return (
      <div className="chat-chart-widget chat-chart-widget--error" role="figure" aria-label="Chart error">
        <div className="chat-chart-widget__title">Chart could not be rendered</div>
        <p className="chat-chart-widget__err">{parsed.error}</p>
        <details className="chat-chart-widget__raw">
          <summary>Source</summary>
          <pre>{source}</pre>
        </details>
      </div>
    );
  }

  const { spec } = parsed;
  const title = spec.title?.trim();

  if (spec.type === 'pie') {
    const pieData =
      spec.segments && spec.segments.length > 0
        ? spec.segments.map((s, i) => ({
            name: s.name,
            value: s.value,
            fill: s.color || spec.colors?.[i] || PALETTE[i % PALETTE.length],
          }))
        : (spec.labels ?? []).map((name, i) => ({
            name,
            value: spec.data![i],
            fill: spec.colors?.[i] || PALETTE[i % PALETTE.length],
          }));

    return (
      <div className="chat-chart-widget" role="figure" aria-label={title || 'Pie chart'}>
        {title ? <div className="chat-chart-widget__title">{title}</div> : null}
        <div className="chat-chart-widget__canvas">
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie
                data={pieData}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                outerRadius={100}
                label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}
              >
                {pieData.map((entry, i) => (
                  <Cell key={`${entry.name}-${i}`} fill={entry.fill} stroke="rgba(0,0,0,0.2)" />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ background: '#1a1a18', border: '1px solid rgba(255,255,255,0.12)', borderRadius: 8 }}
                labelStyle={{ color: '#e0e0e0' }}
                itemStyle={{ color: '#e0e0e0' }}
              />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>
    );
  }

  const labels = spec.labels!;
  const series = spec.series!;
  const rows = labels.map((label, i) => {
    const row: Record<string, string | number> = { label };
    for (const s of series) {
      row[s.name] = s.data[i] ?? 0;
    }
    return row;
  });

  const axisStyle = { stroke: '#555', tick: { fill: '#aaa', fontSize: 12 } };
  const tooltipStyle = {
    contentStyle: { background: '#1a1a18', border: '1px solid rgba(255,255,255,0.12)', borderRadius: 8 },
    labelStyle: { color: '#e0e0e0' },
    itemStyle: { color: '#e0e0e0' },
  };

  const ChartBody =
    spec.type === 'line' ? (
      <LineChart data={rows} margin={{ top: 8, right: 8, left: 0, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
        <XAxis dataKey="label" {...axisStyle} />
        <YAxis {...axisStyle} />
        <Tooltip {...tooltipStyle} />
        <Legend />
        {series.map((s, idx) => (
          <Line
            key={s.name}
            type="monotone"
            dataKey={s.name}
            stroke={s.color || PALETTE[idx % PALETTE.length]}
            strokeWidth={2}
            dot={{ r: 3, fill: s.color || PALETTE[idx % PALETTE.length] }}
          />
        ))}
      </LineChart>
    ) : (
      <BarChart data={rows} margin={{ top: 8, right: 8, left: 0, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
        <XAxis dataKey="label" {...axisStyle} />
        <YAxis {...axisStyle} />
        <Tooltip {...tooltipStyle} />
        <Legend />
        {series.map((s, idx) => (
          <Bar key={s.name} dataKey={s.name} fill={s.color || PALETTE[idx % PALETTE.length]} radius={[4, 4, 0, 0]} />
        ))}
      </BarChart>
    );

  return (
    <div className="chat-chart-widget" role="figure" aria-label={title || `${spec.type} chart`}>
      {title ? <div className="chat-chart-widget__title">{title}</div> : null}
      <div className="chat-chart-widget__canvas">
        <ResponsiveContainer width="100%" height={280}>
          {ChartBody}
        </ResponsiveContainer>
      </div>
    </div>
  );
}
