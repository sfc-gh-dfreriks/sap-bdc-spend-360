import { useFilters } from '@/hooks/useFilters';
import { useQuery } from '@/hooks/useQuery';
import { fetchSuppliers } from '@/lib/api';
import { formatDollar, formatPct, formatNumber } from '@/lib/utils';
import MetricCard from '@/components/MetricCard';
import { Building2, PieChart, Truck } from 'lucide-react';
import ChartCard from '@/components/ChartCard';
import DataTable from '@/components/DataTable';
import ReactECharts from 'echarts-for-react';

export default function Suppliers() {
  const { selectedCategories, selectedCompanies } = useFilters();
  const has = selectedCategories.length > 0 && selectedCompanies.length > 0;
  const { data, loading, error } = useQuery(
    () => has ? fetchSuppliers(selectedCategories, selectedCompanies) : Promise.resolve(null),
    [selectedCategories.join(','), selectedCompanies.join(',')]);
  if (!has) return <div className="rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm text-amber-800">Select at least one category and company.</div>;
  if (loading) return <div className="h-64 animate-pulse rounded-xl bg-gray-200" />;
  if (error) return <div className="rounded-lg border border-red-300 bg-red-50 p-4 text-sm text-red-800">Error: {error}</div>;
  if (!data) return null;
  const top = data.top ?? [];
  const c = data.concentration ?? {};

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <MetricCard title="Active Suppliers" value={formatNumber(c.supplierCount)} icon={Building2} accent="border-cyan-300/50 bg-gradient-to-br from-cyan-50 to-sky-50" />
        <MetricCard title="Top 10 Concentration" value={formatPct(c.top10Pct)} icon={PieChart} accent="border-purple-300/50 bg-gradient-to-br from-purple-50 to-indigo-50" delta="Share of total spend" deltaType={c.top10Pct > 60 ? 'negative' : 'neutral'} />
        <MetricCard title="Top 50 Concentration" value={formatPct(c.top50Pct)} icon={Truck} accent="border-emerald-300/50 bg-gradient-to-br from-emerald-50 to-green-50" delta="Share of total spend" deltaType="neutral" />
      </div>
      <ChartCard title="Top 20 Suppliers by Spend">
        <ReactECharts option={{ tooltip: { trigger: 'axis', formatter: (p: any) => `${p[0].name}: ${formatDollar(p[0].value)}` },
          grid: { left: 90, right: 30, bottom: 20, top: 10 }, xAxis: { type: 'value', axisLabel: { formatter: (v: number) => formatDollar(v) } },
          yAxis: { type: 'category', data: top.map((d: any) => d.name).reverse(), axisLabel: { fontSize: 10 } },
          series: [{ type: 'bar', data: top.map((d: any) => d.spend).reverse(), itemStyle: { borderRadius: [0, 4, 4, 0], color: '#06b6d4' }, barMaxWidth: 16 }] }} style={{ height: 460 }} />
      </ChartCard>
      <ChartCard title="Supplier Detail">
        <DataTable columns={[
          { key: 'name', label: 'Supplier' },
          { key: 'spend', label: 'Spend', format: (v: any) => formatDollar(v) },
          { key: 'lines', label: 'PO Lines' },
          { key: 'categories', label: 'Categories' },
          { key: 'contractPct', label: '% On Contract', format: (v: any) => `${v}%` },
        ]} data={top} />
      </ChartCard>
    </div>
  );
}
