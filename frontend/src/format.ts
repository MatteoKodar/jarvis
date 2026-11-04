const currency = new Intl.NumberFormat('sv-SE', {
  style: 'currency', currency: 'SEK', maximumFractionDigits: 2,
});
const timestamp = new Intl.DateTimeFormat('sv-SE', {
  dateStyle: 'short', timeStyle: 'short', timeZone: 'Europe/Stockholm',
});

export const money = (ore: number) => currency.format(ore / 100);
export const date = (value: string | number) => timestamp.format(new Date(value));
