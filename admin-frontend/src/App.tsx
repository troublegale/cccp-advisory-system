import { useCallback, useState } from "react";
import UploadModal from "./components/UploadModal";
import ActiveVersionModal from "./components/ActiveVersionModal";
import AllVersionsModal from "./components/AllVersionsModal";

type ModalType = "upload" | "active" | "all" | null;
interface Result {
  message: string;
  ok: boolean;
}

const actions = [
  {
    key: "upload" as const,
    label: "Загрузить архив",
    description:
      "Загрузить ZIP-архив с .md файлами как новую версию базы знаний. После загрузки файлы будут автоматически проиндексированы.",
  },
  {
    key: "active" as const,
    label: "Активная версия",
    description:
      "Просмотр информации о текущей активной версии базы знаний, включая список файлов и возможность скачать архив.",
  },
  {
    key: "all" as const,
    label: "Все версии",
    description:
      "Список всех загруженных версий. Здесь можно активировать, удалить или скачать любую версию.",
  },
];

export default function App() {
  const [modal, setModal] = useState<ModalType>(null);
  const [result, setResult] = useState<Result | null>(null);

  const handleResult = useCallback((message: string, ok: boolean) => {
    setResult({ message, ok });
  }, []);

  return (
    <div
      style={{
        maxWidth: 620,
        margin: "0 auto",
        padding: "40px 20px",
      }}
    >
      {/* Header */}
      <header
        style={{
          textAlign: "center",
          marginBottom: 36,
          paddingBottom: 28,
          borderBottom: "2px solid var(--border)",
        }}
      >
        <h1
          style={{
            fontSize: "1.6rem",
            fontWeight: 700,
            color: "var(--warm-800)",
            marginBottom: 6,
          }}
        >
          Администрирование базы знаний
        </h1>
        <p
          style={{
            fontSize: "0.95rem",
            color: "var(--text-secondary)",
            fontWeight: 500,
          }}
        >
          ДЮКЦ ИТМО
        </p>
      </header>

      {/* Action buttons */}
      <section
        style={{
          background: "#fff",
          borderRadius: "var(--radius)",
          padding: 24,
          boxShadow: "0 2px 12px var(--shadow)",
          marginBottom: 20,
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {actions.map((a) => (
            <div
              key={a.key}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 16,
              }}
            >
              <button
                className="btn btn-primary"
                style={{ minWidth: 180, flexShrink: 0 }}
                onClick={() => setModal(a.key)}
              >
                {a.label}
              </button>
              <span
                style={{
                  fontSize: "0.85rem",
                  color: "var(--text-secondary)",
                  lineHeight: 1.4,
                }}
              >
                {a.description}
              </span>
            </div>
          ))}
        </div>
      </section>

      {/* Result area */}
      {result && (
        <div className={`result-bar ${result.ok ? "success" : "error"}`}>
          <span className="result-text">{result.message}</span>
          <button className="result-close" onClick={() => setResult(null)}>
            &times;
          </button>
        </div>
      )}

      {/* Modals */}
      {modal === "upload" && (
        <UploadModal
          onClose={() => setModal(null)}
          onResult={handleResult}
        />
      )}
      {modal === "active" && (
        <ActiveVersionModal
          onClose={() => setModal(null)}
          onResult={handleResult}
        />
      )}
      {modal === "all" && (
        <AllVersionsModal
          onClose={() => setModal(null)}
          onResult={handleResult}
        />
      )}
    </div>
  );
}
