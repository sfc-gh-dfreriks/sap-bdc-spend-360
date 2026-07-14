import { useQuery } from '@/hooks/useQuery';
import { fetchSavings } from '@/lib/api';
import { formatDollar, formatNumber } from '@/lib/utils';
import MetricCard from '@/components/MetricCard';
import ChartCard from '@/components/ChartCard';
import DataTable from '@/components/DataTable';
import ReactECharts from 'echarts-for-react';
import { PiggyBank, TrendingUp, Loader, Target } from 'lucide-react';

export default function Savings() {
  const { data, loading, error } = useQuery(() => fetchSavings(), []);
  if (loading) return <div className="h-64 animate-pulse rounded-xl bg-gray-200" />;
  if (error) return <div className="rounded-lg border border-red-300 bg-red-50 p-4 text-sm text-red-800">Error: {error}</div>;
  if (!data) return null;
  const k = data.kpis ?? {};
  const byType = data.byType ?? [];
  const byStatus = data.byStatus ?? [];
  const byCategory = data.byCategory ?? [];
  const pipeline = data.pipeline ?? [];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard title="Total Identified Savings" value={formatDollar(k.totalIdentified)} icon={PiggyBank} accent="border-cyan-300/50 bg-gradient-to-br from-cyan-50 to-sky-50" delta={`${formatNumber(k.opportunities)} opportunities`} deltaType="neutral" />
        <MetricCard title="Realized Savings" value={formatDollar(k.realized)} icon={TrendingUp} accent="border-emerald-300/50 bg-gradient-to-br from-emerald-50 to-green-50" delta="Captured" deltaType="positive" />
        <MetricCard title="In-Progress" value={formatDollar(k.inProgress)} icon={Loader} accent="border-amber-300/50 bg-gradient-to-br from-amber-50 to-orange-50" delta="Being executed" deltaType="neutral" />
        <MetricCard title="Opportunities" value={formatNumber(k.opportunities)} icon={Target} accent="border-purple-300/50 bg-gradient-to-br from-purple-50 to-indigo-50" />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <ChartCard title="Savings by Lever">
          <ReactECharts option={{ tooltip: { trigger: 'axis', formatter: (p: any) => `${p[0].name}: ${formatDollar(p[0].value)}` },
            grid: { left: 150, right: 30, bottom: 20, top: 10 },
            xAxis: { type: 'value', axisLabel: { formatter: (v: number) => formatDollar(v) } },
            yAxis: { type: 'category', data: byType.map((d: any) => d.name).reverse() },
            series: [{ type: 'bar', data: byType.map((d: any) => d.savings).reverse(), itemStyle: { color: '#06b6d4', borderRadius: [0,4,4,0] }, barMaxWidth: 22 }] }} style={{ height: 300 }} />
        </ChartCard>
        <ChartCard title="Savings Pipeline by Status">
          <ReactECharts option={{ tooltip: { trigger: 'item', formatter: (p: any) => `${p.name}: ${formatDollar(p.value)} (${p.percent}%)` },
            series: [{ type: 'pie', radius: ['45%', '70%'], data: byStatus.map((d: any) => ({ name: d.name, value: d.savings })),
              itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 }, label: { formatter: '{b}\n{d}%', fontSize: 12 } }] }} style={{ height: 300 }} />
        </ChartCard>
      </div>

      <ChartCard title="Savings Opportunity by Category">
        <ReactECharts option={{ tooltip: { trigger: 'axis', formatter: (p: any) => `${p[0].name}: ${formatDollar(p[0].value)}` },
          grid: { left: 70, right: 20, bottom: 90, top: 10 },
          xAxis: { type: 'category', data: byCategory.map((d: any) => d.name), axisLabel: { rotate: 40, fontSize: 10 } },
          yAxis: { type: 'value', axisLabel: { formatter: (v: number) => formatDollar(v) } },
          series: [{ type: 'bar', data: byCategory.map((d: any) => d.savings), itemStyle: { color: '#10b981', borderRadius: [4,4,0,0] }, barMaxWidth: 28 }] }} style={{ height: 320 }} />
      </ChartCard>

      <ChartCard title="Top Savings Opportunities">
        <DataTable columns={[
          { key: 'oppId', label: 'ID' },
          { key: 'category', label: 'Category' },
          { key: 'oppType', label: 'Lever' },
          { key: 'estimatedSavings', label: 'Est. Savings', format: (v: any) => formatDollar(v) },
          { key: 'savingsPct', label: 'Save %', format: (v: any) => `${v}%` },
          { key: 'status', label: 'Status' },
          { key: 'owner', label: 'Owner' },
          { key: 'targetDate', label: 'Target' },
        ]} data={pipeline} />
      </ChartCard>
    </div>
  );
}
