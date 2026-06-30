import { clsx } from "clsx";

interface CardProps {
  title: string;
  value: string;
  subtitle?: string;
  className?: string;
}

export default function Card({ title, value, subtitle, className }: CardProps) {
  return (
    <div className={clsx("bg-white rounded-xl shadow-sm border border-gray-100 p-5", className)}>
      <p className="text-sm text-gray-500 font-medium">{title}</p>
      <p className="text-2xl font-bold mt-1">{value}</p>
      {subtitle && <p className="text-xs text-gray-400 mt-1">{subtitle}</p>}
    </div>
  );
}
