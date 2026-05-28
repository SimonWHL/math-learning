import { useState } from 'react';

interface ConfigPanelProps {
  onGenerate: (count: number, operations: string[]) => void;
  onDownload: (count: number, operations: string[]) => void;
  loading: boolean;
  downloading: boolean;
}

export function ConfigPanel({ onGenerate, onDownload, loading, downloading }: ConfigPanelProps) {
  const [count, setCount] = useState(20);
  const [addEnabled, setAddEnabled] = useState(true);
  const [subEnabled, setSubEnabled] = useState(true);

  const getOperations = (): string[] => {
    const ops: string[] = [];
    if (addEnabled) ops.push('add');
    if (subEnabled) ops.push('subtract');
    return ops.length > 0 ? ops : ['add'];
  };

  const hasValidOps = addEnabled || subEnabled;

  return (
    <div className="config-panel">
      <h2>配置</h2>

      <div className="config-item">
        <label>
          题目数量：<strong>{count}</strong> 题
        </label>
        <input
          type="range"
          min={10}
          max={100}
          step={5}
          value={count}
          onChange={(e) => setCount(Number(e.target.value))}
        />
        <div className="range-labels">
          <span>10</span>
          <span>50</span>
          <span>100</span>
        </div>
      </div>

      <div className="config-item">
        <label>运算类型：</label>
        <div className="checkbox-group">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={addEnabled}
              onChange={(e) => setAddEnabled(e.target.checked)}
            />
            加法 (a + b)
          </label>
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={subEnabled}
              onChange={(e) => setSubEnabled(e.target.checked)}
            />
            减法 (a - b)
          </label>
        </div>
      </div>

      <div className="config-actions">
        <button
          className="btn btn-primary"
          onClick={() => onGenerate(count, getOperations())}
          disabled={loading || !hasValidOps}
        >
          {loading ? '生成中...' : '预览题目'}
        </button>
        <button
          className="btn btn-secondary"
          onClick={() => onDownload(count, getOperations())}
          disabled={downloading || !hasValidOps}
        >
          {downloading ? '下载中...' : '下载 Word 文档'}
        </button>
      </div>
    </div>
  );
}
