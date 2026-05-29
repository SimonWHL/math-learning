const API_BASE = '/api';

export interface Problem {
  id: number;
  expression: string;
  answer: number;
  remainder: number | null;
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

// --- Grading API ---

export interface GradeResultItem {
  id: number;
  expression: string;
  correct_answer: number;
  correct_remainder: number | null;
  student_answer: string | null;
  student_remainder: string | null;
  is_correct: boolean;
}

export interface GradeScore {
  total: number;
  correct: number;
  wrong: number;
  accuracy: number;
}

export interface GradeResponse {
  problems: GradeResultItem[];
  annotated_image: string;
  score: GradeScore;
  ocr_mode_used: string;
}

export async function gradeImage(params: {
  image: File;
  count: number;
  operations: string[];
  seed: number | null;
  ocrMode: string;
  apiKey?: string;
  baseUrl?: string;
  model?: string;
}): Promise<GradeResponse> {
  const formData = new FormData();
  formData.append('image', params.image);
  formData.append('count', String(params.count));
  formData.append('operations', JSON.stringify(params.operations));
  if (params.seed !== null) formData.append('seed', String(params.seed));
  formData.append('ocr_mode', params.ocrMode);
  if (params.apiKey) formData.append('api_key', params.apiKey);
  if (params.baseUrl) formData.append('base_url', params.baseUrl);
  if (params.model) formData.append('model', params.model);

  const resp = await fetch(`${API_BASE}/grade`, {
    method: 'POST',
    body: formData,
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new Error(`批改失败: ${err.detail || resp.statusText}`);
  }
  return resp.json();
}

export async function recheckGrade(params: {
  problems: { id: number; student_answer: string | null; student_remainder: string | null }[];
  count: number;
  operations: string[];
  seed: number | null;
}): Promise<GradeResponse> {
  const resp = await fetch(`${API_BASE}/grade/recheck`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!resp.ok) {
    throw new Error(`重新批改失败: ${resp.statusText}`);
  }
  return resp.json();
}
