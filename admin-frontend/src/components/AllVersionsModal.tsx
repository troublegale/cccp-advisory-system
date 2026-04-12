import { useCallback, useEffect, useState } from "react";
import {
  listVersions,
  activateVersion,
  deleteVersion,
  type KBVersion,
} from "../api";
import Modal from "./Modal";
import VersionTable from "./VersionTable";

interface Props {
  onClose: () => void;
  onResult: (msg: string, ok: boolean) => void;
}

type Confirm = { action: "activate" | "delete"; version: KBVersion } | null;

export default function AllVersionsModal({ onClose, onResult }: Props) {
  const [versions, setVersions] = useState<KBVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [confirm, setConfirm] = useState<Confirm>(null);

  const load = useCallback(() => {
    setLoading(true);
    listVersions()
      .then(setVersions)
      .catch((e) =>
        onResult(
          `Ошибка: ${e instanceof Error ? e.message : String(e)}`,
          false
        )
      )
      .finally(() => setLoading(false));
  }, [onResult]);

  useEffect(load, [load]);

  const handleActivate = (v: KBVersion) => {
    setConfirm({ action: "activate", version: v });
  };

  const handleDelete = (v: KBVersion) => {
    setConfirm({ action: "delete", version: v });
  };

  const executeConfirm = async () => {
    if (!confirm) return;
    const { action, version: v } = confirm;
    setConfirm(null);
    if (action === "activate") {
      try {
        await activateVersion(v.version_num);
        onResult(`Версия ${v.version_num} активирована`, true);
        load();
      } catch (e) {
        onResult(
          `Ошибка активации: ${e instanceof Error ? e.message : String(e)}`,
          false
        );
      }
    } else {
      try {
        await deleteVersion(v.version_num);
        onResult(`Версия ${v.version_num} удалена`, true);
        load();
      } catch (e) {
        onResult(
          `Ошибка удаления: ${e instanceof Error ? e.message : String(e)}`,
          false
        );
      }
    }
  };

  return (
    <Modal title="Все версии" wide onClose={onClose}>
      {confirm && (
        <div className="confirm-overlay" onClick={() => setConfirm(null)}>
          <div className="confirm-dialog" onClick={(e) => e.stopPropagation()}>
            <p className="confirm-text">
              {confirm.action === "delete"
                ? `Удалить версию ${confirm.version.version_num}?`
                : `Активировать версию ${confirm.version.version_num}?`}
            </p>
            <div className="confirm-actions">
              <button className="btn btn-primary" onClick={executeConfirm}>
                Да
              </button>
              <button
                className="btn btn-secondary"
                onClick={() => setConfirm(null)}
              >
                Отмена
              </button>
            </div>
          </div>
        </div>
      )}
      {loading ? (
        <div className="processing">Загрузка...</div>
      ) : (
        <VersionTable
          versions={versions}
          showActions
          onActivate={handleActivate}
          onDelete={handleDelete}
        />
      )}
    </Modal>
  );
}
