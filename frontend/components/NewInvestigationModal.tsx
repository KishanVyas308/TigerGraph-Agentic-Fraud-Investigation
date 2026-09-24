"use client";

import React, { useState } from "react";
import {
  TriggerInvestigationRequest,
  TriggerType,
} from "@/types/api";
import { X, Play, Zap, AlertCircle } from "lucide-react";

interface NewInvestigationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (request: TriggerInvestigationRequest) => Promise<void>;
  isSubmitting: boolean;
}

const PRESETS = [
  {
    title: "Velocity Burst Alert",
    trigger: "TRANSACTION_ALERT" as TriggerType,
    txId: "TXN_BURST_001",
    custId: "CUST_9912",
    accounts: "ACC_5501, ACC_5502",
    desc: "Rapid transaction burst exceeding standard velocity thresholds",
  },
  {
    title: "Device Anomaly & Sharing",
    trigger: "GRAPH_ANOMALY" as TriggerType,
    txId: "TXN_DEV_4401",
    custId: "CUST_3301",
    accounts: "ACC_8812",
    desc: "New device login matching prior known fraud cluster",
  },
  {
    title: "High Risk Offshore Transfer",
    trigger: "HIGH_RISK_RULE" as TriggerType,
    txId: "TXN_MERCH_771",
    custId: "CUST_1105",
    accounts: "ACC_9921",
    desc: "Out-of-pattern cross-border wire to flagged high-risk beneficiary",
  },
];

export const NewInvestigationModal: React.FC<NewInvestigationModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  isSubmitting,
}) => {
  const [triggerType, setTriggerType] = useState<TriggerType>("TRANSACTION_ALERT");
  const [transactionId, setTransactionId] = useState<string>("TXN_ALERT_100");
  const [customerId, setCustomerId] = useState<string>("CUST_5001");
  const [accountIds, setAccountIds] = useState<string>("ACC_1001");
  const [caseId, setCaseId] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleApplyPreset = (p: typeof PRESETS[0]) => {
    setTriggerType(p.trigger);
    setTransactionId(p.txId);
    setCustomerId(p.custId);
    setAccountIds(p.accounts);
    setCaseId(`CASE_${Date.now().toString().slice(-6)}`);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const accounts = accountIds
      .split(",")
      .map((a) => a.trim())
      .filter((a) => a.length > 0);

    const req: TriggerInvestigationRequest = {
      trigger_type: triggerType,
      transaction_id: transactionId.trim() || undefined,
      customer_id: customerId.trim() || undefined,
      account_ids: accounts.length > 0 ? accounts : undefined,
      case_id: caseId.trim() || undefined,
    };

    try {
      await onSubmit(req);
      onClose();
    } catch (err: any) {
      setError(err?.message || "Failed to trigger investigation");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-lg bg-brand-900 border border-brand-700 rounded-2xl shadow-2xl overflow-hidden glass-panel">
        {/* Modal Header */}
        <div className="p-4 px-6 border-b border-brand-700/80 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Zap className="w-5 h-5 text-orange-400" />
            <h2 className="text-base font-bold text-white tracking-wide">
              Trigger New Fraud Investigation
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-brand-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-5 max-h-[80vh] overflow-y-auto">
          {/* Preset Buttons */}
          <div>
            <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-2">
              Investigation Presets
            </label>
            <div className="grid grid-cols-1 gap-2">
              {PRESETS.map((p, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => handleApplyPreset(p)}
                  className="flex flex-col items-start p-2.5 rounded-lg border border-brand-700/60 bg-brand-950/60 hover:bg-brand-800/60 hover:border-orange-500/40 text-left transition-all group"
                >
                  <div className="flex items-center justify-between w-full">
                    <span className="text-xs font-bold text-slate-200 group-hover:text-orange-400">
                      {p.title}
                    </span>
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-brand-800 text-slate-400">
                      {p.trigger}
                    </span>
                  </div>
                  <span className="text-[11px] text-slate-400 mt-1">{p.desc}</span>
                </button>
              ))}
            </div>
          </div>

          {error && (
            <div className="p-3 rounded-lg bg-red-950/80 border border-red-500/50 flex items-center gap-2 text-xs text-red-200">
              <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Trigger Category
              </label>
              <select
                value={triggerType}
                onChange={(e) => setTriggerType(e.target.value as TriggerType)}
                className="w-full px-3 py-2 bg-brand-950 border border-brand-700 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-orange-500/60 font-mono"
              >
                <option value="TRANSACTION_ALERT">TRANSACTION_ALERT</option>
                <option value="HIGH_RISK_RULE">HIGH_RISK_RULE</option>
                <option value="CUSTOMER_REPORT">CUSTOMER_REPORT</option>
                <option value="ANALYST_REFERRAL">ANALYST_REFERRAL</option>
                <option value="GRAPH_ANOMALY">GRAPH_ANOMALY</option>
              </select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Transaction ID
                </label>
                <input
                  type="text"
                  value={transactionId}
                  onChange={(e) => setTransactionId(e.target.value)}
                  placeholder="e.g. TXN_1092"
                  className="w-full px-3 py-2 bg-brand-950 border border-brand-700 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-orange-500/60 font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Customer ID
                </label>
                <input
                  type="text"
                  value={customerId}
                  onChange={(e) => setCustomerId(e.target.value)}
                  placeholder="e.g. CUST_882"
                  className="w-full px-3 py-2 bg-brand-950 border border-brand-700 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-orange-500/60 font-mono"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Associated Account IDs (comma-separated)
              </label>
              <input
                type="text"
                value={accountIds}
                onChange={(e) => setAccountIds(e.target.value)}
                placeholder="e.g. ACC_1001, ACC_1002"
                className="w-full px-3 py-2 bg-brand-950 border border-brand-700 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-orange-500/60 font-mono"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Custom Case ID (Optional)
              </label>
              <input
                type="text"
                value={caseId}
                onChange={(e) => setCaseId(e.target.value)}
                placeholder="Leave blank for auto-generated UUID"
                className="w-full px-3 py-2 bg-brand-950 border border-brand-700 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-orange-500/60 font-mono"
              />
            </div>

            {/* Modal Actions */}
            <div className="pt-3 border-t border-brand-700/60 flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={onClose}
                disabled={isSubmitting}
                className="px-4 py-2 rounded-lg bg-brand-800 hover:bg-brand-700 text-xs font-semibold text-slate-300 transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className="flex items-center gap-2 px-5 py-2 rounded-lg bg-gradient-to-r from-orange-500 to-amber-600 hover:from-orange-600 hover:to-amber-700 text-xs font-bold text-white shadow-glow-high transition-all disabled:opacity-50"
              >
                {isSubmitting ? (
                  <>
                    <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    <span>Investigating...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-3.5 h-3.5" />
                    <span>Run Investigation</span>
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};
