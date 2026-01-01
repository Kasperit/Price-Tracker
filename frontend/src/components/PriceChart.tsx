import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { PriceHistory } from '../api';

interface PriceChartProps {
  history: PriceHistory[];
}

function PriceChart({ history }: PriceChartProps) {
  // Sort by date ascending for the chart
  const sortedHistory = [...history].sort(
    (a, b) => new Date(a.scraped_at).getTime() - new Date(b.scraped_at).getTime()
  );

  const data = sortedHistory.map((item) => ({
    date: new Date(item.scraped_at).toLocaleDateString('fi-FI', {
      year: 'numeric',
      month: 'short',
    }),
    price: item.price,
    originalPrice: item.original_price,
  }));

  const prices = sortedHistory.map((h) => h.price);
  const minPrice = Math.min(...prices);
  const maxPrice = Math.max(...prices);
  const avgPrice = prices.reduce((a, b) => a + b, 0) / prices.length;

  // Add some padding to Y axis
  const yMin = Math.floor(minPrice * 0.95);
  const yMax = Math.ceil(maxPrice * 1.05);

  const formatPrice = (value: number) => `${value.toFixed(0)}€`;

  if (history.length === 0) {
    return (
      <div className="empty-state">
        No price history available yet
      </div>
    );
  }

  return (
    <div className="price-chart-container">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={data}
          margin={{ top: 5, right: 10, left: -10, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 11, fill: '#64748b' }}
            tickLine={{ stroke: '#e2e8f0' }}
            angle={-45}
            textAnchor="end"
            height={60}
          />
          <YAxis
            domain={[yMin, yMax]}
            tickFormatter={formatPrice}
            tick={{ fontSize: 11, fill: '#64748b' }}
            tickLine={{ stroke: '#e2e8f0' }}
            width={45}
          />
          <Tooltip
            formatter={(value: number) => [formatPrice(value), 'Price']}
            contentStyle={{
              backgroundColor: 'white',
              border: '1px solid #e2e8f0',
              borderRadius: '8px',
              fontSize: '12px',
            }}
          />
          <ReferenceLine
            y={avgPrice}
            stroke="#94a3b8"
            strokeDasharray="5 5"
            label={{
              value: `Avg: ${formatPrice(avgPrice)}`,
              position: 'right',
              fontSize: 10,
              fill: '#64748b',
            }}
          />
          <Line
            type="monotone"
            dataKey="price"
            stroke="#2563eb"
            strokeWidth={2}
            dot={{ fill: '#2563eb', strokeWidth: 2, r: 3 }}
            activeDot={{ r: 5, fill: '#1d4ed8' }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export default PriceChart;
