import { useFilters } from '@/hooks/useFilters';
import { useQuery } from '@/hooks/useQuery';
import { fetchCategories } from '@/lib/api';
import { formatDollar } from '@/lib/utils';
import ChartCard from '@/components/ChartCard';
import DataTable from '@/components/DataTable';
import ReactECharts from 'echarts-for-react';

export default function Categories() {
  const { selectedCategories, selectedCompanies } = useFilters();
  const has = selectedCategories.length > 0 && selectedCompanies.length > 0;
  const { data, loading, error } = useQuery(
    () => has ? fetchCategories(selectedCategories, selectedCompanies) : Promise.resolve(null),
    [selectedCategories.join(','), selectedCompanies.join(',')]);
  if (!has) return <div className="rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm text-amber-800">Select at least one category and company.</div>;
  if (loading) return <div className="h-64 animate-pulse rounded-xl bg-gray-200" />;
  if (error) return <div className="rounded-lg border border-red-300 bg-red-50 p-4 text-sm text-red-800">Error: {error}</div>;
  if (!data) return null;
  const byCat = data.byCat ?? [];
  const contract = data.contractByCat ?? [];

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <ChartCard title="Spend by Category" className="lg:col-span-2">
        <ReactECharts option={{ tooltip: { trigger: 'axis', formatter: (p: any) => `${p[0].name}: ${formatDollar(p[0].value)}` },
          grid: { left: 70, right: 20, bottom: 90, top: 10 },
          xAxis: { type: 'category', data: byCat.map((d: any) => d.name), axisLabel: { rotate: 40, fontSize: 10 } },
          yAxis: { type: 'value', axisLabel: { formatter: (v: number) => formatDollar(v) } },
          series: [{ type: 'bar', data: byCat.map((d: any) => d.spend), itemStyle: { color: '#06b6d4', borderRadius: [4, 4, 0, 0] }, barMaxWidth: 28 }] }} style={{ height: 340 }} />
      </ChartCard>
      <ChartCard title="Contract Compliance by Category">
        <ReactECharts option={{ tooltip: { trigger: 'axis', formatter: (p: any) => `${p[0].name}: ${p[0].value}% on contract` },
          grid: { left: 150, right: 30, bottom: 20, top: 10 }, xAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%' } },
          yAxis: { type: 'category', data: contract.map((d: any) => d.name).reverse(), axisLabel: { fontSize: 10 } },
          series: [{ type: 'bar', data: contract.map((d: any) => d.contractPct).reverse(), itemStyle: { borderRadius: [0, 4, 4, 0], color: '#10b981' }, barMaxWidth: 16 }] }} style={{ height: 360 }} />
      </ChartCard>
      <ChartCard title="Category Detail">
        <DataTable columns={[
          { key: 'name', label: 'Category' },
          { key: 'spend', label: 'Spend', format: (v: any) => formatDollar(v) },
          { key: 'lines', label: 'PO Lines' },
          { key: 'avgPrice', label: 'Avg Unit Price', format: (v: any) => formatDollar(v) },
        ]} data={byCat} />
      </ChartCard>
    </div>
  );
}
