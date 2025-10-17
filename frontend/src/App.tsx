import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import UploadPage from './pages/UploadPage';
import MatchingPage from './pages/MatchingPage';

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-background">
        <Routes>
          <Route path="/" element={<Navigate to="/upload" replace />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/matching" element={<MatchingPage />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App;
