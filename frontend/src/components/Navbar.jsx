import { Link, NavLink } from "react-router-dom";
import { Radar, Search as SearchIcon, Layers } from "lucide-react";

export default function Navbar() {
  const linkClass = ({ isActive }) =>
    `overline transition-colors duration-200 hover:text-slate-100 ${
      isActive ? "text-slate-100" : "text-slate-500"
    }`;
  return (
    <header
      data-testid="app-navbar"
      className="sticky top-0 z-30 bg-slate-950/80 backdrop-blur-xl border-b border-slate-800"
    >
      <div className="max-w-7xl mx-auto px-6 lg:px-10 h-16 flex items-center justify-between">
        <Link to="/" data-testid="nav-home" className="flex items-center gap-2.5 group">
          <div className="w-8 h-8 border border-slate-700 grid place-items-center bg-slate-900 group-hover:border-slate-500 transition-colors duration-200">
            <Radar className="w-4 h-4 text-emerald-400" strokeWidth={1.5} />
          </div>
          <div className="leading-none">
            <div className="font-display text-[15px] font-bold tracking-tight text-slate-100">PRISM</div>
            <div className="text-[10px] font-mono uppercase tracking-[0.25em] text-slate-500">news.bias.terminal</div>
          </div>
        </Link>
        <nav className="flex items-center gap-8">
          <NavLink data-testid="nav-feed" to="/" end className={linkClass}>
            <span className="flex items-center gap-1.5"><Layers className="w-3 h-3" />Feed</span>
          </NavLink>
          <NavLink data-testid="nav-search" to="/search" className={linkClass}>
            <span className="flex items-center gap-1.5"><SearchIcon className="w-3 h-3" />Search</span>
          </NavLink>
          <NavLink data-testid="nav-about" to="/about" className={linkClass}>
            About
          </NavLink>
        </nav>
      </div>
    </header>
  );
}
