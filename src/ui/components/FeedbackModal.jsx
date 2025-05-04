/**
 * FeedbackModal component for collecting user feedback.
 * 
 * This component provides a modal interface for users to rate their experience
 * and submit comments. It handles the submission to the feedback API endpoint.
 */
import React, { useState } from "react";
import PropTypes from "prop-types";

/**
 * Feedback modal component
 * 
 * @param {Object} props - Component props
 * @param {string} props.userId - User ID for feedback submission
 * @returns {JSX.Element} Rendered component
 */
export default function FeedbackModal({ userId }) {
  // State for modal visibility and form values
  const [open, setOpen] = useState(false);
  const [rating, setRating] = useState(5);
  const [comment, setComment] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);
  
  /**
   * Handle feedback submission
   */
  const send = async () => {
    try {
      setIsSubmitting(true);
      setError(null);
      
      // Send feedback to API
      const response = await fetch("/api/feedback/", {
        method: "POST",
        body: JSON.stringify({ 
          user_id: userId, 
          rating, 
          comments: comment 
        }),
        headers: { 
          "Content-Type": "application/json" 
        },
      });
      
      // Handle response
      if (!response.ok) {
        throw new Error("Failed to submit feedback");
      }
      
      // Close modal on success
      setOpen(false);
      
      // Reset form
      setRating(5);
      setComment("");
    } catch (err) {
      // Handle error
      setError(err.message || "An error occurred");
    } finally {
      setIsSubmitting(false);
    }
  };
  
  /**
   * Handle modal close
   */
  const handleClose = () => {
    setOpen(false);
    setError(null);
  };
  
  return (
    <>
      {/* Feedback button */}
      <button 
        onClick={() => setOpen(true)} 
        className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded transition-colors"
        aria-label="Open feedback form"
      >
        Feedback
      </button>
      
      {/* Modal overlay */}
      {open && (
        <div 
          className="fixed inset-0 grid place-items-center bg-black/50 z-50"
          onClick={handleClose}
          role="dialog"
          aria-modal="true"
          aria-labelledby="feedback-title"
        >
          {/* Modal content */}
          <div 
            className="bg-white p-6 rounded-lg shadow-xl max-w-md w-full mx-4"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal header */}
            <h2 
              id="feedback-title"
              className="text-xl font-semibold mb-4 text-gray-800"
            >
              Rate your experience
            </h2>
            
            {/* Rating input */}
            <div className="mb-4">
              <label htmlFor="rating" className="block text-sm font-medium text-gray-700 mb-1">
                Rating (1-5)
              </label>
              <div className="flex items-center">
                {[1, 2, 3, 4, 5].map((value) => (
                  <button
                    key={value}
                    type="button"
                    className={`h-10 w-10 mx-1 rounded-full flex items-center justify-center ${
                      rating >= value 
                        ? 'bg-yellow-400 text-yellow-800' 
                        : 'bg-gray-200 text-gray-600'
                    }`}
                    onClick={() => setRating(value)}
                    aria-label={`Rate ${value} out of 5`}
                    aria-pressed={rating === value}
                  >
                    {value}
                  </button>
                ))}
              </div>
            </div>
            
            {/* Comment textarea */}
            <div className="mb-4">
              <label htmlFor="comment" className="block text-sm font-medium text-gray-700 mb-1">
                Comments (optional)
              </label>
              <textarea 
                id="comment"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={comment} 
                onChange={(e) => setComment(e.target.value)}
                rows="4"
                placeholder="Tell us about your experience..."
              />
            </div>
            
            {/* Error message */}
            {error && (
              <div className="mb-4 p-2 bg-red-100 text-red-700 rounded">
                {error}
              </div>
            )}
            
            {/* Action buttons */}
            <div className="flex justify-end space-x-2">
              <button 
                onClick={handleClose}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                disabled={isSubmitting}
              >
                Cancel
              </button>
              <button 
                onClick={send} 
                className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-md disabled:opacity-50"
                disabled={isSubmitting}
              >
                {isSubmitting ? 'Submitting...' : 'Submit'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

// PropTypes for type checking
FeedbackModal.propTypes = {
  userId: PropTypes.string.isRequired
};