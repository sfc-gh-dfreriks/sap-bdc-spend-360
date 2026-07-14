import React, { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import { fetchFilters } from '@/lib/api';

interface FilterContextType {
  categories: string[];
  selectedCategories: string[];
  setSelectedCategories: (v: string[]) => void;
  companies: string[];
  selectedCompanies: string[];
  setSelectedCompanies: (v: string[]) => void;
  loading: boolean;
}

const FilterContext = createContext<FilterContextType>({
  categories: [], selectedCategories: [], setSelectedCategories: () => {},
  companies: [], selectedCompanies: [], setSelectedCompanies: () => {},
  loading: true,
});

export function FilterProvider({ children }: { children: ReactNode }) {
  const [categories, setCategories] = useState<string[]>([]);
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
  const [companies, setCompanies] = useState<string[]>([]);
  const [selectedCompanies, setSelectedCompanies] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchFilters()
      .then((data) => {
        setCategories(data.categories); setSelectedCategories(data.categories);
        setCompanies(data.companies); setSelectedCompanies(data.companies);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  return React.createElement(
    FilterContext.Provider,
    { value: { categories, selectedCategories, setSelectedCategories, companies, selectedCompanies, setSelectedCompanies, loading } },
    children
  );
}

export function useFilters() { return useContext(FilterContext); }
