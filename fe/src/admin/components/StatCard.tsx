interface StatCardProps {
  label: string;
  value: string;
  description?: string;
}

export function StatCard({ label, value, description }: StatCardProps) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-5">
      <dt className="text-sm font-medium text-gray-500 mb-1">{label}</dt>
      <dd className="text-3xl font-bold text-gray-900">{value}</dd>
      {description !== undefined && <p className="text-sm text-gray-400 mt-1">{description}</p>}
    </div>
  );
}
