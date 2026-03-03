import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { type EntityDetail as EntityDetailData, getEntity, getEntityByElementId } from "@/api/client";
import { SourceBadge } from "@/components/common/SourceBadge";
import { type EntityType, entityColors } from "@/styles/tokens";

import styles from "./EntityDetail.module.css";

interface EntityDetailProps {
  entityId: string | null;
  onClose: () => void;
}

export function EntityDetail({ entityId, onClose }: EntityDetailProps) {
  const { t } = useTranslation();
  const [entity, setEntity] = useState<EntityDetailData | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!entityId) {
      setEntity(null);
      return;
    }
    setLoading(true);
    const isCpfOrCnpj = /^\d{11}$/.test(entityId) || /^\d{14}$/.test(entityId);
    const fetcher = isCpfOrCnpj ? getEntity(entityId) : getEntityByElementId(entityId);
    fetcher
      .then(setEntity)
      .catch(() => setEntity(null))
      .finally(() => setLoading(false));
  }, [entityId]);

  if (!entityId) return null;

  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <span className={styles.title}>{t("entity.detail")}</span>
        <button onClick={onClose} className={styles.close}>
          &times;
        </button>
      </div>

      {loading && <p className={styles.loading}>{t("common.loading")}</p>}

      {entity && (
        <div className={styles.content}>
          <div
            className={styles.typeTag}
            style={{ color: entityColors[entity.type as EntityType] ?? "#555" }}
          >
            {t(`entity.${entity.type}`, entity.type)}
          </div>
          <h3 className={styles.name}>
            {String(entity.properties.name ?? entity.properties.razao_social ?? entity.properties.nome ?? "N/A")}
          </h3>

          {entity.properties.cnpj && (
            <p className={styles.document}>
              {String(entity.properties.cnpj)}
            </p>
          )}

          <div className={styles.properties}>
            {Object.entries(entity.properties).filter(
              ([key]) => !["name", "razao_social", "nome", "cpf", "cnpj", "cpf_cnpj"].includes(key),
            ).map(([key, value]) => (
              <div key={key} className={styles.property}>
                <span className={styles.propKey}>{key}</span>
                <span className={styles.propValue}>{String(value ?? "-")}</span>
              </div>
            ))}
          </div>

          {(entity.sources ?? []).length > 0 && (
            <div className={styles.sources}>
              <span className={styles.sourcesLabel}>{t("common.source")}:</span>
              {(entity.sources ?? []).map((s) => (
                <SourceBadge key={s.database} source={s.database} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
