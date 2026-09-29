import { useQuery } from '@/hooks/useQuery';
import { fetchLineage } from '@/lib/api';
import { formatNumber } from '@/lib/utils';
import ChartCard from '@/components/ChartCard';
import { ChevronRight } from 'lucide-react';

const TONE: Record<string, string> = {
  sap: 'border-slate-300 bg-slate-50 text-slate-800',
  bronze: 'border-amber-300 bg-amber-50 text-amber-900',
  silver: 'border-sky-300 bg-sky-50 text-sky-900',
  gold: 'border-emerald-300 bg-emerald-50 text-emerald-900',
  ai: 'border-purple-300 bg-purple-50 text-purple-900',
};

/** Long Snowflake identifiers break at dots/underscores instead of widening the table. */
function Ident({ value }: { value: unknown }) {
  const s = String(value ?? '');
  return <span className="font-mono text-[11px] leading-snug [overflow-wrap:anywhere]">{s.replace(/([._])/g, '$1\u200b')}</span>;
}

export default function Lineage() {
  const { data, loading, error } = useQuery(() => fetchLineage(), []);
  if (loading) return <div className="h-64 animate-pulse rounded-xl bg-gray-200" />;
  if (error) return <div className="rounded-lg border border-red-300 bg-red-50 p-4 text-sm text-red-800">Error: {error}</div>;
  if (!data) return null;
  const layers = data.layers ?? [];
  const products = data.products ?? [];
  const curated = data.curated ?? [];

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
            <div key={layer.name} className="flex min-w-0 flex-1 items-stretch gap-2">
              <div className={`min-w-0 flex-1 rounded-xl border p-4 ${TONE[layer.tone] ?? TONE.sap}`}>
                <p className="text-sm font-bold">{layer.name}</p>
                <ul className="mt-2 space-y-1">
                  {(layer.objects ?? []).map((o: string) => (
                    <li key={o} className="opacity-90"><Ident value={o} /></li>
                  ))}
                </ul>
              </div>
              {i < layers.length - 1 && (
                <div className="hidden shrink-0 items-center lg:flex"><ChevronRight className="h-5 w-5 text-gray-400" /></div>
              )}
            </div>
          ))}
        </div>
      </ChartCard>

      <ChartCard title="SAP BDC Source Data Products">
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="w-full table-fixed text-sm">
            <colgroup>
              <col className="w-[13%]" /><col className="w-[16%]" /><col className="w-[25%]" />
              <col className="w-[21%]" /><col className="w-[16%]" /><col className="w-[9%]" />
            </colgroup>
            <thead>
              <tr className="bg-sf-dark text-left text-white">
                <th className="px-3 py-2.5 font-medium">SAP Source System</th>
                <th className="px-3 py-2.5 font-medium">BDC Data Product</th>
                <th className="px-3 py-2.5 font-medium">L0 Object (Bronze)</th>
                <th className="px-3 py-2.5 font-medium">L1 / Curated Object</th>
                <th className="px-3 py-2.5 font-medium">Used For</th>
                <th className="px-3 py-2.5 text-right font-medium">Rows</th>
              </tr>
            </thead>
            <tbody>
              {products.map((p: any, i: number) => (
                <tr key={`${p.dataProduct}-${i}`} className={`align-top ${i % 2 === 0 ? 'bg-white' : 'bg-sky-50/50'}`}>
                  <td className="px-3 py-2 text-gray-700">{p.sapSystem}</td>
                  <td className="px-3 py-2 font-medium text-gray-800">{p.dataProduct}</td>
                  <td className="px-3 py-2 text-gray-700"><Ident value={p.l0Object} /></td>
                  <td className="px-3 py-2 text-gray-700"><Ident value={p.l1Object} /></td>
                  <td className="px-3 py-2 text-xs text-gray-600">{p.usage}</td>
                  <td className="px-3 py-2 text-right tabular-nums text-gray-700">{p.rows == null ? '—' : formatNumber(p.rows)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-xs leading-relaxed text-gray-500">
          {curated.length > 0 && <>Curated L2 tables: {curated.map((c: any) => `${c.object} (${formatNumber(c.rows)} rows)`).join(' · ')}. </>}
          {data.note}
        </p>
      </ChartCard>
    </div>
  );
}
