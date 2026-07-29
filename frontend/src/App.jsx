import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import { useEffect } from "react";
import Navbar from "./components/Navbar";
import Footer from "./components/Footer";
import Home from "./pages/Home";
import Problem from "./pages/Problem";
import Solution from "./pages/Solution";
import Dashboard from "./pages/Dashboard";
import About from "./pages/About";

function ScrollToTop() {
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);
  return null;
}

function Layout({ children }) {
  return (
    <div className="min-h-screen flex flex-col bg-abyss">
      <Navbar />
      <main className="flex-1">{children}</main>
      <Footer />
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <ScrollToTop />
      <Layout>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/problem" element={<Problem />} />
          <Route path="/solution" element={<Solution />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/about" element={<About />} />
          <Route
            path="*"
            element={
              <div className="min-h-[60vh] flex flex-col items-center justify-center text-center px-5">
                <h1 className="font-display text-4xl font-semibold text-frost mb-3">404</h1>
                <p className="text-mist">This page doesn't exist in the digital twin.</p>
              </div>
            }
          />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
