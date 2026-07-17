import { BarChart, Bar, XAxis, YAxis, ReferenceLine, ResponsiveContainer, Tooltip, Cell } from "recharts";
import { sentimentColor } from "../lib/api";

export default function SentimentBarChart({ data }) {
  const chartData = data.map((d) => ({ ...d, name: d.source }));
  const height = Math.max(240, chartData.length * 40);
  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer>
        <BarChart data={chartData} layout="vertical" margin={{ top: 8, right: 24, left: 12, bottom: 8 }}>
          <XAxis
            type="number"
            domain={[-1, 1]}
            ticks={[-1, -0.5, 0, 0.5, 1]}
            stroke="#334155"
            tick={{ fill: "#64748b", fontSize: 10, fontFamily: "JetBrains Mono" }}
            axisLine={{ stroke: "#1e293b" }}
          />
          <YAxis
            type="category"
            dataKey="name"
            stroke="#334155"
            tick={{ fill: "#94a3b8", fontSize: 11, fontFamily: "JetBrains Mono" }}
            axisLine={{ stroke: "#1e293b" }}
            width={90}
          />
          <ReferenceLine x={0} stroke="#475569" strokeDasharray="3 3" />
          <Tooltip
            cursor={{ fill: "rgba(148,163,184,0.05)" }}
            contentStyle={{
              background: "#0f172a",
              border: "1px solid #1e293b",
              borderRadius: 2,
              fontFamily: "JetBrains Mono",
              fontSize: 11,
              color: "#e2e8f0",
            }}
            formatter={(v, _, item) => [`${v > 0 ? "+" : ""}${v.toFixed(2)}`, item.payload.sentiment_label]}
            labelFormatter={(l) => l}
          />
          <Bar dataKey="sentiment_score" radius={[0, 0, 0, 0]}>
            {chartData.map((d, i) => (
              <Cell key={i} fill={sentimentColor(d.sentiment_score)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
