import { useQuery } from '@/hooks/useQuery';
import { fetchSustainability } from '@/lib/api';
import { formatDollar, formatNumber } from '@/lib/utils';
import MetricCard from '@/components/MetricCard';
import ChartCard from '@/components/ChartCard';
import DataTable from '@/components/DataTable';
import ReactECharts from 'echarts-for-react';
import { Leaf, Recycle, Users, Sprout } from 'lucide-react';

export default function Sustainability() {
  const { data, loading, error } = useQuery(() => fetchSustainability(), []);
  if (loading) return <div className="h-64 animate-pulse rounded-xl bg-gray-200" />;
  if (error) return <div className="rounded-lg border border-red-300 bg-red-50 p-4 text-sm text-red-800">Error: {error}</div>;
  if (!data) return null;
  const k = data.kpis ?? {};
  const byRegion = data.byRegion ?? [];
  const diverseByClass = data.diverseByClass ?? [];
  const esgBuckets = data.esgBuckets ?? [];
  const topEsg = data.topEsg ?? [];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard title="Avg ESG Score" value={`${k.avgEsg ?? 0}/100`} icon={Leaf} accent="border-emerald-300/50 bg-gradient-to-br from-emerald-50 to-green-50" delta="Higher is better" deltaType="positive" />
        <MetricCard title="Sustainable Spend" value={formatDollar(k.sustainableSpend)} icon={Recycle} accent="border-teal-300/50 bg-gradient-to-br from-teal-50 to-cyan-50" delta={`${formatNumber(k.sustainableSuppliers)} suppliers`} deltaType="neutral" />
        <MetricCard title="Diverse Spend" value={formatDollar(k.diverseSpend)} icon={Users} accent="border-indigo-300/50 bg-gradient-to-br from-indigo-50 to-purple-50" delta={`${formatNumber(k.diverseSuppliers)} suppliers`} deltaType="neutral" />
        <MetricCard title="Sustainable Suppliers" value={formatNumber(k.sustainableSuppliers)} icon={Sprout} accent="border-lime-300/50 bg-gradient-to-br from-lime-50 to-green-50" />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <ChartCard title="ESG Pillars by Region (Env / Social / Governance)">
          <ReactECharts option={{ tooltip: { trigger: 'axis' }, legend: { data: ['Env', 'Social', 'Gov'], top: 0 },
            grid: { left: 60, right: 20, bottom: 30, top: 30 },
            xAxis: { type: 'category', data: byRegion.map((d: any) => d.name) },
            yAxis: { type: 'value', max: 100 },
            series: [
              { name: 'Env', type: 'bar', data: byRegion.map((d: any) => d.env), itemStyle: { color: '#10b981' }, barMaxWidth: 22 },
              { name: 'Social', type: 'bar', data: byRegion.map((d: any) => d.social), itemStyle: { color: '#3b82f6' }, barMaxWidth: 22 },
              { name: 'Gov', type: 'bar', data: byRegion.map((d: any) => d.gov), itemStyle: { color: '#8b5cf6' }, barMaxWidth: 22 },
            ] }} style={{ height: 320 }} />
        </ChartCard>
        <ChartCard title="Suppliers by ESG Band">
          <ReactECharts option={{ tooltip: { trigger: 'item' },
            series: [{ type: 'pie', radius: ['45%', '70%'], data: esgBuckets.map((d: any) => ({ name: d.name, value: d.suppliers })),
              itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 }, label: { formatter: '{b}\n{d}%', fontSize: 11 } }] }} style={{ height: 320 }} />
        </ChartCard>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <ChartCard title="Diverse Spend by Classification">
          <ReactECharts option={{ tooltip: { trigger: 'axis', formatter: (p: any) => `${p[0].name}: ${formatDollar(p[0].value)}` },
            grid: { left: 130, right: 30, bottom: 20, top: 10 },
            xAxis: { type: 'value', axisLabel: { formatter: (v: number) => formatDollar(v) } },
            yAxis: { type: 'category', data: diverseByClass.map((d: any) => d.name).reverse() },
            series: [{ type: 'bar', data: diverseByClass.map((d: any) => d.spend).reverse(), itemStyle: { color: '#6366f1', borderRadius: [0,4,4,0] }, barMaxWidth: 22 }] }} style={{ height: 300 }} />
        </ChartCard>
        <ChartCard title="Top ESG-Rated Suppliers">
          <DataTable columns={[
            { key: 'name', label: 'Supplier' },
            { key: 'esgScore', label: 'ESG' },
            { key: 'envScore', label: 'Env' },
            { key: 'socialScore', label: 'Social' },
            { key: 'govScore', label: 'Gov' },
            { key: 'annualSpend', label: 'Annual Spend', format: (v: any) => formatDollar(v) },
          ]} data={topEsg} />
        </ChartCard>
      </div>
    </div>
  );
}
