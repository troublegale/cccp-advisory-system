import { useEffect, useState } from "react";
import { getActiveVersion, activeArchiveUrl, type KBVersion } from "../api";
import Modal from "./Modal";
import VersionTable from "./VersionTable";

interface Props {
  onClose: () => void;
  onResult: (msg: string, ok: boolean) => void;
}

export default function ActiveVersionModal({ onClose, onResult }: Props) {
  const [version, setVersion] = useState<KBVersion | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getActiveVersion()
      .then(setVersion)
      .catch((e) =>
        onResult(
          `Ошибка: ${e instanceof Error ? e.message : String(e)}`,
          false
        )
      )
      .finally(() => setLoading(false));
  }, [onResult]);

  return (
    <Modal title="Активная версия" onClose={onClose}>
      {loading ? (
        <div className="processing">Загрузка...</div>
      ) : version ? (
        <>
          <VersionTable versions={[version]} />
          <div style={{ marginTop: 16, textAlign: "center" }}>
            <a
              className="btn btn-secondary"
              href={activeArchiveUrl()}
              download
            >
              Скачать архив версии
            </a>
          </div>
        </>
      ) : (
        <div className="no-data">Нет активной версии</div>
      )}
    </Modal>
  );
}
