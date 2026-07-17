import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Legend, Tooltip } from "recharts";
import { FRAME_META } from "../lib/api";

// Data: array of publishers with their primary_frame; we compute per-frame intensity.
export default function FrameRadar({ publishers }) {
  const frameKeys = Object.keys(FRAME_META);
  const frameShortLabels = { economic_impact: "Economic", political_conflict: "Political", human_interest: "Human", environmental: "Environ.", public_health: "Health", tech_innovation: "Tech", national_security: "Security", corporate_profit: "Corporate", social_justice: "Justice", legal_regulatory: "Legal" };

  const data = frameKeys.map((f) => {
    const row = { frame: frameShortLabels[f] || f };
    publishers.forEach((p) => {
      row[p.source] = p.primary_frame === f ? 1 : 0;
    });
    return row;
  });

  const palette = ["#60a5fa", "#f43f5e", "#facc15", "#10b981", "#a855f7", "#fb923c", "#2dd4bf", "#818cf8", "#ec4899", "#94a3b8"];

  return (
    <div style={{ width: "100%", height: 380 }}>
      <ResponsiveContainer>
        <RadarChart data={data} outerRadius="72%">
          <PolarGrid stroke="#1e293b" />
          <PolarAngleAxis dataKey="frame" tick={{ fill: "#94a3b8", fontSize: 10, fontFamily: "JetBrains Mono" }} />
          <PolarRadiusAxis stroke="#334155" tick={false} axisLine={false} domain={[0, 1]} />
          <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", fontFamily: "JetBrains Mono", fontSize: 11, color: "#e2e8f0" }} />
          <Legend
            wrapperStyle={{ fontFamily: "JetBrains Mono", fontSize: 10, color: "#94a3b8", paddingTop: 12 }}
            iconType="square"
            iconSize={8}
          />
          {publishers.map((p, i) => (
            <Radar key={p.source} name={p.source} dataKey={p.source} stroke={palette[i % palette.length]} fill={palette[i % palette.length]} fillOpacity={0.15} strokeWidth={1.5} />
          ))}
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
