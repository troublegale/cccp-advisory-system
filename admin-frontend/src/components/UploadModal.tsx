import { useRef, useState } from "react";
import { uploadVersion, activateVersion, type KBVersion } from "../api";
import Modal from "./Modal";

interface Props {
  onClose: () => void;
  onResult: (msg: string, ok: boolean) => void;
}

type Stage = "form" | "processing" | "confirm";

export default function UploadModal({ onClose, onResult }: Props) {
  const [stage, setStage] = useState<Stage>("form");
  const [file, setFile] = useState<File | null>(null);
  const [comment, setComment] = useState("");
  const [uploaded, setUploaded] = useState<KBVersion | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = async () => {
    if (!file) return;
    setStage("processing");
    try {
      const ver = await uploadVersion(file, comment || undefined);
      setUploaded(ver);
      setStage("confirm");
    } catch (e) {
      onResult(
        `Ошибка загрузки: ${e instanceof Error ? e.message : String(e)}`,
        false
      );
      onClose();
    }
  };

  const handleActivate = async (yes: boolean) => {
    if (yes && uploaded) {
      try {
        await activateVersion(uploaded.version_num);
        onResult(
          `Версия ${uploaded.version_num} загружена и активирована`,
          true
        );
      } catch (e) {
        onResult(
          `Версия загружена, но ошибка активации: ${e instanceof Error ? e.message : String(e)}`,
          false
        );
      }
    } else if (uploaded) {
      onResult(
        `Версия ${uploaded.version_num} загружена (статус: ingested)`,
        true
      );
    }
    onClose();
  };

  return (
    <Modal title="Загрузка архива" onClose={onClose}>
      {stage === "form" && (
        <>
          <div className="form-group">
            <label>Описание версии (необязательно)</label>
            <input
              className="form-input"
              type="text"
              placeholder="Например: обновлены описания продуктов"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
            />
          </div>
          <div className="form-group">
            <label>ZIP-архив с .md файлами</label>
            <div
              className="file-picker"
              onClick={() => inputRef.current?.click()}
            >
              <input
                ref={inputRef}
                type="file"
                accept=".zip"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
              <div className="file-picker-label">
                Нажмите для выбора файла или перетащите сюда
              </div>
              {file && <div className="file-picker-name">{file.name}</div>}
            </div>
          </div>
          <button
            className="btn btn-primary"
            style={{ width: "100%" }}
            disabled={!file}
            onClick={handleSubmit}
          >
            Загрузить
          </button>
        </>
      )}

      {stage === "processing" && (
        <div className="processing">Запрос обрабатывается...</div>
      )}

      {stage === "confirm" && (
        <>
          <p className="confirm-text">
            Сделать загруженную версию активной?
          </p>
          <div className="confirm-actions">
            <button
              className="btn btn-primary"
              onClick={() => handleActivate(true)}
            >
              Да
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => handleActivate(false)}
            >
              Нет
            </button>
          </div>
        </>
      )}
    </Modal>
  );
}
