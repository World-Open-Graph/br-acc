import { useCallback, useEffect, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router";
import { Group, Panel, Separator } from "react-resizable-panels";

import { Spinner } from "@/components/common/Spinner";
import { EntityDetail } from "@/components/entity/EntityDetail";
import { ControlsSidebar } from "@/components/graph/ControlsSidebar";
import { GraphCanvas } from "@/components/graph/GraphCanvas";
import { useGraphData } from "@/hooks/useGraphData";
import { useGraphExplorerStore } from "@/stores/graphExplorer";

import styles from "./GraphExplorer.module.css";

export function GraphExplorer() {
  const { t } = useTranslation();
  const { entityId } = useParams<{ entityId: string }>();

  const reset = useGraphExplorerStore((s) => s.reset);
  const store = useGraphExplorerStore();
  const { depth, enabledTypes, enabledRelTypes, selectedNodeIds, sidebarCollapsed, detailPanelOpen } = store;

  const { data, loading, error } = useGraphData(entityId, depth);

  useEffect(() => {
    reset();
  }, [entityId, reset]);

  const typeCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    if (data) {
      for (const node of data.nodes) {
        counts[node.type] = (counts[node.type] ?? 0) + 1;
      }
    }
    return counts;
  }, [data]);

  const relTypeCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    if (data) {
      for (const edge of data.edges) {
        counts[edge.type] = (counts[edge.type] ?? 0) + 1;
      }
    }
    return counts;
  }, [data]);

  const selectedNodeId = useMemo(() => {
    const ids = Array.from(selectedNodeIds);
    return ids.length === 1 ? ids[0] : null;
  }, [selectedNodeIds]);

  const handleCloseDetail = useCallback(() => {
    store.selectNode(null);
  }, [store]);

  return (
    <div className={styles.explorer}>
      <Group orientation="horizontal" id="graph-explorer">
        <Panel
          defaultSize={sidebarCollapsed ? 4 : 18}
          minSize={4}
          maxSize={30}
          collapsible
        >
          <ControlsSidebar
            collapsed={sidebarCollapsed}
            onToggle={store.toggleSidebar}
            depth={depth}
            onDepthChange={store.setDepth}
            enabledTypes={enabledTypes}
            onToggleType={store.toggleType}
            enabledRelTypes={enabledRelTypes}
            onToggleRelType={store.toggleRelType}
            typeCounts={typeCounts}
            relTypeCounts={relTypeCounts}
          />
        </Panel>

        <Separator className={styles.resizeHandle} />

        <Panel minSize={30}>
          <div className={styles.canvasArea}>
            {loading && (
              <div className={styles.loadingOverlay}>
                <Spinner variant="scan" size="lg" />
              </div>
            )}
            {error && <p className={styles.status}>{error}</p>}
            {data && entityId && (
              <GraphCanvas
                data={data}
                centerId={entityId}
                enabledTypes={enabledTypes}
                enabledRelTypes={enabledRelTypes}
                hiddenNodeIds={store.hiddenNodeIds}
                selectedNodeIds={selectedNodeIds}
                hoveredNodeId={store.hoveredNodeId}
                layoutMode={store.layoutMode}
                onNodeClick={(id) => store.selectNode(id)}
                onNodeDeselect={() => store.selectNode(null)}
                onNodeHover={(id) => store.setHoveredNode(id)}
                onNodeRightClick={(x, y, nodeId) => store.setContextMenu({ x, y, nodeId })}
                onLayoutChange={store.setLayoutMode}
                onFullscreen={store.toggleFullscreen}
                sidebarCollapsed={sidebarCollapsed}
              />
            )}
            {!loading && !data && !error && (
              <p className={styles.status}>{t("graph.noData")}</p>
            )}
          </div>
        </Panel>

        {selectedNodeId && detailPanelOpen && (
          <>
            <Separator className={styles.resizeHandle} />
            <Panel defaultSize={25} minSize={15} maxSize={40}>
              <div className={styles.detailPanel}>
                <EntityDetail entityId={selectedNodeId} onClose={handleCloseDetail} />
              </div>
            </Panel>
          </>
        )}
      </Group>
    </div>
  );
}
