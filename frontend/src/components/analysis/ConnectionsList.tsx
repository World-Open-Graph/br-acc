import { memo, useCallback, useMemo, useRef } from "react";
import { useTranslation } from "react-i18next";

import type { GraphNode } from "@/api/client";
import { entityColors } from "@/styles/tokens";

import styles from "./ConnectionsList.module.css";

interface ConnectionsListProps {
  nodes: GraphNode[];
  centerId: string;
  selectedNodeId: string | null;
  onSelectNode: (id: string) => void;
}

interface GroupedType {
  type: string;
  nodes: GraphNode[];
}

function ConnectionsListInner({
  nodes,
  centerId,
  selectedNodeId,
  onSelectNode,
}: ConnectionsListProps) {
  const { t } = useTranslation();
  const listRef = useRef<HTMLDivElement>(null);

  const getDisplayName = useCallback(
    (node: GraphNode): string => {
      const label = node.label.trim();
      if (label) return label;

      const documentId = node.document_id?.trim();
      if (documentId) return documentId;

      const shortId = node.id.split(":").at(-1) ?? node.id;
      return `${t(`entity.${node.type}`, node.type)} #${shortId}`;
    },
    [t],
  );

  const grouped = useMemo(() => {
    const groups = new Map<string, GraphNode[]>();
    for (const node of nodes) {
      if (node.id === centerId) continue;
      const list = groups.get(node.type) ?? [];
      list.push(node);
      groups.set(node.type, list);
    }
    const result: GroupedType[] = [];
    for (const [type, typeNodes] of groups) {
      result.push({ type, nodes: typeNodes });
    }
    return result.sort((a, b) => b.nodes.length - a.nodes.length);
  }, [nodes, centerId]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      const items = listRef.current?.querySelectorAll<HTMLElement>(
        "[role=option]",
      );
      if (!items?.length) return;

      const currentIndex = Array.from(items).findIndex(
        (el) => el === document.activeElement,
      );

      if (e.key === "ArrowDown") {
        e.preventDefault();
        const next = currentIndex < items.length - 1 ? currentIndex + 1 : 0;
        items[next]?.focus();
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        const prev = currentIndex > 0 ? currentIndex - 1 : items.length - 1;
        items[prev]?.focus();
      } else if (e.key === "Enter" && currentIndex >= 0) {
        e.preventDefault();
        const nodeId = items[currentIndex]?.dataset.nodeid;
        if (nodeId) onSelectNode(nodeId);
      }
    },
    [onSelectNode],
  );

  const totalConnections = nodes.filter((n) => n.id !== centerId).length;

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h2 className={styles.title}>{t("analysis.connections")}</h2>
        <span className={styles.count}>{totalConnections}</span>
      </div>

      <div
        ref={listRef}
        className={styles.list}
        role="listbox"
        aria-label={t("analysis.connections")}
        onKeyDown={handleKeyDown}
      >
        {grouped.map(({ type, nodes: typeNodes }) => {
          const color = entityColors[type] ?? "var(--text-muted)";
          return (
            <div key={type} className={styles.group}>
              <div className={styles.groupHeader}>
                <span
                  className={styles.groupDot}
                  style={{ backgroundColor: color }}
                />
                <span className={styles.groupName}>
                  {t(`entity.${type}`, type)}
                </span>
                <span className={styles.groupCount}>{typeNodes.length}</span>
              </div>
              {typeNodes.map((node) => (
                <button
                  key={node.id}
                  role="option"
                  aria-selected={node.id === selectedNodeId}
                  data-nodeid={node.id}
                  className={`${styles.item} ${node.id === selectedNodeId ? styles.selected : ""}`}
                  onClick={() => onSelectNode(node.id)}
                  tabIndex={-1}
                >
                  <span
                    className={styles.itemDot}
                    style={{ backgroundColor: color }}
                  />
                  <span className={styles.itemName}>{getDisplayName(node)}</span>
                  <span className={styles.itemSource}>
                    {node.sources[0]?.database ?? ""}
                  </span>
                </button>
              ))}
            </div>
          );
        })}

        {totalConnections === 0 && (
          <p className={styles.empty}>{t("analysis.noConnections")}</p>
        )}
      </div>
    </div>
  );
}

export const ConnectionsList = memo(ConnectionsListInner);
