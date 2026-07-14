import { useFilters } from '@/hooks/useFilters';
import { useQuery } from '@/hooks/useQuery';
import { fetchPurchaseOrders } from '@/lib/api';
import { formatDollar } from '@/lib/utils';
import ChartCard from '@/components/ChartCard';
import DataTable from '@/components/DataTable';

export default function PurchaseOrders() {
  const { selectedCategories, selectedCompanies } = useFilters();
  const has = selectedCategories.length > 0 && selectedCompanies.length > 0;
  const { data, loading, error } = useQuery(
    () => has ? fetchPurchaseOrders(selectedCategories, selectedCompanies) : Promise.resolve(null),
    [selectedCategories.join(','), selectedCompanies.join(',')]);
  if (!has) return <div className="rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm text-amber-800">Select at least one category and company.</div>;
  if (loading) return <div className="h-64 animate-pulse rounded-xl bg-gray-200" />;
  if (error) return <div className="rounded-lg border border-red-300 bg-red-50 p-4 text-sm text-red-800">Error: {error}</div>;
  if (!data) return null;

  return (
    <ChartCard title="Purchase Orders" subtitle="Top 200 by spend (filtered)">
      <DataTable columns={[
        { key: 'poId', label: 'PO' },
        { key: 'supplier', label: 'Supplier' },
        { key: 'category', label: 'Category' },
        { key: 'company', label: 'Company' },
        { key: 'poDate', label: 'PO Date' },
        { key: 'orderQuantity', label: 'Qty' },
        { key: 'netPrice', label: 'Unit Price', format: (v: any) => formatDollar(v) },
        { key: 'spend', label: 'Spend', format: (v: any) => formatDollar(v) },
        { key: 'onContract', label: 'On Contract' },
        { key: 'buyer', label: 'Buyer' },
      ]} data={data.rows ?? []} />
    </ChartCard>
  );
}
