interface PriceTagProps {
  price: number | null;
  currency?: string;
}

export default function PriceTag({ price, currency = "GEL" }: PriceTagProps) {
  if (price === null || price === undefined) {
    return <span className="text-neutral-400 text-sm">N/A</span>;
  }

  const symbol = currency === "GEL" ? "₾" : currency;

  return (
    <span className="font-semibold text-amber-600 dark:text-amber-400">
      {symbol} {Number(price).toFixed(2)}
    </span>
  );
}
