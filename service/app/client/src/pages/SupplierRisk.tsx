import { useQuery } from '@/hooks/useQuery';
import { fetchSupplierRisk } from '@/lib/api';
import { formatDollar, formatNumber } from '@/lib/utils';
import MetricCard from '@/components/MetricCard';
import ChartCard from '@/components/ChartCard';
import DataTable from '@/components/DataTable';
import ReactECharts from 'echarts-for-react';
import { ShieldAlert, ShieldCheck, AlertTriangle, GitFork } from 'lucide-react';

export default function SupplierRisk() {
  const { data, loading, error } = useQuery(() => fetchSupplierRisk(), []);
  if (loading) return <div className="h-64 animate-pulse rounded-xl bg-gray-200" />;
  if (error) return <div className="rounded-lg border border-red-300 bg-red-50 p-4 text-sm text-red-800">Error: {error}</div>;
  if (!data) return null;
  const k = data.kpis ?? {};
  const byTier = data.byTier ?? [];
  const byRegion = data.byRegion ?? [];
  const topRisk = data.topRisk ?? [];
  const scatter = data.scatter ?? [];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard title="Suppliers Assessed" value={formatNumber(k.supplierCount)} icon={ShieldCheck} accent="border-cyan-300/50 bg-gradient-to-br from-cyan-50 to-sky-50" />
        <MetricCard title="Avg Risk Score" value={`${k.avgRisk ?? 0}/100`} icon={ShieldAlert} accent="border-amber-300/50 bg-gradient-to-br from-amber-50 to-orange-50" delta="Lower is better" deltaType="neutral" />
        <MetricCard title="High-Risk Suppliers" value={formatNumber(k.highRiskSuppliers)} icon={AlertTriangle} accent="border-red-300/50 bg-gradient-to-br from-red-50 to-rose-50" delta="Risk score ≥ 70" deltaType="negative" />
        <MetricCard title="Single-Source Spend" value={formatDollar(k.singleSourceSpend)} icon={GitFork} accent="border-purple-300/50 bg-gradient-to-br from-purple-50 to-indigo-50" delta="Supply continuity risk" deltaType="negative" />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <ChartCard title="Spend & Risk by Supplier Tier">
          <ReactECharts option={{ tooltip: { trigger: 'axis' },
            legend: { data: ['Spend', 'Avg Risk'], top: 0 },
            grid: { left: 70, right: 50, bottom: 30, top: 30 },
            xAxis: { type: 'category', data: byTier.map((d: any) => d.name) },
            yAxis: [{ type: 'value', axisLabel: { formatter: (v: number) => formatDollar(v) } }, { type: 'value', max: 100, position: 'right', axisLabel: { formatter: '{value}' } }],
            series: [
              { name: 'Spend', type: 'bar', data: byTier.map((d: any) => d.spend), itemStyle: { color: '#06b6d4', borderRadius: [4,4,0,0] }, barMaxWidth: 40 },
              { name: 'Avg Risk', type: 'line', yAxisIndex: 1, data: byTier.map((d: any) => d.avgRisk), itemStyle: { color: '#ef4444' }, symbolSize: 8 },
            ] }} style={{ height: 320 }} />
        </ChartCard>
        <ChartCard title="Average Risk Score by Region">
          <ReactECharts option={{ tooltip: { trigger: 'axis' },
            grid: { left: 90, right: 30, bottom: 20, top: 10 },
            xAxis: { type: 'value', max: 100 },
            yAxis: { type: 'category', data: byRegion.map((d: any) => d.name).reverse() },
            series: [{ type: 'bar', data: byRegion.map((d: any) => d.avgRisk).reverse(), itemStyle: { color: '#f59e0b', borderRadius: [0,4,4,0] }, barMaxWidth: 22 }] }} style={{ height: 320 }} />
        </ChartCard>
      </div>

      <ChartCard title="Risk vs. Spend (bubble = supplier)">
        <ReactECharts option={{ tooltip: { formatter: (p: any) => `${p.data[2]}<br/>Risk: ${p.data[0]} · Spend: ${formatDollar(p.data[1])}` },
          grid: { left: 70, right: 30, bottom: 40, top: 20 },
          xAxis: { type: 'value', name: 'Risk Score', max: 100 },
          yAxis: { type: 'value', name: 'Annual Spend', axisLabel: { formatter: (v: number) => formatDollar(v) } },
          series: [{ type: 'scatter', symbolSize: 10, data: scatter.map((d: any) => [d.riskScore, d.spend, d.name]),
            itemStyle: { color: '#7c3aed', opacity: 0.55 } }] }} style={{ height: 340 }} />
      </ChartCard>

      <ChartCard title="Highest-Risk Suppliers">
        <DataTable columns={[
          { key: 'name', label: 'Supplier' },
          { key: 'country', label: 'Country' },
          { key: 'riskScore', label: 'Risk' },
          { key: 'financialRisk', label: 'Financial' },
          { key: 'geoRisk', label: 'Geo' },
          { key: 'complianceRisk', label: 'Compliance' },
          { key: 'annualSpend', label: 'Annual Spend', format: (v: any) => formatDollar(v) },
          { key: 'isSingleSource', label: 'Single Source', format: (v: any) => (v ? 'Yes' : 'No') },
        ]} data={topRisk} />
      </ChartCard>
    </div>
  );
}
