import { useState } from 'react';
import { FilterProvider } from '@/hooks/useFilters';
import Sidebar, { NAV_ITEMS, type PageId } from '@/components/Sidebar';
import Overview from '@/pages/Overview';
import Categories from '@/pages/Categories';
import Suppliers from '@/pages/Suppliers';
import SupplierRisk from '@/pages/SupplierRisk';
import Sustainability from '@/pages/Sustainability';
import Savings from '@/pages/Savings';
import Contracts from '@/pages/Contracts';
import PurchaseOrders from '@/pages/PurchaseOrders';
import Lineage from '@/pages/Lineage';
import Analyst from '@/pages/Analyst';

const PAGE_COMPONENTS: Record<string, React.FC> = {
  overview: Overview,
  categories: Categories,
  suppliers: Suppliers,
  'supplier-risk': SupplierRisk,
  sustainability: Sustainability,
  savings: Savings,
  contracts: Contracts,
  'purchase-orders': PurchaseOrders,
  lineage: Lineage,
  analyst: Analyst,
};

function AppShell() {
  const [activePage, setActivePage] = useState<PageId>('overview');
  const navItem = NAV_ITEMS.find((n) => n.id === activePage)!;
  const Icon = navItem.icon;
  const PageComponent = PAGE_COMPONENTS[activePage];
  return (
    <div className="min-h-screen bg-gray-50">
      <Sidebar activePage={activePage} onNavigate={setActivePage} />
      <main className="ml-64 min-h-screen p-6">
        <div className="mb-6 flex items-center gap-3">
          <Icon className="h-6 w-6 text-sf-primary" />
          <h1 className="text-2xl font-bold text-sf-deeper">{navItem.label}</h1>
        </div>
        {PageComponent ? <PageComponent /> : null}
      </main>
    </div>
  );
}

export default function App() {
  return (
    <FilterProvider>
      <AppShell />
    </FilterProvider>
  );
}
