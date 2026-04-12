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

export default function AllVersionsModal({ onClose, onResult }: Props) {
  const [versions, setVersions] = useState<KBVersion[]>([]);
  const [loading, setLoading] = useState(true);

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

  const handleActivate = async (v: KBVersion) => {
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
  };

  const handleDelete = async (v: KBVersion) => {
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
  };

  return (
    <Modal title="Все версии" onClose={onClose}>
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
