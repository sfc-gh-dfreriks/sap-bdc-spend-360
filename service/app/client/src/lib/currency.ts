// Reporting currency for every money figure in the app. PO spend is stored in
// document currency (USD/EUR/JPY); the server converts each PO line at the ECB
// reference rate for its PO date. The active value is module-level so the data
// layer and formatters can read it without threading it through every page.
export const CURRENCIES = ['USD', 'EUR', 'JPY'] as const;
export type Currency = (typeof CURRENCIES)[number];

const SYMBOL: Record<Currency, string> = { USD: '$', EUR: '€', JPY: '¥' };

let active: Currency = 'USD';
export const getCurrency = () => active;
export const setCurrency = (c: Currency) => { active = c; };
export const currencySymbol = (c: Currency = active) => SYMBOL[c];
