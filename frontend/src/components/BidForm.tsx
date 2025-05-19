/* eslint-disable no-unused-vars */
"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import * as z from "zod";

import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { toast } from "sonner"; // Assuming sonner is set up for notifications (Sprint 5)

const bidFormSchema = z.object({
  projectTitle: z.string().min(5, { message: "Project title must be at least 5 characters." }),
  category: z.string({ required_error: "Please select a category." }),
  jobType: z.string().min(3, { message: "Job type must be at least 3 characters." }),
  detailedDescription: z.string().min(20, { message: "Description must be at least 20 characters." }),
  location: z.string().min(5, { message: "Please enter at least a 5-digit ZIP code." }), // Basic validation for ZIP
  timeline: z.string().min(3, { message: "Please provide a timeline expectation." }),
  budgetMax: z.coerce.number().optional(), // Coerce to number, optional
  allowGroupBidding: z.boolean(), // Removed .default(false), react-hook-form's defaultValues will handle it
});

export type BidFormValues = z.infer<typeof bidFormSchema>;

// Predefined categories for the select dropdown
const categories = [
  { value: "repair", label: "Repair" },
  { value: "new_project", label: "New Project" },
  { value: "continual_service", label: "Continual Service" },
  { value: "handyman", label: "Handyman" },
  { value: "labor_only", label: "Labor Only" },
  { value: "emergency", label: "Emergency" },
];

export function BidForm() {
  const form = useForm<BidFormValues>({
    resolver: zodResolver(bidFormSchema),
    defaultValues: {
      projectTitle: "",
      category: "", // Changed from undefined to empty string for required string field
      jobType: "",
      detailedDescription: "",
      location: "",
      timeline: "",
      budgetMax: undefined, // Explicitly undefined for optional number
      allowGroupBidding: false, // Explicitly set to match Zod default
    },
  });

  async function onSubmit(data: BidFormValues) {
    console.log("BidForm submitted:", data);
    try {
      const response = await fetch('http://localhost:8000/bids', { 
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        let errorMessage = 'Failed to submit bid. Please try again.';
        try {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorMessage; 
        } catch (e) {
          errorMessage = `Failed to submit bid. Status: ${response.status}`;
        }
        throw new Error(errorMessage);
      }

      toast.success("Bid request submitted successfully!");
      form.reset(); 
    } catch (error) {
      console.error("Error submitting bid:", error);
      const message = error instanceof Error ? error.message : "An unknown error occurred.";
      toast.error(message);
    }
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
        <FormField
          control={form.control}
          name="projectTitle"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Project Title / Summary</FormLabel>
              <FormControl>
                <Input placeholder="e.g., Kitchen Remodel" {...field} />
              </FormControl>
              <FormDescription>
                A brief title for your project or bid request.
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="category"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Category</FormLabel>
              <Select onValueChange={field.onChange} defaultValue={field.value}>
                <FormControl>
                  <SelectTrigger>
                    <SelectValue placeholder="Select a project category" />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  {categories.map((cat) => (
                    <SelectItem key={cat.value} value={cat.value}>
                      {cat.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <FormDescription>
                What type of project is this?
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="jobType"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Job Type / Specifics</FormLabel>
              <FormControl>
                <Input placeholder="e.g., Interior Painting, Weekly Lawn Mowing" {...field} />
              </FormControl>
              <FormDescription>
                Describe the specific job or service required.
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="detailedDescription"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Detailed Description</FormLabel>
              <FormControl>
                <Textarea
                  placeholder="Please describe the project in detail. Include scope, materials (if known), desired outcome, etc."
                  className="resize-none"
                  rows={5}
                  {...field}
                />
              </FormControl>
              <FormDescription>
                The more detail, the better the agent can assist.
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="location"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Project Location (ZIP Code or Full Address)</FormLabel>
              <FormControl>
                <Input placeholder="e.g., 90210 or 123 Main St, Anytown, USA" {...field} />
              </FormControl>
              <FormDescription>
                Please provide at least the ZIP code for the project location.
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="timeline"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Timeline Expectation</FormLabel>
              <FormControl>
                <Input placeholder="e.g., ASAP, Within 2 weeks, Flexible" {...field} />
              </FormControl>
              <FormDescription>
                When do you need this project completed by?
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="budgetMax"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Maximum Budget (Optional)</FormLabel>
              <FormControl>
                <Input type="number" placeholder="e.g., 1500" {...field} onChange={event => field.onChange(+event.target.value)} />
              </FormControl>
              <FormDescription>
                What is the maximum amount you are willing to spend? (Enter numbers only)
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="allowGroupBidding"
          render={({ field }) => (
            <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
              <div className="space-y-0.5">
                <FormLabel className="text-base">Allow Group Bidding?</FormLabel>
                <FormDescription>
                  Allow multiple contractors to bid on this project together as a group.
                </FormDescription>
              </div>
              <FormControl>
                <Switch
                  checked={field.value}
                  onCheckedChange={field.onChange}
                />
              </FormControl>
            </FormItem>
          )}
        />

        <Button type="submit">Submit Bid Request</Button>
      </form>
    </Form>
  );
}
