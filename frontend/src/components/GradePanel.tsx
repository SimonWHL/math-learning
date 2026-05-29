import { useState, useRef } from 'react';

interface GradePanelProps {
  onGrade: (params: {
    image: File;
    count: number;
    operations: string[];
    seed: number | null;
    ocrMode: string;
    apiKey?: string;
  }) => void;
  loading: boolean;
}

export function GradePanel({ onGrade, loading }: GradePanelProps) {
  const [image, setImage] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [count, setCount] = useState(20);
  const [seed, setSeed] = useState('');
  const [addEnabled, setAddEnabled] = useState(true);
  const [subEnabled, setSubEnabled] = useState(true);
  const [divEnabled, setDivEnabled] = useState(false);
  const [ocrMode, setOcrMode] = useState('local');
  const [apiKey, setApiKey] = useState('');
  const fileRef = useRef<HTMLInputElement>(null);

  const handleFile = (file: File) => {
    setImage(file);
    const url = URL.createObjectURL(file);
    setPreview(url);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('image/')) handleFile(file);
  };

  const getOperations = (): string[] => {
    const ops: string[] = [];
    if (addEnabled) ops.push('add');
    if (subEnabled) ops.push('subtract');
    if (divEnabled) ops.push('divide_remainder');
    return ops.length > 0 ? ops : ['add'];
  };

  const handleSubmit = () => {
    if (!image) return;
    onGrade({
      image,
      count,
      operations: getOperations(),
      seed: seed ? parseInt(seed) : null,
      ocrMode,
      apiKey: ocrMode === 'cloud' ? apiKey : undefined,
    });
  };

  return (
    <div className="config-panel">
      <h2>批改试卷</h2>

      {/* Image Upload */}
      <div className="config-item">
        <label>上传学生答题照片：</label>
        <div
          className="upload-area"
          onClick={() => fileRef.current?.click()}
          onDrop={handleDrop}
          onDragOver={(e) => e.preventDefault()}
        >
          {preview ? (
            <img src={preview} alt="preview" className="upload-preview" />
          ) : (
            <div className="upload-placeholder">
              <span>点击或拖拽图片到此处上传</span>
            </div>
          )}
        </div>
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          hidden
          onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
        />
      </div>

      {/* Count */}
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
      </div>

      {/* Seed */}
      <div className="config-item">
        <label>随机种子 (与生成时一致)：</label>
        <input
          type="number"
          className="seed-input"
          value={seed}
          onChange={(e) => setSeed(e.target.value)}
          placeholder="输入生成时使用的 seed"
        />
      </div>

      {/* Operations */}
      <div className="config-item">
        <label>运算类型：</label>
        <div className="checkbox-group">
          <label className="checkbox-label">
            <input type="checkbox" checked={addEnabled} onChange={(e) => setAddEnabled(e.target.checked)} />
            加法
          </label>
          <label className="checkbox-label">
            <input type="checkbox" checked={subEnabled} onChange={(e) => setSubEnabled(e.target.checked)} />
            减法
          </label>
          <label className="checkbox-label">
            <input type="checkbox" checked={divEnabled} onChange={(e) => setDivEnabled(e.target.checked)} />
            有余数除法
          </label>
        </div>
      </div>

      {/* OCR Mode */}
      <div className="config-item">
        <label>识别模式：</label>
        <div className="radio-group">
          <label className="radio-label">
            <input type="radio" name="ocr" value="local" checked={ocrMode === 'local'} onChange={() => setOcrMode('local')} />
            本地 OCR (PaddleOCR)
          </label>
          <label className="radio-label">
            <input type="radio" name="ocr" value="cloud" checked={ocrMode === 'cloud'} onChange={() => setOcrMode('cloud')} />
            云端 AI 视觉模型
          </label>
        </div>
        {ocrMode === 'cloud' && (
          <div className="cloud-config">
            <input
              type="password"
              className="seed-input"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="API Key"
            />
          </div>
        )}
      </div>

      <div className="config-actions">
        <button
          className="btn btn-primary"
          onClick={handleSubmit}
          disabled={loading || !image}
        >
          {loading ? '批改中...' : '开始批改'}
        </button>
      </div>
    </div>
  );
}
