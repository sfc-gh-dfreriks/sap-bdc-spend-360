import { useState } from 'react';
import { FilterProvider, useFilters } from '@/hooks/useFilters';
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
import AskCortexPage from '@/pages/AskCortexPage';
import AskCortex from '@/components/AskCortex';

// Ask Cortex: per-page topic (server TOPICS in routes/askCortex.ts) + suggested questions.
const ASK: Record<string, { topic: string; suggestions: string[] }> = {
  overview: { topic: 'overview', suggestions: ['What is driving total spend this period?', 'Which company and category dominate spend?'] },
  categories: { topic: 'categories', suggestions: ['Which categories are growing fastest quarter over quarter?', 'Where is category spend spread across too many suppliers?'] },
  suppliers: { topic: 'suppliers', suggestions: ['Is our supplier base too concentrated?', 'Which top suppliers have low contract coverage?'] },
  'supplier-risk': { topic: 'supplier-risk', suggestions: ['Which high-spend suppliers are the biggest risk?', 'How much spend is exposed to single-source suppliers?'] },
  sustainability: { topic: 'sustainability', suggestions: ['Which high-spend suppliers are ESG laggards?', 'How could we grow diverse-supplier spend?'] },
  savings: { topic: 'savings', suggestions: ['Which savings opportunities should we prioritise?', 'How much identified savings is still unrealised?'] },
  contracts: { topic: 'contracts', suggestions: ['Where is maverick spend highest?', 'Which suppliers should we put under contract first?'] },
  'purchase-orders': { topic: 'purchase-orders', suggestions: ['Which buyers place the most off-contract spend?', 'Are any large PO lines unusual?'] },
};

const PAGE_COMPONENTS: Record<string, React.FC> = {
  'ask-cortex': AskCortexPage,
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
  const { currency } = useFilters();
  return (
    <div className="min-h-screen bg-gray-50">
      <Sidebar activePage={activePage} onNavigate={setActivePage} />
      <main className="ml-64 min-h-screen p-6">
        <div className="mb-6 flex items-center gap-3">
          <Icon className="h-6 w-6 text-sf-primary" />
          <h1 className="text-2xl font-bold text-sf-deeper">{navItem.label}</h1>
        </div>
        {ASK[activePage] && (
          <div className="mb-6">
            <AskCortex key={`${activePage}-${currency}`} topic={ASK[activePage].topic}
              label={`Ask Cortex about ${navItem.label}`} suggestions={ASK[activePage].suggestions} />
          </div>
        )}
        {PageComponent ? <PageComponent key={currency} /> : null}
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
