import { useState } from "react";
import type { KBVersion } from "../api";
import { archiveUrl } from "../api";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function StatusBadge({ status }: { status: string }) {
  const labels: Record<string, string> = {
    active: "Активна",
    ingested: "Загружена",
    uploaded: "Загружается",
    failed: "Ошибка",
  };
  return (
    <span className={`status status-${status}`}>
      {labels[status] ?? status}
    </span>
  );
}

function FilesCell({ version }: { version: KBVersion }) {
  const [open, setOpen] = useState(false);
  return (
    <div>
      <button className="files-toggle" onClick={() => setOpen(!open)}>
        {version.file_count} {version.file_count === 1 ? "файл" : "файлов"}{" "}
        {open ? "▴" : "▾"}
      </button>
      {open && (
        <ul className="files-list">
          {version.files.map((f) => (
            <li key={f.s3_key}>
              {f.filename}
              <span className="file-size">{formatBytes(f.size_bytes)}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

const COMMENT_TRUNCATE = 40;

function CommentCell({ comment }: { comment: string | null }) {
  const [expanded, setExpanded] = useState(false);

  if (!comment) return <span>—</span>;

  const isLong = comment.length > COMMENT_TRUNCATE;

  if (!isLong) return <span>{comment}</span>;

  return (
    <div className="comment-cell">
      {expanded ? (
        <div>
          <span className="comment-text-full">{comment}</span>{" "}
          <button className="comment-toggle" onClick={() => setExpanded(false)}>
            свернуть
          </button>
        </div>
      ) : (
        <div className="comment-short">
          <span className="comment-text-truncated">{comment}</span>
          <button className="comment-toggle" onClick={() => setExpanded(true)}>
            ещё
          </button>
        </div>
      )}
    </div>
  );
}

interface Props {
  versions: KBVersion[];
  showActions?: boolean;
  onActivate?: (v: KBVersion) => void;
  onDelete?: (v: KBVersion) => void;
}

export default function VersionTable({
  versions,
  showActions,
  onActivate,
  onDelete,
}: Props) {
  if (versions.length === 0) {
    return <div className="no-data">Нет данных</div>;
  }

  return (
    <table className="version-table">
      <thead>
        <tr>
          <th>№</th>
          <th>Статус</th>
          <th>Дата</th>
          <th>Файлы</th>
          <th>Комментарий</th>
          {showActions && <th>Действия</th>}
        </tr>
      </thead>
      <tbody>
        {versions.map((v) => (
          <tr key={v.id}>
            <td>{v.version_num}</td>
            <td>
              <StatusBadge status={v.status} />
            </td>
            <td className="col-date">{formatDate(v.created_at)}</td>
            <td>
              <FilesCell version={v} />
            </td>
            <td>
              <CommentCell comment={v.comment} />
            </td>
            {showActions && (
              <td>
                <div className="actions-cell">
                  {v.status !== "active" && (
                    <>
                      <button
                        className="btn btn-outline-primary btn-sm"
                        onClick={() => onActivate?.(v)}
                        title="Сделать активной"
                      >
                        Активировать
                      </button>
                      <button
                        className="btn btn-outline-danger btn-sm"
                        onClick={() => onDelete?.(v)}
                        title="Удалить версию"
                      >
                        Удалить
                      </button>
                    </>
                  )}
                  <a
                    className="btn btn-outline-secondary btn-sm"
                    href={archiveUrl(v.version_num)}
                    download
                  >
                    Скачать
                  </a>
                </div>
              </td>
            )}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
