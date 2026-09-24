"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Activity, AlertTriangle, ArrowLeft, Bell, BookOpen, Network, Plus, ShieldCheck, Siren } from "lucide-react";
import { api } from "@/lib/api";
import { CaseQueueItem, InvestigationResponse, TriggerInvestigationRequest } from "@/types/api";
import { Header } from "@/components/Header";
import { CaseQueue } from "@/components/CaseQueue";
import { InvestigationWorkspace } from "@/components/InvestigationWorkspace";
import { NewInvestigationModal } from "@/components/NewInvestigationModal";

export default function AnalystConsolePage() {
  const [cases, setCases] = useState<CaseQueueItem[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const [showMobileWorkspace, setShowMobileWorkspace] = useState(false);
  const [isLoadingCases, setIsLoadingCases] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSubmittingNew, setIsSubmittingNew] = useState(false);

  const fetchCases = useCallback(async () => {
    setIsRefreshing(true);
    try {
      const response = await api.listCases();
      setCases(response.cases || []);
      setSelectedCaseId((current) => current ?? response.cases?.[0]?.case_id ?? null);
    } catch (error) {
      console.warn("Could not load cases from backend:", error);
    } finally {
      setIsLoadingCases(false);
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchCases();
  }, [fetchCases]);

  const metrics = useMemo(() => ({
    critical: cases.filter((item) => item.risk_level === "CRITICAL").length,
    active: cases.filter((item) => ["OPEN", "IN_PROGRESS", "AWAITING_EVIDENCE"].includes(item.status)).length,
    approvals: cases.filter((item) => item.status === "AWAITING_APPROVAL").length,
    completed: cases.filter((item) => ["COMPLETED", "RESOLVED", "CLOSED"].includes(item.status)).length,
  }), [cases]);

  const handleTriggerInvestigation = async (request: TriggerInvestigationRequest) => {
    setIsSubmittingNew(true);
    try {
      const newCase = await api.triggerInvestigation(request);
      await fetchCases();
      setSelectedCaseId(newCase.case_id);
      setShowMobileWorkspace(true);
    } finally {
      setIsSubmittingNew(false);
    }
  };

  const handleCaseUpdated = (updated: InvestigationResponse) => {
    setCases((current) => current.map((item) => item.case_id === updated.case_id ? {
      ...item,
      status: updated.case_status,
      risk_level: updated.risk_level,
      confidence: updated.confidence,
      primary_action: updated.post_evidence_action?.action_type,
    } : item));
  };

  const selectCase = (caseId: string) => {
    setSelectedCaseId(caseId);
    setShowMobileWorkspace(true);
  };

  return (
    <div className="min-h-screen bg-[#070a10] text-slate-100 selection:bg-orange-500/30">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(circle_at_12%_0%,rgba(249,115,22,0.10),transparent_28%),radial-gradient(circle_at_88%_20%,rgba(14,165,233,0.07),transparent_24%)]" />

      <aside className="fixed inset-y-0 left-0 z-40 hidden w-[72px] flex-col items-center border-r border-white/[0.07] bg-[#090d15]/95 py-4 backdrop-blur-xl lg:flex">
        <div className="grid h-10 w-10 place-items-center rounded-xl bg-gradient-to-br from-orange-400 to-orange-600 text-white shadow-[0_0_28px_rgba(249,115,22,0.28)]">
          <ShieldCheck className="h-5 w-5" />
        </div>
        <nav className="mt-8 flex flex-1 flex-col items-center gap-2">
          {[
            { icon: Siren, label: "Investigations", active: true },
            { icon: Network, label: "Graph intelligence" },
            { icon: BookOpen, label: "Policy memory" },
            { icon: Bell, label: "Alerts" },
          ].map(({ icon: Icon, label, active }) => (
            <button key={label} title={label} className={`grid h-11 w-11 place-items-center rounded-xl border transition-all ${active ? "border-orange-500/30 bg-orange-500/10 text-orange-400" : "border-transparent text-slate-500 hover:border-white/10 hover:bg-white/[0.04] hover:text-slate-200"}`}>
              <Icon className="h-[18px] w-[18px]" />
            </button>
          ))}
        </nav>
        <div className="grid h-9 w-9 place-items-center rounded-full border border-emerald-500/20 bg-emerald-500/10 text-[11px] font-bold text-emerald-300">FA</div>
      </aside>

      <div className="relative flex min-h-screen flex-col lg:pl-[72px]">
        <Header onNewInvestigation={() => setIsModalOpen(true)} onRefreshCases={fetchCases} isRefreshing={isRefreshing} />

        <main className="flex min-h-0 flex-1 flex-col px-3 pb-3 pt-3 sm:px-5 sm:pb-5 lg:px-6">
          <section className="mb-3 grid grid-cols-2 gap-2 xl:grid-cols-4">
            {[
              { label: "Active cases", value: metrics.active, icon: Activity, tone: "text-sky-400" },
              { label: "Critical risk", value: metrics.critical, icon: AlertTriangle, tone: "text-red-400" },
              { label: "Awaiting approval", value: metrics.approvals, icon: ShieldCheck, tone: "text-amber-400" },
              { label: "Resolved", value: metrics.completed, icon: ShieldCheck, tone: "text-emerald-400" },
            ].map(({ label, value, icon: Icon, tone }) => (
              <div key={label} className="metric-card flex min-h-[68px] items-center justify-between px-4 py-3">
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">{label}</p>
                  <p className="mt-1 text-2xl font-semibold tracking-tight text-white">{value}</p>
                </div>
                <Icon className={`h-5 w-5 ${tone}`} />
              </div>
            ))}
          </section>

          <section className="grid min-h-0 flex-1 grid-cols-1 gap-3 lg:grid-cols-[340px_minmax(0,1fr)] xl:grid-cols-[380px_minmax(0,1fr)]">
            <div className={`${showMobileWorkspace ? "hidden lg:flex" : "flex"} min-h-[620px] flex-col lg:h-[calc(100vh-174px)]`}>
              <CaseQueue cases={cases} selectedCaseId={selectedCaseId} onSelectCase={selectCase} isLoading={isLoadingCases} />
            </div>

            <div className={`${showMobileWorkspace ? "flex" : "hidden lg:flex"} min-h-[620px] min-w-0 flex-col lg:h-[calc(100vh-174px)]`}>
              <button onClick={() => setShowMobileWorkspace(false)} className="mb-2 flex w-fit items-center gap-2 rounded-lg border border-white/10 bg-white/[0.04] px-3 py-2 text-xs font-semibold text-slate-300 lg:hidden">
                <ArrowLeft className="h-4 w-4" /> Back to queue
              </button>
              {selectedCaseId ? (
                <InvestigationWorkspace key={selectedCaseId} caseId={selectedCaseId} onCaseUpdated={handleCaseUpdated} />
              ) : (
                <div className="flex h-full flex-col items-center justify-center rounded-2xl border border-dashed border-white/10 bg-white/[0.025] p-8 text-center">
                  <div className="mb-5 grid h-16 w-16 place-items-center rounded-2xl border border-orange-500/20 bg-orange-500/10 text-orange-400"><ShieldCheck className="h-8 w-8" /></div>
                  <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-orange-400">Investigation command</p>
                  <h2 className="mt-2 text-xl font-semibold text-white">Select a case to begin analysis</h2>
                  <p className="mt-2 max-w-md text-sm leading-6 text-slate-500">Review graph evidence, policy controls, risk signals, and the complete decision timeline in one workspace.</p>
                  <button onClick={() => setIsModalOpen(true)} className="mt-6 flex items-center gap-2 rounded-xl bg-orange-500 px-4 py-2.5 text-xs font-bold text-white shadow-[0_10px_30px_rgba(249,115,22,0.22)] transition hover:bg-orange-400">
                    <Plus className="h-4 w-4" /> Launch investigation
                  </button>
                </div>
              )}
            </div>
          </section>
        </main>
      </div>

      <NewInvestigationModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} onSubmit={handleTriggerInvestigation} isSubmitting={isSubmittingNew} />
    </div>
  );
}
