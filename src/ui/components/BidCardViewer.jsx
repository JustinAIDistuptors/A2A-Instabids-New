"use client";

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { 
  AlertCircle, 
  Calendar, 
  DollarSign, 
  MapPin, 
  Tag, 
  Tool, 
  Users, 
  Clock, 
  Edit, 
  Trash2 
} from 'lucide-react';
import { useToast } from "@/components/ui/use-toast";
import { formatCurrency, formatDate } from '@/lib/utils';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";

/**
 * BidCardViewer component for displaying bid card details
 * 
 * @param {Object} props - Component props
 * @param {string} props.bidCardId - ID of the bid card to display
 * @param {boolean} props.isOwner - Whether the current user is the owner of the bid card
 * @param {Function} props.onEdit - Function to call when the edit button is clicked
 * @param {Function} props.onDelete - Function to call when the delete button is clicked
 */
export default function BidCardViewer({ 
  bidCardId, 
  isOwner = false,
  onEdit,
  onDelete
}) {
  const [bidCard, setBidCard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  
  const router = useRouter();
  const { toast } = useToast();

  // Fetch bid card data
  useEffect(() => {
    const fetchBidCard = async () => {
      try {
        setLoading(true);
        const response = await fetch(`/api/bid-cards/${bidCardId}`);
        
        if (!response.ok) {
          throw new Error(`Failed to fetch bid card: ${response.statusText}`);
        }
        
        const data = await response.json();
        setBidCard(data);
      } catch (err) {
        console.error('Error fetching bid card:', err);
        setError(err.message);
        toast({
          title: "Error",
          description: `Could not load bid card: ${err.message}`,
          variant: "destructive",
        });
      } finally {
        setLoading(false);
      }
    };
    
    if (bidCardId) {
      fetchBidCard();
    }
  }, [bidCardId, toast]);

  // Handle delete confirmation
  const handleDeleteConfirm = async () => {
    try {
      const response = await fetch(`/api/bid-cards/${bidCardId}`, {
        method: 'DELETE',
      });
      
      if (!response.ok) {
        throw new Error(`Failed to delete bid card: ${response.statusText}`);
      }
      
      toast({
        title: "Success",
        description: "Bid card deleted successfully",
      });
      
      // Close dialog and call onDelete callback
      setDeleteDialogOpen(false);
      if (onDelete) {
        onDelete(bidCardId);
      } else {
        // Navigate back if no callback provided
        router.push('/projects');
      }
    } catch (err) {
      console.error('Error deleting bid card:', err);
      toast({
        title: "Error",
        description: `Could not delete bid card: ${err.message}`,
        variant: "destructive",
      });
    }
  };

  // Handle edit button click
  const handleEdit = () => {
    if (onEdit) {
      onEdit(bidCardId, bidCard);
    } else {
      router.push(`/bid-cards/${bidCardId}/edit`);
    }
  };

  // Loading state
  if (loading) {
    return (
      <Card className="w-full">
        <CardContent className="pt-6">
          <div className="flex items-center justify-center h-40">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Error state
  if (error) {
    return (
      <Card className="w-full border-destructive">
        <CardContent className="pt-6">
          <div className="flex flex-col items-center justify-center h-40 text-center">
            <AlertCircle className="h-12 w-12 text-destructive mb-4" />
            <p className="text-destructive font-semibold">Error loading bid card</p>
            <p className="text-muted-foreground text-sm mt-2">{error}</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  // No bid card found
  if (!bidCard) {
    return (
      <Card className="w-full">
        <CardContent className="pt-6">
          <div className="flex flex-col items-center justify-center h-40 text-center">
            <AlertCircle className="h-12 w-12 text-muted-foreground mb-4" />
            <p className="font-semibold">Bid card not found</p>
            <p className="text-muted-foreground text-sm mt-2">The requested bid card could not be found</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Format budget range
  const budgetDisplay = bidCard.budget_min && bidCard.budget_max
    ? `${formatCurrency(bidCard.budget_min)} - ${formatCurrency(bidCard.budget_max)}`
    : bidCard.budget_min
      ? `From ${formatCurrency(bidCard.budget_min)}`
      : bidCard.budget_max
        ? `Up to ${formatCurrency(bidCard.budget_max)}`
        : 'Not specified';

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex justify-between items-start">
          <div>
            <CardTitle className="text-xl">{bidCard.job_type}</CardTitle>
            <CardDescription className="mt-1">
              Created {formatDate(bidCard.created_at)}
            </CardDescription>
          </div>
          <Badge variant={getCategoryVariant(bidCard.category)} className="capitalize">
            {bidCard.category}
          </Badge>
        </div>
      </CardHeader>
      
      <CardContent>
        <Tabs defaultValue="details" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="details">Details</TabsTrigger>
            <TabsTrigger value="additional">Additional Info</TabsTrigger>
          </TabsList>
          
          <TabsContent value="details" className="space-y-4 mt-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="flex items-start space-x-2">
                <DollarSign className="h-5 w-5 text-muted-foreground shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium">Budget Range</p>
                  <p className="text-muted-foreground">{budgetDisplay}</p>
                </div>
              </div>
              
              <div className="flex items-start space-x-2">
                <Clock className="h-5 w-5 text-muted-foreground shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium">Timeline</p>
                  <p className="text-muted-foreground">{bidCard.timeline || 'Not specified'}</p>
                </div>
              </div>
              
              <div className="flex items-start space-x-2">
                <MapPin className="h-5 w-5 text-muted-foreground shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium">Location</p>
                  <p className="text-muted-foreground">{bidCard.location || 'Not specified'}</p>
                </div>
              </div>
              
              <div className="flex items-start space-x-2">
                <Users className="h-5 w-5 text-muted-foreground shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium">Group Bidding</p>
                  <p className="text-muted-foreground">{bidCard.group_bidding ? 'Enabled' : 'Disabled'}</p>
                </div>
              </div>
            </div>
            
            <Separator className="my-4" />
            
            <div className="flex items-start space-x-2">
              <Tool className="h-5 w-5 text-muted-foreground shrink-0 mt-0.5" />
              <div>
                <p className="font-medium">Job Type</p>
                <p className="text-muted-foreground">{bidCard.job_type}</p>
              </div>
            </div>
          </TabsContent>
          
          <TabsContent value="additional" className="space-y-4 mt-4">
            {Object.keys(bidCard.details || {}).length > 0 ? (
              <div className="grid grid-cols-1 gap-4">
                {Object.entries(bidCard.details).map(([key, value]) => (
                  <div key={key} className="flex items-start space-x-2">
                    <Tag className="h-5 w-5 text-muted-foreground shrink-0 mt-0.5" />
                    <div>
                      <p className="font-medium capitalize">{key.replace(/_/g, ' ')}</p>
                      <p className="text-muted-foreground">
                        {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-6 text-muted-foreground">
                No additional details available
              </div>
            )}
          </TabsContent>
        </Tabs>
      </CardContent>
      
      {isOwner && (
        <CardFooter className="flex justify-end space-x-2">
          <Button variant="outline" size="sm" onClick={handleEdit}>
            <Edit className="h-4 w-4 mr-2" />
            Edit
          </Button>
          
          <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
            <DialogTrigger asChild>
              <Button variant="destructive" size="sm">
                <Trash2 className="h-4 w-4 mr-2" />
                Delete
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Delete Bid Card</DialogTitle>
                <DialogDescription>
                  Are you sure you want to delete this bid card? This action cannot be undone.
                </DialogDescription>
              </DialogHeader>
              <DialogFooter>
                <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
                  Cancel
                </Button>
                <Button variant="destructive" onClick={handleDeleteConfirm}>
                  Delete
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </CardFooter>
      )}
    </Card>
  );
}

// Helper function to get badge variant based on category
function getCategoryVariant(category) {
  const variants = {
    repair: "destructive",
    renovation: "default",
    installation: "secondary",
    maintenance: "outline",
    construction: "accent",
    other: "secondary"
  };
  
  return variants[category?.toLowerCase()] || "default";
}