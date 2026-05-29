import { useState } from 'react';
import type { GradeResultItem, GradeScore } from '../api';

interface GradeResultProps {
  results: GradeResultItem[];
  annotatedImage: string;
  score: GradeScore;
  onRecheck: (problems: { id: number; student_answer: string | null; student_remainder: string | null }[]) => void;
  rechecking: boolean;
}

export function GradeResult({ results, annotatedImage, score, onRecheck, rechecking }: GradeResultProps) {
  const [editable, setEditable] = useState<Record<number, { answer: string; remainder: string }>>({});

  const getEdited = (id: number, field: 'answer' | 'remainder', original: string | null) => {
    return editable[id]?.[field] ?? original ?? '';
  };

  const setEdited = (id: number, field: 'answer' | 'remainder', value: string) => {
    setEditable((prev) => ({
      ...prev,
      [id]: { ...prev[id], [field]: value, answer: prev[id]?.answer ?? '', remainder: prev[id]?.remainder ?? '' },
    }));
  };

  const handleRecheck = () => {
    const problems = results.map((r) => ({
      id: r.id,
      student_answer: getEdited(r.id, 'answer', r.student_answer) || null,
      student_remainder: getEdited(r.id, 'remainder', r.student_remainder) || null,
    }));
    onRecheck(problems);
  };

  if (results.length === 0) return null;

  return (
    <div className="grade-result">
      {/* Score Summary */}
      <div className={`score-banner ${score.accuracy >= 80 ? 'score-good' : score.accuracy >= 60 ? 'score-ok' : 'score-bad'}`}>
        <div className="score-number">{score.correct}/{score.total}</div>
        <div className="score-detail">
          正确 {score.correct} 题 | 错误 {score.wrong} 题 | 正确率 {score.accuracy.toFixed(0)}%
        </div>
      </div>

      {/* Annotated Image */}
      {annotatedImage && (
        <div className="annotated-section">
          <h3>标注照片</h3>
          <div className="annotated-image-wrapper">
            <img src={`data:image/jpeg;base64,${annotatedImage}`} alt="标注后的试卷" />
          </div>
        </div>
      )}

      {/* Problem List */}
      <div className="problems-section">
        <div className="problems-section-header">
          <h3>题目详情</h3>
          <button className="btn btn-secondary btn-sm" onClick={handleRecheck} disabled={rechecking}>
            {rechecking ? '重新批改中...' : '重新批改'}
          </button>
        </div>
        <div className="grade-table">
          <div className="grade-table-header">
            <span className="col-id">#</span>
            <span className="col-expr">题目</span>
            <span className="col-correct">正确答案</span>
            <span className="col-student">学生答案</span>
            <span className="col-result">结果</span>
          </div>
          {results.map((r) => (
            <div key={r.id} className={`grade-table-row ${r.is_correct ? 'row-correct' : 'row-wrong'}`}>
              <span className="col-id">{r.id}</span>
              <span className="col-expr">{r.expression.replace(' = ____', '')}</span>
              <span className="col-correct">
                {r.correct_answer}
                {r.correct_remainder !== null && <> ... {r.correct_remainder}</>}
              </span>
              <span className="col-student">
                <input
                  className="answer-input"
                  value={getEdited(r.id, 'answer', r.student_answer)}
                  onChange={(e) => setEdited(r.id, 'answer', e.target.value)}
                  placeholder="?"
                />
                {r.correct_remainder !== null && (
                  <>
                    {' ... '}
                    <input
                      className="answer-input answer-input-sm"
                      value={getEdited(r.id, 'remainder', r.student_remainder)}
                      onChange={(e) => setEdited(r.id, 'remainder', e.target.value)}
                      placeholder="?"
                    />
                  </>
                )}
              </span>
              <span className="col-result">{r.is_correct ? '✓' : '✗'}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
