import { useState } from 'react';
import { ConfigPanel } from './components/ConfigPanel';
import { ProblemPreview } from './components/ProblemPreview';
import { GradePanel } from './components/GradePanel';
import { GradeResult } from './components/GradeResult';
import { generateProblems, downloadWord, gradeImage, recheckGrade } from './api';
import type { Problem, GradeResultItem, GradeScore } from './api';
import './App.css';

type Tab = 'generate' | 'grade';

function App() {
  const [tab, setTab] = useState<Tab>('generate');

  // Generate state
  const [problems, setProblems] = useState<Problem[]>([]);
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState(false);

  // Grade state
  const [gradeResults, setGradeResults] = useState<GradeResultItem[]>([]);
  const [annotatedImage, setAnnotatedImage] = useState('');
  const [score, setScore] = useState<GradeScore | null>(null);
  const [gradeLoading, setGradeLoading] = useState(false);
  const [recheckLoading, setRecheckLoading] = useState(false);

  // Shared state
  const [error, setError] = useState<string | null>(null);
  const [gradeParams, setGradeParams] = useState<{ count: number; operations: string[]; seed: number | null } | null>(null);

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

  const handleGrade = async (params: {
    image: File;
    count: number;
    operations: string[];
    seed: number | null;
    ocrMode: string;
    apiKey?: string;
  }) => {
    setGradeLoading(true);
    setError(null);
    try {
      const data = await gradeImage(params);
      setGradeResults(data.problems);
      setAnnotatedImage(data.annotated_image);
      setScore(data.score);
      setGradeParams({ count: params.count, operations: params.operations, seed: params.seed });
    } catch (e) {
      setError(e instanceof Error ? e.message : '批改失败');
    } finally {
      setGradeLoading(false);
    }
  };

  const handleRecheck = async (editedProblems: { id: number; student_answer: string | null; student_remainder: string | null }[]) => {
    if (!gradeParams) return;
    setRecheckLoading(true);
    setError(null);
    try {
      const data = await recheckGrade({
        problems: editedProblems,
        count: gradeParams.count,
        operations: gradeParams.operations,
        seed: gradeParams.seed,
      });
      setGradeResults(data.problems);
      setScore(data.score);
    } catch (e) {
      setError(e instanceof Error ? e.message : '重新批改失败');
    } finally {
      setRecheckLoading(false);
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>口算练习题生成器</h1>
        <p>生成口算题 / 拍照批改试卷</p>
      </header>

      <nav className="tab-nav">
        <button className={`tab-btn ${tab === 'generate' ? 'tab-active' : ''}`} onClick={() => setTab('generate')}>
          生成题目
        </button>
        <button className={`tab-btn ${tab === 'grade' ? 'tab-active' : ''}`} onClick={() => setTab('grade')}>
          批改试卷
        </button>
      </nav>

      <main className="app-main">
        {error && <div className="error-message">{error}</div>}

        {tab === 'generate' ? (
          <>
            <ConfigPanel
              onGenerate={handleGenerate}
              onDownload={handleDownload}
              loading={loading}
              downloading={downloading}
            />
            <ProblemPreview problems={problems} />
          </>
        ) : (
          <>
            <GradePanel onGrade={handleGrade} loading={gradeLoading} />
            <GradeResult
              results={gradeResults}
              annotatedImage={annotatedImage}
              score={score ?? { total: 0, correct: 0, wrong: 0, accuracy: 0 }}
              onRecheck={handleRecheck}
              rechecking={recheckLoading}
            />
          </>
        )}
      </main>
    </div>
  );
}

export default App;
