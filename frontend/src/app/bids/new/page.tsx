"use client"; // The BidForm is a client component

import { BidForm } from "@/components/BidForm"; // Adjust path if necessary

export default function NewBidPage() {
  return (
    <div className="container mx-auto py-10 px-4">
      <header className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-gray-100">
          Create New Bid Request
        </h1>
        <p className="mt-2 text-lg text-gray-600 dark:text-gray-400">
          Fill out the details below to submit a new bid request. Our agents will get to work for you!
        </p>
      </header>
      
      <main>
        <div className="max-w-2xl mx-auto">
          <BidForm />
        </div>
      </main>
    </div>
  );
}
