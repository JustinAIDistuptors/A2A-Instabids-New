import React from "react";

export default function BidCardPreview({ card }) {
  if (!card) return null;
  return (
    <div className="rounded-xl shadow p-4 border bg-white max-w-xl">
      <h2 className="text-xl font-semibold mb-2">{card.scope_json.title}</h2>
      <p className="mb-2">{card.scope_json.description}</p>
      <div className="text-sm text-gray-500">
        <span className="mr-2">Category: {card.category}</span>
        <span>Status: {card.status}</span>
      </div>
    </div>
  );
}