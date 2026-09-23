"use client";

import React, { useState, useEffect, useCallback } from "react";
import { CaseQueueItem, InvestigationResponse, TriggerInvestigationRequest } from "@/types/api";
import { api } from "@/lib/api";
import { Header } from "@/components/Header";
import { CaseQueue } from "@/components/CaseQueue";
import { InvestigationWorkspace } from "@/components/InvestigationWorkspace";
import { NewInvestigationModal } from "@/components/NewInvestigationModal";
import { ShieldCheck, PlusCircle, ArrowLeft } from "lucide-react";

export default function AnalystConsolePage() {
  const [cases, setCases] = useState<CaseQueueItem[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const [isLoadingCases, setIsLoadingCases] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [isSubmittingNew, setIsSubmittingNew] = useState<boolean>(false);

  // Fetch case queue
  const fetchCases = useCallback(async () => {
    setIsRefreshing(true);
    try {
      const res = await api.listCases();
      setCases(res.cases || []);
      // If no case is selected and cases exist, select the first one
      if (!selectedCaseId && res.cases && res.cases.length > 0) {
        setSelectedCaseId(res.cases[0].case_id);
      }
    } catch (err) {
      console.warn("Could not load cases from backend:", err);
    } finally {
      setIsLoadingCases(false);
      setIsRefreshing(false);
    }
  }, [selectedCaseId]);

  useEffect(() => {
    fetchCases();
  }, [fetchCases]);

  // Handle new investigation trigger
  const handleTriggerInvestigation = async (req: TriggerInvestigationRequest) => {
    setIsSubmittingNew(true);
    try {
      const newCase = await api.triggerInvestigation(req);
      await fetchCases();
      setSelectedCaseId(newCase.case_id);
    } finally {
      setIsSubmittingNew(false);
    }
  };

  // Case update callback (from approval or evidence addition)
  const handleCaseUpdated = (updated: InvestigationResponse) => {
    // Update local case in queue
    setCases((prev) =>
      prev.map((c) =>
        c.case_id === updated.case_id
          ? {
              ...c,
              status: updated.case_status,
              risk_level: updated.risk_level,
              confidence: updated.confidence,
              primary_action: updated.post_evidence_action?.action_type,
            }
          : c
      )
    );
  };

  return (
    <div className="min-h-screen flex flex-col bg-brand-950 text-slate-100 font-sans selection:bg-orange-500/30 selection:text-orange-200">
      {/* Top Application Header */}
      <Header
        onNewInvestigation={() => setIsModalOpen(true)}
        onRefreshCases={fetchCases}
        isRefreshing={isRefreshing}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8 flex flex-col gap-6">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-[calc(100vh-8.5rem)] min-h-[640px]">
          {/* Left Column: Triage Queue (4 cols on lg) */}
          <div className="lg:col-span-4 h-full flex flex-col">
            <CaseQueue
              cases={cases}
              selectedCaseId={selectedCaseId}
              onSelectCase={(id) => setSelectedCaseId(id)}
              isLoading={isLoadingCases}
            />
          </div>

          {/* Right Column: Case Intelligence Workspace (8 cols on lg) */}
          <div className="lg:col-span-8 h-full flex flex-col">
            {selectedCaseId ? (
              <InvestigationWorkspace
                key={selectedCaseId}
                caseId={selectedCaseId}
                onCaseUpdated={handleCaseUpdated}
              />
            ) : (
              <div className="h-full flex flex-col items-center justify-center p-8 bg-brand-900/40 border border-brand-700/60 rounded-xl glass-panel text-center">
                <div className="w-16 h-16 rounded-2xl bg-orange-500/10 border border-orange-500/20 flex items-center justify-center mb-4 text-orange-400">
                  <ShieldCheck className="w-8 h-8" />
                </div>
                <h3 className="text-base font-bold text-white mb-1">
                  TigerGraph Fraud Intelligence Analyst Console
                </h3>
                <p className="text-xs text-slate-400 max-w-sm mb-6">
                  Select an active case from the triage queue on the left, or launch an autonomous investigation across the transaction graph.
                </p>
                <button
                  onClick={() => setIsModalOpen(true)}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg bg-orange-500 hover:bg-orange-600 text-white font-semibold text-xs shadow-glow-high transition-all"
                >
                  <PlusCircle className="w-4 h-4" />
                  <span>Launch New Investigation</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Trigger Modal */}
      <NewInvestigationModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSubmit={handleTriggerInvestigation}
        isSubmitting={isSubmittingNew}
      />
    </div>
  );
}
