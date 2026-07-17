import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "sonner";
import Navbar from "./components/Navbar";
import Home from "./pages/Home";
import StoryDetail from "./pages/StoryDetail";
import Search from "./pages/Search";
import About from "./pages/About";

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-slate-950 text-slate-100 grain relative">
        <Navbar />
        <main className="relative z-10">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/story/:id" element={<StoryDetail />} />
            <Route path="/search" element={<Search />} />
            <Route path="/about" element={<About />} />
          </Routes>
        </main>
        <footer className="border-t border-slate-900 mt-20 py-8 relative z-10">
          <div className="max-w-7xl mx-auto px-6 lg:px-10 flex items-center justify-between text-xs text-slate-600 font-mono">
            <span>PRISM · News Bias Terminal</span>
            <span className="uppercase tracking-[0.2em]">Phase 1 · demo build</span>
          </div>
        </footer>
        <Toaster theme="dark" position="bottom-right" toastOptions={{ style: { background: "#0f172a", border: "1px solid #1e293b", color: "#e2e8f0", fontFamily: "JetBrains Mono", fontSize: 12 } }} />
      </div>
    </BrowserRouter>
  );
}

export default App;
