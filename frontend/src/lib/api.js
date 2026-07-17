import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const api = axios.create({ baseURL: API, timeout: 30000 });

export const fetchStories = async (params = {}) => {
  const { data } = await api.get("/stories", { params });
  return data;
};

export const fetchStory = async (id) => {
  const { data } = await api.get(`/stories/${id}`);
  return data;
};

export const fetchStats = async () => {
  const { data } = await api.get("/stats");
  return data;
};

export const searchStories = async (query, limit = 12) => {
  const { data } = await api.post("/search", { query, limit });
  return data;
};

export const FRAME_META = {
  economic_impact: { label: "Economic Impact", color: "#60a5fa", bg: "bg-blue-500/10", text: "text-blue-300", border: "border-blue-500/30" },
  political_conflict: { label: "Political Conflict", color: "#f43f5e", bg: "bg-rose-500/10", text: "text-rose-300", border: "border-rose-500/30" },
  human_interest: { label: "Human Interest", color: "#facc15", bg: "bg-yellow-500/10", text: "text-yellow-300", border: "border-yellow-500/30" },
  environmental: { label: "Environmental", color: "#10b981", bg: "bg-emerald-500/10", text: "text-emerald-300", border: "border-emerald-500/30" },
  public_health: { label: "Public Health", color: "#ec4899", bg: "bg-pink-500/10", text: "text-pink-300", border: "border-pink-500/30" },
  tech_innovation: { label: "Tech Innovation", color: "#818cf8", bg: "bg-indigo-500/10", text: "text-indigo-300", border: "border-indigo-500/30" },
  national_security: { label: "National Security", color: "#fb923c", bg: "bg-orange-500/10", text: "text-orange-300", border: "border-orange-500/30" },
  corporate_profit: { label: "Corporate Profit", color: "#a855f7", bg: "bg-purple-500/10", text: "text-purple-300", border: "border-purple-500/30" },
  social_justice: { label: "Social Justice", color: "#2dd4bf", bg: "bg-teal-500/10", text: "text-teal-300", border: "border-teal-500/30" },
  legal_regulatory: { label: "Legal & Regulatory", color: "#94a3b8", bg: "bg-slate-500/15", text: "text-slate-300", border: "border-slate-500/30" },
};

export const sentimentColor = (score) => {
  if (score > 0.15) return "#10b981";
  if (score < -0.15) return "#f43f5e";
  return "#60a5fa";
};

export const sentimentLabel = (score) => {
  if (score > 0.15) return "Positive";
  if (score < -0.15) return "Negative";
  return "Neutral";
};

export const relativeTime = (iso) => {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return `${Math.floor(diff)}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
};
