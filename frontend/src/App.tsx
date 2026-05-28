import { useState } from 'react';
import { ConfigPanel } from './components/ConfigPanel';
import { ProblemPreview } from './components/ProblemPreview';
import { generateProblems, downloadWord } from './api';
import type { Problem } from './api';
import './App.css';

function App() {
  const [problems, setProblems] = useState<Problem[]>([]);
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = async (count: number, operations: string[]) => {
    setLoading(true);
    setError(null);
    try {
      const data = await generateProblems({ count, operations });
      setProblems(data.problems);
    } catch (e) {
      setError(e instanceof Error ? e.message : '生成失败');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (count: number, operations: string[]) => {
    setDownloading(true);
    setError(null);
    try {
      await downloadWord({ count, operations });
    } catch (e) {
      setError(e instanceof Error ? e.message : '下载失败');
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>口算练习题生成器</h1>
        <p>100 以内加减法口算题，一键生成 Word 文档</p>
      </header>

      <main className="app-main">
        <ConfigPanel
          onGenerate={handleGenerate}
          onDownload={handleDownload}
          loading={loading}
          downloading={downloading}
        />

        {error && <div className="error-message">{error}</div>}

        <ProblemPreview problems={problems} />
      </main>
    </div>
  );
}

export default App;
