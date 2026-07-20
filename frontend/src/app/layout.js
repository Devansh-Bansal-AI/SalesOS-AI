import './globals.css';

export const metadata = {
  title: 'SalesOS AI — Multi-Agent Sales Operations Platform',
  description: 'AI-powered sales workspace for lead qualification, conversation intelligence, meeting scheduling, and CRM management.',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
