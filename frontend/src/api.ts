const API_BASE = '/api';

export interface Problem {
  id: number;
  expression: string;
  answer: number;
}

export interface GenerateRequest {
  count: number;
  operations: string[];
  seed?: number | null;
}

export interface GenerateResponse {
  problems: Problem[];
  count: number;
}

export async function generateProblems(req: GenerateRequest): Promise<GenerateResponse> {
  const resp = await fetch(`${API_BASE}/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!resp.ok) {
    throw new Error(`生成失败: ${resp.statusText}`);
  }
  return resp.json();
}

export async function downloadWord(req: GenerateRequest): Promise<void> {
  const resp = await fetch(`${API_BASE}/download`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!resp.ok) {
    throw new Error(`下载失败: ${resp.statusText}`);
  }
  const blob = await resp.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `口算练习_${req.count}题.docx`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
