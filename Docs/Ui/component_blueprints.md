# Component Blueprints 📐

> One‑pager reference for frequently used UI widgets.
> Each entry links to code in `/components/ui/`.

| Component | Path | Purpose | States to handle |
|-----------|------|---------|------------------|
| **AgentChat** | `/components/ui/agent-chat.tsx` | Streamed conversation w/ `useChat` | loading, streaming, error |
| **BidCard** | `/components/ui/bid-card.tsx` | Display contractor bid summary | pending, updated, accepted, rejected |
| **Timeline** | `/components/ui/timeline.tsx` | Persistent agent action log | collapsed, expanded |
| **ProgressStepper** | `/components/ui/progress-stepper.tsx` | Visual workflow stage tracker | current, completed, blocked |
| **ToastCenter** | `/components/ui/toast-center.tsx` | Multiplexed notifications | info, success, warning, error |

### Example: BidCard (props & markup)
```tsx
export interface BidCardProps {
  contractor: string
  price: number            // in cents
  status: 'pending' | 'accepted' | 'rejected'
  submittedAt: string      // ISO timestamp
  onSelect?: () => void
}
