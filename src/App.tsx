import { BrowserRouter as Router, Routes, Route, Link } from "react-router-dom";
import HidatoFrontendApp from "./Hidato";
import AnalysisPage from "./AnalysisPage";

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-black text-white">
        {/* Top Navigation */}
        <div className="flex gap-4 p-4 border-b border-gray-700 bg-[#111]">
          <Link
            to="/"
            className="px-4 py-2 rounded bg-amber-500 text-black font-semibold"
          >
            Game
          </Link>

          <Link
            to="/analysis"
            className="px-4 py-2 rounded bg-blue-500 text-white font-semibold"
          >
            Analysis
          </Link>
        </div>

        {/* Routes */}
        <Routes>
          <Route path="/" element={<HidatoFrontendApp />} />
          <Route path="/analysis" element={<AnalysisPage />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;