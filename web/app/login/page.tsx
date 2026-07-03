import { Suspense } from "react";
import LoginForm from "./LoginForm";

export default function LoginPage() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-8 w-full max-w-sm">
        <h1 className="text-xl font-bold text-gray-800 mb-1">ControlGastos</h1>
        <p className="text-sm text-gray-500 mb-6">Entre para ver seus gastos</p>
        <Suspense>
          <LoginForm />
        </Suspense>
      </div>
    </div>
  );
}
