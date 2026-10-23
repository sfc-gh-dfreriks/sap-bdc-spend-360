import { Sparkles } from 'lucide-react';
import AskCortex from '@/components/AskCortex';

const SUGGESTIONS = [
  'Where is our biggest savings opportunity right now?',
  'Which categories have the most off-contract (maverick) spend?',
  'Which high-spend suppliers carry the most risk?',
  'How concentrated is our spend in the top 10 suppliers?',
  'How has monthly spend trended and what is driving it?',
  'How do our ESG and diverse-supplier numbers look?',
];

export default function AskCortexPage() {
  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-indigo-200 bg-gradient-to-br from-indigo-50/60 via-white to-sky-50/60 p-5 shadow-sm">
        <div className="flex items-center gap-2 text-sm font-bold text-indigo-700">
          <Sparkles className="h-4 w-4" /> Cortex spend analysis
        </div>
        <p className="mt-1 text-sm text-gray-600">
          Ask a question across spend, suppliers, contract compliance, supplier risk, ESG and savings.
          Cortex answers from live facts queried from the SAP BDC data products in Snowflake. Supplier risk,
          ESG/diversity and savings figures are representative enrichment data.
        </p>
      </div>
      <AskCortex topic="general" label="Analyse overall spend" suggestions={SUGGESTIONS} />
    </div>
  );
}
