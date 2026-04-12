import {
  BrowserRouter as Router,
  Routes,
  Route,
  NavLink,
} from "react-router-dom";
import HidatoFrontendApp from "./Hidato";
import AnalysisPage from "./AnalysisPage";

function navLinkClass({ isActive }: { isActive: boolean }) {
  return [
    "px-5 py-2.5 rounded-full text-sm font-semibold transition-all duration-200 border shadow-sm",
    isActive
      ? "bg-amber-200 text-stone-950 border-amber-700/70 shadow-[0_4px_18px_rgba(0,0,0,0.25)]"
      : "bg-[linear-gradient(180deg,rgba(84,58,34,0.95)_0%,rgba(55,38,24,0.98)_100%)] text-amber-100 border-amber-900/40 hover:bg-[linear-gradient(180deg,rgba(103,73,43,0.96)_0%,rgba(65,45,28,0.99)_100%)] hover:text-amber-50",
  ].join(" ");
}

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-[radial-gradient(circle_at_top,#2d1b12_0%,#16110d_45%,#0b0907_100%)] text-white">
        <div className="border-b border-amber-900/25 bg-[linear-gradient(180deg,rgba(55,35,24,0.92)_0%,rgba(24,17,13,0.98)_100%)] backdrop-blur">
          <div className="mx-auto flex max-w-7xl gap-3 px-4 py-4 md:px-8">
            <NavLink to="/" className={navLinkClass} end>
              Game Board
            </NavLink>

            <NavLink to="/analysis" className={navLinkClass}>
              Analysis
            </NavLink>
          </div>
        </div>

        <Routes>
          <Route path="/" element={<HidatoFrontendApp />} />
          <Route path="/analysis" element={<AnalysisPage />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;