"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { apiClient } from "@/lib/api";
import { LoginRequest } from "@/types";
import toast from "react-hot-toast";

export default function LoginPage() {
  const [formData, setFormData] = useState<LoginRequest>({
    email: "",
    password: "",
  });
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const response = await apiClient.login(formData);
      toast.success("Login successful!");
      router.push("/");
    } catch (error: any) {
      console.error("Login error:", error);
      toast.error(error.response?.data?.detail || "Login failed");
    } finally {
      setIsLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData((prev) => ({
      ...prev,
      [e.target.name]: e.target.value,
    }));
  };

  // Demo credentials for testing - these should match your FastAPI backend
  const fillDemoCredentials = () => {
    setFormData({
      email: "admin@example.com", // Update this to match your backend demo data
      password: "password123", // Update this to match your backend demo data
    });
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            Sign in to GuzoSync
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Real-time bus tracking system
          </p>
        </div>
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          <div className="rounded-md shadow-sm -space-y-px">
            <div>
              <label htmlFor="email" className="sr-only">
                Email address
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-t-md focus:outline-none focus:ring-primary-500 focus:border-primary-500 focus:z-10 sm:text-sm"
                placeholder="Email address"
                value={formData.email}
                onChange={handleChange}
              />
            </div>
            <div>
              <label htmlFor="password" className="sr-only">
                Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                required
                className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-b-md focus:outline-none focus:ring-primary-500 focus:border-primary-500 focus:z-10 sm:text-sm"
                placeholder="Password"
                value={formData.password}
                onChange={handleChange}
              />
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={isLoading}
              className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? "Signing in..." : "Sign in"}
            </button>
          </div>

          <div className="text-center">
            <button
              type="button"
              onClick={fillDemoCredentials}
              className="text-sm text-primary-600 hover:text-primary-500"
            >
              Fill demo credentials
            </button>
          </div>
        </form>

        <div className="mt-6 p-4 bg-blue-50 rounded-md">
          <h3 className="text-sm font-medium text-blue-800 mb-2">
            Demo Credentials:
          </h3>
          <div className="text-xs text-blue-700 space-y-1">
            <p>
              <strong>Note:</strong> Use credentials from your FastAPI backend
              database
            </p>
            <p>
              Check your backend's demo data or create users via registration
            </p>
            <p>
              <strong>Default:</strong> admin@example.com / password123
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
