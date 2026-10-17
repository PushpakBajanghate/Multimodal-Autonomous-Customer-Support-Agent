'use client';

import React, { useState } from 'react';
import { CustomerOrderSummary } from '../../types/chat';

interface DemoOrdersPanelProps {
  orders: CustomerOrderSummary[];
  onSelectOrder: (text: string) => void;
}

export const DemoOrdersPanel: React.FC<DemoOrdersPanelProps> = ({ orders, onSelectOrder }) => {
  const [open, setOpen] = useState(true);
  if (orders.length === 0) return null;

  return (
    <div className="border-b border-[#ece9f4] bg-[#fbfaff] px-4 py-2.5 sm:px-8">
      <div className="mx-auto max-w-[1100px]">
        <button type="button" onClick={() => setOpen(value => !value)} className="flex w-full items-center justify-between text-left">
          <span className="text-[10px] font-bold uppercase tracking-[.14em] text-[#7868cb]">Demo order IDs · click an order to track</span>
          <span className="text-xs text-[#8f88a5]">{open ? 'Hide' : `Show ${orders.length}`}</span>
        </button>
        {open && (
          <div className="mt-2 flex gap-1.5 overflow-x-auto pb-0.5 no-scrollbar">
            {orders.map(order => (
              <button
                key={order.id}
                type="button"
                onClick={() => onSelectOrder(`Please track the status of my order #${order.id}`)}
                className="shrink-0 rounded-lg border border-[#e5e0f2] bg-white px-2.5 py-1.5 text-left shadow-sm transition hover:border-[#b9aef0] hover:bg-[#f7f5ff]"
                title={order.items[0]?.product_name || `Order #${order.id}`}
              >
                <span className="block text-[11px] font-bold text-[#514975]">#{order.id}</span>
                <span className="block text-[9px] capitalize text-[#918aa4]">{order.status} · ₹{order.total_amount.toLocaleString('en-IN')}</span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
