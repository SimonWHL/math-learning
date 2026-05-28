import type { Problem } from '../api';

interface ProblemPreviewProps {
  problems: Problem[];
}

export function ProblemPreview({ problems }: ProblemPreviewProps) {
  if (problems.length === 0) {
    return (
      <div className="preview-empty">
        <p>点击「预览题目」按钮生成口算题</p>
      </div>
    );
  }

  return (
    <div className="preview-container">
      <div className="preview-header">
        <h2>口算练习题</h2>
        <p className="preview-info">
          姓名：__________&nbsp;&nbsp;&nbsp;&nbsp;班级：__________&nbsp;&nbsp;&nbsp;&nbsp;日期：__________
        </p>
      </div>
      <div className="problems-grid">
        {problems.map((p) => (
          <div key={p.id} className="problem-cell">
            <span className="problem-id">{p.id}.</span>
            <span className="problem-expr">{p.expression}</span>
          </div>
        ))}
      </div>
      <div className="preview-footer">
        共 {problems.length} 题
      </div>
    </div>
  );
}
