import Link from "next/link";
import LogoutButton from "./LogoutButton";

export default function Navbar() {
  return (
    <nav className="bg-white border-b border-gray-200 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 flex items-center gap-6 h-14">
        <Link href="/" className="font-bold text-blue-600 text-lg">
          ControlGastos
        </Link>
        <Link
          href="/"
          className="text-sm text-gray-600 hover:text-blue-600 transition-colors"
        >
          Dashboard
        </Link>
        <Link
          href="/expenses"
          className="text-sm text-gray-600 hover:text-blue-600 transition-colors"
        >
          Historico
        </Link>
        <LogoutButton />
      </div>
    </nav>
  );
}
