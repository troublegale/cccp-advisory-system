const BASE = "/api/v1/knowledge-base";

export interface KBFile {
  filename: string;
  s3_key: string;
  size_bytes: number;
  sha256: string;
}

export interface KBVersion {
  id: string;
  version_num: number;
  created_at: string;
  status: string;
  s3_prefix: string;
  qdrant_collection: string | null;
  file_count: number;
  comment: string | null;
  files: KBFile[];
}

export async function uploadVersion(
  file: File,
  comment?: string
): Promise<KBVersion> {
  const form = new FormData();
  form.append("archive", file);
  if (comment) form.append("comment", comment);
  const res = await fetch(`${BASE}/versions`, { method: "POST", body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => null);
    throw new Error(err?.detail ?? `Ошибка загрузки: ${res.status}`);
  }
  return res.json();
}

export async function listVersions(): Promise<KBVersion[]> {
  const res = await fetch(`${BASE}/versions`);
  if (!res.ok) throw new Error(`Ошибка получения версий: ${res.status}`);
  return res.json();
}

export async function getActiveVersion(): Promise<KBVersion | null> {
  const res = await fetch(`${BASE}/versions/active`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Ошибка: ${res.status}`);
  return res.json();
}

export async function activateVersion(versionNum: number): Promise<KBVersion> {
  const res = await fetch(`${BASE}/versions/${versionNum}/activate`, {
    method: "POST",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => null);
    throw new Error(err?.detail ?? `Ошибка активации: ${res.status}`);
  }
  return res.json();
}

export async function deleteVersion(versionNum: number): Promise<void> {
  const res = await fetch(`${BASE}/versions/${versionNum}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => null);
    throw new Error(err?.detail ?? `Ошибка удаления: ${res.status}`);
  }
}

export function archiveUrl(versionNum: number): string {
  return `${BASE}/versions/${versionNum}/archive`;
}

export function activeArchiveUrl(): string {
  return `${BASE}/versions/active/archive`;
}
