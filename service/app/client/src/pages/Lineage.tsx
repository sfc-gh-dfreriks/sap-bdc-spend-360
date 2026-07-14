import { useQuery } from '@/hooks/useQuery';
import { fetchLineage } from '@/lib/api';
import { formatNumber } from '@/lib/utils';
import ChartCard from '@/components/ChartCard';
import DataTable from '@/components/DataTable';
import { ChevronRight } from 'lucide-react';

const TONE: Record<string, string> = {
  sap: 'border-slate-300 bg-slate-50 text-slate-800',
  bronze: 'border-amber-300 bg-amber-50 text-amber-900',
  silver: 'border-sky-300 bg-sky-50 text-sky-900',
  gold: 'border-emerald-300 bg-emerald-50 text-emerald-900',
  ai: 'border-purple-300 bg-purple-50 text-purple-900',
};

export default function Lineage() {
  const { data, loading, error } = useQuery(() => fetchLineage(), []);
  if (loading) return <div className="h-64 animate-pulse rounded-xl bg-gray-200" />;
  if (error) return <div className="rounded-lg border border-red-300 bg-red-50 p-4 text-sm text-red-800">Error: {error}</div>;
  if (!data) return null;
  const layers = data.layers ?? [];
  const products = data.products ?? [];

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-sf-primary/30 bg-gradient-to-br from-sky-50 to-cyan-50 p-5">
        <p className="text-xs font-semibold uppercase tracking-wider text-sf-dark/70">Source Systems</p>
        <p className="mt-1 text-lg font-bold text-sf-deeper">{(data.sourceSystems ?? []).join('  ·  ')}</p>
        <p className="mt-2 text-sm leading-relaxed text-gray-600">{data.summary}</p>
        <p className="mt-2 text-xs text-gray-500">Snowflake database: <span className="font-mono">{data.database}</span></p>
      </div>

      <ChartCard title="Medallion Lineage — SAP BDC → Snowflake → Application">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-stretch">
          {layers.map((layer: any, i: number) => (
            <div key={layer.name} className="flex flex-1 items-stretch gap-2">
              <div className={`flex-1 rounded-xl border p-4 ${TONE[layer.tone] ?? TONE.sap}`}>
                <p className="text-sm font-bold">{layer.name}</p>
                <ul className="mt-2 space-y-1">
                  {layer.objects.map((o: string) => (
                    <li key={o} className="font-mono text-[11px] leading-snug opacity-90">{o}</li>
                  ))}
                </ul>
              </div>
              {i < layers.length - 1 && (
                <div className="hidden items-center lg:flex"><ChevronRight className="h-5 w-5 text-gray-400" /></div>
              )}
            </div>
          ))}
        </div>
      </ChartCard>

      <ChartCard title="SAP BDC Source Data Products">
        <DataTable columns={[
          { key: 'sapSystem', label: 'SAP Source System' },
          { key: 'dataProduct', label: 'BDC Data Product' },
          { key: 'l0Object', label: 'L0 Object (Bronze)' },
          { key: 'l1Object', label: 'L1 / Curated Object' },
          { key: 'rows', label: 'Rows', format: (v: any) => formatNumber(v) },
        ]} data={products} />
      </ChartCard>
    </div>
  );
}
