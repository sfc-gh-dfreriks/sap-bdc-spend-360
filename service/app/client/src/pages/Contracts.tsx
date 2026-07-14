import { useFilters } from '@/hooks/useFilters';
import { useQuery } from '@/hooks/useQuery';
import { fetchContracts } from '@/lib/api';
import { formatDollar } from '@/lib/utils';
import ChartCard from '@/components/ChartCard';
import ReactECharts from 'echarts-for-react';

export default function Contracts() {
  const { selectedCategories, selectedCompanies } = useFilters();
  const has = selectedCategories.length > 0 && selectedCompanies.length > 0;
  const { data, loading, error } = useQuery(
    () => has ? fetchContracts(selectedCategories, selectedCompanies) : Promise.resolve(null),
    [selectedCategories.join(','), selectedCompanies.join(',')]);
  if (!has) return <div className="rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm text-amber-800">Select at least one category and company.</div>;
  if (loading) return <div className="h-64 animate-pulse rounded-xl bg-gray-200" />;
  if (error) return <div className="rounded-lg border border-red-300 bg-red-50 p-4 text-sm text-red-800">Error: {error}</div>;
  if (!data) return null;

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <ChartCard title="On vs Off Contract Spend">
        <ReactECharts option={{ tooltip: { trigger: 'item', formatter: (p: any) => `${p.name}: ${formatDollar(p.value)} (${p.percent}%)` },
          series: [{ type: 'pie', radius: ['45%', '72%'], center: ['50%', '55%'],
            data: (data.split ?? []).map((d: any) => ({ name: d.name, value: d.spend, itemStyle: { color: d.name === 'On Contract' ? '#10b981' : '#ef4444' } })),
            itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 }, label: { formatter: '{b}\n{d}%', fontSize: 12 } }] }} style={{ height: 340 }} />
      </ChartCard>
      <ChartCard title="Contract Compliance by Company">
        <ReactECharts option={{ tooltip: { trigger: 'axis', formatter: (p: any) => `${p[0].name}: ${p[0].value}%` },
          grid: { left: 110, right: 30, bottom: 20, top: 10 }, xAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%' } },
          yAxis: { type: 'category', data: (data.byCompany ?? []).map((d: any) => d.name) },
          series: [{ type: 'bar', data: (data.byCompany ?? []).map((d: any) => d.contractPct), itemStyle: { borderRadius: [0, 4, 4, 0], color: '#10b981' }, barMaxWidth: 26 }] }} style={{ height: 340 }} />
      </ChartCard>
      <ChartCard title="Off-Contract Spend by Category (savings opportunity)" className="lg:col-span-2">
        <ReactECharts option={{ tooltip: { trigger: 'axis', formatter: (p: any) => `${p[0].name}: ${formatDollar(p[0].value)} off contract` },
          grid: { left: 70, right: 20, bottom: 90, top: 10 },
          xAxis: { type: 'category', data: (data.offContractByCat ?? []).map((d: any) => d.name), axisLabel: { rotate: 40, fontSize: 10 } },
          yAxis: { type: 'value', axisLabel: { formatter: (v: number) => formatDollar(v) } },
          series: [{ type: 'bar', data: (data.offContractByCat ?? []).map((d: any) => d.offContractSpend), itemStyle: { color: '#f59e0b', borderRadius: [4, 4, 0, 0] }, barMaxWidth: 28 }] }} style={{ height: 320 }} />
      </ChartCard>
    </div>
  );
}
