import { useFilters } from '@/hooks/useFilters';
import { useQuery } from '@/hooks/useQuery';
import { fetchOverview } from '@/lib/api';
import { formatDollar, formatPct, formatNumber } from '@/lib/utils';
import MetricCard, { DollarSign, Receipt, Building2, FileText } from '@/components/MetricCard';
import ChartCard from '@/components/ChartCard';
import ReactECharts from 'echarts-for-react';

const PALETTE = ['#06b6d4', '#8b5cf6', '#f59e0b', '#10b981', '#ef4444', '#3b82f6', '#ec4899', '#14b8a6'];

export default function Overview() {
  const { selectedCategories, selectedCompanies } = useFilters();
  const has = selectedCategories.length > 0 && selectedCompanies.length > 0;
  const { data, loading, error } = useQuery(
    () => has ? fetchOverview(selectedCategories, selectedCompanies) : Promise.resolve(null),
    [selectedCategories.join(','), selectedCompanies.join(',')]);
  if (!has) return <div className="rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm text-amber-800">Select at least one category and company.</div>;
  if (loading) return <div className="grid grid-cols-4 gap-4">{Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-28 animate-pulse rounded-xl bg-gray-200" />)}</div>;
  if (error) return <div className="rounded-lg border border-red-300 bg-red-50 p-4 text-sm text-red-800">Error: {error}</div>;
  if (!data?.kpis) return null;
  const k = data.kpis;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard title="Total Spend" value={formatDollar(k.totalSpend)} icon={DollarSign} accent="border-cyan-300/50 bg-gradient-to-br from-cyan-50 to-sky-50" delta={`${formatNumber(k.poLines)} PO lines`} deltaType="neutral" />
        <MetricCard title="Suppliers" value={formatNumber(k.suppliers)} icon={Building2} accent="border-purple-300/50 bg-gradient-to-br from-purple-50 to-indigo-50" delta={`${formatNumber(k.categories)} categories`} deltaType="neutral" />
        <MetricCard title="On-Contract Spend" value={formatPct(k.contractPct)} icon={FileText} accent="border-emerald-300/50 bg-gradient-to-br from-emerald-50 to-green-50" delta={k.contractPct >= 70 ? 'Strong compliance' : 'Opportunity'} deltaType={k.contractPct >= 70 ? 'positive' : 'negative'} />
        <MetricCard title="Avg PO Value" value={formatDollar(k.avgPoValue)} icon={Receipt} accent="border-amber-300/50 bg-gradient-to-br from-amber-50 to-orange-50" delta="Per line item" deltaType="neutral" />
      </div>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <ChartCard title="Spend by Category">
          <ReactECharts option={{ tooltip: { trigger: 'axis', formatter: (p: any) => `${p[0].name}: ${formatDollar(p[0].value)}` },
            grid: { left: 150, right: 30, bottom: 20, top: 10 }, xAxis: { type: 'value', axisLabel: { formatter: (v: number) => formatDollar(v) } },
            yAxis: { type: 'category', data: (data.byCat ?? []).map((d: any) => d.name).reverse(), axisLabel: { fontSize: 10 } },
            series: [{ type: 'bar', data: (data.byCat ?? []).map((d: any) => d.spend).reverse(), itemStyle: { borderRadius: [0, 4, 4, 0], color: '#06b6d4' }, barMaxWidth: 16 }] }} style={{ height: 360 }} />
        </ChartCard>
        <ChartCard title="Top 10 Suppliers by Spend">
          <ReactECharts option={{ tooltip: { trigger: 'axis', formatter: (p: any) => `${p[0].name}: ${formatDollar(p[0].value)}` },
            grid: { left: 90, right: 30, bottom: 20, top: 10 }, xAxis: { type: 'value', axisLabel: { formatter: (v: number) => formatDollar(v) } },
            yAxis: { type: 'category', data: (data.topSuppliers ?? []).map((d: any) => d.name).reverse(), axisLabel: { fontSize: 10 } },
            series: [{ type: 'bar', data: (data.topSuppliers ?? []).map((d: any) => d.spend).reverse(), itemStyle: { borderRadius: [0, 4, 4, 0], color: '#8b5cf6' }, barMaxWidth: 16 }] }} style={{ height: 360 }} />
        </ChartCard>
        <ChartCard title="Monthly Spend Trend" className="lg:col-span-2">
          <ReactECharts option={{ tooltip: { trigger: 'axis', formatter: (p: any) => `${p[0].name}<br/>${formatDollar(p[0].value)}` },
            grid: { left: 70, right: 20, bottom: 30, top: 20 },
            xAxis: { type: 'category', data: (data.trend ?? []).map((d: any) => d.month), boundaryGap: false },
            yAxis: { type: 'value', axisLabel: { formatter: (v: number) => formatDollar(v) } },
            series: [{ type: 'line', smooth: true, symbol: 'circle', symbolSize: 6, data: (data.trend ?? []).map((d: any) => d.spend),
              lineStyle: { color: '#06b6d4', width: 3 }, itemStyle: { color: '#06b6d4' },
              areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(6,182,212,0.35)' }, { offset: 1, color: 'rgba(6,182,212,0.03)' }] } } }] }} style={{ height: 300 }} />
        </ChartCard>
        <ChartCard title="Spend by Company" className="lg:col-span-2">
          <ReactECharts option={{ tooltip: { trigger: 'item', formatter: (p: any) => `${p.name}: ${formatDollar(p.value)} (${p.percent}%)` },
            series: [{ type: 'pie', radius: ['40%', '70%'], center: ['50%', '55%'],
              data: (data.byCompany ?? []).map((d: any, i: number) => ({ name: d.name, value: d.spend, itemStyle: { color: PALETTE[i % PALETTE.length] } })),
              itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 }, label: { formatter: '{b}\n{d}%', fontSize: 11 } }] }} style={{ height: 300 }} />
        </ChartCard>
      </div>
    </div>
  );
}
