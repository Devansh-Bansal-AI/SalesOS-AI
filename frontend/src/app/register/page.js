// ============================================================
// SalesOS AI — Register Page
// ============================================================

'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useAuth, AuthProvider } from '@/lib/auth';

function RegisterForm() {
  const { register, isLoading, error } = useAuth();
  const [form, setForm] = useState({
    organization_name: '',
    first_name: '',
    last_name: '',
    email: '',
    password: '',
  });

  const handleChange = (e) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await register(form);
    } catch {
      // Error handled by auth context
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-container">
        <div className="auth-logo">
          <h1>SalesOS AI</h1>
          <p>Create your organization</p>
        </div>

        <div className="auth-card">
          <form className="auth-form" onSubmit={handleSubmit}>
            <div className="input-group">
              <label htmlFor="organization_name">Organization Name</label>
              <input
                id="organization_name"
                name="organization_name"
                type="text"
                className="input"
                placeholder="Acme Inc."
                value={form.organization_name}
                onChange={handleChange}
                required
                autoFocus
              />
            </div>

            <div className="flex gap-4">
              <div className="input-group" style={{ flex: 1 }}>
                <label htmlFor="first_name">First Name</label>
                <input
                  id="first_name"
                  name="first_name"
                  type="text"
                  className="input"
                  placeholder="John"
                  value={form.first_name}
                  onChange={handleChange}
                  required
                />
              </div>
              <div className="input-group" style={{ flex: 1 }}>
                <label htmlFor="last_name">Last Name</label>
                <input
                  id="last_name"
                  name="last_name"
                  type="text"
                  className="input"
                  placeholder="Doe"
                  value={form.last_name}
                  onChange={handleChange}
                  required
                />
              </div>
            </div>

            <div className="input-group">
              <label htmlFor="reg-email">Email</label>
              <input
                id="reg-email"
                name="email"
                type="email"
                className="input"
                placeholder="john@acme.com"
                value={form.email}
                onChange={handleChange}
                required
              />
            </div>

            <div className="input-group">
              <label htmlFor="reg-password">Password</label>
              <input
                id="reg-password"
                name="password"
                type="password"
                className="input"
                placeholder="Min 8 characters"
                value={form.password}
                onChange={handleChange}
                required
                minLength={8}
              />
            </div>

            {error && <p className="error-text">{error}</p>}

            <button
              type="submit"
              className="btn btn-primary btn-lg w-full"
              disabled={isLoading}
            >
              {isLoading ? 'Creating…' : 'Create Organization'}
            </button>
          </form>
        </div>

        <div className="auth-footer">
          Already have an account?{' '}
          <Link href="/login">Sign in</Link>
        </div>
      </div>
    </div>
  );
}

export default function RegisterPage() {
  return (
    <AuthProvider>
      <RegisterForm />
    </AuthProvider>
  );
}
