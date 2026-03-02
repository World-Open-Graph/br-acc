import { useEffect } from "react";
import { useParams } from "react-router";

import { AnnotationEditor } from "@/components/investigation/AnnotationEditor";
import { InvestigationDetail } from "@/components/investigation/InvestigationDetail";
import { InvestigationPanel } from "@/components/investigation/InvestigationPanel";
import { TagManager } from "@/components/investigation/TagManager";
import { Timeline } from "@/components/investigation/Timeline";
import { useInvestigationStore } from "@/stores/investigation";
import { addJourneyEntry } from "@/lib/journey";

import styles from "./Investigations.module.css";

export function Investigations() {
  const { investigationId } = useParams<{ investigationId: string }>();
  const { setActiveInvestigation, activeInvestigationId } = useInvestigationStore();

  // Sync URL param to store
  useEffect(() => {
    if (investigationId && investigationId !== activeInvestigationId) {
      setActiveInvestigation(investigationId);
      if (investigationId) addJourneyEntry({ type: "investigation", title: "Investigacao " + investigationId.slice(0, 20), url: window.location.pathname });
    }
  }, [investigationId, activeInvestigationId, setActiveInvestigation]);

  return (
    <div className={styles.page}>
      <InvestigationPanel />
      <div className={styles.content}>
        <InvestigationDetail />
        {activeInvestigationId && (
          <>
            <AnnotationEditor />
            <TagManager />
            <Timeline />
          </>
        )}
      </div>
    </div>
  );
}
